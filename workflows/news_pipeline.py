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
    classifier = Classify(category='头条')
    classified = classifier._process_headlines(deduped["items"])

    return classified
