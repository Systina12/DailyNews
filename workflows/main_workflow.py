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


def run_main_workflow(categories=None, hours: float = 24):
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
            send_html_email(subject=subject, html_body=merged_summary)
            logger.info(f"分类 [{category}] 邮件已发送，subject={subject}")
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


def run_realtime_workflow(categories=None, hours: float = 1):
    """
    实时预热工作流（轻量版，供 crontab 每 N 分钟调用）

    当前实现：
    - 仅执行「拉取 → 预处理 → 多分类」阶段
    - 主要用于后续接入：缓存打分结果、重大新闻吹哨
    - 不做风险评估、不生成摘要、不发邮件（避免与主工作流重复）

    注意：
    - 这是新增的补充入口，不影响原有 run_main_workflow 行为
    """
    settings.ensure_directories()
    settings.validate()

    default_categories = ["头条", "政治", "财经", "科技", "国际"]
    categories = categories or default_categories

    logger.info(
        f"开始实时预热工作流（realtime），多分类: {categories}，hours={hours}"
    )

    # 仅跑到分类这一步，后续缓存/吹哨逻辑可在这里接入
    blocks = run_news_pipeline_all(categories=categories, hours=hours)

    # 统计一下本次各分类条数，方便在日志里观察
    logger.info("=" * 60)
    logger.info("realtime 预热结果（仅分类阶段）：")
    for block in blocks:
        cat = block.get("category", "unknown")
        items = block.get("items") or []
        logger.info(f"  [{cat}]: {len(items)} 条")
    logger.info("=" * 60)

    return {
        "blocks": blocks,
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "categories": categories,
            "hours": float(hours),
            "mode": "realtime",
        },
    }


def run_hourly_workflow(categories=None, hours: float = 24):
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
        f"以 hourly 模式运行主工作流，categories={categories or '默认'}, hours={hours}"
    )
    return run_main_workflow(categories=categories, hours=hours)


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
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    cats = [x.strip() for x in (args.categories or "").split(",") if x.strip()] or None
    if args.mode == "full":
        # 原有行为：完整跑一遍（保持向后兼容）
        run_main_workflow(categories=cats, hours=args.hours)
    elif args.mode == "realtime":
        # 轻量实时预热：仅拉取+分类，后续可在此接入缓存/吹哨
        run_realtime_workflow(categories=cats, hours=args.hours)
    elif args.mode == "hourly":
        # 小时报：当前等价于完整主流程，未来可在此复用缓存结果
        run_hourly_workflow(categories=cats, hours=args.hours)