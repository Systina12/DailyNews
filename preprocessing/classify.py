# preprocessing/classify.py
from __future__ import annotations

import math
import os
import re
from typing import Any, Dict, List, Tuple


class Classify:
    """
    新闻分类器

    支持类别：头条、政治、财经、科技、国际

    现在优先级：
    1) 订阅源/标签直通（FreshRSS 的 categories / origin.title）
    2) 关键词规则（你原来的）
    3) 国际兜底
    """

    def __init__(self, category: str):
        self.category = category

    # ---------- 工具函数 ----------
    def _safe_link(self, item: Dict[str, Any]) -> str:
        link = ""
        canonical = item.get("canonical")
        if isinstance(canonical, list) and canonical:
            link = canonical[0].get("href", "") or ""
        if not link:
            alternate = item.get("alternate")
            if isinstance(alternate, list) and alternate:
                link = alternate[0].get("href", "") or ""
        if not link:
            link = item.get("link", "") or ""
        return str(link)

    def _full_text(self, item: Dict[str, Any]) -> str:
        title = str(item.get("title") or "")
        src = str((item.get("origin") or {}).get("title") or item.get("source") or "")
        cats = " ".join(str(c) for c in (item.get("categories") or []) if c)
        summary = str(item.get("summaryText") or "")
        summary2 = ""
        if isinstance(item.get("summary"), dict):
            summary2 = str(item.get("summary", {}).get("content") or "")
        else:
            summary2 = str(item.get("summary") or "")
        link = self._safe_link(item)
        return " ".join([title, src, cats, summary, summary2, link]).lower()

    # ---------- 你原来的硬排除 ----------
    def _is_hard_excluded(self, item: Dict[str, Any]) -> bool:
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        link = self._safe_link(item).lower()
        full_text = self._full_text(item)

        hard_exclude = [
            "sneak peek", "preview", "episode", "season",
            "super bowl", "nfl", "olympic", "world cup", "beat ", "wins ", "defeats ",
            "athlete", "curling", "skating",
            "music", "singer", "band", "album", "song",
            "dog show", "kennel",
            "60 minutes", "48 hours", "face the nation", "sunday morning",
            "the takeout", "weekend news", "almanac", "passage:",
        ]
        if any(kw in full_text for kw in hard_exclude):
            return True
        if "cbsnews.com/video/" in link or "60-minutes-transcript" in link:
            return True
        if ("cbs" in src or "bbc" in src):
            if re.match(r"^\d{1,2}/\d{1,2}", title) or re.match(r"^\d{4}:\s", title):
                return True
        return False

    def _is_soft_content(self, item: Dict[str, Any]) -> bool:
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        soft_keywords = [
            "video", "interview", "transcript", "nature", "art", "museum", "culture",
            "review", "book", "film", "celebrity", "entertainment",
        ]
        if any(kw in title for kw in soft_keywords):
            return True
        if "bbc" in src and any(kw in title for kw in ["culture", "future", "travel", "worklife"]):
            return True
        if any(s in src for s in ["cbs", "nbc", "abc"]):
            if any(kw in title for kw in ["celebrity", "sports", "entertainment"]):
                return True
        return False

    # ---------- 新增：订阅源/标签直通分类 ----------
    def _classify_by_labels(self, item: Dict[str, Any]) -> str | None:
        src = (item.get("origin", {}).get("title") or "").lower()
        categories = item.get("categories", []) or []
        cats = " ".join(str(c).lower() for c in categories)

        def hit(*tokens: str) -> bool:
            return any(t in src or t in cats for t in tokens)

        # 头条：保留你原来的“top/头条”逻辑
        if hit("top", "头条"):
            return "头条"

        # 政治/财经/科技/国际：按 label/来源名做直通
        if hit("label/政治", "政治", "politics", "politica"):
            return "政治"
        if hit("label/财经", "财经", "business", "econom", "economia"):
            return "财经"
        if hit("label/科技", "科技", "tech", "science", "scienza"):
            return "科技"

        # 俄罗斯 label：你现在只有一个统一源，先把它归到“国际”再让国际规则去抽样
        if hit("label/俄罗斯", "俄罗斯"):
            return "国际"

        if hit("label/国际", "国际", "world", "international", "全球", "环球"):
            return "国际"

        return None

    # ---------- 关键词兜底（保留你原来的） ----------
    def _classify_by_keywords(self, item: Dict[str, Any]) -> str:
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        categories = item.get("categories", []) or []
        cats = " ".join(str(c).lower() for c in categories)

        if ("top" in src or "top" in cats or "头条" in src or "头条" in cats) and not self._is_soft_content(item):
            return "头条"

        political_keywords = [
            "election", "vote", "parliament", "government", "president", "prime minister",
            "policy", "sanction", "cabinet", "congress", "senate", "politic",
            "选举", "政府", "总统", "议会", "内阁", "制裁",
        ]
        if any(kw in title for kw in political_keywords) or "politics" in src or "politica" in src:
            return "政治"

        econ_keywords = [
            "economy", "economic", "market", "stock", "inflation", "bank", "finance", "business",
            "economia", "borsa", "mercato",
            "经济", "股市", "通胀", "银行",
        ]
        if any(kw in title for kw in econ_keywords) or "business" in src or "economia" in src:
            return "财经"

        tech_keywords = [
            "tech", "technology", "ai", "artificial intelligence", "software", "chip", "science", "scienza",
            "科技", "人工智能", "半导体",
        ]
        if any(kw in title for kw in tech_keywords) or "tech" in src or "science" in src or "scienza" in src:
            return "科技"

        return "国际"

    def _classify_item(self, item: Dict[str, Any]) -> str:
        # 先走订阅源/标签直通
        by_label = self._classify_by_labels(item)
        if by_label:
            # 头条要额外过滤软内容
            if by_label == "头条" and self._is_soft_content(item):
                return "国际"
            return by_label

        # 再走关键词兜底
        return self._classify_by_keywords(item)

    # ---------- 新增：国际“垃圾桶”动态保留 ----------
    def _reduce_international(self, selected_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        n = len(selected_raw)
        low_water = int(os.getenv("INTL_KEEP_LOW_WATERMARK", "10"))   # 少于等于这个数：全留
        ratio = float(os.getenv("INTL_KEEP_RATIO", "0.2"))          # 多的时候：按比例留
        min_keep = int(os.getenv("INTL_MIN_KEEP", "10"))             # 下限
        max_keep = int(os.getenv("INTL_MAX_KEEP", "50"))             # 上限

        if n <= low_water:
            return selected_raw

        target = int(math.ceil(n * ratio))
        target = max(min_keep, target)
        target = min(max_keep, target)

        important = [
            # 英文
            "war", "ceasefire", "missile", "nuclear", "sanction", "coup", "terror",
            "earthquake", "tsunami", "flood", "outbreak", "pandemic",
            "summit", "diplom", "un ", "g7", "eu ", "nato",
            "central bank", "inflation", "rate hike", "gdp",
            # 中文
            "战争", "停火", "导弹", "核", "制裁", "政变", "恐袭",
            "地震", "海啸", "洪水", "疫情", "爆发",
            "峰会", "外交", "联合国", "七国集团", "欧盟", "北约",
            "央行", "加息", "通胀", "gdp",
            # 俄文/词干（让俄文标题也有机会“重要”）
            "войн", "перемир", "рак", "ядер", "санкц", "переворот", "теракт",
            "землетр", "наводн", "эпидем", "саммит", "диплом", "оон", "нато",
        ]
        penalty = [
            "travel", "tourism", "recipe", "fashion", "beauty", "celebrity", "gossip",
            "movie", "film", "music", "tv", "show", "podcast", "quiz",
            "旅游", "菜谱", "时尚", "美妆", "明星", "八卦", "电影", "音乐", "综艺", "播客", "测验",
            "путеше", "рецеп", "мода", "красот", "шоу", "фильм", "музык",
        ]

        scored: List[Tuple[int, int, Dict[str, Any]]] = []
        for it in selected_raw:
            text = self._full_text(it)
            s = 0
            for kw in important:
                if kw in text:
                    s += 2
            for kw in penalty:
                if kw in text:
                    s -= 2
            try:
                published = int(it.get("published") or 0)
            except Exception:
                published = 0
            scored.append((s, published, it))

        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        kept = [it for _, _, it in scored[:target]]

        # 输出时按时间倒序更直观（通常 RSS 已经是新到旧，但这里保险）
        kept.sort(key=lambda it: int(it.get("published") or 0), reverse=True)
        return kept

    # ---------- 主处理 ----------
    def _process_headlines(self, raw_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        selected_raw: List[Dict[str, Any]] = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if not title or not str(title).strip():
                continue

            if self._is_hard_excluded(item):
                continue

            item_category = self._classify_item(item)
            if item_category != self.category:
                continue

            selected_raw.append(item)

        # 国际：动态抽样（垃圾桶治理）
        if self.category == "国际":
            selected_raw = self._reduce_international(selected_raw)

        # 构建输出
        result = []
        for idx, item in enumerate(selected_raw, start=1):
            link = self._safe_link(item)
            summary = item.get("summaryText")
            if not summary:
                if isinstance(item.get("summary"), dict):
                    summary = item.get("summary", {}).get("content", "")
                else:
                    summary = item.get("summary", "")
            result.append(
                {
                    "id": f"H{idx}",
                    "title": item.get("title", ""),
                    "summary": summary or "",
                    "link": link,
                    "source": (item.get("origin") or {}).get("title") or item.get("source") or "",
                    "published": item.get("published"),
                }
            )

        return {"section": "headline", "items": result}