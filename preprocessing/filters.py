# preprocessing/filters.py
"""
新闻过滤器集合

历史行为：
- filter_ru() 会把带 “俄罗斯” label 的新闻全部剔除

现在行为（可配置）：
- RUSSIA_FILTER_POLICY=exclude  -> 旧行为：排除俄罗斯
- RUSSIA_FILTER_POLICY=include  -> 完全保留俄罗斯（不做处理）
- RUSSIA_FILTER_POLICY=denoise  -> 保留俄罗斯，但做降噪（默认）

降噪可配：
- RUSSIA_DENOISE_MAX_KEEP：俄罗斯新闻最多保留多少条（默认 60）
- RUSSIA_DENOISE_MIN_SCORE：最低分阈值（默认 1）
- RUSSIA_DENOISE_BLACKLIST：逗号分隔，命中直接丢（可追加你遇到的噪声词）
- RUSSIA_DENOISE_WHITELIST：逗号分隔，命中加分（可追加高信号主题词）
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple

from config import settings
from utils.logger import get_logger

logger = get_logger("filters")

RUSSIA_LABEL = getattr(settings, "RUSSIA_LABEL", "user/-/label/俄罗斯")


def _parse_csv_env(name: str) -> List[str]:
    raw = os.getenv(name, "")
    if not raw or not raw.strip():
        return []
    parts = re.split(r"[,\n;]+", raw)
    return [p.strip().lower() for p in parts if p.strip()]


# “高信号”主题（命中会加分）：偏政经军、能源、制裁、地缘
_DEFAULT_WHITELIST = [
    # 英文
    "russia", "russian", "moscow", "kremlin", "putin", "ukraine", "nato",
    "sanction", "g7", "un", "iaea", "oil", "gas", "energy", "nuclear",
    "missile", "defense", "war", "ceasefire", "negotiation",
    # 中文
    "俄罗斯", "俄方", "莫斯科", "克里姆林宫", "普京", "乌克兰", "北约", "制裁",
    "七国集团", "联合国", "国际原子能机构", "石油", "天然气", "能源", "核",
    "导弹", "国防", "战争", "停火", "谈判",
    # 俄文/词干（别追求完美，先实用）
    "росси", "москв", "кремл", "путин", "украин", "нато", "санкц",
    "нефт", "газ", "энерг", "ядер", "рак", "обор", "войн", "переговор",
]

# “低信号/噪声”主题（命中会扣分；黑名单则是命中直接丢）
_DEFAULT_PENALTY = [
    # 英文
    "horoscope", "astrology", "celebrity", "gossip", "recipe", "travel", "tourism",
    "fashion", "beauty", "game", "gaming", "quiz", "podcast", "review",
    "movie", "film", "music", "concert", "tv", "show",
    "football", "hockey", "match", "tournament", "sport",
    "weather",
    # 中文
    "星座", "八卦", "明星", "娱乐", "综艺", "电影", "电视剧", "音乐", "演唱会",
    "体育", "比赛", "足球", "冰球", "旅游", "美食", "菜谱", "测验", "播客",
    "天气",
    # 俄文/词干
    "гороскоп", "астрол", "зодиак", "рецеп", "путеше", "туризм",
    "мода", "красот", "игр", "спорт", "футбол", "хокке", "матч",
    "концерт", "музык", "фильм", "сериал", "шоу", "погода", "тест",
]

# 命中就直接丢（你可以用环境变量追加）
_DEFAULT_BLACKLIST = [
    # 常见“内容农场”/“导流”词
    "促销", "优惠", "折扣", "sponsored", "advertisement",
]


def _get_item_link(item: Dict[str, Any]) -> str:
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


def _item_text(item: Dict[str, Any]) -> str:
    parts: List[str] = []
    for k in ("title", "summaryText"):
        v = item.get(k)
        if v:
            parts.append(str(v))
    summary = item.get("summary")
    if isinstance(summary, dict):
        parts.append(str(summary.get("content", "") or ""))
    elif summary:
        parts.append(str(summary))
    origin_title = (item.get("origin") or {}).get("title")
    if origin_title:
        parts.append(str(origin_title))
    link = _get_item_link(item)
    if link:
        parts.append(link)

    return " ".join(p for p in parts if p).lower()


def _is_russia_item(item: Dict[str, Any]) -> bool:
    cats = item.get("categories", [])
    if not isinstance(cats, list):
        return False
    return any(str(c) == RUSSIA_LABEL for c in cats)


def _score_russia_item(text: str, whitelist: List[str], penalty: List[str]) -> int:
    score = 0
    for kw in whitelist:
        if kw and kw in text:
            score += 2
    for kw in penalty:
        if kw and kw in text:
            score -= 2

    # 轻微结构性降噪：标题太短/像公告/像导流
    if len(text) < 30:
        score -= 1
    if any(x in text for x in ["press release", "statement", "观点", "评论", "opinion"]):
        score -= 2
    if any(x in text for x in ["video", "视频", "фото", "видео"]):
        score -= 1

    return score


def _denoise_russia_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    max_keep = int(os.getenv("RUSSIA_DENOISE_MAX_KEEP", "60"))
    min_score = int(os.getenv("RUSSIA_DENOISE_MIN_SCORE", "1"))

    env_blacklist = _parse_csv_env("RUSSIA_DENOISE_BLACKLIST")
    env_whitelist = _parse_csv_env("RUSSIA_DENOISE_WHITELIST")

    blacklist = [x.lower() for x in (_DEFAULT_BLACKLIST + env_blacklist) if x]
    whitelist = [x.lower() for x in (_DEFAULT_WHITELIST + env_whitelist) if x]
    penalty = [x.lower() for x in _DEFAULT_PENALTY if x]

    scored: List[Tuple[int, int, Dict[str, Any]]] = []
    kept_after_blacklist: List[Dict[str, Any]] = []

    for it in items:
        title = (it.get("title") or "").strip()
        if not title:
            continue

        text = _item_text(it)

        # 黑名单：命中直接丢（强降噪）
        if any(bad in text for bad in blacklist):
            continue

        kept_after_blacklist.append(it)

        published = 0
        try:
            published = int(it.get("published") or 0)
        except Exception:
            published = 0

        score = _score_russia_item(text, whitelist=whitelist, penalty=penalty)
        scored.append((score, published, it))

    # 先按阈值筛
    passed = [(s, p, it) for (s, p, it) in scored if s >= min_score]

    # 如果阈值过严导致全空：退化成“只做黑名单 + 按时间取前 N”
    if not passed:
        fallback = kept_after_blacklist[:]
        fallback.sort(key=lambda x: int(x.get("published") or 0), reverse=True)
        return fallback[:max_keep]

    # 按分数/时间排序取前 N
    passed.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [it for (_, _, it) in passed[:max_keep]]


def filter_ru(data: Dict[str, Any], policy: str | None = None) -> Dict[str, Any]:
    """
    俄罗斯条目处理（兼容旧函数名）

    policy:
      - exclude: 删除所有俄罗斯 label 条目（旧行为）
      - include: 全部保留
      - denoise: 保留但降噪（默认）
    """
    if not isinstance(data, dict):
        return {"items": []}

    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        out = dict(data)
        out["items"] = []
        return out

    _policy = (policy or os.getenv("RUSSIA_FILTER_POLICY", "denoise")).strip().lower()
    ru_items = [it for it in items if isinstance(it, dict) and _is_russia_item(it)]

    if _policy == "exclude":
        kept = [it for it in items if isinstance(it, dict) and not _is_russia_item(it)]
        logger.info(f"Russia policy=exclude total={len(items)} ru={len(ru_items)} kept={len(kept)}")
        out = dict(data)
        out["items"] = kept
        return out

    if _policy == "include":
        logger.info(f"Russia policy=include total={len(items)} ru={len(ru_items)} kept={len(items)}")
        out = dict(data)
        out["items"] = [it for it in items if isinstance(it, dict)]
        return out

    # 默认 denoise
    ru_kept = _denoise_russia_items(ru_items)
    ru_kept_ids = {id(it) for it in ru_kept}

    kept: List[Dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if _is_russia_item(it):
            if id(it) in ru_kept_ids:
                kept.append(it)
        else:
            kept.append(it)

    logger.info(
        f"Russia policy=denoise total={len(items)} ru={len(ru_items)} kept_ru={len(ru_kept)} kept_total={len(kept)}"
    )
    out = dict(data)
    out["items"] = kept
    return out


def filter_high_risk_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """过滤出 ds_risk == 'high' 的条目"""
    return [item for item in items if item.get("ds_risk") == "high"]


def filter_low_risk_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """过滤出 ds_risk == 'low' 的条目"""
    return [item for item in items if item.get("ds_risk") == "low"]