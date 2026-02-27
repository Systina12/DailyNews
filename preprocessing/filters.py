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
    俄罗斯新闻过滤策略
    
    俄罗斯源是"大一统"源，包含政治、经济、娱乐、体育等所有内容。
    需要激进的黑名单过滤，去掉垃圾内容，保留高质量新闻。
    过滤后的新闻会并入正常分类流程（政治/财经/科技/国际）。
    
    RUSSIA_FILTER_POLICY:
      - exclude: 直接删除所有俄罗斯新闻
      - include: 保留所有，不做任何过滤
      - aggressive (默认): 激进黑名单过滤
    """
    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        out = dict(data)
        out["items"] = []
        return out

    policy = os.getenv("RUSSIA_FILTER_POLICY", "aggressive").strip().lower()

    if policy == "include":
        # 完全不过滤
        out = dict(data)
        out["items"] = [it for it in items if isinstance(it, dict)]
        return out

    if policy == "exclude":
        # 删除所有俄罗斯新闻
        kept = [it for it in items if isinstance(it, dict) and not _is_russia(it)]
        out = dict(data)
        out["items"] = kept
        return out

    # aggressive (默认): 激进黑名单过滤
    # 俄罗斯源是大杂烩，需要严格过滤
    blacklist = [x.lower() for x in (DEFAULT_BLACKLIST + _parse_csv_env("RUSSIA_DENOISE_BLACKLIST"))]

    non_ru = [it for it in items if isinstance(it, dict) and not _is_russia(it)]
    ru = [it for it in items if isinstance(it, dict) and _is_russia(it)]

    # 激进过滤：只要包含黑名单关键词就丢弃
    ru_filtered = []
    for it in ru:
        text = _item_text(it)
        # 黑名单过滤
        if any(bad in text for bad in blacklist):
            continue
        # 标题太短（<40字符）通常是垃圾
        if len(text.strip()) < 40:
            continue
        ru_filtered.append(it)

    out = dict(data)
    out["items"] = non_ru + ru_filtered
    return out


def filter_high_risk_items(items):
    return [item for item in items if item.get("ds_risk") == "high"]


def filter_low_risk_items(items):
    return [item for item in items if item.get("ds_risk") == "low"]