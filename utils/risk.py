
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

    for line in response_text.strip().split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue

        parts = line.split(':', 1)
        if len(parts) == 2:
            item_id = parts[0].strip()
            risk_level = parts[1].strip().lower()

            if risk_level in ['low', 'high']:
                risk_map[item_id] = risk_level

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

    for item in items:
        item_id = item.get("id", "").replace("H", "")  # 移除 H 前缀
        risk_level = risk_map.get(item_id, "unknown")

        item_copy = item.copy()
        item_copy["ds_risk"] = risk_level
        items_with_risk.append(item_copy)

    return items_with_risk

