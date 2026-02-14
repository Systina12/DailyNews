"""
完整的新闻处理主工作流

整合所有处理步骤：
1. 获取和预处理新闻
2. 风险评估
3. 生成摘要
"""

from workflows.news_pipeline import run_news_pipeline
from workflows.risk_assessment import run_risk_assessment_pipeline
from workflows.summary_generation import run_summary_generation_pipeline
from config import settings
from utils.logger import get_logger
from monitoring import metrics

logger = get_logger("main_workflow")


def run_main_workflow():
    """
    执行完整的新闻处理工作流

    流程：
    1. 获取 24 小时新闻并预处理（过滤、去重、分类）
    2. 使用 Gemini 评估 DeepSeek 风险等级
    3. 根据风险等级生成摘要：
       - 低风险：使用 DeepSeek
       - 高风险：使用 Gemini

    Returns:
        dict: 完整的处理结果
            {
                "classified_data": {...},  # 分类后的新闻数据
                "risk_data": {...},        # 风险标注后的数据
                "summaries": {             # 生成的摘要
                    "low_risk_summary": "...",
                    "high_risk_summary": "...",
                    "meta": {...}
                }
            }

    Raises:
        ValueError: 配置错误
        RuntimeError: 运行时错误
    """

    logger.info("=" * 60)
    logger.info("开始执行新闻处理工作流")
    logger.info("=" * 60)

    # 确保必要的目录存在
    settings.ensure_directories()

    # 步骤 1: 获取和预处理新闻
    logger.info("\n[步骤 1/3] 获取和预处理新闻...")
    classified_data = run_news_pipeline()
    item_count = len(classified_data.get('items', []))
    logger.info(f"✓ 完成预处理，共 {item_count} 条新闻")
    metrics.increment_counter("news_processed", item_count)

    # 步骤 2: 风险评估
    logger.info("\n[步骤 2/3] 评估 DeepSeek 风险等级...")
    risk_data = run_risk_assessment_pipeline(classified_data)

    low_count = sum(1 for item in risk_data.get("items", []) if item.get("ds_risk") == "low")
    high_count = sum(1 for item in risk_data.get("items", []) if item.get("ds_risk") == "high")
    logger.info(f"✓ 完成风险评估")
    logger.info(f"  - 低风险: {low_count} 条")
    logger.info(f"  - 高风险: {high_count} 条")
    metrics.record_risk_assessment(item_count, low_count, high_count)

    # 步骤 3: 生成摘要
    logger.info("\n[步骤 3/3] 生成新闻摘要...")
    summaries = run_summary_generation_pipeline(risk_data)
    logger.info(f"✓ 完成摘要生成")
    logger.info(f"  - 低风险摘要: {'已生成' if summaries.get('low_risk_summary') else '无'}")
    logger.info(f"  - 高风险摘要: {'已生成' if summaries.get('high_risk_summary') else '无'}")

    logger.info("\n" + "=" * 60)
    logger.info("工作流执行完成")
    logger.info("=" * 60)

    # 打印指标摘要
    metrics.print_summary()

    return {
        "classified_data": classified_data,
        "risk_data": risk_data,
        "summaries": summaries
    }


if __name__ == "__main__":
    try:
        result = run_main_workflow()

        # 输出摘要到文件
        from datetime import datetime
        from pathlib import Path

        output_dir = settings.DATA_DIR
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存合并后的摘要（主要输出）
        if result["summaries"].get("merged_summary"):
            merged_file = output_dir / f"summary_{timestamp}.html"
            with open(merged_file, "w", encoding="utf-8") as f:
                f.write(result["summaries"]["merged_summary"])
            logger.info(f"\n合并摘要已保存到: {merged_file}")

        # 保存单独的摘要（用于调试）
        if result["summaries"].get("low_risk_summary"):
            low_file = output_dir / f"low_risk_summary_{timestamp}.html"
            with open(low_file, "w", encoding="utf-8") as f:
                f.write(result["summaries"]["low_risk_summary"])
            logger.info(f"低风险摘要已保存到: {low_file}")

        if result["summaries"].get("high_risk_summary"):
            high_file = output_dir / f"high_risk_summary_{timestamp}.html"
            with open(high_file, "w", encoding="utf-8") as f:
                f.write(result["summaries"]["high_risk_summary"])
            logger.info(f"高风险摘要已保存到: {high_file}")

    except Exception as e:
        logger.error(f"\n错误: {e}", exc_info=True)
        raise
