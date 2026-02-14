import re


class Classify:
    """
    新闻分类器

    流程：过滤 → 分类 → 筛选
    支持5个类别：头条、政治、财经、科技、国际
    """

    def __init__(self, category):
        """
        Args:
            category: 要提取的类别（头条/政治/财经/科技/国际）
        """
        self.category = category

    def _is_excluded(self, item):
        """
        判断是否应该排除（娱乐、体育、节目等非新闻内容）

        Returns:
            bool: True表示应该排除
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        link = (
            item.get("canonical", [{}])[0].get("href") or
            item.get("alternate", [{}])[0].get("href") or
            item.get("link") or ""
        ).lower()

        # 收集所有文本用于关键词匹配
        text_parts = [
            title,
            item.get("summaryText", ""),
            item.get("summary", {}).get("content", "") if isinstance(item.get("summary"), dict) else "",
            str(item.get("summary", "")),
            link
        ]
        full_text = " ".join(str(p) for p in text_parts if p).lower()

        # 排除关键词：娱乐、体育、节目
        exclude_keywords = [
            # 节目/预告
            "sneak peek", "preview", "episode", "season",
            "interview", "transcript",
            # 体育
            "super bowl", "nfl", "olympic", "world cup",
            "beat ", "wins ", "defeats ", "athlete",
            "curling", "skating",
            # 娱乐
            "music", "singer", "band", "album", "song",
            "eagles", "henley",
            # 展览/宠物
            "dog show", "kennel", "show where", "wins gold",
            # 电视栏目
            "60 minutes", "48 hours",
            "face the nation", "sunday morning",
            "the takeout", "weekend news",
            "almanac", "passage:",
            # 软内容
            "video", "nature", "art", "museum", "culture",
            "review", "book", "film", "celebrity", "entertainment"
        ]

        if any(kw in full_text for kw in exclude_keywords):
            return True

        # CBS视频和文字稿
        if "cbsnews.com/video/" in link or "60-minutes-transcript" in link:
            return True

        # 美媒节目型标题（日期前缀）
        if ("cbs" in src or "bbc" in src):
            if re.match(r"^\d{1,2}/\d{1,2}", title) or re.match(r"^\d{4}:\s", title):
                return True

        # BBC软内容栏目
        if "bbc" in src and any(kw in title for kw in ["culture", "future", "travel", "worklife"]):
            return True

        return False

    def _classify_item(self, item):
        """
        将新闻分类到5个类别之一

        分类优先级：头条 > 政治 > 财经 > 科技 > 国际

        Returns:
            str: 类别名称
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        categories = item.get("categories", [])
        cats = " ".join(str(c).lower() for c in categories)

        # 1. 头条：来源标记为top
        if "top" in src or "top" in cats:
            return "头条"

        # 2. 政治
        political_keywords = [
            "election", "vote", "parliament", "government",
            "president", "prime minister", "policy", "sanction",
            "cabinet", "congress", "senate", "politic",
            "选举", "政府", "总统", "议会", "内阁", "制裁"
        ]
        if (any(kw in title for kw in political_keywords) or
            "politics" in src or "politica" in src):
            return "政治"

        # 3. 财经
        econ_keywords = [
            "economy", "economic", "market", "stock",
            "inflation", "bank", "finance", "business",
            "economia", "borsa", "mercato",
            "经济", "股市", "通胀", "银行"
        ]
        if (any(kw in title for kw in econ_keywords) or
            "business" in src or "economia" in src):
            return "财经"

        # 4. 科技
        tech_keywords = [
            "tech", "technology", "ai", "artificial intelligence",
            "software", "chip", "science", "scienza",
            "科技", "人工智能", "半导体"
        ]
        if (any(kw in title for kw in tech_keywords) or
            "tech" in src or "science" in src or "scienza" in src):
            return "科技"

        # 5. 国际（兜底）
        return "国际"

    def _process_headlines(self, raw_items):
        """
        处理新闻：过滤 → 分类 → 筛选

        Args:
            raw_items: 原始新闻列表

        Returns:
            dict: {"section": "headline", "items": [...]}
        """
        result = []

        for item in raw_items:
            # 跳过无标题
            if not item.get("title"):
                continue

            # 第一步：排除非新闻内容
            if self._is_excluded(item):
                continue

            # 第二步：分类
            item_category = self._classify_item(item)

            # 第三步：筛选目标类别
            if item_category != self.category:
                continue

            # 提取链接
            link = (
                item.get("canonical", [{}])[0].get("href") or
                item.get("alternate", [{}])[0].get("href") or
                item.get("link") or ""
            )

            # 提取摘要
            summary = item.get("summaryText")
            if not summary:
                if isinstance(item.get("summary"), dict):
                    summary = item.get("summary", {}).get("content", "")
                else:
                    summary = item.get("summary", "")

            # 构建结果
            result.append({
                "id": f"H{len(result) + 1}",
                "title": item["title"],
                "summary": summary or "",
                "link": link,
                "source": item.get("origin", {}).get("title") or item.get("source") or "",
                "published": item.get("published"),
            })

        return {
            "section": "headline",
            "items": result,
        }
