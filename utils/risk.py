from utils.logger import get_logger

logger = get_logger("risk")


def parse_risk_response(response_text):
    """
    解析 Gemini 返回的风险评分

    Args:
        response_text: Gemini 返回的文本，格式如：
            1:low
            2:high
            3:low

    Returns:
        dict: 编号到风险等级的映射，如 {"1": "low", "2": "high", "3": "low"}
    """
    risk_map = {}

    if not response_text:
        logger.error("风险响应为空")
        return risk_map

    logger.debug(f"开始解析风险响应，原始文本长度: {len(response_text)}")
    
    # 记录原始响应的前500字符用于调试
    preview = response_text[:500] if len(response_text) > 500 else response_text
    logger.debug(f"响应预览: {preview}")

    lines = response_text.strip().split('\n')
    logger.debug(f"分割后共 {len(lines)} 行")

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        # 跳过可能的markdown代码块标记
        if line.startswith('```'):
            continue

        if ':' not in line:
            logger.warning(f"第 {line_num} 行格式错误（缺少冒号）: {line}")
            continue

        parts = line.split(':', 1)
        if len(parts) == 2:
            item_id = parts[0].strip()
            risk_level = parts[1].strip().lower()

            # 验证 item_id 是数字
            if not item_id.isdigit():
                logger.warning(f"第 {line_num} 行编号无效（非数字）: {item_id}")
                continue

            if risk_level in ['low', 'high']:
                risk_map[item_id] = risk_level
            else:
                logger.warning(f"第 {line_num} 行风险等级无效: {risk_level}，将标记为 high（保守策略）")
                risk_map[item_id] = "high"  # 保守策略：未知风险视为高风险
        else:
            logger.warning(f"第 {line_num} 行格式错误: {line}")

    logger.info(f"解析完成，识别 {len(risk_map)} 条风险标注")
    
    if len(risk_map) == 0:
        logger.error("未能解析出任何有效的风险标注！")
    
    return risk_map


def annotate_risk_levels(items, risk_map):
    """
    将风险等级标注到新闻条目

    Args:
        items: 新闻条目列表，每个条目需要有 id 字段
        risk_map: 编号到风险等级的映射，如 {"1": "low", "2": "high"}

    Returns:
        list: 标注了 ds_risk 字段的新闻条目列表
    """
    items_with_risk = []
    matched_count = 0
    unknown_count = 0

    logger.debug(f"开始标注风险等级，共 {len(items)} 条新闻，risk_map 包含 {len(risk_map)} 条标注")

    # 如果risk_map为空，所有新闻标记为高风险
    if not risk_map:
        logger.warning("risk_map 为空，将所有新闻标记为 high（保守策略）")
        for item in items:
            item_copy = item.copy()
            item_copy["ds_risk"] = "high"
            items_with_risk.append(item_copy)
        return items_with_risk

    for idx, item in enumerate(items, start=1):
        # 尝试多种方式匹配ID
        item_id_raw = item.get("id", "")
        item_id = item_id_raw.replace("H", "")  # 移除 H 前缀
        
        # 尝试使用索引匹配（从1开始）
        idx_str = str(idx)
        
        # 优先使用item_id，如果不存在则使用索引
        if item_id and item_id in risk_map:
            risk_level = risk_map[item_id]
            matched_count += 1
        elif idx_str in risk_map:
            risk_level = risk_map[idx_str]
            matched_count += 1
            logger.debug(f"新闻 {item_id_raw} 使用索引 {idx_str} 匹配到风险等级")
        else:
            risk_level = "high"  # 默认为 high（保守策略）
            unknown_count += 1
            logger.warning(f"新闻 {item_id_raw} (编号 {item_id}, 索引 {idx_str}) 未找到风险标注，标记为 high（保守策略）")

        item_copy = item.copy()
        item_copy["ds_risk"] = risk_level
        items_with_risk.append(item_copy)

    logger.info(f"标注完成 - 成功匹配: {matched_count}, 未匹配: {unknown_count}")

    if unknown_count > 0:
        logger.warning(f"有 {unknown_count} 条新闻未找到风险标注，已标记为 high（保守策略）")

    return items_with_risk

