"""
实时缓存管理器
实现按小时JSON文件存储、动态清理和吹哨状态管理
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
import hashlib

from config import settings
from utils.logger import get_logger

logger = get_logger("cache_manager")


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.cache_dir = settings.REALTIME_CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.alert_threshold = settings.ALERT_THRESHOLD
    
    def _get_hour_key(self, dt: Optional[datetime] = None) -> str:
        """获取小时键，格式：YYYY-MM-DD_HH"""
        if dt is None:
            dt = datetime.now()
        return dt.strftime("%Y-%m-%d_%H")
    
    def _get_hour_file_path(self, hour_key: str) -> Path:
        """获取小时缓存文件路径"""
        return self.cache_dir / f"{hour_key}.json"
    
    def _calculate_old_hour_key(self) -> str:
        """计算24小时前的小时键"""
        old_time = datetime.now() - timedelta(hours=settings.CACHE_RETENTION_HOURS)
        return self._get_hour_key(old_time)
    
    def cleanup_old_cache(self):
        """动态清理：删除24小时前的缓存文件"""
        old_hour_key = self._calculate_old_hour_key()
        old_file = self._get_hour_file_path(old_hour_key)
        
        if old_file.exists():
            try:
                old_file.unlink()
                logger.info(f"清理旧缓存文件: {old_hour_key}.json")
            except Exception as e:
                logger.error(f"清理缓存文件失败 {old_file}: {e}")
    
    def _generate_item_id(self, item: Dict) -> str:
        """生成新闻项的唯一ID"""
        # 优先使用RSS ID，如果没有则基于标题和发布时间生成
        rss_id = item.get("id") or item.get("guid") or ""
        if rss_id:
            return f"rss_{rss_id}"
        
        # 备用方案：基于标题和发布时间生成哈希
        title = item.get("title", "")
        published = item.get("published", "")
        content = f"{title}|{published}"
        return f"hash_{hashlib.md5(content.encode()).hexdigest()}"
    
    def _is_major_news(self, importance_score: int) -> bool:
        """判断是否为重大新闻"""
        return importance_score >= self.alert_threshold
    
    def save_news_items(self, items: List[Dict], category: str, importance_scores: List[int]):
        """
        保存新闻项到当前小时缓存文件
        
        Args:
            items: 新闻项列表
            category: 新闻分类
            importance_scores: 重要性评分列表（与items一一对应）
        """
        hour_key = self._get_hour_key()
        cache_file = self._get_hour_file_path(hour_key)
        
        # 加载现有缓存
        cache_data = self._load_cache_file(cache_file)
        
        # 更新缓存数据
        updated_count = 0
        for item, score in zip(items, importance_scores):
            item_id = self._generate_item_id(item)
            
            # 检查是否已存在（避免重复）
            existing_item = None
            for cached_item in cache_data["items"]:
                if cached_item.get("id") == item_id:
                    existing_item = cached_item
                    break
            
            if existing_item:
                # 更新现有项
                existing_item.update({
                    "title": item.get("title", ""),
                    "summary": item.get("summaryText", ""),
                    "category": category,
                    "importance_score": score,
                    "is_major": self._is_major_news(score),
                    "updated_at": datetime.now().isoformat()
                })
            else:
                # 添加新项
                cache_data["items"].append({
                    "id": item_id,
                    "title": item.get("title", ""),
                    "summary": item.get("summaryText", ""),
                    "category": category,
                    "importance_score": score,
                    "is_major": self._is_major_news(score),
                    "alert_sent": False,
                    "used_in_hourly": False,
                    "processed_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "raw_data": item  # 保存原始数据供后续使用
                })
                updated_count += 1
        
        # 保存缓存文件
        cache_data["last_updated"] = datetime.now().isoformat()
        self._save_cache_file(cache_file, cache_data)
        
        logger.info(f"更新缓存文件 {hour_key}.json: 新增/更新 {updated_count} 条新闻")
    
    def _load_cache_file(self, cache_file: Path) -> Dict:
        """加载缓存文件"""
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载缓存文件失败 {cache_file}: {e}")
        
        # 返回默认结构
        return {
            "hour": cache_file.stem,
            "last_updated": datetime.now().isoformat(),
            "items": []
        }
    
    def _save_cache_file(self, cache_file: Path, data: Dict):
        """保存缓存文件"""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存文件失败 {cache_file}: {e}")
            raise
    
    def get_major_alerts(self) -> List[Dict]:
        """获取需要发送吹哨告警的重大新闻"""
        hour_key = self._get_hour_key()
        cache_file = self._get_hour_file_path(hour_key)
        
        if not cache_file.exists():
            return []
        
        cache_data = self._load_cache_file(cache_file)
        major_alerts = []
        
        for item in cache_data["items"]:
            if (item.get("is_major") and 
                not item.get("alert_sent") and 
                not item.get("used_in_hourly")):
                major_alerts.append(item)
        
        # 按重要性评分排序
        major_alerts.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
        
        # 限制数量
        max_alerts = min(settings.ALERT_MAX_PER_CYCLE, len(major_alerts))
        return major_alerts[:max_alerts]
    
    def mark_alerts_sent(self, alert_ids: List[str]):
        """标记吹哨告警已发送"""
        hour_key = self._get_hour_key()
        cache_file = self._get_hour_file_path(hour_key)
        
        if not cache_file.exists() or not alert_ids:
            return
        
        cache_data = self._load_cache_file(cache_file)
        updated_count = 0
        
        for item in cache_data["items"]:
            if item.get("id") in alert_ids and not item.get("alert_sent"):
                item["alert_sent"] = True
                item["updated_at"] = datetime.now().isoformat()
                updated_count += 1
        
        if updated_count > 0:
            self._save_cache_file(cache_file, cache_data)
            logger.info(f"标记 {updated_count} 条吹哨告警为已发送")
    
    def get_unused_for_hourly(self, lookback_hours: int = 1) -> List[Dict]:
        """
        获取未用于小时报的新闻
        
        Args:
            lookback_hours: 回溯小时数（默认1小时）
        """
        unused_items = []
        
        # 获取最近N小时的缓存文件
        for i in range(lookback_hours):
            hour_dt = datetime.now() - timedelta(hours=i)
            hour_key = self._get_hour_key(hour_dt)
            cache_file = self._get_hour_file_path(hour_key)
            
            if cache_file.exists():
                cache_data = self._load_cache_file(cache_file)
                for item in cache_data["items"]:
                    if not item.get("used_in_hourly"):
                        unused_items.append(item)
        
        # 按处理时间排序（最新的优先）
        unused_items.sort(key=lambda x: x.get("processed_at", ""), reverse=True)
        
        logger.info(f"获取到 {len(unused_items)} 条未使用的新闻（回溯 {lookback_hours} 小时）")
        return unused_items
    
    def mark_as_used(self, item_ids: List[str]):
        """标记新闻为已使用（用于小时报）"""
        # 需要在所有缓存文件中查找并标记
        updated_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            cache_data = self._load_cache_file(cache_file)
            file_updated = False
            
            for item in cache_data["items"]:
                if item.get("id") in item_ids and not item.get("used_in_hourly"):
                    item["used_in_hourly"] = True
                    item["updated_at"] = datetime.now().isoformat()
                    updated_count += 1
                    file_updated = True
            
            if file_updated:
                self._save_cache_file(cache_file, cache_data)
        
        if updated_count > 0:
            logger.info(f"标记 {updated_count} 条新闻为已使用")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        stats = {
            "total_files": 0,
            "total_items": 0,
            "major_items": 0,
            "unused_items": 0,
            "alerted_items": 0
        }
        
        for cache_file in self.cache_dir.glob("*.json"):
            stats["total_files"] += 1
            cache_data = self._load_cache_file(cache_file)
            
            for item in cache_data["items"]:
                stats["total_items"] += 1
                if item.get("is_major"):
                    stats["major_items"] += 1
                if not item.get("used_in_hourly"):
                    stats["unused_items"] += 1
                if item.get("alert_sent"):
                    stats["alerted_items"] += 1
        
        return stats
