import re


class Classify:
    """
    新闻分类器

    流程：硬排除 → 分类（头条需额外检查软内容）→ 筛选
    支持5个类别：头条、政治、财经、科技、国际
    """

    def __init__(self, category):
        """
        Args:
            category: 要提取的类别（头条/政治/财经/科技/国际）
        """
        self.category = category

    def _is_hard_excluded(self, item):
        """
        硬排除：娱乐、体育、节目等明确不要的内容

        Returns:
            bool: True表示应该完全排除
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        link = (
            item.get("canonical", [{}])[0].get("href") or
            item.get("alternate", [{}])[0].get("href") or
            item.get("link") or ""
        ).lower()

        # 收集所有文本
        text_parts = [
            title,
            item.get("summaryText", ""),
            item.get("summary", {}).get("content", "") if isinstance(item.get("summary"), dict) else "",
            str(item.get("summary", "")),
            link
        ]
        full_text = " ".join(str(p) for p in text_parts if p).lower()

        # 硬排除关键词：娱乐、体育、节目
        hard_exclude = [
            # 节目/预告
            "sneak peek", "preview", "episode", "season",
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
        ]

        if any(kw in full_text for kw in hard_exclude):
            return True

        # CBS视频和文字稿
        if "cbsnews.com/video/" in link or "60-minutes-transcript" in link:
            return True

        # 美媒节目型标题（日期前缀）
        if ("cbs" in src or "bbc" in src):
            if re.match(r"^\d{1,2}/\d{1,2}", title) or re.match(r"^\d{4}:\s", title):
                return True

        return False

    def _is_soft_content(self, item):
        """
        软内容判断：视频、访谈、文化等（只影响"头条"分类）

        Returns:
            bool: True表示是软内容
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()

        # 软内容关键词
        soft_keywords = [
            "video", "interview", "transcript",
            "nature", "art", "museum", "culture",
            "review", "book", "film", "celebrity", "entertainment"
        ]

        if any(kw in title for kw in soft_keywords):
            return True

        # BBC软内容栏目
        if "bbc" in src and any(kw in title for kw in ["culture", "future", "travel", "worklife"]):
            return True

        # 美媒娱乐/生活
        if any(s in src for s in ["cbs", "nbc", "abc"]):
            if any(kw in title for kw in ["celebrity", "sports", "entertainment"]):
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

        # 1. 头条：来源标记为top 且 不是软内容
        if ("top" in src or "top" in cats or "头条" in src or "头条" in cats) and not self._is_soft_content(item):
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
        处理新闻：硬排除 → 分类 → 筛选

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

            # 第一步：硬排除（娱乐、体育、节目等）
            if self._is_hard_excluded(item):
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
