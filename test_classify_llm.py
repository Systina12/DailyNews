#!/usr/bin/env python3
"""
测试 LLM 分类功能
"""

from preprocessing.classify import Classify
from utils.logger import get_logger

logger = get_logger("test")

# 测试数据
test_items = [
    {
        "title": "Trump announces new tariff policy on China",
        "summaryText": "President announces 25% tariffs on Chinese imports",
        "origin": {"title": "Reuters"}
    },
    {
        "title": "Stock market hits record high amid tech rally",
        "summaryText": "S&P 500 reaches new peak as tech stocks surge",
        "origin": {"title": "Bloomberg"}
    },
    {
        "title": "New AI model breaks performance records",
        "summaryText": "Latest language model shows significant improvements",
        "origin": {"title": "TechCrunch"}
    },
    {
        "title": "Celebrity couple announces divorce",
        "summaryText": "Hollywood stars split after 10 years",
        "origin": {"title": "Entertainment Weekly"}
    },
    {
        "title": "Football team wins championship",
        "summaryText": "Local team takes home the trophy",
        "origin": {"title": "ESPN"}
    },
]

def test_classification():
    """测试分类功能"""
    logger.info("开始测试分类...")
    
    # 测试政治分类
    classifier = Classify(category="政治")
    result = classifier._process_headlines(test_items)
    
    logger.info(f"政治类新闻: {len(result['items'])} 条")
    for item in result['items']:
        logger.info(f"  - {item['title']}")
    
    # 测试财经分类
    classifier = Classify(category="财经")
    result = classifier._process_headlines(test_items)
    
    logger.info(f"财经类新闻: {len(result['items'])} 条")
    for item in result['items']:
        logger.info(f"  - {item['title']}")
    
    # 测试科技分类
    classifier = Classify(category="科技")
    result = classifier._process_headlines(test_items)
    
    logger.info(f"科技类新闻: {len(result['items'])} 条")
    for item in result['items']:
        logger.info(f"  - {item['title']}")

if __name__ == "__main__":
    test_classification()
