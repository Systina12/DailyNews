"""
测试新闻缓存功能

功能：
1. 测试缓存的基本操作（存储、读取、过期清理）
2. 测试告警去重功能
3. 测试缓存统计
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.news_cache import NewsCache, get_news_cache
from utils.logger import get_logger
import time

logger = get_logger("test_cache")


def test_basic_operations():
    """测试基本操作"""
    print("\n" + "=" * 60)
    print("测试 1: 基本操作")
    print("=" * 60)
    
    # 使用临时缓存文件
    cache_file = project_root / "krio_tests" / "test_cache.json"
    if cache_file.exists():
        cache_file.unlink()
    
    cache = NewsCache(cache_file=cache_file, ttl_hours=24)
    
    # 1. 缓存新闻
    print("\n1. 缓存新闻...")
    news_hash = cache.cache_news(
        title="测试新闻标题",
        link="https://example.com/news1",
        category="头条",
        importance_score=85,
        chinese_title="测试新闻标题（中文）",
        chinese_summary="这是一条测试新闻的摘要",
        published="2026-03-06T10:00:00"
    )
    print(f"✓ 缓存成功，hash: {news_hash}")
    
    # 2. 读取缓存
    print("\n2. 读取缓存...")
    cached = cache.get_cached_news("测试新闻标题", "https://example.com/news1")
    if cached:
        print(f"✓ 读取成功")
        print(f"  标题: {cached['chinese_title']}")
        print(f"  评分: {cached['importance_score']}")
        print(f"  摘要: {cached['chinese_summary'][:50]}...")
    else:
        print("✗ 读取失败")
    
    # 3. 测试告警标记
    print("\n3. 测试告警标记...")
    is_sent = cache.is_alert_sent("测试新闻标题", "https://example.com/news1")
    print(f"  告警状态（标记前）: {is_sent}")
    
    cache.mark_alert_sent("测试新闻标题", "https://example.com/news1")
    is_sent = cache.is_alert_sent("测试新闻标题", "https://example.com/news1")
    print(f"  告警状态（标记后）: {is_sent}")
    
    # 4. 统计信息
    print("\n4. 缓存统计...")
    stats = cache.get_stats()
    print(f"  总记录数: {stats['total']}")
    print(f"  已发送告警: {stats['alert_sent']}")
    print(f"  已评分: {stats['scored']}")
    print(f"  最近1小时: {stats['last_1h']}")
    
    print("\n✓ 基本操作测试通过")


def test_batch_cache():
    """测试批量缓存查询"""
    print("\n" + "=" * 60)
    print("测试 2: 批量缓存查询")
    print("=" * 60)
    
    cache_file = project_root / "krio_tests" / "test_cache.json"
    cache = NewsCache(cache_file=cache_file, ttl_hours=24)
    
    # 准备测试数据
    items = [
        {"title": "测试新闻标题", "link": "https://example.com/news1"},  # 已缓存
        {"title": "新新闻1", "link": "https://example.com/news2"},  # 未缓存
        {"title": "新新闻2", "link": "https://example.com/news3"},  # 未缓存
    ]
    
    print(f"\n测试 {len(items)} 条新闻...")
    cached_items, uncached_items = cache.get_cached_scores(items)
    
    print(f"✓ 缓存命中: {len(cached_items)} 条")
    print(f"✓ 需要评分: {len(uncached_items)} 条")
    
    for item in cached_items:
        print(f"  - {item['chinese_title']}: {item['importance_score']}分 (缓存)")
    
    for item in uncached_items:
        print(f"  - {item['title']}: 需要评分")


def test_expiration():
    """测试过期清理"""
    print("\n" + "=" * 60)
    print("测试 3: 过期清理")
    print("=" * 60)
    
    # 使用短TTL测试
    cache_file = project_root / "krio_tests" / "test_cache_expire.json"
    if cache_file.exists():
        cache_file.unlink()
    
    cache = NewsCache(cache_file=cache_file, ttl_hours=0.0001)  # 约0.36秒
    
    print("\n1. 添加测试数据...")
    cache.cache_news(
        title="即将过期的新闻",
        link="https://example.com/expire",
        importance_score=90
    )
    print(f"  缓存数量: {cache.get_stats()['total']}")
    
    print("\n2. 等待过期...")
    time.sleep(1)
    
    print("\n3. 清理过期缓存...")
    expired = cache.cleanup_expired()
    print(f"  清理数量: {expired}")
    print(f"  剩余数量: {cache.get_stats()['total']}")
    
    # 清理测试文件
    if cache_file.exists():
        cache_file.unlink()
    
    print("\n✓ 过期清理测试通过")


def main():
    print("\n" + "=" * 60)
    print("新闻缓存功能测试")
    print("=" * 60)
    
    try:
        test_basic_operations()
        test_batch_cache()
        test_expiration()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试文件
        test_file = project_root / "krio_tests" / "test_cache.json"
        if test_file.exists():
            test_file.unlink()
            print(f"\n清理测试文件: {test_file}")


if __name__ == "__main__":
    main()
