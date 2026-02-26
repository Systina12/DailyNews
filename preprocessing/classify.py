# preprocessing/classify.py

import os
import re
import math
from typing import Dict, List


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
        """硬排除：娱乐、体育、节目等明确不要的内容"""
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()

        # 安全提取链接
        link = ""
        canonical = item.get("canonical")
        if isinstance(canonical, list) and len(canonical) > 0:
            link = canonical[0].get("href", "")
        if not link:
            alternate = item.get("alternate")
            if isinstance(alternate, list) and len(alternate) > 0:
                link = alternate[0].get("href", "")
        if not link:
            link = item.get("link", "")
        link = (link or "").lower()

        # 收集所有文本
        text_parts = [
            title,
            item.get("summaryText", ""),
            item.get("summary", {}).get("content", "") if isinstance(item.get("summary"), dict) else "",
            str(item.get("summary", "")),
            link,
        ]
        full_text = " ".join(str(p) for p in text_parts if p).lower()

        hard_exclude = [
            # 节目/预告
            "sneak peek", "preview", "episode", "season",
            # 体育
            "super bowl", "nfl", "olympic", "world cup", "beat ", "wins ", "defeats ",
            "athlete", "curling", "skating",
            # 娱乐
            "music", "singer", "band", "album", "song", "eagles", "henley",
            # 展览/宠物
            "dog show", "kennel", "show where", "wins gold",
            # 电视栏目
            "60 minutes", "48 hours", "face the nation", "sunday morning",
            "the takeout", "weekend news", "almanac", "passage:",
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
        """软内容判断：视频、访谈、文化等（只影响"头条"分类）"""
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()

        soft_keywords = [
            "video", "interview", "transcript", "nature", "art", "museum", "culture",
            "review", "book", "film", "celebrity", "entertainment",
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
    用于处理包含俄罗斯新闻的分类逻辑，并进行关键词去噪音
    """

    # 噪音关键词黑名单（娱乐、体育、生活类）
    NOISE_KEYWORDS = [
        "horoscope", "astrology", "celebrity", "gossip", "recipe", "travel", "tourism",
        "fashion", "beauty", "quiz", "podcast", "movie", "film", "music", "tv", "show",
        "football", "hockey", "match", "tournament", "weather", "sport",
        "星座", "八卦", "明星", "娱乐", "美食", "菜谱", "旅游", "体育", "比赛", "天气",
        "гороскоп", "астрол", "рецеп", "путеше", "туризм", "спорт", "футбол", "хокке", "погода",
    ]

    def _is_noise(self, item):
        """判断是否为噪音内容（娱乐、体育、生活等）"""
        title = (item.get("title") or "").lower()
        summary = (item.get("summaryText") or "").lower()

        # 检查标题和摘要中是否包含噪音关键词
        text = f"{title} {summary}"
        return any(kw in text for kw in self.NOISE_KEYWORDS)

    def _classify_item(self, item):
        """
        根据俄罗斯新闻的特征进行分类
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        categories = item.get("categories", [])
        cats = " ".join(str(c).lower() for c in categories)

        # 特别处理俄罗斯新闻标签
        if "label/俄罗斯" in cats or "россия" in src:
            return "俄罗斯"

        # 如果新闻来自俄罗斯来源，或涉及俄罗斯相关事务
        russian_keywords = ["russia", "russian", "putin", "путин", "kremlin", "кремл", "moscow", "москв"]
        if any(kw in title for kw in russian_keywords):
            return "俄罗斯"

        # 调用父类的方法，如果新闻没涉及俄罗斯，按父类规则分类
        return super()._classify_item(item)

    def _process_headlines(self, items):
        """
        处理俄罗斯新闻：硬排除 → 去噪音 → 分类 → 筛选
        """
        result = []
        for item in items:
            # 1. 硬排除
            if self._is_hard_excluded(item):
                continue

            # 2. 分类
            predicted_category = self._classify_item(item)

            # 3. 筛选：只保留俄罗斯分类的新闻
            if predicted_category == self.category:
                # 4. 去噪音：过滤掉娱乐、体育等内容
                if not self._is_noise(item):
                    result.append(item)

        return {
            "section": "headline",
            "items": result
        }
