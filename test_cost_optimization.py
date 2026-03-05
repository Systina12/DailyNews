#!/usr/bin/env python3
"""
测试LLM成本优化效果

运行此脚本来验证：
1. 分类置信度阈值优化
2. 风险评估快速检查优化
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from preprocessing.classify import Classify
from workflows.risk_assessment import _quick_risk_check
from config import settings


def test_classify_threshold():
    """测试分类置信度阈值"""
    print("=" * 60)
    print("测试1: 分类置信度阈值")
    print("=" * 60)
    
    print(f"当前阈值: {settings.CLASSIFY_CONFIDENCE_THRESHOLD}")
    print(f"预期: 0.60（从0.75降低）")
    
    # 创建测试新闻
    test_items = [
        {
            "title": "Trump announces new tariff policy",
            "summaryText": "President Trump announced new tariffs on imports...",
            "origin": {"title": "CNN Politics"}
        },
        {
            "title": "Stock market reaches new high",
            "summaryText": "The S&P 500 reached a record high today...",
            "origin": {"title": "Bloomberg Business"}
        },
        {
            "title": "New AI breakthrough in healthcare",
            "summaryText": "Researchers developed a new AI system...",
            "origin": {"title": "TechCrunch"}
        }
    ]
    
    classifier = Classify(category="政治")
    
    llm_count = 0
    rule_count = 0
    
    for item in test_items:
        category, confidence = classifier._classify_item(item)
        
        if confidence >= settings.CLASSIFY_CONFIDENCE_THRESHOLD:
            rule_count += 1
            status = "✓ 规则分类"
        else:
            llm_count += 1
            status = "→ 需要LLM"
        
        print(f"\n标题: {item['title'][:50]}...")
        print(f"  分类: {category}, 置信度: {confidence:.2f}, {status}")
    
    print(f"\n总结:")
    print(f"  规则分类: {rule_count}/{len(test_items)} ({rule_count/len(test_items)*100:.0f}%)")
    print(f"  需要LLM: {llm_count}/{len(test_items)} ({llm_count/len(test_items)*100:.0f}%)")
    print(f"  预期节省: {(0.75-0.60)/0.75*100:.0f}% LLM调用")


def test_risk_quick_check():
    """测试风险评估快速检查"""
    print("\n" + "=" * 60)
    print("测试2: 风险评估快速检查")
    print("=" * 60)
    
    print(f"快速检查启用: {settings.RISK_ENABLE_QUICK_CHECK}")
    
    # 测试新闻
    test_items = [
        {
            "title": "US economy grows 3% in Q4",
            "summaryText": "The US economy expanded at an annual rate of 3% in the fourth quarter...",
            "expected": "low",
            "reason": "不包含中国敏感词"
        },
        {
            "title": "China announces new tech policy",
            "summaryText": "Beijing unveiled a new technology development plan...",
            "expected": None,
            "reason": "包含'China'和'Beijing'"
        },
        {
            "title": "Taiwan election results announced",
            "summaryText": "Taiwan's presidential election concluded with...",
            "expected": None,
            "reason": "包含'Taiwan'"
        },
        {
            "title": "Apple releases new iPhone",
            "summaryText": "Apple Inc. announced the latest iPhone model with improved features...",
            "expected": "low",
            "reason": "不包含敏感词"
        },
        {
            "title": "中国经济增长放缓",
            "summaryText": "中国国家统计局公布最新经济数据...",
            "expected": None,
            "reason": "包含'中国'"
        },
        {
            "title": "欧洲央行降息",
            "summaryText": "欧洲央行宣布降低基准利率...",
            "expected": "low",
            "reason": "不包含敏感词"
        }
    ]
    
    safe_count = 0
    llm_count = 0
    correct_count = 0
    
    for item in test_items:
        result = _quick_risk_check(item)
        
        if result == "low":
            safe_count += 1
            status = "✓ 明显安全（跳过LLM）"
        else:
            llm_count += 1
            status = "→ 需要LLM判断"
        
        # 检查是否符合预期
        is_correct = (result == item["expected"])
        correct_count += is_correct
        
        print(f"\n标题: {item['title'][:50]}")
        print(f"  结果: {status}")
        print(f"  原因: {item['reason']}")
        print(f"  {'✓ 正确' if is_correct else '✗ 错误'}")
    
    print(f"\n总结:")
    print(f"  明显安全: {safe_count}/{len(test_items)} ({safe_count/len(test_items)*100:.0f}%)")
    print(f"  需要LLM: {llm_count}/{len(test_items)} ({llm_count/len(test_items)*100:.0f}%)")
    print(f"  准确率: {correct_count}/{len(test_items)} ({correct_count/len(test_items)*100:.0f}%)")
    print(f"  预期节省: {safe_count/len(test_items)*100:.0f}% LLM调用")


def test_cost_estimation():
    """估算成本节省"""
    print("\n" + "=" * 60)
    print("测试3: 成本节省估算")
    print("=" * 60)
    
    # 假设每天1000条新闻
    daily_news = 1000
    
    # 价格（每百万token）
    gemini_flash_lite_input = 0.10
    gemini_flash_lite_output = 0.40
    
    # 分类优化
    classify_before = 0.30  # 30%需要LLM
    classify_after = 0.18   # 18%需要LLM（降低40%）
    classify_tokens_in = 500
    classify_tokens_out = 100
    
    classify_cost_before = (
        daily_news * classify_before * 
        (classify_tokens_in * gemini_flash_lite_input + classify_tokens_out * gemini_flash_lite_output) / 1_000_000
    )
    classify_cost_after = (
        daily_news * classify_after * 
        (classify_tokens_in * gemini_flash_lite_input + classify_tokens_out * gemini_flash_lite_output) / 1_000_000
    )
    
    # 风险评估优化
    risk_batches_before = 10
    risk_batches_after = 5  # 减少50%
    risk_tokens_in = 3000
    risk_tokens_out = 200
    
    risk_cost_before = (
        risk_batches_before * 
        (risk_tokens_in * gemini_flash_lite_input + risk_tokens_out * gemini_flash_lite_output) / 1_000_000
    )
    risk_cost_after = (
        risk_batches_after * 
        (risk_tokens_in * gemini_flash_lite_input + risk_tokens_out * gemini_flash_lite_output) / 1_000_000
    )
    
    print(f"假设: 每天处理 {daily_news} 条新闻\n")
    
    print("分类优化:")
    print(f"  优化前: {classify_cost_before:.4f} USD/天")
    print(f"  优化后: {classify_cost_after:.4f} USD/天")
    print(f"  节省: {classify_cost_before - classify_cost_after:.4f} USD/天 ({(classify_cost_before - classify_cost_after)/classify_cost_before*100:.0f}%)")
    
    print(f"\n风险评估优化:")
    print(f"  优化前: {risk_cost_before:.4f} USD/天")
    print(f"  优化后: {risk_cost_after:.4f} USD/天")
    print(f"  节省: {risk_cost_before - risk_cost_after:.4f} USD/天 ({(risk_cost_before - risk_cost_after)/risk_cost_before*100:.0f}%)")
    
    total_before = classify_cost_before + risk_cost_before
    total_after = classify_cost_after + risk_cost_after
    
    print(f"\n总计:")
    print(f"  优化前: {total_before:.4f} USD/天")
    print(f"  优化后: {total_after:.4f} USD/天")
    print(f"  节省: {total_before - total_after:.4f} USD/天 ({(total_before - total_after)/total_before*100:.0f}%)")
    print(f"\n  月度节省: {(total_before - total_after) * 30:.2f} USD")
    print(f"  年度节省: {(total_before - total_after) * 365:.2f} USD")


if __name__ == "__main__":
    print("\n🔍 LLM成本优化测试\n")
    
    try:
        test_classify_threshold()
        test_risk_quick_check()
        test_cost_estimation()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
