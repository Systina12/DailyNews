"""
新闻摘要生成工作流
"""
import re
from datetime import datetime

from llms.build_prompt import build_headline_prompt
from llms.llms import LLMClient
from utils.link_processor import process_summary_links
from utils.merge_summaries import merge_summaries
from utils.logger import get_logger

logger = get_logger("summary_generation")


def _looks_non_chinese(html: str) -> bool:
    """
    粗略判断摘要是否明显不是中文。
    忽略 HTML 标签后，若英文字母显著多于中文字符，则认为需要重试。
    """
    if not html:
        return False

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))

    if cjk_count == 0 and latin_count > 30:
        return True

    return latin_count > cjk_count * 1.2


def _strengthen_chinese_requirement(prompt: str) -> str:
    """为摘要生成追加更强的中文输出约束。"""
    extra_rules = """

【最终输出强约束】
- 最终输出必须是简体中文 HTML
- 任何新闻内容都必须翻译成中文，不允许整段英文、俄文或其他外文直接出现在正文中
- 如果输出中出现大段外文，视为答案错误，请重写为中文
"""
    return prompt + extra_rules


def _format_html_title(category: str, date_str: str | None, hour_str: str) -> str:
    """
    输出格式：YY-MM-DD-HH-栏目
    - date_str 优先用传入的 YYYY-MM-DD；否则用当前日期
    - hour_str 用当前小时（00-23）
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 只支持 YYYY-MM-DD；不符合就回退当前日期
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", date_str.strip())
    if m:
        yy = m.group(1)[-2:]
        mm = m.group(2)
        dd = m.group(3)
    else:
        now = datetime.now()
        yy = now.strftime("%y")
        mm = now.strftime("%m")
        dd = now.strftime("%d")

    cat = (category or "unknown").strip()
    return f"{yy}-{mm}-{dd}-{hour_str}-{cat}"


def _force_h1_title(html: str, title: str) -> str:
    """
    强制把 HTML 的第一个 <h1> 改成指定 title。
    - 若没有 <h1>，则在最前面插入。
    - 支持完整HTML文档和简单HTML片段
    """
    if not html:
        return f"<h1>{title}</h1>"

    # 转义title中的HTML特殊字符
    escaped_title = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    if re.search(r"<h1[^>]*>.*?</h1>", html, flags=re.DOTALL):
        # 替换第一个h1标签（保留可能的属性）
        return re.sub(
            r"<h1[^>]*>.*?</h1>",
            f"<h1>{escaped_title}</h1>",
            html,
            count=1,
            flags=re.DOTALL
        )

    return f"<h1>{escaped_title}</h1>\n{html}"


def run_summary_generation_pipeline(risk_annotated_data):
    """
    执行新闻摘要生成工作流
    """
    if not risk_annotated_data or risk_annotated_data.get("section") != "headline":
        raise ValueError("输入数据必须是 headline 类型，且 items 已包含 ds_risk")

    category = risk_annotated_data.get("category")
    date_str = risk_annotated_data.get("dateStr") or risk_annotated_data.get("date")

    # 标题用“当前小时”（00-23）
    now_hour = datetime.now().strftime("%H")
    forced_title = _format_html_title(category or "unknown", date_str, now_hour)

    items = risk_annotated_data.get("items", [])
    low_items = [it for it in items if it.get("ds_risk") == "low"]
    high_items = [it for it in items if it.get("ds_risk") == "high"]

    logger.info(
        f"开始生成摘要，共 {len(items)} 条新闻"
        + (f"（{category}）" if category else "")
        + f"，低风险 {len(low_items)}，高风险 {len(high_items)}"
    )

    llm_client = LLMClient()

    # ---------- 低风险（DeepSeek 主，触发过滤才 fallback Gemini）----------
    low_risk_summary = ""
    low_meta = {"model_used": None, "is_fallback": False, "filter_reason": None}
    low_refs = []
    if low_items:
        low_block = {
            "section": "headline",
            "items": low_items,
        }
        if category:
            low_block["category"] = category
        if date_str:
            low_block["dateStr"] = date_str

        low_prompt_data = build_headline_prompt(low_block, risk_filter="low")
        low_refs = low_prompt_data.get("refs", [])

        logger.info("生成低风险摘要（DeepSeek 主 + fallback）...")
        resp = llm_client.request_with_fallback(
            prompt=low_prompt_data["prompt"],
            primary="deepseek",
            temperature=0.3,
            max_tokens=4000,
        )

        low_risk_summary = resp.get("content", "") or ""
        low_meta = {
            "model_used": resp.get("model_used"),
            "is_fallback": bool(resp.get("is_fallback")),
            "filter_reason": resp.get("filter_reason"),
        }

        if _looks_non_chinese(low_risk_summary):
            logger.warning("低风险摘要检测到外文占比过高，追加中文强约束后重试一次")
            retry_prompt = _strengthen_chinese_requirement(low_prompt_data["prompt"])
            retry_resp = llm_client.request_with_fallback(
                prompt=retry_prompt,
                primary="deepseek",
                temperature=0.2,
                max_tokens=4000,
            )
            low_risk_summary = retry_resp.get("content", "") or low_risk_summary
            low_meta = {
                "model_used": retry_resp.get("model_used"),
                "is_fallback": bool(retry_resp.get("is_fallback")),
                "filter_reason": retry_resp.get("filter_reason"),
            }

        logger.info(f"✓ 低风险摘要生成完成，模型: {low_meta['model_used']}, fallback: {low_meta['is_fallback']}")
    else:
        logger.info("低风险新闻为空，跳过低风险摘要生成")

    # ---------- 高风险（直接 Gemini）----------
    high_risk_summary = ""
    high_refs = []
    if high_items:
        high_block = {
            "section": "headline",
            "items": high_items,
        }
        if category:
            high_block["category"] = category
        if date_str:
            high_block["dateStr"] = date_str

        high_prompt_data = build_headline_prompt(high_block, risk_filter="high")
        high_refs = high_prompt_data.get("refs", [])

        logger.info("生成高风险摘要（Gemini）...")
        high_risk_summary = llm_client.request_gemini(
            prompt=high_prompt_data["prompt"],
            temperature=0.3,
            max_tokens=4000,
        ) or ""

        if _looks_non_chinese(high_risk_summary):
            logger.warning("高风险摘要检测到外文占比过高，追加中文强约束后重试一次")
            retry_prompt = _strengthen_chinese_requirement(high_prompt_data["prompt"])
            high_risk_summary = llm_client.request_gemini(
                prompt=retry_prompt,
                temperature=0.2,
                max_tokens=4000,
            ) or high_risk_summary

        logger.info("✓ 高风险摘要生成完成")
    else:
        logger.info("高风险新闻为空，跳过高风险摘要生成")

    # ---------- 合并（先合并再替换链接，避免合并时引用重编号失效）----------
    merged_summary = merge_summaries(
        low_risk_summary,
        high_risk_summary,
        date=date_str,
        category=category,
        add_section_headers=True,
    )

    # 合并后统一把 #refN 替换为真实 URL
    # 低/高风险各自 refs 编号从 1 开始；合并时高风险引用会被平移
    all_refs = []
    offset = 0
    
    # 添加低风险引用（编号不变）
    if low_refs:
        all_refs.extend(low_refs)
        # 计算偏移量：低风险最大编号
        offset = max(r.get("n", 0) for r in low_refs if isinstance(r.get("n"), int)) or 0

    # 添加高风险引用（编号需要加上偏移）
    if high_refs:
        for r in high_refs:
            n = r.get("n")
            if isinstance(n, int):
                shifted = dict(r)
                shifted["n"] = n + offset
                all_refs.append(shifted)
            else:
                all_refs.append(r)

    # 替换链接
    merged_summary = process_summary_links(merged_summary, all_refs)

    # 分开版本也替换链接（使用原始编号）
    low_risk_summary = process_summary_links(low_risk_summary, low_refs) if low_risk_summary else ""
    high_risk_summary = process_summary_links(high_risk_summary, high_refs) if high_risk_summary else ""

    # ✅ 统一强制标题（合并/不合并都生效）
    merged_summary = _force_h1_title(merged_summary, forced_title) if merged_summary else ""
    low_risk_summary = _force_h1_title(low_risk_summary, forced_title) if low_risk_summary else ""
    high_risk_summary = _force_h1_title(high_risk_summary, forced_title) if high_risk_summary else ""

    return {
        "low_risk_summary": low_risk_summary,
        "high_risk_summary": high_risk_summary,
        "merged_summary": merged_summary,
        "meta": {
            "category": category,
            "dateStr": date_str,
            "titleHour": now_hour,
            "forcedTitle": forced_title,
            "total_items": len(items),
            "low_items": len(low_items),
            "high_items": len(high_items),
            "low_model_used": low_meta.get("model_used"),
            "low_is_fallback": low_meta.get("is_fallback"),
            "low_filter_reason": low_meta.get("filter_reason"),
        },
    }
