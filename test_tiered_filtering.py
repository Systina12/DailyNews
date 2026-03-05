#!/usr/bin/env python3
"""
测试分层过滤逻辑
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


def simulate_tiered_filtering(hours: int):
    """模拟分层过滤"""
    print(f"\n{'='*60}")
    print(f"模拟 {hours} 小时报的分层过滤")
    print(f"{'='*60}\n")
    
    # 模拟原始数据
    original_counts = {
        "头条": 80,
        "政治": 50,
        "财经": 40,
        "科技": 30,
        "国际": 40
    }
    
    print("第一轮：初始分类")
    for cat, count in original_counts.items():
        print(f"  {cat}: {count} 条")
    print()
    
    # 计算水位线
    headline_low, headline_max = calculate_headline_limits(hours)
    secondary_low = int(headline_low * 1.5)
    secondary_max = int(headline_max * 1.5)
    
    print(f"水位线设置：")
    print(f"  头条：低水位 {headline_low}, 最大 {headline_max}")
    print(f"  次级：低水位 {secondary_low}, 最大 {secondary_max}")
    print(f"  国际：低水位 {headline_low}, 最大 {headline_max}")
    print()
    
    # 第二轮：头条过滤
    print("第二轮：头条过滤（LLM 评分 + 水位线）")
    headline_count = original_counts["头条"]
    headline_keep = int(headline_count * 0.6)
    headline_keep = max(8, min(headline_keep, headline_max))
    headline_drop = headline_count - headline_keep
    
    print(f"  头条：{headline_count} 条 → 保留 {headline_keep} 条，下放 {headline_drop} 条")
    
    # 模拟下放分配
    drop_to_politics = int(headline_drop * 0.4)
    drop_to_economy = int(headline_drop * 0.3)
    drop_to_tech = int(headline_drop * 0.2)
    drop_to_intl = headline_drop - drop_to_politics - drop_to_economy - drop_to_tech
    
    print(f"    ├─ 政治：+{drop_to_politics} 条")
    print(f"    ├─ 财经：+{drop_to_economy} 条")
    print(f"    ├─ 科技：+{drop_to_tech} 条")
    print(f"    └─ 国际：+{drop_to_intl} 条")
    print()
    
    # 更新次级分类数量
    secondary_counts = {
        "政治": original_counts["政治"] + drop_to_politics,
        "财经": original_counts["财经"] + drop_to_economy,
        "科技": original_counts["科技"] + drop_to_tech
    }
    
    # 第三轮：次级分类过滤
    print("第三轮：次级分类过滤（1.5倍水位线）")
    total_drop_to_intl = 0
    
    for cat, count in secondary_counts.items():
        keep = int(count * 0.6)
        keep = max(10, min(keep, secondary_max))
        drop = count - keep
        total_drop_to_intl += drop
        
        print(f"  {cat}：{count} 条 → 保留 {keep} 条，下放 {drop} 条")
        secondary_counts[cat] = keep
    
    print(f"    ↓ 全部下放到国际：{total_drop_to_intl} 条")
    print()
    
    # 第四轮：国际过滤
    print("第四轮：国际过滤（与头条同级水位线）")
    intl_count = original_counts["国际"] + drop_to_intl + total_drop_to_intl
    intl_keep = int(intl_count * 0.6)
    intl_keep = max(8, min(intl_keep, headline_max))
    intl_discard = intl_count - intl_keep
    
    print(f"  国际：{original_counts['国际']} 条（原始）+ {drop_to_intl + total_drop_to_intl} 条（下放）= {intl_count} 条")
    print(f"    ↓ 应用水位线")
    print(f"    保留：{intl_keep} 条")
    print(f"    丢弃：{intl_discard} 条 ❌")
    print()
    
    # 最终结果
    print(f"{'='*60}")
    print("最终结果：")
    print(f"  头条：{headline_keep} 条")
    print(f"  政治：{secondary_counts['政治']} 条")
    print(f"  财经：{secondary_counts['财经']} 条")
    print(f"  科技：{secondary_counts['科技']} 条")
    print(f"  国际：{intl_keep} 条")
    
    total_original = sum(original_counts.values())
    total_final = headline_keep + sum(secondary_counts.values()) + intl_keep
    filter_rate = (total_original - total_final) / total_original * 100
    
    print(f"  总计：{total_final} 条（从 {total_original} 条过滤）")
    print(f"  过滤率：{filter_rate:.1f}%")
    print(f"{'='*60}")


def test_different_hours():
    """测试不同时间范围"""
    print("\n" + "="*60)
    print("分层过滤测试")
    print("="*60)
    
    # 测试不同时间范围
    for hours in [1, 4, 8, 16, 24]:
        simulate_tiered_filtering(hours)
    
    # 水位线对比表
    print("\n" + "="*60)
    print("水位线对比表")
    print("="*60)
    print(f"{'时间':<8} {'头条':<15} {'次级(1.5倍)':<20} {'国际':<15}")
    print("-" * 60)
    
    for hours in [1, 4, 8, 16, 24]:
        low, max_k = calculate_headline_limits(hours)
        sec_low = int(low * 1.5)
        sec_max = int(max_k * 1.5)
        print(f"{hours}小时    {low}-{max_k:<12} {sec_low}-{sec_max:<17} {low}-{max_k}")
    
    print("="*60)


if __name__ == "__main__":
    test_different_hours()
    
    print("\n设计优势：")
    print("1. ✅ 头条最严格，只保留最重要的")
    print("2. ✅ 次级相对宽松（1.5倍），允许更多专业内容")
    print("3. ✅ 国际兜底，但也有限制")
    print("4. ✅ 不丢失重要信息，逐层下放")
    print("5. ✅ 自动平衡，无需手动调整")
    print("\n你的想法很好，这个设计更合理！🎉")
