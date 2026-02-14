import re


class Classify:
    """
    新闻分类器

    支持5个类别：头条、政治、财经、科技、国际
    """

    # 硬政治关键词
    POLITICAL_KEYS = [
        "election", "vote", "parliament", "government", "president", "prime minister",
        "policy", "sanction", "cabinet", "congress", "senate", "politic",
        "选举", "政府", "总统", "议会", "内阁", "制裁"
    ]

    # 财经关键词
    ECON_KEYS = [
        "economy", "economic", "market", "stock", "inflation", "bank", "finance", "business",
        "economia", "borsa", "mercato", "经济", "股市", "通胀", "银行"
    ]

    # 科技关键词
    TECH_KEYS = [
        "tech", "technology", "ai", "artificial intelligence", "software", "chip",
        "science", "scienza", "科技", "人工智能", "半导体"
    ]

    # 明确排除的软内容关键词（娱乐、体育等）
    BLOCK_KEYS = [
        "sneak peek", "preview", "episode", "season",
        "super bowl", "nfl", "olympic", "world cup",
        "beat ", "wins ", "defeats ",
        "music", "singer", "band", "album", "song",
        "eagles", "henley",
        "dog show", "kennel", "show where", "wins gold",
        "curling", "skating", "athlete",
        "60 minutes", "48 hours",
        "face the nation", "sunday morning",
        "almanac", "passage:",
        "interview", "transcript",
        "the takeout", "weekend news",
    ]

    def __init__(self, category):
        """
        初始化分类器

        Args:
            category: 要提取的类别，可选值：头条、政治、财经、科技、国际
        """
        self.category = category

    def _is_soft_content(self, item):
        """
        判断是否是软内容（视频、访谈、文化、生活方式等）

        Args:
            item: 新闻条目

        Returns:
            bool: True表示是软内容，应该排除
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()

        # 视频 / 节目 / 文化 / 生活方式
        soft_keywords = [
            "video", "transcript", "interview", "sunday morning",
            "the takeout", "nature", "art", "museum", "culture",
            "review", "book", "film"
        ]

        if any(k in title for k in soft_keywords):
            return True

        # BBC 特有软内容
        if src and "bbc" in src:
            bbc_soft = ["culture", "future", "travel", "worklife"]
            if any(k in title for k in bbc_soft):
                return True

        # 美媒 Top Stories 的娱乐 / 生活
        if src and any(s in src for s in ["cbs", "nbc", "abc"]):
            us_soft = ["celebrity", "sports", "entertainment"]
            if any(k in title for k in us_soft):
                return True

        return False

    def _classify_item(self, item):
        """
        将单个新闻分类到5个类别之一

        Args:
            item: 新闻条目

        Returns:
            str: 类别名称（头条、政治、财经、科技、国际）
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        categories = item.get("categories", [])
        cats = " ".join(str(c).lower() for c in categories)

        # 1️⃣ 头条（必须是硬新闻）
        if (("top" in src or "top" in cats) and not self._is_soft_content(item)):
            return "头条"

        # 2️⃣ 政治
        if (any(k in title for k in self.POLITICAL_KEYS) or
            "politica" in src or "politics" in src):
            return "政治"

        # 3️⃣ 财经
        if (any(k in title for k in self.ECON_KEYS) or
            "economia" in src or "business" in src):
            return "财经"

        # 4️⃣ 科技
        if (any(k in title for k in self.TECH_KEYS) or
            "scienza" in src or "science" in src or "tech" in src):
            return "科技"

        # 5️⃣ 国际（兜底）
        return "国际"

    def _process_headlines(self, raw_items):
        """
        处理新闻：过滤、分类、提取指定类别

        Args:
            raw_items: 原始新闻列表

        Returns:
            dict: 包含section和items的字典
        """
        PREFIX = "H"

        # ---------- 文本收集 ----------
        def collect_text(it):
            parts = [
                it.get("title"),
                it.get("summaryText"),
                it.get("summary", {}).get("content")
                    if isinstance(it.get("summary"), dict)
                    else None,
                it.get("summary") if isinstance(it.get("summary"), str) else None,
                it.get("link"),
            ]
            return " ".join(p for p in parts if p).lower()

        # ---------- 是否屏蔽（硬排除） ----------
        def is_blocked(item):
            text = collect_text(item)
            src = (item.get("origin", {}).get("title") or "").lower()

            link = (
                item.get("canonical", [{}])[0].get("href")
                or item.get("alternate", [{}])[0].get("href")
                or item.get("link")
                or ""
            ).lower()

            title = (item.get("title") or "").lower()

            # 关键词
            if any(k in text for k in self.BLOCK_KEYS):
                return True

            # CBS transcript
            if "60-minutes-transcript" in link:
                return True

            # CBS 视频
            if "cbsnews.com/video/" in link:
                return True

            # 美媒节目型标题结构
            if ("cbs" in src or "bbc" in src):
                if re.match(r"^\d{1,2}/\d{1,2}", title):
                    return True
                if re.match(r"^\d{4}:\s", title):
                    return True

            return False

        # ---------- 第一步：过滤掉硬排除内容 ----------
        filtered_items = []
        for it in raw_items:
            if not it.get("title"):
                continue
            if is_blocked(it):
                continue
            filtered_items.append(it)

        # ---------- 第二步：分类并筛选目标类别 ----------
        result = []
        for it in filtered_items:
            # 分类
            item_category = self._classify_item(it)

            # 只保留目标类别
            if item_category != self.category:
                continue

            link = (
                it.get("canonical", [{}])[0].get("href")
                or it.get("alternate", [{}])[0].get("href")
                or it.get("link")
                or ""
            )

            result.append({
                "id": f"{PREFIX}{len(result)+1}",
                "title": it["title"],
                "summary": (
                    it.get("summaryText")
                    or (it.get("summary") or {}).get("content")
                    if isinstance(it.get("summary"), dict)
                    else it.get("summary")
                    or ""
                ),
                "link": link,
                "source": it.get("origin", {}).get("title")
                          or it.get("source")
                          or "",
                "published": it.get("published"),
            })

        return {
            "section": "headline",
            "items": result,
        }
