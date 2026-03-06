"""
主工作流入口：新闻处理 -> 风险评估 -> 摘要生成 -> 写入文件（支持多分类 + hours 参数）
"""
import os
import argparse
from datetime import datetime

from config import settings
from monitoring.metrics import metrics
from workflows.news_pipeline import run_news_pipeline_all
from workflows.risk_assessment import run_risk_assessment_pipeline
from workflows.summary_generation import run_summary_generation_pipeline
from utils.email_sender import send_html_email
from utils.logger import get_logger

logger = get_logger("main_workflow")


def _safe_filename(s: str) -> str:
    """简单的文件名清洗：把空格/斜杠等替换掉，避免写文件失败"""
    if not s:
        return "unknown"
    bad = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
    out = s
    for ch in bad:
        out = out.replace(ch, "_")
    return out


def run_main_workflow(categories=None, hours: float = 24, test: bool = False):
    """
    运行主工作流（多分类）

    ⚠ 注意：
    - 作为库函数：保持原有行为不变（完整执行：拉取 → 分类 → 风险评估 → 摘要 → 写文件+发邮件）
    - CLI 层面的 --mode 逻辑仅影响 __main__ 分支，避免破坏既有调用方式

    Args:
        categories: 分类列表，默认 ["头条","政治","财经","科技","国际"]
        hours: 拉取最近多少小时的新闻（默认 24）
    """
    settings.ensure_directories()
    settings.validate()

    default_categories = ["头条", "政治", "财经", "科技", "国际"]
    categories = categories or default_categories

    # 用“精确到秒”的时间戳做本次运行的输出文件后缀
    run_ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    # 邮件标题只用“小时”
    hour_cn = f"{datetime.now().strftime('%H')}点"

    logger.info(f"开始主工作流，多分类: {categories}，hours={hours}")

    # 1) 获取 + 预处理 + 分类（一次拉取，多分类输出）
    logger.info("运行新闻预处理与分类...")
    blocks = run_news_pipeline_all(categories=categories, hours=hours)

    results = []
    for block in blocks:
        category = block.get("category", "unknown")
        items = block.get("items", [])

        logger.info(f"分类 [{category}] 共有 {len(items)} 条")
        if not items:
            logger.info(f"分类 [{category}] 无新闻，跳过风险评估与摘要生成")
            continue

        # 计数：处理条数（按分类累计）
        metrics.increment_counter(f"news_processed_{category}", len(items))

        # 2) 风险评估（Gemini）
        logger.info(f"分类 [{category}] 进行风险评估...")
        risk_data = run_risk_assessment_pipeline(block)

        low_count = sum(1 for it in risk_data.get("items", []) if it.get("ds_risk") == "low")
        high_count = sum(1 for it in risk_data.get("items", []) if it.get("ds_risk") == "high")
        metrics.record_risk_assessment(
            total=len(risk_data.get("items", [])),
            low=low_count,
            high=high_count,
        )

        # 3) 摘要生成
        logger.info(f"分类 [{category}] 生成摘要...")
        summaries = run_summary_generation_pipeline(risk_data)
        merged_summary = summaries.get("merged_summary", "") or ""
        meta = summaries.get("meta", {}) or {}

        # 如果低风险触发 fallback，记录一次
        if meta.get("low_is_fallback"):
            metrics.record_fallback(
                reason=meta.get("low_filter_reason") or "content_filtered",
                primary_model="deepseek",
                fallback_model="gemini",
            )

        # 4) 写入文件：每类一个 merged html（文件名精确到秒）
        date_str = meta.get("dateStr") or datetime.now().strftime("%Y-%m-%d")
        safe_cat = _safe_filename(category)
        filename = f"summary_{safe_cat}_{date_str}_{run_ts}.html"
        out_path = os.path.join(str(settings.DATA_DIR), filename)

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(merged_summary)
            logger.info(f"分类 [{category}] 输出文件: {out_path}")
        except IOError as e:
            logger.error(f"写入文件失败: {out_path}, 错误: {e}")
            raise RuntimeError(f"写入文件失败: {e}")
        results.append(
            {
                "category": category,
                "output_path": out_path,
                "meta": meta,
            }
        )

        # ✅ 发送邮件：标题不带日期，只要小时
        try:
            subject = f"{hour_cn}-{category}"
            send_html_email(subject=subject, html_body=merged_summary, test_mode=test)
            logger.info(
                f"分类 [{category}] 邮件已发送，subject={subject}, test_mode={test}"
            )
        except Exception as e:
            logger.warning(f"分类 [{category}] 邮件发送失败: {e}，继续处理其他任务")

    # 5) 打印指标摘要
    metrics.print_summary()

    return {
        "results": results,
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "categories": categories,
            "hours": float(hours),
        },
    }


