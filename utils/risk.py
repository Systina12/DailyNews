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

    logger.debug(f"开始解析风险响应，原始文本长度: {len(response_text)}")

    lines = response_text.strip().split('\n')
    logger.debug(f"分割后共 {len(lines)} 行")

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        if ':' not in line:
            logger.warning(f"第 {line_num} 行格式错误（缺少冒号）: {line}")
            continue

        parts = line.split(':', 1)
        if len(parts) == 2:
            item_id = parts[0].strip()
            risk_level = parts[1].strip().lower()

            if risk_level in ['low', 'high']:
                risk_map[item_id] = risk_level
            else:
                logger.warning(f"第 {line_num} 行风险等级无效: {risk_level}")
        else:
            logger.warning(f"第 {line_num} 行格式错误: {line}")

    logger.info(f"解析完成，识别 {len(risk_map)} 条风险标注")
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

    for item in items:
        item_id = item.get("id", "").replace("H", "")  # 移除 H 前缀
        risk_level = risk_map.get(item_id, "unknown")

        if risk_level == "unknown":
            unknown_count += 1
            logger.warning(f"新闻 {item.get('id')} (编号 {item_id}) 未找到风险标注")
        else:
            matched_count += 1

        item_copy = item.copy()
        item_copy["ds_risk"] = risk_level
        items_with_risk.append(item_copy)

    logger.info(f"标注完成 - 成功匹配: {matched_count}, 未匹配: {unknown_count}")

    if unknown_count > 0:
        logger.warning(f"有 {unknown_count} 条新闻未找到风险标注，将标记为 unknown")

    return items_with_risk

