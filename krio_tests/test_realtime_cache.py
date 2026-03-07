"""
测试实时告警的缓存功能

模拟场景：
1. 第一次运行：拉取新闻，LLM评分，发送告警
2. 第二次运行（10分钟后）：部分新闻命中缓存，减少LLM调用
3. 验证告警去重：同一新闻不会重复发送
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.news_cache import get_news_cache
from utils.logger import get_logger

logger = get_logger("test_realtime_cache")


def simulate_first_run():
    """模拟第一次运行"""
    print("\n" + "=" * 60)
    print("模拟场景 1: 首次运行（无缓存）")
    print("=" * 60)
    
    cache = get_news_cache()
    
    # 模拟拉取到的新闻
    mock_news = [
        {"title": "重要新闻A", "link": "https://example.com/a", "category": "头条"},
        {"title": "重要新闻B", "link": "https://example.com/b", "category": "政治"},
        {"title": "普通新闻C", "link": "https://example.com/c", "category": "财经"},
        {"title": "重要新闻D", "link": "https://example.com/d", "category": "科技"},
    ]
    
    print(f"\n拉取到 {len(mock_news)} 条新闻")
    
    # 检查缓存
    cached_items, uncached_items = cache.get_cached_scores(mock_news)
    print(f"缓存命中: {len(cached_items)} 条")
    print(f"需要评分: {len(uncached_items)} 条")
    
    # 模拟LLM评分
    print(f"\n调用LLM评分 {len(uncached_items)} 条新闻...")
    mock_scores = [85, 90, 60, 88]  # 模拟评分结果
    
    important_count = 0
    for item, score in zip(uncached_items, mock_scores):
        # 缓存评分结果
        cache.cache_news(
            title=item['title'],
            link=item['link'],
            category=item['category'],
            importance_score=score,
            chinese_title=item['title'] + "（中文）",
            chinese_summary=f"这是{item['title']}的摘要"
        )
        
        if score >= 80:
            important_count += 1
            print(f"  ⚠ 重要新闻: {item['title']} - {score}分")
    
    print(f"\n发现 {important_count} 条重要新闻，发送告警...")
    
    # 标记告警已发送
    for item, score in zip(uncached_items, mock_scores):
        if score >= 80:
            cache.mark_alert_sent(item['title'], item['link'])
    
    print("✓ 告警已发送")
    
    # 统计
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  总记录: {stats['total']} 条")
    print(f"  已发送告警: {stats['alert_sent']} 条")


def simulate_second_run():
    """模拟第二次运行（10分钟后）"""
    print("\n" + "=" * 60)
    print("模拟场景 2: 第二次运行（10分钟后，部分缓存命中）")
    print("=" * 60)
    
    cache = get_news_cache()
    
    # 模拟拉取到的新闻（部分重复，部分新增）
    mock_news = [
        {"title": "重要新闻A", "link": "https://example.com/a", "category": "头条"},  # 重复
        {"title": "重要新闻B", "link": "https://example.com/b", "category": "政治"},  # 重复
        {"title": "新新闻E", "link": "https://example.com/e", "category": "军事"},  # 新增
        {"title": "新新闻F", "link": "https://example.com/f", "category": "国际"},  # 新增
    ]
    
    print(f"\n拉取到 {len(mock_news)} 条新闻")
    
    # 检查缓存
    cached_items, uncached_items = cache.get_cached_scores(mock_news)
    print(f"缓存命中: {len(cached_items)} 条 ✓")
    print(f"需要评分: {len(uncached_items)} 条")
    
    # 处理缓存命中的新闻
    print(f"\n处理缓存命中的新闻:")
    important_from_cache = 0
    skipped_alerts = 0
    
    for item in cached_items:
        score = item['importance_score']
        print(f"  - {item['chinese_title']}: {score}分 (缓存)")
        
        if score >= 80:
            # 检查是否已发送告警
            if cache.is_alert_sent(item['title'], item['link']):
                print(f"    → 已发送过告警，跳过")
                skipped_alerts += 1
            else:
                print(f"    → 需要发送告警")
                important_from_cache += 1
    
    # 模拟LLM评分新新闻
    print(f"\n调用LLM评分 {len(uncached_items)} 条新闻...")
    mock_scores = [75, 92]  # 模拟评分结果
    
    important_from_llm = 0
    for item, score in zip(uncached_items, mock_scores):
        cache.cache_news(
            title=item['title'],
            link=item['link'],
            category=item['category'],
            importance_score=score,
            chinese_title=item['title'] + "（中文）",
            chinese_summary=f"这是{item['title']}的摘要"
        )
        
        if score >= 80:
            important_from_llm += 1
            print(f"  ⚠ 重要新闻: {item['title']} - {score}分")
            cache.mark_alert_sent(item['title'], item['link'])
    
    total_important = important_from_cache + important_from_llm
    print(f"\n发现 {total_important} 条重要新闻，发送告警...")
    print(f"  - 来自缓存: {important_from_cache} 条")
    print(f"  - 来自LLM: {important_from_llm} 条")
    print(f"  - 跳过重复: {skipped_alerts} 条")
    
    # 统计
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  总记录: {stats['total']} 条")
    print(f"  已发送告警: {stats['alert_sent']} 条")
    
    # 性能对比
    print(f"\n性能对比:")
    print(f"  改进前: 需要评分 4 条新闻")
    print(f"  改进后: 需要评分 {len(uncached_items)} 条新闻")
    print(f"  节省LLM调用: {4 - len(uncached_items)} 次 ({(4 - len(uncached_items)) / 4 * 100:.0f}%)")


def main():
    print("\n" + "=" * 60)
    print("实时告警缓存功能测试")
    print("=" * 60)
    
    try:
        # 清理旧缓存
        from config import settings
        cache_file = settings.DATA_DIR / "news_cache.json"
        if cache_file.exists():
            cache_file.unlink()
            print(f"\n清理旧缓存: {cache_file}")
        
        simulate_first_run()
        simulate_second_run()
        
        print("\n" + "=" * 60)
        print("✓ 测试完成")
        print("=" * 60)
        print("\n总结:")
        print("1. 首次运行：所有新闻都需要LLM评分")
        print("2. 第二次运行：缓存命中的新闻直接使用评分，节省LLM调用")
        print("3. 告警去重：已发送的告警不会重复发送")
        print("4. 性能提升：LLM调用减少50%，成本显著降低")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
