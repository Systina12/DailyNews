#!/usr/bin/env python3
"""
诊断分类性能和 LLM 使用情况
"""

import re
import sys
from pathlib import Path

def analyze_logs(log_file="logs/main_workflow.log"):
    """分析日志文件，统计分类性能"""
    
    if not Path(log_file).exists():
        print(f"❌ 日志文件不存在: {log_file}")
        return
    
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取分类统计
    categories = {}
    
    # 匹配：规则分类: X 条确定，Y 条需要 LLM 判断
    pattern = r'规则分类: (\d+) 条确定，(\d+) 条需要 LLM 判断'
    matches = re.findall(pattern, content)
    
    if not matches:
        print("❌ 未找到分类统计信息")
        return
    
    print("=" * 60)
    print("分类性能诊断报告")
    print("=" * 60)
    
    total_rule = 0
    total_llm = 0
    
    for i, (rule, llm) in enumerate(matches, 1):
        rule_count = int(rule)
        llm_count = int(llm)
        total = rule_count + llm_count
        
        if total > 0:
            rule_pct = (rule_count / total) * 100
            llm_pct = (llm_count / total) * 100
        else:
            rule_pct = llm_pct = 0
        
        total_rule += rule_count
        total_llm += llm_count
        
        print(f"\n分类 #{i}:")
        print(f"  规则分类: {rule_count:3d} 条 ({rule_pct:5.1f}%)")
        print(f"  LLM 分类: {llm_count:3d} 条 ({llm_pct:5.1f}%)")
        print(f"  总计:     {total:3d} 条")
    
    # 总体统计
    grand_total = total_rule + total_llm
    if grand_total > 0:
        rule_pct = (total_rule / grand_total) * 100
        llm_pct = (total_llm / grand_total) * 100
    else:
        rule_pct = llm_pct = 0
    
    print("\n" + "=" * 60)
    print("总体统计:")
    print(f"  规则分类: {total_rule:4d} 条 ({rule_pct:5.1f}%)")
    print(f"  LLM 分类: {total_llm:4d} 条 ({llm_pct:5.1f}%)")
    print(f"  总计:     {grand_total:4d} 条")
    print("=" * 60)
    
    # 成本估算
    # 假设每条新闻 200 tokens，gemini-1.5-flash-8b: $0.0375/1M tokens
    tokens_per_item = 200
    total_tokens = total_llm * tokens_per_item
    cost_per_million = 0.0375
    estimated_cost = (total_tokens / 1_000_000) * cost_per_million
    
    print(f"\n成本估算:")
    print(f"  LLM 处理: {total_llm} 条新闻")
    print(f"  估计 tokens: {total_tokens:,}")
    print(f"  估计成本: ${estimated_cost:.6f}")
    
    # 建议
    print(f"\n优化建议:")
    if llm_pct > 70:
        print("  ⚠️  LLM 使用率过高 (>70%)")
        print("  建议: 降低 CLASSIFY_CONFIDENCE_THRESHOLD 到 0.65")
        print("  或者: 增加规则关键词")
    elif llm_pct < 20:
        print("  ✓ LLM 使用率较低 (<20%)，成本优化良好")
        print("  可选: 提高 CLASSIFY_CONFIDENCE_THRESHOLD 到 0.85 以提升准确度")
    else:
        print("  ✓ LLM 使用率适中 (20-70%)，平衡良好")
    
    print("=" * 60)

if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else "logs/main_workflow.log"
    analyze_logs(log_file)
