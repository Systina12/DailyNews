#!/usr/bin/env python3
"""
测试头条智能排序和黑名单学习机制
"""

import json
from pathlib import Path
from workflows.news_pipeline import (
    _load_learned_blacklist,
    _save_learned_blacklist,
    _extract_keywords,
    _update_blacklist_from_low_scores,
    _prioritize_headlines
)
from config import settings
from utils.logger import get_logger

logger = get_logger("test_headline_learning")


def test_keyword_extraction():
    """测试关键词提取"""
    print("\n=== 测试关键词提取 ===")
    
    test_cases = [
        "俄罗斯一动物园在节日后对老虎实施间歇性禁食",
        "塔季扬娜·纳夫卡谈及了佩斯科夫的衣橱",
        "索契最昂贵房屋的价格被公布",
        "芬兰私营社会服务领域的集体协议谈判已达成协议"
    ]
    
    for text in test_cases:
        keywords = _extract_keywords(text)
        print(f"文本: {text}")
        print(f"关键词: {keywords}\n")


def test_blacklist_learning():
    """测试黑名单学习机制"""
    print("\n=== 测试黑名单学习 ===")
    
    import time
    
    # 模拟低分新闻
    low_score_items = [
        ({"title": "俄罗斯一动物园在节日后对老虎实施间歇性禁食", "summaryText": "动物园管理员表示这是正常的饮食管理"}, 15),
        ({"title": "塔季扬娜·纳夫卡谈及了佩斯科夫的衣橱", "summaryText": "时尚评论家对此发表看法"}, 20),
        ({"title": "索契最昂贵房屋的价格被公布", "summaryText": "房地产市场分析"}, 25),
        ({"title": "有建议提供给居住在小户型公寓的俄罗斯民众", "summaryText": "生活小贴士"}, 18),
        ({"title": "一名俄罗斯女性在接受一项流行美容程序后展示了其布满伤口的面部", "summaryText": "美容事故警示"}, 22),
    ]
    
    # 清空现有黑名单（测试用）
    blacklist_file = settings.DATA_DIR / "headline_blacklist.json"
    if blacklist_file.exists():
        backup_file = settings.DATA_DIR / "headline_blacklist_backup.json"
        import shutil
        shutil.copy(blacklist_file, backup_file)
        print(f"已备份现有黑名单到: {backup_file}")
    
    # 初始化空黑名单
    _save_learned_blacklist({})
    
    # 第一次学习
    print("\n第一次学习（5条低分新闻）:")
    _update_blacklist_from_low_scores(low_score_items)
    blacklist = _load_learned_blacklist()
    print(f"黑名单大小: {len(blacklist)}")
    print(f"前10个关键词:")
    for kw, entry in list(blacklist.items())[:10]:
        print(f"  {kw}: 频率={entry['freq']:.2f}, 最后出现={time.strftime('%Y-%m-%d', time.localtime(entry['last_seen']))}")
    
    # 第二次学习（模拟衰减）
    print("\n第二次学习（相同的5条新闻）:")
    _update_blacklist_from_low_scores(low_score_items)
    blacklist = _load_learned_blacklist()
    print(f"黑名单大小: {len(blacklist)}")
    print(f"前10个关键词:")
    for kw, entry in list(blacklist.items())[:10]:
        print(f"  {kw}: 频率={entry['freq']:.2f}, 最后出现={time.strftime('%Y-%m-%d', time.localtime(entry['last_seen']))}")
    
    # 第三次学习（不同的低分新闻）
    new_low_score_items = [
        ({"title": "医生未能挽救一名患癌的16岁博主", "summaryText": "悲伤的故事"}, 30),
        ({"title": "一名女性在查看生日照片后决定改变其健康管理方式", "summaryText": "励志故事"}, 28),
        ({"title": "有评估对莫斯科三月节日期间的降雪概率进行了预测", "summaryText": "天气预报"}, 25),
    ]
    
    print("\n第三次学习（3条新的低分新闻）:")
    _update_blacklist_from_low_scores(new_low_score_items)
    blacklist = _load_learned_blacklist()
    print(f"黑名单大小: {len(blacklist)}")
    print(f"前10个关键词:")
    for kw, entry in list(blacklist.items())[:10]:
        print(f"  {kw}: 频率={entry['freq']:.2f}, 最后出现={time.strftime('%Y-%m-%d', time.localtime(entry['last_seen']))}")


