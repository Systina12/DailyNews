RUSSIA_LABEL = "user/-/label/俄罗斯"



def filter_ru(data):
    items = data.get("items", [])

    filtered = [
        item for item in items
        if RUSSIA_LABEL not in item.get("categories", [])
    ]

    new_data = data.copy()
    new_data["items"] = filtered

    return new_data


def filter_high_risk_items(items):
    """
    过滤出高风险的新闻条目

    Args:
        items: 包含 ds_risk 字段的新闻列表

    Returns:
        list: 只包含 ds_risk == "high" 的条目
    """
    return [
        item for item in items
        if item.get("ds_risk") == "high"
    ]


def filter_low_risk_items(items):
    """
    过滤出低风险的新闻条目

    Args:
        items: 包含 ds_risk 字段的新闻列表

    Returns:
        list: 只包含 ds_risk == "low" 的条目
    """
    return [
        item for item in items
        if item.get("ds_risk") == "low"
    ]
