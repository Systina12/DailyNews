"""
新闻缓存模块

功能：
1. 存储已评分的新闻（避免重复LLM调用）
2. 存储已发送的告警（避免重复告警）
3. 24小时滚动窗口自动清理
4. 跨工作流数据复用

数据结构：
{
    "news_hash": {
        "title": "新闻标题",
        "link": "链接",
        "category": "分类",
        "importance_score": 85,
        "chinese_title": "中文标题",
        "chinese_summary": "中文摘要",
        "published": "2026-03-06T10:00:00",
        "cached_at": 1234567890.0,
        "alert_sent": true,
        "alert_sent_at": 1234567890.0
    }
}
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from utils.logger import get_logger

logger = get_logger("news_cache")


class NewsCache:
    """新闻缓存管理器"""
    
    def __init__(self, cache_file: Path = None, ttl_hours: float = 24):
        """
        初始化缓存
        
        Args:
            cache_file: 缓存文件路径
            ttl_hours: 缓存有效期（小时）
        """
        from config import settings
        self.cache_file = cache_file or (settings.DATA_DIR / "news_cache.json")
        self.ttl_seconds = ttl_hours * 3600
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """加载缓存文件"""
        if not self.cache_file.exists():
            logger.info(f"缓存文件不存在，创建新缓存: {self.cache_file}")
            return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            logger.info(f"加载缓存成功，共 {len(cache)} 条记录")
            return cache
        except Exception as e:
            logger.error(f"加载缓存失败: {e}，创建新缓存")
            return {}
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"缓存已保存，共 {len(self.cache)} 条记录")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def _generate_hash(self, title: str, link: str = "") -> str:
        """
        生成新闻唯一标识
        
        使用标题+链接的hash，避免同一新闻的重复处理
        """
        content = f"{title.strip().lower()}|{link.strip()}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def cleanup_expired(self) -> int:
        """
        清理过期缓存（超过TTL的记录）
        
        Returns:
            清理的记录数
        """
        now = time.time()
        expired_keys = []
        
        for key, data in self.cache.items():
            cached_at = data.get('cached_at', 0)
            if now - cached_at > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"清理过期缓存 {len(expired_keys)} 条")
            self._save_cache()
        
        return len(expired_keys)
    
    def get_cached_news(self, title: str, link: str = "") -> Optional[Dict]:
        """
        获取缓存的新闻数据
        
        Args:
            title: 新闻标题
            link: 新闻链接
            
        Returns:
            缓存的新闻数据，如果不存在或已过期则返回None
        """
        news_hash = self._generate_hash(title, link)
        
        if news_hash not in self.cache:
            return None
        
        data = self.cache[news_hash]
        cached_at = data.get('cached_at', 0)
        
        # 检查是否过期
        if time.time() - cached_at > self.ttl_seconds:
            logger.debug(f"缓存已过期: {title[:50]}")
            del self.cache[news_hash]
            self._save_cache()
            return None
        
        logger.debug(f"命中缓存: {title[:50]}")
        return data
    
    def cache_news(
        self,
        title: str,
        link: str = "",
        category: str = "",
        importance_score: Optional[int] = None,
        chinese_title: Optional[str] = None,
        chinese_summary: Optional[str] = None,
        published: str = "",
        alert_sent: bool = False
    ) -> str:
        """
        缓存新闻数据
        
        Args:
            title: 原始标题
            link: 链接
            category: 分类
            importance_score: 重要性评分
            chinese_title: 中文标题
            chinese_summary: 中文摘要
            published: 发布时间
            alert_sent: 是否已发送告警
            
        Returns:
            新闻hash
        """
        news_hash = self._generate_hash(title, link)
        now = time.time()
        
        # 如果已存在，更新数据
        if news_hash in self.cache:
            existing = self.cache[news_hash]
            if importance_score is not None:
                existing['importance_score'] = importance_score
            if chinese_title is not None:
                existing['chinese_title'] = chinese_title
            if chinese_summary is not None:
                existing['chinese_summary'] = chinese_summary
            if alert_sent:
                existing['alert_sent'] = True
                existing['alert_sent_at'] = now
            existing['cached_at'] = now  # 更新缓存时间
        else:
            # 创建新记录
            self.cache[news_hash] = {
                'title': title,
                'link': link,
                'category': category,
                'importance_score': importance_score,
                'chinese_title': chinese_title or title,
                'chinese_summary': chinese_summary,
                'published': published,
                'cached_at': now,
                'alert_sent': alert_sent,
                'alert_sent_at': now if alert_sent else None
            }
        
        self._save_cache()
        return news_hash
    
    def mark_alert_sent(self, title: str, link: str = "") -> bool:
        """
        标记新闻已发送告警
        
        Returns:
            是否成功标记
        """
        news_hash = self._generate_hash(title, link)
        
        if news_hash not in self.cache:
            logger.warning(f"尝试标记不存在的新闻: {title[:50]}")
            return False
        
        self.cache[news_hash]['alert_sent'] = True
        self.cache[news_hash]['alert_sent_at'] = time.time()
        self._save_cache()
        
        logger.debug(f"标记告警已发送: {title[:50]}")
        return True
    
    def is_alert_sent(self, title: str, link: str = "") -> bool:
        """
        检查是否已发送告警
        
        Returns:
            是否已发送
        """
        cached = self.get_cached_news(title, link)
        if not cached:
            return False
        
        return cached.get('alert_sent', False)
    
    def get_cached_scores(self, items: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        批量获取缓存的评分
        
        Args:
            items: 新闻列表
            
        Returns:
            (已缓存的新闻, 需要评分的新闻)
        """
        cached_items = []
        uncached_items = []
        
        for item in items:
            title = item.get('title', '')
            link = item.get('link', '')
            
            cached = self.get_cached_news(title, link)
            
            if cached and cached.get('importance_score') is not None:
                # 使用缓存数据
                item_with_cache = item.copy()
                item_with_cache['importance_score'] = cached['importance_score']
                item_with_cache['chinese_title'] = cached.get('chinese_title', title)
                item_with_cache['chinese_summary'] = cached.get('chinese_summary', '')
                item_with_cache['from_cache'] = True
                cached_items.append(item_with_cache)
            else:
                uncached_items.append(item)
        
        if cached_items:
            logger.info(f"从缓存获取 {len(cached_items)} 条新闻评分")
        if uncached_items:
            logger.info(f"需要评分 {len(uncached_items)} 条新闻")
        
        return cached_items, uncached_items
    
    def get_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            统计数据
        """
        now = time.time()
        total = len(self.cache)
        alert_sent = sum(1 for v in self.cache.values() if v.get('alert_sent'))
        scored = sum(1 for v in self.cache.values() if v.get('importance_score') is not None)
        
        # 按时间分组
        last_1h = sum(1 for v in self.cache.values() if now - v.get('cached_at', 0) < 3600)
        last_6h = sum(1 for v in self.cache.values() if now - v.get('cached_at', 0) < 6 * 3600)
        last_24h = sum(1 for v in self.cache.values() if now - v.get('cached_at', 0) < 24 * 3600)
        
        return {
            'total': total,
            'alert_sent': alert_sent,
            'scored': scored,
            'last_1h': last_1h,
            'last_6h': last_6h,
            'last_24h': last_24h,
            'cache_file': str(self.cache_file),
            'ttl_hours': self.ttl_seconds / 3600
        }


# 全局单例
_cache_instance = None


def get_news_cache() -> NewsCache:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = NewsCache()
    return _cache_instance
