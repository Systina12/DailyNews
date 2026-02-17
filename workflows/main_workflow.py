"""
主工作流入口
"""

import os
from datetime import datetime

from config import settings
from monitoring.metrics import metrics
from workflows.news_pipeline import run_news_pipeline_all
from workflows.risk_assessment import run_risk_assessment_pipeline
from workflows.summary_generation import run_summary_generation_pipeline


def _safe_filename(text: str) -> str:
    """
    把分类名这种文本简单转换成适合文件名的形式（保留中文也可以，但这里做基础清理）
    """
    return (
        str(text)
        .strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )


def run_main_workflow(categories=None):
    """
    执行完整工作流（多分类版本）：
    1) 新闻获取与预处理（多分类输出）
    2) 风险评估（每个分类单独评估）
    3) 摘要生成（每个分类单独生成）
    4) 写入 data 目录
    5) 输出指标摘要

    Args:
        categories: 可选，分类列表。默认使用 workflows/news_pipeline.py 里的 DEFAULT_CATEGORIES
    """
    # 0. 准备目录
    settings.ensure_directories()

    # 1. 多分类预处理
    blocks = run_news_pipeline_all(categories=categories)

    results = []
    for block in blocks:
        category = block.get("category", "头条")
        items = block.get("items", [])
        if not items:
            # 该分类为空，跳过后续 LLM 调用
            continue

        # 计数：每个分类处理的新闻数累加
        metrics.increment_counter("news_processed", len(items))

        # 2. 风险评估
        risk_block = run_risk_assessment_pipeline(block)

        # 统计 low/high
        low_count = len([it for it in risk_block.get("items", []) if it.get("ds_risk") == "low"])
        high_count = len([it for it in risk_block.get("items", []) if it.get("ds_risk") == "high"])
        metrics.record_risk_assessment(total=low_count + high_count, low=low_count, high=high_count)

        # 3. 摘要生成
        summary_result = run_summary_generation_pipeline(risk_block)

        # 如果低风险摘要触发 fallback，记录一次
        meta = summary_result.get("meta", {})
        if meta.get("low_risk_is_fallback"):
            metrics.record_fallback(
                reason=meta.get("low_risk_filter_reason") or "unknown",
                primary_model="deepseek",
                fallback_model="gemini",
            )

        # 4. 写文件（每类一个 merged）
        date_str = meta.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
        fname = f"summary_{_safe_filename(category)}_{date_str}.html"
        out_path = os.path.join(settings.DATA_DIR, fname)

        merged_summary = summary_result.get("merged_summary") or ""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(merged_summary)

        results.append(
            {
                "category": category,
                "count": len(items),
                "low": low_count,
                "high": high_count,
                "file": out_path,
            }
        )

    # 5. 打印指标摘要
    metrics.print_summary()

    return results


if __name__ == "__main__":
    # 直接运行脚本时，执行多分类并落盘
    run_main_workflow()
