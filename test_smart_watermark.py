#!/usr/bin/env python3
"""
测试智能水位线逻辑
"""

import math


def calculate_headline_limits(hours: int):
    """计算头条水位线"""
    BASE_HOURS = 1
    BASE_LOW_WATERMARK = 10
    BASE_MAX_KEEP = 20
    
    time_ratio = hours / BASE_HOURS
    time_multiplier = math.sqrt(time_ratio)
    
    low_watermark = int(BASE_LOW_WATERMARK * time_multiplier)
    max_keep = int(BASE_MAX_KEEP * time_multiplier)
    
    return low_watermark, max_keep


def apply_smart_watermark(total: int, low_watermark: int, max_keep: int, category: str):
    """
    智能水位线逻辑
    
    策略：
    - 数量 ≤ 低水位：全部保留
    - 低水位 < 数量 ≤ 最大值：保留 60%，但至少保留最大值的 60%
    - 数量 > 最大值：保留 60%，但至少保留最大值的 80%，且不超过最大值
    """
    # 情况1：数量 ≤ 低水位
    if total <= low_watermark:
        return total, 0, "数量少，全部保留"
    
    # 计算保留数量
    keep_ratio = 0.6
    keep_count = int(total * keep_ratio)
    
    # 情况2：低水位 < 数量 ≤ 最大值
    if total <= max_keep:
        min_keep = int(max_keep * 0.6)
        keep_count = max(keep_count, min_keep)
        
        if keep_count >= total:
            return total, 0, "数量适中，全部保留"
        
        return keep_count, total - keep_count, f"数量适中，至少保留 {min_keep}"
    
    # 情况3：数量 > 最大值
    else:
        min_keep = int(max_keep * 0.8)
        keep_count = max(keep_count, min_keep)
        keep_count = min(keep_count, max_keep)  # 不超过最大值
        
        return keep_count, total - keep_count, f"数量超出，至少保留 {min_keep}，不超过 {max_keep}"


def test_smart_watermark():
    """测试智能水位线"""
    print("\n" + "="*70)
    print("智能水位线测试（8小时报）")
    print("="*70)
    
    hours = 8
    headline_low, headline_max = calculate_headline_limits(hours)
    secondary_low = int(headline_low * 1.5)
    secondary_max = int(headline_max * 1.5)
    
    print(f"\n水位线设置：")
    print(f"  头条：低水位 {headline_low}, 最大 {headline_max}")
    print(f"  次级：低水位 {secondary_low}, 最大 {secondary_max}")
    print(f"  国际：低水位 {headline_low}, 最大 {headline_max}")
    
    # 测试不同数量的次级分类
    test_cases = [
        ("科技", 20),   # 数量少
        ("科技", 36),   # 数量适中（接近低水位）
        ("政治", 62),   # 数量适中（超过低水位，但小于最大值）
        ("财经", 90),   # 数量超出最大值
        ("政治", 150),  # 数量远超最大值
    ]
    
    print(f"\n{'='*70}")
    print("次级分类测试（低水位 {}, 最大 {}）".format(secondary_low, secondary_max))
    print("="*70)
    print(f"{'分类':<8} {'原始':<8} {'保留':<8} {'下放':<8} {'说明':<30}")
    print("-"*70)
    
    for category, total in test_cases:
        keep, drop, reason = apply_smart_watermark(total, secondary_low, secondary_max, category)
        print(f"{category:<8} {total:<8} {keep:<8} {drop:<8} {reason:<30}")
    
    # 测试国际分类
    test_cases_intl = [
        30,   # 数量少
        50,   # 数量适中
        90,   # 数量超出
        150,  # 数量远超
    ]
    
    print(f"\n{'='*70}")
    print("国际分类测试（低水位 {}, 最大 {}）".format(headline_low, headline_max))
    print("="*70)
    print(f"{'原始':<8} {'保留':<8} {'丢弃':<8} {'说明':<30}")
    print("-"*70)
    
    for total in test_cases_intl:
        keep, drop, reason = apply_smart_watermark(total, headline_low, headline_max, "国际")
        print(f"{total:<8} {keep:<8} {drop:<8} {reason:<30}")


def test_comparison():
    """对比旧逻辑和新逻辑"""
    print("\n" + "="*70)
    print("旧逻辑 vs 新逻辑对比（8小时报，次级分类）")
    print("="*70)
    
    hours = 8
    headline_low, headline_max = calculate_headline_limits(hours)
    secondary_low = int(headline_low * 1.5)
    secondary_max = int(headline_max * 1.5)
    
    print(f"\n水位线：低水位 {secondary_low}, 最大 {secondary_max}")
    print(f"\n{'原始数量':<10} {'旧逻辑保留':<12} {'新逻辑保留':<12} {'差异':<10} {'说明':<30}")
    print("-"*70)
    
    test_counts = [20, 30, 36, 50, 62, 80, 90, 120, 150]
    
    for total in test_counts:
        # 旧逻辑：简单的 60% 或最大值
        old_keep = int(total * 0.6)
        old_keep = max(10, min(old_keep, secondary_max))
        
        # 新逻辑：智能水位线
        new_keep, _, reason = apply_smart_watermark(total, secondary_low, secondary_max, "次级")
        
        diff = new_keep - old_keep
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        
        print(f"{total:<10} {old_keep:<12} {new_keep:<12} {diff_str:<10} {reason:<30}")


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "="*70)
    print("边界情况测试")
    print("="*70)
    
    hours = 8
    headline_low, headline_max = calculate_headline_limits(hours)
    secondary_low = int(headline_low * 1.5)
    secondary_max = int(headline_max * 1.5)
    
    print(f"\n水位线：低水位 {secondary_low}, 最大 {secondary_max}")
    print(f"  60% 阈值：{int(secondary_max * 0.6)}")
    print(f"  80% 阈值：{int(secondary_max * 0.8)}")
    
    # 边界情况
    edge_cases = [
        (secondary_low, "正好等于低水位"),
        (secondary_low + 1, "刚超过低水位"),
        (int(secondary_max * 0.6), "正好等于 60% 阈值"),
        (secondary_max, "正好等于最大值"),
        (secondary_max + 1, "刚超过最大值"),
        (int(secondary_max * 0.8 / 0.6), "削减后正好等于 80% 阈值"),
    ]
    
    print(f"\n{'原始数量':<12} {'保留':<8} {'下放/丢弃':<12} {'说明':<30}")
    print("-"*70)
    
    for total, desc in edge_cases:
        keep, drop, reason = apply_smart_watermark(total, secondary_low, secondary_max, "次级")
        print(f"{total:<12} {keep:<8} {drop:<12} {desc:<30}")


if __name__ == "__main__":
    test_smart_watermark()
    test_comparison()
    test_edge_cases()
    
    print("\n" + "="*70)
    print("设计优势：")
    print("="*70)
    print("1. ✅ 数量少的栏目（如科技）不会被过度削减")
    print("2. ✅ 数量适中的栏目保留更多（至少 60% 的最大值）")
    print("3. ✅ 数量超出的栏目也保留足够多（至少 80% 的最大值）")
    print("4. ✅ 避免一刀切，根据实际情况智能调整")
    print("5. ✅ 逻辑简洁，易于理解和维护")
    print("\n你的想法很好，这个设计更智能！🎉")