def run_realtime_workflow(categories=None, hours: float = 1, importance_threshold: int = 80, test: bool = False):
    """
    实时监控工作流（轻量版，供 crontab 每 N 分钟调用）

    功能：
    - 拉取 → 预处理 → 多分类
    - LLM 评分检测重要新闻
    - 发现高分新闻（≥threshold）立即发送通知邮件
    - 不做风险评估、不生成完整摘要（避免与主工作流重复）

    Args:
        categories: 分类列表
        hours: 拉取最近多少小时的新闻（默认 1 小时）
        importance_threshold: 重要性阈值（默认 80 分）
        test: 测试模式，邮件发送到 TEST_EMAIL
    """
    settings.ensure_directories()
    settings.validate()

    default_categories = ["头条", "政治", "财经", "科技", "国际"]
    categories = categories or default_categories

    logger.info(
        f"开始实时监控工作流（realtime），多分类: {categories}，hours={hours}，阈值={importance_threshold}，test={test}"
    )

    # 1. 拉取和分类
    blocks = run_news_pipeline_all(categories=categories, hours=hours)

    # 2. 检测重要新闻
    from llms.llms import LLMClient
    from workflows.news_pipeline import score_news_importance
    
    llm_client = LLMClient()
    important_news = []
    
    for block in blocks:
        cat = block.get("category", "unknown")
        items = block.get("items") or []
        
        if not items:
            logger.info(f"[{cat}] 无新闻，跳过评分")
            continue
            
        logger.info(f"[{cat}] 评分 {len(items)} 条新闻...")
        
        try:
            # LLM 批量评分
            items_with_scores = score_news_importance(items, llm_client)
            
            # 筛选高分新闻
            for item, score in items_with_scores:
                if score >= importance_threshold:
                    # 生成中文摘要（如果原文不是中文）
                    title = item.get("title", "")
                    original_summary = item.get("summaryText", "")[:300]
                    link = item.get("link", "")
                    
                    # 使用LLM生成精炼的中文摘要
                    try:
                        summary_prompt = f"""请将以下新闻翻译成中文（如果不是中文），并提炼成1-2句话的精炼摘要（50-80字）。

标题：{title}
原文摘要：{original_summary}

要求：
1. 如果是中文，直接提炼摘要
2. 如果是外文，先翻译再提炼
3. 保留关键信息（人物、地点、事件、影响）
4. 语言简洁、客观、准确
5. 只返回摘要内容本身，不要任何标记、标题、说明文字
6. 不要包含"摘要："、"翻译："、"**"等标记

直接输出摘要："""
                        
                        refined_summary = llm_client.request_gemini_flash(
                            prompt=summary_prompt,
                            temperature=0.3,
                            max_tokens=200
                        ).strip()
                        
                        # 清理可能的格式标记
                        refined_summary = refined_summary.replace("**摘要：**", "").replace("**翻译：**", "")
                        refined_summary = refined_summary.replace("摘要：", "").replace("翻译：", "")
                        refined_summary = refined_summary.replace("**", "").strip()
                        
                        # 翻译标题（如果需要）
                        title_prompt = f"""将以下新闻标题翻译成中文（如果已经是中文则保持不变）：

{title}

要求：
1. 只返回翻译后的标题本身
2. 保持简洁准确
3. 不要添加任何说明、标记、引号
4. 不要包含"翻译："、"标题："等前缀

直接输出标题："""
                        
                        chinese_title = llm_client.request_gemini_flash(
                            prompt=title_prompt,
                            temperature=0.3,
                            max_tokens=100
                        ).strip()
                        
                        # 清理可能的格式标记
                        chinese_title = chinese_title.replace("**翻译：**", "").replace("**标题：**", "")
                        chinese_title = chinese_title.replace("翻译：", "").replace("标题：", "")
                        chinese_title = chinese_title.replace("**", "").replace('"', '').replace("'", "").strip()
                        
                    except Exception as e:
                        logger.error(f"生成摘要失败: {e}，使用原文")
                        refined_summary = original_summary[:200]
                        chinese_title = title
                    
                    important_news.append({
                        "category": cat,
                        "score": score,
                        "title": chinese_title,
                        "original_title": title,
                        "link": link,  # 确保链接被正确传递
                        "summary": refined_summary,
                        "published": item.get("published", ""),
                    })
                    logger.warning(f"⚠ 发现重要新闻 [{cat}] {score}分: {chinese_title[:50]}")
        
        except Exception as e:
            logger.error(f"[{cat}] 评分失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    # 3. 发送通知邮件
    if important_news:
        logger.info(f"发现 {len(important_news)} 条重要新闻，准备发送通知...")
        
        try:
            # 构建邮件内容
            html_body = _build_alert_email(important_news, importance_threshold)
            
            # 发送邮件
            hour_cn = datetime.now().strftime("%H:%M")
            subject = f"🚨 重要新闻提醒 ({hour_cn}) - {len(important_news)}条"
            
            send_html_email(subject=subject, html_body=html_body, test_mode=test)
            logger.info(f"✓ 重要新闻通知已发送（test_mode={test}）")
            
        except Exception as e:
            logger.error(f"发送通知邮件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.info("未发现重要新闻")

    # 4. 统计结果
    logger.info("=" * 60)
    logger.info("realtime 监控结果：")
    for block in blocks:
        cat = block.get("category", "unknown")
        items = block.get("items") or []
        logger.info(f"  [{cat}]: {len(items)} 条")
    logger.info(f"  重要新闻: {len(important_news)} 条")
    logger.info("=" * 60)

    return {
        "blocks": blocks,
        "important_news": important_news,
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "categories": categories,
            "hours": float(hours),
            "mode": "realtime",
            "importance_threshold": importance_threshold,
            "test_mode": test,
        },
    }


def _build_alert_email(important_news, threshold):
    """构建重要新闻提醒邮件的 HTML"""
    # 使用普通字符串拼接，避免 f-string 中的花括号问题
    html_parts = []
    
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }
        .header { background-color: #d32f2f; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .news-item { border-left: 4px solid #d32f2f; padding: 15px; margin-bottom: 15px; background-color: #fff3f3; }
        .score { display: inline-block; background-color: #d32f2f; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold; }
        .category { display: inline-block; background-color: #666; color: white; padding: 3px 8px; border-radius: 3px; margin-left: 5px; }
        .title { font-size: 16px; font-weight: bold; margin: 10px 0; color: #333; }
        .summary { color: #666; margin: 10px 0; line-height: 1.5; }
        .link { color: #1976d2; text-decoration: none; }
        .footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚨 重要新闻提醒</h2>
            <p>检测到 """ + str(len(important_news)) + """ 条重要性评分 ≥""" + str(threshold) + """ 的新闻</p>
        </div>
""")
    
    # 按评分排序
    sorted_news = sorted(important_news, key=lambda x: x["score"], reverse=True)
    
    for news in sorted_news:
        # 转义HTML特殊字符
        title = news.get('title', '无标题').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        summary = news.get('summary', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        link = news.get('link', '')
        
        # 记录链接信息（用于调试）
        logger.info(f"构建邮件项 - 标题: {title[:40]}, 链接: {link if link else '(空)'}")
        
        # 处理链接
        if not link or link.strip() == '':
            # 链接为空时，使用Google搜索作为备用
            import urllib.parse
            search_query = urllib.parse.quote(news.get('original_title', title))
            link = f"https://www.google.com/search?q={search_query}"
            link_text = "搜索原文 →"
            logger.warning(f"新闻链接为空，使用Google搜索: {title[:40]}")
        else:
            # 转义链接中的特殊字符
            link = link.replace('&', '&amp;').replace('"', '&quot;')
            link_text = "查看原文 →"
        
        html_parts.append(f"""
        <div class="news-item">
            <div>
                <span class="score">{news['score']}分</span>
                <span class="category">{news.get('category', '未知')}</span>
            </div>
            <div class="title">{title}</div>
            <div class="summary">{summary}</div>
            <div><a class="link" href="{link}" target="_blank">{link_text}</a></div>
        </div>
""")
    
    html_parts.append("""
        <div class="footer">
            <p>此邮件由 DailyNews 实时监控系统自动发送</p>
            <p>生成时间: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </div>
    </div>
</body>
</html>
""")
    
    return ''.join(html_parts)


def run_hourly_workflow(categories=None, hours: float = 24, test: bool = False):
    """
    小时报工作流入口。

    设计意图：
    - 为 crontab 提供一个显式的 --mode=hourly 入口
    - 当前直接复用完整主工作流逻辑（未来可在这里接入“复用缓存结果”的优化）

    Args:
        categories: 分类列表，默认同 run_main_workflow
        hours: 拉取最近多少小时的新闻（默认 24）
    """
    logger.info(
        f"以 hourly 模式运行主工作流，categories={categories or '默认'}, hours={hours}, test={test}"
    )
    return run_main_workflow(categories=categories, hours=hours, test=test)


def _parse_args():
    p = argparse.ArgumentParser(description="DailyNews 主工作流（多分类）")
    p.add_argument(
        "--hours",
        type=float,
        default=24,
        help="拉取最近多少小时的新闻，可以是小数（例如 0.25 表示 15 分钟，默认 24）",
    )
    p.add_argument(
        "--categories",
        type=str,
        default="",
        help='分类列表，逗号分隔，例如： "头条,政治,财经,科技"；不传则用默认分类',
    )
    p.add_argument(
        "--mode",
        type=str,
        default="full",
        choices=["full", "realtime", "hourly"],
        help="运行模式：full=完整流程（默认，向后兼容）；realtime=轻量预热；hourly=小时摘要",
    )
    p.add_argument(
        "--test",
        action="store_true",
        help="测试模式：只把邮件发送到 TEST_EMAIL/TEST-EMAIL 环境变量指定的地址",
    )
    p.add_argument(
        "--threshold",
        type=int,
        default=80,
        help="实时监控模式的重要性阈值（默认 80 分），只在 --mode=realtime 时生效",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    cats = [x.strip() for x in (args.categories or "").split(",") if x.strip()] or None
    if args.mode == "full":
        # 原有行为：完整跑一遍（保持向后兼容）
        run_main_workflow(categories=cats, hours=args.hours, test=args.test)
    elif args.mode == "realtime":
        # 实时监控：拉取+分类+评分+吹哨
        run_realtime_workflow(
            categories=cats, 
            hours=args.hours, 
            importance_threshold=args.threshold,
            test=args.test
        )
    elif args.mode == "hourly":
        # 小时报：当前等价于完整主流程，未来可在此复用缓存结果
        run_hourly_workflow(categories=cats, hours=args.hours, test=args.test)