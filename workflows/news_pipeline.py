"""
新闻处理工作流
"""

from ingestion.RSSclient import RSSClient
from preprocessing.filters import filter_ru
from preprocessing.dedupe import dedupe_items
from preprocessing.classify import Classify


def run_news_pipeline():
    """
    执行完整的新闻处理工作流

    流程：
    1. 从 FreshRSS 获取 24 小时新闻
    2. 过滤俄罗斯相关内容
    3. 去重
    4. 分类处理头条

    Returns:
        dict: 分类后的新闻数据
            - section: 数据类型标识
            - items: 新闻条目列表

    Raises:
        ValueError: 配置错误
        RuntimeError: 运行时错误
    """

    # 1. 获取新闻
    rss = RSSClient()
    data = rss.get_24h_news()

    # 2. 过滤俄罗斯相关内容
    filtered = filter_ru(data)

    # 3. 去重
    deduped = dedupe_items(filtered)

    # 4. 分类头条
    classifier = Classify(category=category)
    classified = classifier._process_headlines(deduped["items"])

    # 给下游留一个类别信息（不影响旧逻辑，不用也没事）
    classified["category"] = category
    return classified


def run_news_pipeline_all(categories=None):
    """
    执行多分类的新闻处理工作流（目标1用这个）

    流程：
    1. 从 FreshRSS 获取 24 小时新闻
    2. 过滤俄罗斯相关内容
    3. 去重
    4. 对每个分类分别产出一个 block

    Args:
        categories: 分类列表，默认使用 DEFAULT_CATEGORIES

    Returns:
        list[dict]: 每个分类一个 block，形如：
            [
              {"section": "headline", "category": "头条", "items": [...]},
              {"section": "headline", "category": "政治", "items": [...]},
              ...
            ]
    """
    categories = categories or DEFAULT_CATEGORIES

    # 1. 获取新闻
    rss = RSSClient()
    data = rss.get_24h_news()

    # 2. 过滤俄罗斯相关内容
    filtered = filter_ru(data)

    # 3. 去重
    deduped = dedupe_items(filtered)
    raw_items = deduped.get("items", [])

    # 4. 多分类输出
    blocks = []
    for cat in categories:
        classifier = Classify(category=cat)
        block = classifier._process_headlines(raw_items)
        block["category"] = cat
        blocks.append(block)

    return blocks
