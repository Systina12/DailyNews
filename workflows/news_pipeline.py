# workflows/news_pipeline.py

from ingestion.RSSclient import RSSClient
from preprocessing.filters import filter_ru
from preprocessing.dedupe import dedupe_items
from preprocessing.classify import Classify

DEFAULT_CATEGORIES = ["头条", "政治", "财经", "科技", "国际"]


def run_news_pipeline_all(categories=None, hours: int = 24):
    """多分类：一次拉取最近 hours 小时新闻 -> 过滤 -> 去重 -> 每个分类分别产出 block"""
    categories = categories or DEFAULT_CATEGORIES
    rss = RSSClient()
    data = rss.get_news(hours=hours)
    filtered = filter_ru(data)
    deduped = dedupe_items(filtered)
    raw_items = deduped.get("items", [])

    blocks = []
    for cat in categories:
        # 统一使用 Classify，俄罗斯分类已集成到规则中
        classifier = Classify(category=cat)
        block = classifier._process_headlines(raw_items)
        block["category"] = cat
        blocks.append(block)
    return blocks


def run_news_pipeline(category: str = "头条", hours: int = 24):
    """单分类：拉取最近 hours 小时新闻 -> 过滤 -> 去重 -> 分类"""
    rss = RSSClient()
    data = rss.get_news(hours=hours)
    filtered = filter_ru(data)
    deduped = dedupe_items(filtered)

    # 统一使用 Classify
    classifier = Classify(category=category)
    classified = classifier._process_headlines(deduped.get("items", []))
    classified["category"] = category
    return classified
