"""
主工作流入口：新闻处理 -> 风险评估 -> 摘要生成 -> 写入文件（支持多分类 + hours 参数）
"""
import os
import argparse
from datetime import datetime
from typing import List, Dict

from config import settings
from monitoring.metrics import metrics
from workflows.news_pipeline import run_news_pipeline_all
from workflows.news_pipeline import _score_with_llm
from workflows.risk_assessment import run_risk_assessment_pipeline
from workflows.summary_generation import run_summary_generation_pipeline
from utils.email_sender import send_html_email
from utils.logger import get_logger
from utils.snippet import CacheManager

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


def run_main_workflow(categories=None, hours: float = 24, test: bool = False, grok_only: bool = False):
    """
    运行主工作流（多分类）

    ⚠ 注意：
    - 作为库函数：保持原有行为不变（完整执行：拉取 → 分类 → 风险评估 → 摘要 → 写文件+发邮件）
    - CLI 层面的 --mode 逻辑仅影响 __main__ 分支，避免破坏既有调用方式

    Args:
        categories: 分类列表，默认 ["头条","政治","财经","科技","军事","国际"]
        hours: 拉取最近多少小时的新闻（默认 24）
    """
    settings.ensure_directories()
    settings.set_runtime_flags(grok_only=bool(grok_only or settings.GROK_ONLY))
    settings.validate()

    default_categories = ["头条", "政治", "财经", "科技", "军事", "国际"]
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
        if not risk_data.get("risk_skipped"):
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


def run_realtime_workflow(
    categories=None,
    hours: float = 0.25,
    importance_threshold: int | None = None,
    test: bool = False,
    grok_only: bool = False,
):  # 默认15分钟
    """
    实时预热工作流（15分钟任务）
    
    流程：
    1. 拉取最近15分钟新闻
    2. 分类 + 重要性评分
    3. 保存到缓存
    4. 检查并发送吹哨告警
    """
    settings.ensure_directories()
    settings.set_runtime_flags(grok_only=bool(grok_only or settings.GROK_ONLY))
    settings.validate()

    default_categories = ["头条", "政治", "财经", "科技", "军事", "国际"]
    categories = categories or default_categories
    threshold = importance_threshold if importance_threshold is not None else settings.ALERT_THRESHOLD

    logger.info(
        f"开始实时监控工作流（realtime），多分类: {categories}，hours={hours}，阈值={threshold}，test={test}"
    )

    blocks = run_news_pipeline_all(categories=categories, hours=hours)
    cache_manager = CacheManager()

    # 运行前先清理过期缓存
    cache_manager.cleanup_old_cache()

    from llms.llms import LLMClient
    llm_client = LLMClient()

    total_processed = 0
    all_major_alerts = []

    for block in blocks:
        category = block.get("category", "unknown")
        classified_items = block.get("items", [])

        if not classified_items:
            logger.info(f"分类 [{category}] 无新闻，跳过")
            continue

        logger.info(f"分类 [{category}] 处理 {len(classified_items)} 条新闻")

        items_with_scores = _score_with_llm(classified_items, llm_client)

        if not items_with_scores:
            logger.warning(f"分类 [{category}] 评分失败")
            continue

        items = [item for item, _ in items_with_scores]
        scores = [score for _, score in items_with_scores]

        cache_manager.save_news_items(items, category, scores)
        total_processed += len(items)

        for item, score in items_with_scores:
            if score >= threshold:
                item_id = cache_manager._generate_item_id(item)
                all_major_alerts.append({
                    "id": item_id,
                    "title": item.get("title", ""),
                    "summary": item.get("summaryText", ""),
                    "category": category,
                    "importance_score": score,
                    "raw_data": item
                })
    alert_count = 0
    if all_major_alerts:
        pending_alerts = cache_manager.get_major_alerts()

        if pending_alerts:
            alert_count = len(pending_alerts)
            logger.info(f"检测到 {alert_count} 条重大新闻需要吹哨告警")

            try:
                _send_major_news_alerts(pending_alerts, threshold=threshold, test=test)
                alert_ids = [alert["id"] for alert in pending_alerts]
                cache_manager.mark_alerts_sent(alert_ids)
                logger.info(f"吹哨告警邮件已发送 ({alert_count} 条)")
            except Exception as e:
                logger.error(f"发送吹哨告警失败: {e}")
        else:
            logger.info("重大新闻已发送过告警，跳过")

    stats = cache_manager.get_cache_stats()

    logger.info("=" * 60)
    logger.info(f"实时预热完成：处理 {total_processed} 条新闻")
    logger.info(f"重大新闻：{len(all_major_alerts)} 条，吹哨告警：{alert_count} 条")
    logger.info(f"缓存统计：{stats['total_items']} 条新闻，{stats['unused_items']} 条未使用")
    logger.info("=" * 60)

    return {
        "processed": total_processed,
        "major_news": len(all_major_alerts),
        "alerts_sent": alert_count,
        "important_news": all_major_alerts,
        "stats": stats
    }


