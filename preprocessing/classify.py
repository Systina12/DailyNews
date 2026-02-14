import re

class Classify:


    def __init__(self,category):
        pass


    def _process_headlines(self,raw_items):

        PREFIX = "H"

        BLOCK_KEYS = [
            "sneak peek","preview","episode","season",
            "super bowl","nfl","olympic","world cup",
            "beat ","wins ","defeats ",
            "music","singer","band","album","song",
            "eagles","henley",
            "dog show","kennel","show where","wins gold",
            "curling","skating","athlete",
            "60 minutes","48 hours",
            "face the nation","sunday morning",
            "almanac","passage:",
            "interview","transcript",
            "the takeout","weekend news",
        ]

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

        # ---------- 是否屏蔽 ----------
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
            if any(k in text for k in BLOCK_KEYS):
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

        # ---------- 主处理 ----------
        result = []

        for it in raw_items:
            if not it.get("title"):
                continue

            if is_blocked(it):
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


