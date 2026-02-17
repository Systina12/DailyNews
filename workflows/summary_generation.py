"""
新闻摘要生成工作流
"""

from llms.build_prompt import build_headline_prompt
from llms.llms import LLMClient
from utils.link_processor import process_summary_links
from utils.merge_summaries import merge_summaries
from utils.logger import get_logger

logger = get_logger("summary_generation")


def run_summary_generation_pipeline(risk_annotated_data):
    """
    执行新闻摘要生成工作流

    Args:
        risk_annotated_data: 已标注风险等级的新闻数据，格式：
            {
                "section": "headline",
                "category": "头条/政治/财经/科技/国际",  # 可选，但建议带上
                "dateStr": "YYYY-MM-DD",               # 可选
                "items": [{"ds_risk": "low/high/unknown", ...}, ...]
            }

    Returns:
        dict:
            {
                "low_risk_summary": "...html...",
                "high_risk_summary": "...html...",
                "merged_summary": "...html...",
                "meta": {...}
            }
    """
    if not risk_annotated_data or risk_annotated_data.get("section") != "headline":
        raise ValueError("输入数据必须是 headline 类型，且 items 已包含 ds_risk")

    category = risk_annotated_data.get("category")
    date_str = risk_annotated_data.get("dateStr") or risk_annotated_data.get("date")

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
            max_tokens=4000
        )

        low_risk_summary = resp.get("content", "") or ""
        low_meta = {
            "model_used": resp.get("model_used"),
            "is_fallback": bool(resp.get("is_fallback")),
            "filter_reason": resp.get("filter_reason")
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
            max_tokens=4000
        ) or ""
        logger.info("✓ 高风险摘要生成完成")
    else:
        logger.info("高风险新闻为空，跳过高风险摘要生成")

    # ---------- 合并（先合并再替换链接，避免合并时引用重编号失效）----------
    merged_summary = merge_summaries(
        low_risk_summary,
        high_risk_summary,
        date=date_str,
        category=category,
        add_section_headers=True
    )

    # 合并后统一把 #refN 替换为真实 URL
    # 注意：低/高风险各自的 refs 编号都是从 1 开始，合并时高风险引用会被重编号，
    # 因此需要把 high_refs 的 n 也按 offset 平移后再一起替换
    all_refs = []
    offset = 0

    # 计算低风险最大引用编号 offset（与 merge_summaries 的逻辑一致：offset = low_max_ref）
    # 为简化起见：用 low_refs 的最大 n 作为 offset（如果 low 为空则 offset=0）
    if low_refs:
        offset = max(r.get("n", 0) for r in low_refs if isinstance(r.get("n"), int)) or 0

    all_refs.extend(low_refs)

    if high_refs:
        shifted_high_refs = []
        for r in high_refs:
            n = r.get("n")
            if isinstance(n, int):
                shifted = dict(r)
                shifted["n"] = n + offset
                shifted_high_refs.append(shifted)
            else:
                shifted_high_refs.append(r)
        all_refs.extend(shifted_high_refs)

    merged_summary = process_summary_links(merged_summary, all_refs)

    # 如果你仍想保留分开版本，也可以分开替换链接
    low_risk_summary = process_summary_links(low_risk_summary, low_refs) if low_risk_summary else ""
    high_risk_summary = process_summary_links(high_risk_summary, high_refs) if high_risk_summary else ""

    return {
        "low_risk_summary": low_risk_summary,
        "high_risk_summary": high_risk_summary,
        "merged_summary": merged_summary,
        "meta": {
            "category": category,
            "dateStr": date_str,
            "total_items": len(items),
            "low_items": len(low_items),
            "high_items": len(high_items),
            "low_model_used": low_meta.get("model_used"),
            "low_is_fallback": low_meta.get("is_fallback"),
            "low_filter_reason": low_meta.get("filter_reason"),
        }
    }