def run_hourly_workflow(categories=None, hours: float = 1, test: bool = False, grok_only: bool = False):
    """小时摘要模式，先复用完整主流程。"""
    return run_main_workflow(categories=categories, hours=hours, test=test, grok_only=grok_only)


def _build_alert_email(alerts: List[Dict], threshold: int) -> str:
    """构建重大新闻告警邮件 HTML。"""
    current_time = datetime.now().strftime("%H:%M")
    sorted_alerts = sorted(
        alerts,
        key=lambda item: item.get("importance_score", item.get("score", 0)),
        reverse=True,
    )

    lines = [
        "<!DOCTYPE html>",
        "<html><head><meta charset=\"UTF-8\"></head>",
        "<body style=\"font-family: Arial, sans-serif; line-height: 1.6; color: #222;\">",
        "<div style=\"max-width: 900px; margin: 0 auto;\">",
        "<h1 style=\"color: #b00020;\">重大新闻告警</h1>",
        (
            f"<p>时间：{current_time} | 检测到 <strong>{len(sorted_alerts)}</strong> 条 "
            f"重要性评分不低于 <strong>{threshold}</strong> 分的新闻。</p>"
        ),
    ]

    for alert in sorted_alerts:
        score = alert.get("importance_score", alert.get("score", 0))
        category = alert.get("category", "")
        title = alert.get("title", "")
        summary = alert.get("summary", "")
        raw_data = alert.get("raw_data", {}) or {}
        link = raw_data.get("link", "")
        if not link:
            alternate = raw_data.get("alternate")
            if isinstance(alternate, list) and alternate:
                link = alternate[0].get("href", "")
        if not link:
            canonical = raw_data.get("canonical")
            if isinstance(canonical, list) and canonical:
                link = canonical[0].get("href", "")

        lines.append("<div style=\"border: 1px solid #ddd; border-left: 6px solid #b00020; padding: 16px; margin: 16px 0;\">")
        lines.append(f"<div style=\"font-weight: bold; margin-bottom: 8px;\">[{score}分] [{category}]</div>")
        lines.append(f"<div style=\"font-size: 18px; margin-bottom: 8px;\">{title}</div>")
        if summary:
            lines.append(f"<div style=\"color: #555; margin-bottom: 8px;\">{summary}</div>")
        if link:
            lines.append(f"<div><a href=\"{link}\">查看原文</a></div>")
        lines.append("</div>")

    lines.append("</div></body></html>")
    return "\n".join(lines)


def _send_major_news_alerts(alerts: List[Dict], threshold: int, test: bool = False):
    """发送重大新闻告警邮件"""
    if not alerts:
        return

    current_time = datetime.now()
    time_str = current_time.strftime("%H:%M")
    alert_subject = f"重大新闻告警 ({time_str})"
    html_body = _build_alert_email(alerts, threshold)
    send_html_email(subject=alert_subject, html_body=html_body, test_mode=test)

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
        help='分类列表，逗号分隔，例如： "头条,政治,财经,科技,军事"；不传则用默认分类',
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
        default=None,
        help="实时吹哨模式的重要性阈值；不传则使用 ALERT_THRESHOLD",
    )
    p.add_argument(
        "--grok-only",
        action="store_true",
        help="只使用 Grok：跳过 ds 风险审查，并将原有 Gemini/DeepSeek 调用切到 Grok",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    cats = [x.strip() for x in (args.categories or "").split(",") if x.strip()] or None
    if args.mode == "full":
        # 原有行为：完整跑一遍（保持向后兼容）
        run_main_workflow(categories=cats, hours=args.hours, test=args.test, grok_only=args.grok_only)
    elif args.mode == "realtime":
        run_realtime_workflow(
            categories=cats,
            hours=args.hours,
            importance_threshold=args.threshold,
            test=args.test,
            grok_only=args.grok_only,
        )
    elif args.mode == "hourly":
        # 小时报：当前等价于完整主流程，未来可在此复用缓存结果
        run_hourly_workflow(categories=cats, hours=args.hours, test=args.test, grok_only=args.grok_only)
