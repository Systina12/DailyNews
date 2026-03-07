"""
缓存功能集成测试

测试真实的实时告警工作流，验证：
1. 缓存是否正确存储和读取
2. 告警去重是否生效
3. LLM调用是否减少
4. 过期清理是否正常
"""

import sys
import os
from pathlib import Path
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.news_cache import get_news_cache
from utils.logger import get_logger
from config import settings

logger = get_logger("test_cache_integration")


def setup_test_environment():
    """准备测试环境"""
    print("\n" + "=" * 60)
    print("准备测试环境")
    print("=" * 60)
    
    # 清理旧缓存
    cache_file = settings.DATA_DIR / "news_cache.json"
    if cache_file.exists():
        cache_file.unlink()
        print(f"✓ 清理旧缓存: {cache_file}")
    
    # 确保目录存在
    settings.ensure_directories()
    print(f"✓ 数据目录: {settings.DATA_DIR}")


def test_cache_basic_workflow():
    """测试基本缓存工作流"""
    print("\n" + "=" * 60)
    print("测试 1: 基本缓存工作流")
    print("=" * 60)
    
    cache = get_news_cache()
    
    # 模拟第一批新闻
    print("\n步骤 1: 缓存第一批新闻...")
    news_batch_1 = [
        {
            "title": "Test News A",
            "link": "https://example.com/a",
            "category": "头条",
            "score": 85
        },
        {
            "title": "Test News B",
            "link": "https://example.com/b",
            "category": "政治",
            "score": 90
        },
        {
            "title": "Test News C",
            "link": "https://example.com/c",
            "category": "财经",
            "score": 60
        }
    ]
    
    for news in news_batch_1:
        cache.cache_news(
            title=news['title'],
            link=news['link'],
            category=news['category'],
            importance_score=news['score'],
            chinese_title=f"{news['title']}（中文）",
            chinese_summary=f"这是{news['title']}的摘要"
        )
    
    stats = cache.get_stats()
    print(f"✓ 缓存了 {stats['total']} 条新闻")
    assert stats['total'] == 3, f"期望3条，实际{stats['total']}条"
    
    # 测试读取
    print("\n步骤 2: 读取缓存...")
    cached = cache.get_cached_news("Test News A", "https://example.com/a")
    assert cached is not None, "缓存读取失败"
    assert cached['importance_score'] == 85, f"评分不匹配: {cached['importance_score']}"
    print(f"✓ 读取成功: {cached['chinese_title']}, 评分: {cached['importance_score']}")
    
    # 测试批量查询
    print("\n步骤 3: 批量查询...")
    test_items = [
        {"title": "Test News A", "link": "https://example.com/a"},  # 已缓存
        {"title": "Test News B", "link": "https://example.com/b"},  # 已缓存
        {"title": "Test News D", "link": "https://example.com/d"},  # 未缓存
    ]
    
    cached_items, uncached_items = cache.get_cached_scores(test_items)
    print(f"✓ 缓存命中: {len(cached_items)} 条")
    print(f"✓ 需要评分: {len(uncached_items)} 条")
    assert len(cached_items) == 2, f"期望2条命中，实际{len(cached_items)}条"
    assert len(uncached_items) == 1, f"期望1条未命中，实际{len(uncached_items)}条"
    
    print("\n✅ 基本缓存工作流测试通过")


def test_alert_deduplication():
    """测试告警去重"""
    print("\n" + "=" * 60)
    print("测试 2: 告警去重")
    print("=" * 60)
    
    cache = get_news_cache()
    
    test_title = "Test News A"
    test_link = "https://example.com/a"
    
    # 检查初始状态
    print("\n步骤 1: 检查初始告警状态...")
    is_sent = cache.is_alert_sent(test_title, test_link)
    print(f"  告警状态: {is_sent}")
    assert is_sent == False, "初始状态应该是未发送"
    
    # 标记为已发送
    print("\n步骤 2: 标记告警已发送...")
    cache.mark_alert_sent(test_title, test_link)
    
    # 再次检查
    print("\n步骤 3: 再次检查告警状态...")
    is_sent = cache.is_alert_sent(test_title, test_link)
    print(f"  告警状态: {is_sent}")
    assert is_sent == True, "标记后应该是已发送"
    
    # 验证统计
    stats = cache.get_stats()
    print(f"\n统计信息:")
    print(f"  总记录: {stats['total']}")
    print(f"  已发送告警: {stats['alert_sent']}")
    assert stats['alert_sent'] >= 1, "至少应该有1条已发送告警"
    
    print("\n✅ 告警去重测试通过")


