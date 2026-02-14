"""
新闻风险评估工作流
"""

from llms.build_prompt import build_ds_risk_prompt
from llms.llms import LLMClient
from utils.risk import parse_risk_response, annotate_risk_levels


def run_risk_assessment_pipeline(classified_data):
    """
    执行新闻风险评估工作流

    Args:
        classified_data: 分类后的新闻数据，格式：
            {
                "section": "headline",
                "items": [...]
            }

    流程：
    1. 构建风险评估 prompt
    2. 请求 Gemini 进行风险评分
    3. 解析结果并标注每条新闻的风险等级

    Returns:
        dict: 标注了风险等级的新闻数据
            - section: 数据类型标识
            - items: 标注了 ds_risk 字段的新闻条目列表

    Raises:
        ValueError: 配置错误或 API 调用失败
        RuntimeError: 运行时错误
    """

    if not classified_data or classified_data.get("section") != "headline":
        raise ValueError("输入数据必须是 headline 类型的分类结果")

    classified = classified_data

    # 2. 构建风险评估 prompt
    prompt_data = build_ds_risk_prompt(classified)

    if not prompt_data:
        raise ValueError("无法构建风险评估 prompt")

    # 3. 请求 Gemini
    llm_client = LLMClient()
    response = llm_client.request_gemini(
        prompt=prompt_data["prompt"],
        temperature=0.1,
        max_tokens=1000
    )

    # 4. 解析风险评分
    risk_map = parse_risk_response(response)

    # 5. 标注风险等级
    items_with_risk = annotate_risk_levels(classified.get("items", []), risk_map)

    return {
        "section": classified.get("section"),
        "items": items_with_risk
    }
