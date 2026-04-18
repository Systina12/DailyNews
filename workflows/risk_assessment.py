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
                "category": "头条/政治/军事/财经/科技/国际",   # 可选，但建议带上
                "items": [...]
            }

    流程：
    1. 构建风险评估 prompt
    2. 请求 Gemini 进行风险评分（支持批量处理）
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

    items = classified.get("items", [])
    item_count = len(items)
    logger.info(f"开始风险评估，共 {item_count} 条新闻" + (f"（{category}）" if category else ""))

    # 使用配置的批次大小
    from config import settings
    batch_size = settings.RISK_BATCH_SIZE
    
    # 初始化LLM客户端
    llm_client = LLMClient()

    if settings.GROK_ONLY:
        logger.info("GROK_ONLY 已开启，跳过 ds 风险审查，统一标记为 low")
        items_with_risk = []
        for item in items:
            item_copy = item.copy()
            item_copy["ds_risk"] = "low"
            items_with_risk.append(item_copy)

        out = {
            "section": classified.get("section"),
            "items": items_with_risk
        }
        if category:
            out["category"] = category
        if date_str:
            out["dateStr"] = date_str
        out["risk_skipped"] = True
        return out
    
    # 如果新闻数量超过批次大小，需要分批处理
    if item_count > batch_size:
        logger.info(f"新闻数量 {item_count} 超过批次大小 {batch_size}，将分批处理")
        
        # 分批处理
        all_items_with_risk = []
        for batch_start in range(0, item_count, batch_size):
            batch_end = min(batch_start + batch_size, item_count)
            batch_items = items[batch_start:batch_end]
            
            logger.info(f"处理批次 {batch_start//batch_size + 1}/{(item_count-1)//batch_size + 1}（{len(batch_items)} 条）...")
            
            prompt_block = {
                "section": "headline",
                "items": batch_items
            }
            prompt_data = build_ds_risk_prompt(prompt_block, max_items=batch_size)
            
            if not prompt_data:
                logger.warning(f"批次 {batch_start//batch_size + 1} 无法构建 prompt，跳过")
                # 标记为高风险
                for item in batch_items:
                    item_copy = item.copy()
                    item_copy["ds_risk"] = "high"
                    all_items_with_risk.append(item_copy)
                continue
            
            # 请求 Gemini Flash
            try:
                response = llm_client.request_gemini_flash(
                    prompt=prompt_data["prompt"],
                    temperature=0.1,
                    max_tokens=1000
                )
                
                # 解析结果
                risk_map = parse_risk_response(response)
                batch_items_with_risk = annotate_risk_levels(batch_items, risk_map)
                all_items_with_risk.extend(batch_items_with_risk)
                
                logger.info(f"✓ 批次 {batch_start//batch_size + 1} 完成")
                
            except Exception as e:
                logger.error(f"批次 {batch_start//batch_size + 1} 失败: {e}，标记为高风险")
                for item in batch_items:
                    item_copy = item.copy()
                    item_copy["ds_risk"] = "high"
                    all_items_with_risk.append(item_copy)
        
        items_with_risk = all_items_with_risk
        
    else:
        # 单批处理
        prompt_block = {
            "section": "headline",
            "items": items
        }
        prompt_data = build_ds_risk_prompt(prompt_block, max_items=batch_size)

        if not prompt_data:
            raise ValueError("无法构建风险评估 prompt（可能是 items 为空）")

        # 请求 Gemini Flash
        logger.info(f"请求 Gemini Flash 进行风险评估（{item_count} 条，批次大小: {batch_size}）...")
        try:
            response = llm_client.request_gemini_flash(
                prompt=prompt_data["prompt"],
                temperature=0.1,
                max_tokens=1000
            )
            logger.info("✓ Gemini Flash 响应成功")
        except Exception as e:
            logger.error(f"Gemini Flash 风险评估失败: {e}")
            # 失败时标记所有新闻为高风险（保守策略）
            logger.warning("风险评估失败，将所有新闻标记为高风险")
            items_with_risk = []
            for item in items:
                item_copy = item.copy()
                item_copy["ds_risk"] = "high"
                items_with_risk.append(item_copy)
            
            out = {
                "section": classified.get("section"),
                "items": items_with_risk
            }
            if category:
                out["category"] = category
            if date_str:
                out["dateStr"] = date_str
            return out

        # 解析风险评分
        logger.info("解析风险评分...")
        risk_map = parse_risk_response(response)
        logger.info(f"✓ 解析完成，识别 {len(risk_map)} 条风险标注")

        # 标注风险等级
        logger.info("标注风险等级...")
        items_with_risk = annotate_risk_levels(items, risk_map)
    
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
