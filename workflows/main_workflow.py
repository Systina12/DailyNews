"""
主工作流入口：新闻处理 -> 风险评估 -> 摘要生成 -> 写入文件
（目标1：支持多分类）
"""

import os
from datetime import datetime

from config import settings
from monitoring.metrics import metrics
from workflows.news_pipeline import run_news_pipeline_all
from workflows.risk_assessment import run_risk_assessment_pipeline
from workflows.summary_generation import run_summary_generation_pipeline
from utils.logger import get_logger

logger = get_logger("main_workflow")


def _safe_filename(s: str) -> str:
    """
    简单的文件名清洗：把空格/斜杠等替换掉，避免写文件失败
    """
    if not s:
        return "unknown"
    bad = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
    out = s
    for ch in bad:
        out = out.replace(ch, "_")
    return out


def run_main_workflow(categories=None):
    """
    运行主工作流（多分类）

    Args:
        categories: 分类列表，默认 ["头条","政治","财经","科技","国际"]

    Returns:
        dict: 每个分类的结果汇总：
            {
              "results": [
                 {"category": "...", "output_path": "...", "meta": {...}},
                 ...
              ],
              "meta": {"generated_at": "...", "categories": [...]}
            }
    """
    settings.ensure_directories()
    settings.validate()

    default_categories = ["头条", "政治", "财经", "科技"] #, "国际"]
    categories = categories or default_categories

    logger.info(f"开始主工作流，多分类: {categories}")

    # 1) 获取 + 预处理 + 分类（一次拉取，多分类输出）
    logger.info("运行新闻预处理与分类...")
    blocks = run_news_pipeline_all(categories=categories)

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
        metrics.record_risk_assessment(total=len(risk_data.get("items", [])), low=low_count, high=high_count)

        # 3) 摘要生成（低风险 DeepSeek+fallback，高风险 Gemini）
        logger.info(f"分类 [{category}] 生成摘要...")
        summaries = run_summary_generation_pipeline(risk_data)

        merged_summary = summaries.get("merged_summary", "") or ""
        meta = summaries.get("meta", {}) or {}

        # 如果低风险触发 fallback，记录一次
        if meta.get("low_is_fallback"):
            metrics.record_fallback(
                reason=meta.get("low_filter_reason") or "content_filtered",
                primary_model="deepseek",
                fallback_model="gemini"
            )

        # 4) 写入文件：每类一个 merged html
        date_str = meta.get("dateStr") or datetime.now().strftime("%Y-%m-%d")
        safe_cat = _safe_filename(category)
        filename = f"summary_{safe_cat}_{date_str}.html"
        out_path = os.path.join(str(settings.DATA_DIR), filename)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(merged_summary)

        logger.info(f"分类 [{category}] 输出文件: {out_path}")

        results.append({
            "category": category,
            "output_path": out_path,
            "meta": meta
        })

    # 5) 打印指标摘要
    metrics.print_summary()

    return {
        "results": results,
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "categories": categories
        }
    }


if __name__ == "__main__":
    run_main_workflow()
