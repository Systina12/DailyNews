# workflows/news_pipeline.py

from ingestion.RSSclient import RSSClient
from preprocessing.filters import filter_ru
from preprocessing.dedupe import dedupe_items
from preprocessing.classify import Classify, ClassifyRussia

DEFAULT_CATEGORIES = ["头条", "政治", "财经", "科技", "国际", "俄罗斯"]


def _classify_item(self, item):
    """
    将新闻分类到5个类别之一
    分类优先级：头条 > 政治 > 财经 > 科技 > 国际
    """
    title = (item.get("title") or "").lower()
    src = (item.get("origin", {}).get("title") or "").lower()
    categories = item.get("categories", [])
    cats = " ".join(str(c).lower() for c in categories)

    # 1. 头条：来源标记为top 且 不是软内容
    if ("top" in src or "top" in cats or "头条" in src or "头条" in cats) and not self._is_soft_content(item):
        return "头条"

    # 2. 政治
    political_keywords = [
        "election", "vote", "parliament", "government", "president", "prime minister",
        "policy", "sanction", "cabinet", "congress", "senate", "politic",
        "选举", "政府", "总统", "议会", "内阁", "制裁",
    ]
    if (any(kw in title for kw in political_keywords) or "politics" in src or "politica" in src):
        return "政治"

    # 3. 财经
    econ_keywords = [
        "economy", "economic", "market", "stock", "inflation", "bank", "finance", "business",
        "economia", "borsa", "mercato",
        "经济", "股市", "通胀", "银行",
    ]
    if (any(kw in title for kw in econ_keywords) or "business" in src or "economia" in src):
        return "财经"

    # 4. 科技
    tech_keywords = [
        "tech", "technology", "ai", "artificial intelligence", "software", "chip",
        "science", "scienza",
        "科技", "人工智能", "半导体",
    ]
    if (any(kw in title for kw in tech_keywords) or "tech" in src or "science" in src or "scienza" in src):
        return "科技"

    # 5. 国际（兜底）
    return "国际"


def _process_headlines(self, items):
    """
    处理头条新闻：硬排除 → 分类 → 筛选出指定类别的新闻
    """
    result = []
    for item in items:
        # 1. 硬排除
        if self._is_hard_excluded(item):
            continue
        
        # 2. 分类
        predicted_category = self._classify_item(item)
        
        # 3. 筛选：只保留当前分类器指定的类别
        if predicted_category == self.category:
            result.append(item)
    
    return {
        "section": "headline",
        "items": result
    }


class ClassifyRussia(Classify):
    """
    俄罗斯新闻分类器
    用于处理包含俄罗斯新闻的分类逻辑。
    """

    def _classify_item(self, item):
        """
        根据俄罗斯新闻的特征进行分类
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        categories = item.get("categories", [])
        cats = " ".join(str(c).lower() for c in categories)

        # 特别处理俄罗斯新闻标签，直接进行分类
        if "label/俄罗斯" in cats or "россия" in src:
            return "俄罗斯"  # 修改这里：返回"俄罗斯"而不是"国际"

        # 如果新闻来自俄罗斯来源，或涉及俄罗斯相关事务，判定为“国际”或其他
        russian_keywords = ["russia", "россия", "putin", "путин", "kremlin", "кремл"]
        if any(kw in title for kw in russian_keywords):
            return "俄罗斯"  # 修改这里：返回"俄罗斯"而不是"国际"

        # 调用父类的方法，如果新闻没涉及俄罗斯，按父类规则分类
        return super()._classify_item(item)


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
        # 对于"俄罗斯"分类，使用ClassifyRussia
        if cat == "俄罗斯":
            classifier = ClassifyRussia(category=cat)
        else:
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

    # 根据分类选择正确的分类器，确保"俄罗斯"分类能被特殊处理
    if category == "俄罗斯":
        classifier = ClassifyRussia(category=category)
    else:
        classifier = Classify(category=category)

    classified = classifier._process_headlines(deduped.get("items", []))
    classified["category"] = category
    return classified