def test_blacklist_cleanup():
    """测试黑名单清理机制"""
    print("\n=== 测试黑名单清理机制 ===")
    
    import time
    current_time = time.time()
    
    # 创建一个包含低频关键词的黑名单
    test_blacklist = {
        "high_freq_1": {'freq': 0.8, 'last_seen': current_time},
        "high_freq_2": {'freq': 0.7, 'last_seen': current_time},
        "medium_freq_1": {'freq': 0.5, 'last_seen': current_time},
        "medium_freq_2": {'freq': 0.4, 'last_seen': current_time},
        "low_freq_1": {'freq': 0.25, 'last_seen': current_time},  # 应该被清理
        "low_freq_2": {'freq': 0.15, 'last_seen': current_time},  # 应该被清理
        "old_keyword": {'freq': 0.6, 'last_seen': current_time - 40 * 24 * 3600},  # 40天前，应该衰减
    }
    
    _save_learned_blacklist(test_blacklist)
    print(f"初始黑名单: {len(test_blacklist)} 个关键词")
    for kw, entry in test_blacklist.items():
        days_ago = (current_time - entry['last_seen']) / 86400
        print(f"  {kw}: 频率={entry['freq']:.2f}, {days_ago:.0f}天前")
    
    # 模拟一次学习（触发清理）
    low_score_items = [
        ({"title": "测试新闻 high_freq_1", "summaryText": ""}, 20),
        ({"title": "测试新闻 high_freq_2", "summaryText": ""}, 25),
    ]
    
    print("\n执行学习和清理...")
    _update_blacklist_from_low_scores(low_score_items)
    
    blacklist = _load_learned_blacklist()
    print(f"\n清理后黑名单: {len(blacklist)} 个关键词")
    for kw, entry in blacklist.items():
        days_ago = (current_time - entry['last_seen']) / 86400
        print(f"  {kw}: 频率={entry['freq']:.2f}, {days_ago:.0f}天前")
    print("\n✓ 低频关键词已被清理: low_freq_1, low_freq_2")
    print("✓ 旧关键词已衰减: old_keyword")


def test_prioritize_headlines():
    """测试头条排序（不使用 LLM，仅测试黑名单过滤）"""
    print("\n=== 测试头条排序（黑名单过滤）===")
    
    # 准备测试数据
    test_items = [
        {"title": "芬兰私营社会服务领域的集体协议谈判已达成协议", "summaryText": "重要政治新闻"},
        {"title": "俄罗斯一动物园在节日后对老虎实施间歇性禁食", "summaryText": "动物园新闻"},
        {"title": "新的民意调查显示加沙战争后美国公众舆论更倾向于支持巴勒斯坦人", "summaryText": "国际政治"},
        {"title": "塔季扬娜·纳夫卡谈及了佩斯科夫的衣橱", "summaryText": "时尚八卦"},
        {"title": "巴基斯坦宣布与阿富汗进入公开战争状态", "summaryText": "军事冲突"},
    ]
    
    # 不使用 LLM，仅测试黑名单过滤
    sorted_items = _prioritize_headlines(test_items, enable_llm=False, enable_learning=False)
    
    print(f"原始数量: {len(test_items)}")
    print(f"过滤后数量: {len(sorted_items)}")
    print("\n过滤后的新闻:")
    for i, item in enumerate(sorted_items, 1):
        print(f"{i}. {item['title']}")


if __name__ == "__main__":
    print("=" * 60)
    print("头条智能排序和黑名单学习机制测试")
    print("=" * 60)
    
    # 确保数据目录存在
    settings.ensure_directories()
    
    # 运行测试
    test_keyword_extraction()
    test_blacklist_learning()
    test_blacklist_cleanup()
    test_prioritize_headlines()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