def test_cache_expiration():
    """测试缓存过期清理"""
    print("\n" + "=" * 60)
    print("测试 3: 缓存过期清理")
    print("=" * 60)
    
    # 创建短TTL的缓存实例
    cache_file = settings.DATA_DIR / "test_cache_expire.json"
    if cache_file.exists():
        cache_file.unlink()
    
    from utils.news_cache import NewsCache
    cache = NewsCache(cache_file=cache_file, ttl_hours=0.0001)  # 约0.36秒
    
    print("\n步骤 1: 添加测试数据...")
    cache.cache_news(
        title="Expiring News",
        link="https://example.com/expire",
        importance_score=95
    )
    
    stats = cache.get_stats()
    print(f"  缓存数量: {stats['total']}")
    assert stats['total'] == 1, "应该有1条缓存"
    
    print("\n步骤 2: 等待过期（1秒）...")
    time.sleep(1)
    
    print("\n步骤 3: 清理过期缓存...")
    expired_count = cache.cleanup_expired()
    print(f"  清理数量: {expired_count}")
    
    stats = cache.get_stats()
    print(f"  剩余数量: {stats['total']}")
    assert stats['total'] == 0, "应该没有剩余缓存"
    assert expired_count == 1, "应该清理了1条"
    
    # 清理测试文件
    if cache_file.exists():
        cache_file.unlink()
    
    print("\n✅ 缓存过期清理测试通过")


def test_performance_simulation():
    """测试性能提升模拟"""
    print("\n" + "=" * 60)
    print("测试 4: 性能提升模拟")
    print("=" * 60)
    
    cache = get_news_cache()
    
    # 模拟第一次运行（无缓存）
    print("\n场景 1: 首次运行（无缓存）")
    print("-" * 60)
    
    first_run_news = [
        {"title": f"News {i}", "link": f"https://example.com/{i}"} 
        for i in range(1, 11)
    ]
    
    cached_items, uncached_items = cache.get_cached_scores(first_run_news)
    print(f"  拉取新闻: {len(first_run_news)} 条")
    print(f"  缓存命中: {len(cached_items)} 条")
    print(f"  需要评分: {len(uncached_items)} 条")
    print(f"  LLM调用: {len(uncached_items)} 次")
    
    first_run_llm_calls = len(uncached_items)
    assert first_run_llm_calls == 10, "首次运行应该需要10次LLM调用"
    
    # 缓存这些新闻
    for i, item in enumerate(uncached_items, 1):
        cache.cache_news(
            title=item['title'],
            link=item['link'],
            importance_score=70 + i * 2,
            chinese_title=f"{item['title']}（中文）",
            chinese_summary=f"摘要 {i}"
        )
    
    # 模拟第二次运行（部分缓存命中）
    print("\n场景 2: 第二次运行（10分钟后）")
    print("-" * 60)
    
    second_run_news = [
        {"title": f"News {i}", "link": f"https://example.com/{i}"} 
        for i in range(1, 8)  # 前7条是重复的
    ] + [
        {"title": f"News {i}", "link": f"https://example.com/{i}"} 
        for i in range(11, 14)  # 后3条是新的
    ]
    
    cached_items, uncached_items = cache.get_cached_scores(second_run_news)
    print(f"  拉取新闻: {len(second_run_news)} 条")
    print(f"  缓存命中: {len(cached_items)} 条 ✓")
    print(f"  需要评分: {len(uncached_items)} 条")
    print(f"  LLM调用: {len(uncached_items)} 次")
    
    second_run_llm_calls = len(uncached_items)
    assert len(cached_items) == 7, "应该有7条缓存命中"
    assert second_run_llm_calls == 3, "第二次运行应该只需要3次LLM调用"
    
    # 计算性能提升
    print("\n性能对比:")
    print("-" * 60)
    print(f"  改进前: 每次都需要 {len(second_run_news)} 次LLM调用")
    print(f"  改进后: 只需要 {second_run_llm_calls} 次LLM调用")
    
    savings = (len(second_run_news) - second_run_llm_calls) / len(second_run_news) * 100
    print(f"  节省: {savings:.0f}%")
    
    assert savings == 70, f"期望节省70%，实际{savings:.0f}%"
    
    print("\n✅ 性能提升模拟测试通过")


