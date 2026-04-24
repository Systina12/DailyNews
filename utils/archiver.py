"""
新闻归档模块

在 realtime_workflow 链条中调用：
  评分 → 缓存 → 归档 → 吹哨

存储结构：archive/YYYY/MM/DD/important/{news_id}.json
归档字段：id, title, content, link, source, published, tags, importance_score, category, archived_at
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import settings
from utils.logger import get_logger

logger = get_logger("archiver")


def _item_id(item: Dict) -> str:
    """与 CacheManager 保持一致：优先 RSS id，否则 title|published。"""
    rss_id = item.get("id") or item.get("guid") or ""
    if rss_id:
        return f"rss_{rss_id}"
    title = item.get("title", "")
    published = str(item.get("published", ""))
    return "hash_" + hashlib.md5(f"{title}|{published}".encode()).hexdigest()


def _extract_content(item: Dict) -> str:
    summary = item.get("summary")
    if isinstance(summary, dict):
        return summary.get("content", "") or ""
    if isinstance(summary, str):
        return summary
    return item.get("summaryText", "") or ""


def _extract_link(item: Dict) -> str:
    link = item.get("link", "") or ""
    if link:
        return link
    for key in ("alternate", "canonical"):
        val = item.get(key)
        if isinstance(val, list) and val:
            href = val[0].get("href", "") if isinstance(val[0], dict) else ""
            if href:
                return href
    return ""


def _extract_source(item: Dict) -> str:
    origin = item.get("origin") or {}
    if isinstance(origin, dict):
        return origin.get("title", "") or ""
    return ""


def _extract_tags(item: Dict) -> List[str]:
    raw = item.get("categories") or []
    tags = []
    for c in raw:
        if isinstance(c, dict):
            v = c.get("id") or c.get("label") or c.get("name") or ""
        else:
            v = str(c)
        if v:
            tags.append(v)
    return tags


def _extract_published(item: Dict) -> str:
    ts = item.get("published")
    if isinstance(ts, (int, float)) and ts > 0:
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except (ValueError, OSError):
            pass
    return str(ts) if ts else ""


def _serialize_entry(item: Dict, score: int, category: str) -> Dict:
    return {
        "id": _item_id(item),
        "title": item.get("title", ""),
        "content": _extract_content(item),
        "link": _extract_link(item),
        "source": _extract_source(item),
        "published": _extract_published(item),
        "tags": _extract_tags(item),
        "importance_score": score,
        "category": category,
        "archived_at": datetime.now(timezone.utc).isoformat(),
    }


def _archive_path(news_id: str, date_str: str) -> Path:
    """news_id：新闻唯一标识；date_str：YYYY-MM-DD 格式日期字符串。"""
    p = settings.ARCHIVE_DIR / date_str[:4] / date_str[5:7] / date_str[8:10] / "important"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{news_id}.json"


def archive_item(item: Dict, score: int, category: str) -> bool:
    """
    归档单条已评分新闻。
    已存在则跳过（同一天不重复写入）。
    返回是否成功写入。
    """
    entry = _serialize_entry(item, score, category)
    news_id = entry["id"]
    today = datetime.now().strftime("%Y-%m-%d")
    fpath = _archive_path(news_id, today)

    if fpath.exists():
        return False

    try:
        fpath.write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception as e:
        logger.error(f"写归档失败 {fpath}: {e}")
        return False


def archive_batch(
    items_with_scores: List[Tuple[Dict, int]],
    category: str,
    threshold: Optional[int] = None,
) -> int:
    """
    批量归档：只归档 score >= threshold 的条目。
    在 realtime_workflow 中调用。
    默认阈值使用 settings.ARCHIVE_THRESHOLD。
    """
    if threshold is None:
        threshold = settings.ARCHIVE_THRESHOLD
    archived = 0
    for item, score in items_with_scores:
        if score < threshold:
            continue
        if archive_item(item, score, category):
            archived += 1
    if archived:
        logger.info(f"[{category}] 归档 {archived} 条重要新闻（阈值 ≥ {threshold}）")
    return archived
