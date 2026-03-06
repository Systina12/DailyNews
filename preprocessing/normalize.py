# preprocessing/normalize.py
"""
数据标准化模块

功能：
1. 提取和标准化链接字段（canonical > alternate > link）
2. 统一数据格式，方便后续处理
"""

from typing import Any, Dict, List
from utils.logger import get_logger

logger = get_logger("normalize")


def normalize_link(item: Dict[str, Any]) -> str:
    """
    从新闻 item 中提取链接并标准化
    优先级：canonical > alternate > link
    
    Args:
        item: 新闻数据字典
        
    Returns:
        str: 提取的链接，如果没有则返回空字符串
    """
    link = ""
    
    # 1. 尝试从 canonical 数组提取
    canonical = item.get("canonical")
    if isinstance(canonical, list) and canonical:
        link = canonical[0].get("href", "") or ""
    
    # 2. 如果没有，尝试从 alternate 数组提取
    if not link:
        alternate = item.get("alternate")
        if isinstance(alternate, list) and alternate:
            link = alternate[0].get("href", "") or ""
    
    # 3. 最后尝试直接的 link 字段
    if not link:
        link = item.get("link", "") or ""
    
    return link.strip()


def normalize_items(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化新闻数据
    
    功能：
    1. 提取链接到 item["link"] 字段
    2. 确保所有必要字段存在
    
    Args:
        data: RSS 数据字典，包含 items 列表
        
    Returns:
        Dict: 标准化后的数据
    """
    items = data.get("items", [])
    if not isinstance(items, list):
        logger.warning("数据格式错误：items 不是列表")
        return data
    
    normalized_count = 0
    
    for item in items:
        if not isinstance(item, dict):
            continue
        
        # 提取并标准化链接
        original_link = item.get("link", "")
        normalized_link = normalize_link(item)
        
        # 只有当提取的链接与原 link 字段不同时才更新
        if normalized_link and normalized_link != original_link:
            item["link"] = normalized_link
            normalized_count += 1
    
    if normalized_count > 0:
        logger.info(f"标准化 {normalized_count}/{len(items)} 条新闻的链接字段")
    
    return data
