"""
新闻摘要生成工作流
"""

from llms.build_prompt import build_headline_prompt
from llms.llms import LLMClient
from utils.merge_summaries import merge_summaries
from utils.logger import get_logger

logger = get_logger("summary_generation")


def run_summary_generation_pipeline(risk_annotated_data):
    """
    执行新闻摘要生成工作流

    根据风险等级选择不同的 LLM 生成摘要：
    - low 风险：使用 DeepSeek（带自动 fallback 到 Gemini）
    - high 风险：直接使用 Gemini

    Args:
        risk_annotated_data: 标注了风险等级的新闻数据，格式：
            {
                "section": "headline",
                "items": [
                    {
                        "id": "H1",
                        "title": "...",
                        "summary": "...",
                        "ds_risk": "low" or "high",
                        ...
                    },
                    ...
                ]
            }

    Returns:
        dict: 生成的摘要结果
            {
                "low_risk_summary": "生成的 HTML 摘要",
                "high_risk_summary": "生成的 HTML 摘要",
                "merged_summary": "合并后的完整 HTML 摘要",
                "meta": {
                    "low_count": int,
                    "high_count": int,
                    "total_count": int,
                    "low_risk_model": str,      # 实际使用的模型
                    "low_risk_fallback": bool   # 是否触发了 fallback
                }
            }

    Raises:
        ValueError: 配置错误或输入数据格式错误
        RuntimeError: LLM API 调用失败
    """

    if not risk_annotated_data or risk_annotated_data.get("section") != "headline":
        raise ValueError("输入数据必须是 headline 类型的风险标注结果")

    llm_client = LLMClient()
    results = {
        "low_risk_summary": None,
        "high_risk_summary": None,
        "merged_summary": None,
        "meta": {
            "low_count": 0,
            "high_count": 0,
            "total_count": len(risk_annotated_data.get("items", [])),
            "low_risk_model": None,
            "low_risk_fallback": False,
            "fallback_reason": None
        }
    }

    # 1. 处理低风险新闻（使用 DeepSeek，带自动 fallback）
    low_prompt_data = build_headline_prompt(risk_annotated_data, risk_filter="low")

    if low_prompt_data and low_prompt_data.get("prompt"):
        logger.info(f"正在生成低风险新闻摘要...")
        logger.info(f"低风险新闻数量: {low_prompt_data['meta']['filtered']}")

        try:
            response = llm_client.request_with_fallback(
                prompt=low_prompt_data["prompt"],
                temperature=0.3,
                max_tokens=4000,
                primary="deepseek"
            )

            results["low_risk_summary"] = response["content"]
            results["meta"]["low_count"] = low_prompt_data["meta"]["filtered"]
            results["meta"]["low_risk_model"] = response["model_used"]
            results["meta"]["low_risk_fallback"] = response["is_fallback"]
            results["meta"]["fallback_reason"] = response["filter_reason"]

            if response["is_fallback"]:
                logger.info(f"✓ 完成（使用 {response['model_used']}，触发 fallback）")
            else:
                logger.info(f"✓ 完成（使用 {response['model_used']}）")

        except Exception as e:
            logger.error(f"生成低风险摘要失败: {e}")
            raise RuntimeError(f"生成低风险摘要失败: {e}")
    else:
        logger.info("没有低风险新闻需要处理")

    # 2. 处理高风险新闻（使用 Gemini）
    high_prompt_data = build_headline_prompt(risk_annotated_data, risk_filter="high")

    if high_prompt_data and high_prompt_data.get("prompt"):
        logger.info(f"正在使用 Gemini 生成高风险新闻摘要...")
        logger.info(f"高风险新闻数量: {high_prompt_data['meta']['filtered']}")

        try:
            high_summary = llm_client.request_gemini(
                prompt=high_prompt_data["prompt"],
                temperature=0.3,
                max_tokens=4000
            )
            results["high_risk_summary"] = high_summary
            results["meta"]["high_count"] = high_prompt_data["meta"]["filtered"]
            logger.info("✓ 完成（使用 gemini）")
        except Exception as e:
            logger.error(f"Gemini 生成摘要失败: {e}")
            raise RuntimeError(f"Gemini 生成摘要失败: {e}")
    else:
        logger.info("没有高风险新闻需要处理")

    # 3. 合并摘要
    if results["low_risk_summary"] or results["high_risk_summary"]:
        logger.info("正在合并摘要...")
        results["merged_summary"] = merge_summaries(
            low_risk_summary=results["low_risk_summary"],
            high_risk_summary=results["high_risk_summary"],
            add_section_headers=True
        )
        logger.info("✓ 摘要合并完成")

    return results
