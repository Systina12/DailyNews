# preprocessing/filters.py
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple

RUSSIA_LABEL = "user/-/label/俄罗斯"


def _item_text(item: Dict[str, Any]) -> str:
    title = str(item.get("title") or "")
    summary = str(item.get("summaryText") or "")
    summary2 = ""
    if isinstance(item.get("summary"), dict):
        summary2 = str(item.get("summary", {}).get("content") or "")
    else:
        summary2 = str(item.get("summary") or "")

    src = str((item.get("origin") or {}).get("title") or item.get("source") or "")
    link = ""
    canonical = item.get("canonical")
    if isinstance(canonical, list) and canonical:
        link = canonical[0].get("href", "") or ""
    if not link:
        alternate = item.get("alternate")
        if isinstance(alternate, list) and alternate:
            link = alternate[0].get("href", "") or ""
    if not link:
        link = str(item.get("link") or "")

    return " ".join([title, summary, summary2, src, link]).lower()


def _is_russia(item: Dict[str, Any]) -> bool:
    cats = item.get("categories", [])
    if not isinstance(cats, list):
        return False
    return RUSSIA_LABEL in [str(c) for c in cats]


def _parse_csv_env(name: str) -> List[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    parts = re.split(r"[,\n;]+", raw)
    return [p.strip().lower() for p in parts if p.strip()]


# 你可以用环境变量继续加词：
# RUSSIA_DENOISE_BLACKLIST="horoscope,celebrity,recipe,гороскоп,погода"
DEFAULT_BLACKLIST = [
    "horoscope", "astrology", "celebrity", "gossip", "recipe", "travel", "tourism",
    "fashion", "beauty", "quiz", "podcast", "review", "movie", "film", "music", "tv", "show",
    "football", "hockey", "match", "tournament", "weather",
    "星座", "八卦", "明星", "娱乐", "美食", "菜谱", "旅游", "体育", "比赛", "天气",
    "гороскоп", "астрол", "рецеп", "путеше", "туризм", "спорт", "футбол", "хокке", "погода",
]

DEFAULT_WHITELIST = [
    "russia", "russian", "moscow", "kremlin", "putin", "ukraine", "nato",
    "sanction", "oil", "gas", "energy", "nuclear", "missile", "defense", "war",
    "俄罗斯", "莫斯科", "克里姆林宫", "普京", "乌克兰", "北约", "制裁", "石油", "天然气", "能源", "核", "导弹", "战争",
    "росси", "москв", "кремл", "путин", "украин", "нато", "санкц", "нефт", "газ", "энерг", "ядер", "рак", "войн",
]


def _score_russia(item: Dict[str, Any], whitelist: List[str], blacklist: List[str]) -> int:
    text = _item_text(item)
    score = 0
    if any(bad in text for bad in blacklist):
        return -999  # 直接丢
    for kw in whitelist:
        if kw and kw in text:
            score += 2
    # 标题太短一般更像噪声
    if len(text) < 40:
        score -= 1
    return score


def filter_ru(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    RUSSIA_FILTER_POLICY:
      - exclude: 旧行为，直接删除俄罗斯
      - include: 不处理
      - denoise: 保留但降噪（默认）
    """
    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        out = dict(data)
        out["items"] = []
        return out

    policy = os.getenv("RUSSIA_FILTER_POLICY", "denoise").strip().lower()

    if policy == "include":
        out = dict(data)
        out["items"] = [it for it in items if isinstance(it, dict)]
        return out

    if policy == "exclude":
        kept = [it for it in items if isinstance(it, dict) and not _is_russia(it)]
        out = dict(data)
        out["items"] = kept
        return out

    # denoise
    max_keep = int(os.getenv("RUSSIA_DENOISE_MAX_KEEP", "60"))
    min_score = int(os.getenv("RUSSIA_DENOISE_MIN_SCORE", "1"))

    blacklist = [x.lower() for x in (DEFAULT_BLACKLIST + _parse_csv_env("RUSSIA_DENOISE_BLACKLIST"))]
    whitelist = [x.lower() for x in (DEFAULT_WHITELIST + _parse_csv_env("RUSSIA_DENOISE_WHITELIST"))]

    non_ru = [it for it in items if isinstance(it, dict) and not _is_russia(it)]
    ru = [it for it in items if isinstance(it, dict) and _is_russia(it)]

    scored: List[Tuple[int, int, Dict[str, Any]]] = []
    for it in ru:
        score = _score_russia(it, whitelist=whitelist, blacklist=blacklist)
        if score < min_score:
            continue
        try:
            published = int(it.get("published") or 0)
        except Exception:
            published = 0
        scored.append((score, published, it))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    ru_kept = [it for _, _, it in scored[:max_keep]]

    out = dict(data)
    out["items"] = non_ru + ru_kept
    return out


def filter_high_risk_items(items):
    return [item for item in items if item.get("ds_risk") == "high"]


def filter_low_risk_items(items):
    return [item for item in items if item.get("ds_risk") == "low"]