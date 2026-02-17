"""
新闻风险评估工作流
"""

from llms.build_prompt import build_ds_risk_prompt
from llms.llms import LLMClient
from utils.risk import parse_risk_response, annotate_risk_levels
from utils.logger import get_logger

logger = get_logger("risk_assessment")


def run_risk_assessment_pipeline(classified_data):
    """
    执行新闻风险评估工作流

    Args:
        classified_data: 分类后的新闻数据，格式：
            {
                "section": "headline",
                "category": "头条/政治/财经/科技/国际",   # 可选，但建议带上
                "items": [...]
            }

    流程：
    1. 构建风险评估 prompt
    2. 请求 Gemini 进行风险评分
    3. 解析结果并标注每条新闻的风险等级

    Returns:
        dict: 标注了风险等级的新闻数据（保留 category 等字段）
            {
                "section": "headline",
                "category": "...",          # 如果输入有就保留
                "dateStr": "...",           # 如果输入有就保留
                "items": [...],             # 每条带 ds_risk
            }
    """

    if not classified_data or classified_data.get("section") != "headline":
        raise ValueError("输入数据必须是 headline 类型的分类结果")

    classified = classified_data
    category = classified.get("category")
    date_str = classified.get("dateStr") or classified.get("date")

    item_count = len(classified.get("items", []))
    logger.info(f"开始风险评估，共 {item_count} 条新闻" + (f"（{category}）" if category else ""))

    # 2. 构建风险评估 prompt
    logger.info("构建风险评估 prompt...")
    prompt_data = build_ds_risk_prompt(classified)

    if not prompt_data:
        raise ValueError("无法构建风险评估 prompt（可能是 items 为空）")

    # 3. 请求 Gemini
    logger.info("请求 Gemini 进行风险评估...")
    llm_client = LLMClient()
    response = llm_client.request_gemini(
        prompt=prompt_data["prompt"],
        temperature=0.1,
        max_tokens=1000
    )
    logger.info("✓ Gemini 响应成功")

    # 4. 解析风险评分
    logger.info("解析风险评分...")
    risk_map = parse_risk_response(response)
    logger.info(f"✓ 解析完成，识别 {len(risk_map)} 条风险标注")

    # 5. 标注风险等级
    logger.info("标注风险等级...")
    items_with_risk = annotate_risk_levels(classified.get("items", []), risk_map)

    low_count = sum(1 for item in items_with_risk if item.get("ds_risk") == "low")
    high_count = sum(1 for item in items_with_risk if item.get("ds_risk") == "high")
    logger.info(f"✓ 标注完成 - 低风险: {low_count}, 高风险: {high_count}")

    out = {
        "section": classified.get("section"),
        "items": items_with_risk
    }

    # 保留额外字段，供后续 prompt 标题/文件命名使用
    if category:
        out["category"] = category
    if date_str:
        out["dateStr"] = date_str

    return out