def test_cache_statistics():
    """测试缓存统计功能"""
    print("\n" + "=" * 60)
    print("测试 5: 缓存统计功能")
    print("=" * 60)
    
    cache = get_news_cache()
    stats = cache.get_stats()
    
    print("\n当前缓存统计:")
    print("-" * 60)
    print(f"  总记录数: {stats['total']}")
    print(f"  已评分: {stats['scored']}")
    print(f"  已发送告警: {stats['alert_sent']}")
    print(f"  最近1小时: {stats['last_1h']}")
    print(f"  最近6小时: {stats['last_6h']}")
    print(f"  最近24小时: {stats['last_24h']}")
    print(f"  缓存文件: {stats['cache_file']}")
    print(f"  TTL: {stats['ttl_hours']} 小时")
    
    # 验证统计数据的合理性
    assert stats['total'] >= 0, "总记录数应该>=0"
    assert stats['scored'] <= stats['total'], "已评分数应该<=总记录数"
    assert stats['alert_sent'] <= stats['total'], "已发送告警数应该<=总记录数"
    assert stats['last_1h'] <= stats['last_6h'], "1小时数应该<=6小时数"
    assert stats['last_6h'] <= stats['last_24h'], "6小时数应该<=24小时数"
    assert stats['last_24h'] <= stats['total'], "24小时数应该<=总记录数"
    
    print("\n✅ 缓存统计功能测试通过")


def test_cache_file_persistence():
    """测试缓存文件持久化"""
    print("\n" + "=" * 60)
    print("测试 6: 缓存文件持久化")
    print("=" * 60)
    
    cache_file = settings.DATA_DIR / "news_cache.json"
    
    # 添加一条测试数据
    print("\n步骤 1: 添加测试数据...")
    cache1 = get_news_cache()
    cache1.cache_news(
        title="Persistence Test",
        link="https://example.com/persist",
        importance_score=88
    )
    
    # 验证文件存在
    print("\n步骤 2: 验证缓存文件...")
    assert cache_file.exists(), f"缓存文件应该存在: {cache_file}"
    print(f"✓ 缓存文件存在: {cache_file}")
    
    # 重新加载缓存
    print("\n步骤 3: 重新加载缓存...")
    from utils.news_cache import NewsCache
    cache2 = NewsCache(cache_file=cache_file)
    
    # 验证数据仍然存在
    cached = cache2.get_cached_news("Persistence Test", "https://example.com/persist")
    assert cached is not None, "重新加载后数据应该仍然存在"
    assert cached['importance_score'] == 88, "评分应该保持不变"
    print(f"✓ 数据持久化成功: {cached['title']}, 评分: {cached['importance_score']}")
    
    print("\n✅ 缓存文件持久化测试通过")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("缓存功能集成测试")
    print("=" * 60)
    
    try:
        setup_test_environment()
        
        test_cache_basic_workflow()
        test_alert_deduplication()
        test_cache_expiration()
        test_performance_simulation()
        test_cache_statistics()
        test_cache_file_persistence()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
        # 显示最终统计
        cache = get_news_cache()
        stats = cache.get_stats()
        
        print("\n最终缓存状态:")
        print("-" * 60)
        print(f"  总记录: {stats['total']} 条")
        print(f"  已评分: {stats['scored']} 条")
        print(f"  已发送告警: {stats['alert_sent']} 条")
        print(f"  缓存文件: {stats['cache_file']}")
        
        print("\n测试总结:")
        print("-" * 60)
        print("✓ 缓存存储和读取正常")
        print("✓ 告警去重功能正常")
        print("✓ 过期清理功能正常")
        print("✓ 性能提升显著（节省70%的LLM调用）")
        print("✓ 统计功能正常")
        print("✓ 文件持久化正常")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
