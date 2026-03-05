#!/usr/bin/env python3
"""
简化版LLM成本优化测试（不需要依赖）

验证优化配置和逻辑
"""


def test_risk_quick_check_logic():
    """测试风险评估快速检查逻辑"""
    print("=" * 60)
    print("测试: 风险评估快速检查逻辑")
    print("=" * 60)
    
    # 敏感关键词列表（从代码中复制）
    sensitive_keywords = [
        # 中文
        "中国", "中共", "习近平", "北京", "台湾", "台北", "香港", "澳门",
        "西藏", "新疆", "维吾尔", "法轮功", "六四", "天安门",
        # 英文
        "china", "chinese", "ccp", "xi jinping", "beijing", "taiwan", "taipei",
        "hong kong", "macau", "tibet", "xinjiang", "uyghur", "falun gong",
        # 俄文
        "китай", "пекин", "тайвань"
    ]
    
    def quick_check(title, summary):
        """简化的快速检查"""
        text = f"{title} {summary}".lower()
        if not any(kw in text for kw in sensitive_keywords):
            return "low"
        return None
    
    # 测试用例
    test_cases = [
        {
            "title": "US economy grows 3% in Q4",
            "summary": "The US economy expanded at an annual rate of 3%...",
            "expected": "low",
            "reason": "不包含敏感词"
        },
        {
            "title": "China announces new tech policy",
            "summary": "Beijing unveiled a new technology development plan...",
            "expected": None,
            "reason": "包含'China'和'Beijing'"
        },
        {
            "title": "Taiwan election results",
            "summary": "Taiwan's presidential election concluded...",
            "expected": None,
            "reason": "包含'Taiwan'"
        },
        {
            "title": "Apple releases new iPhone",
            "summary": "Apple Inc. announced the latest iPhone model...",
            "expected": "low",
            "reason": "不包含敏感词"
        },
        {
            "title": "中国经济增长放缓",
            "summary": "中国国家统计局公布最新数据...",
            "expected": None,
            "reason": "包含'中国'"
        },
        {
            "title": "欧洲央行降息",
            "summary": "欧洲央行宣布降低基准利率...",
            "expected": "low",
            "reason": "不包含敏感词"
        },
        {
            "title": "Google AI breakthrough",
            "summary": "Google announced a major breakthrough in AI...",
            "expected": "low",
            "reason": "不包含敏感词"
        },
        {
            "title": "Hong Kong protests continue",
            "summary": "Protests in Hong Kong entered their third week...",
            "expected": None,
            "reason": "包含'Hong Kong'"
        }
    ]
    
    safe_count = 0
    llm_count = 0
    correct_count = 0
    
    for i, case in enumerate(test_cases, 1):
        result = quick_check(case["title"], case["summary"])
        
        if result == "low":
            safe_count += 1
            status = "✓ 明显安全（跳过LLM）"
        else:
            llm_count += 1
            status = "→ 需要LLM判断"
        
        is_correct = (result == case["expected"])
        correct_count += is_correct
        
        print(f"\n{i}. {case['title'][:50]}")
        print(f"   结果: {status}")
        print(f"   原因: {case['reason']}")
        print(f"   {'✓ 正确' if is_correct else '✗ 错误'}")
    
    print(f"\n{'='*60}")
    print("总结:")
    print(f"  明显安全: {safe_count}/{len(test_cases)} ({safe_count/len(test_cases)*100:.0f}%)")
    print(f"  需要LLM: {llm_count}/{len(test_cases)} ({llm_count/len(test_cases)*100:.0f}%)")
    print(f"  准确率: {correct_count}/{len(test_cases)} ({correct_count/len(test_cases)*100:.0f}%)")
    print(f"  预期节省LLM调用: {safe_count/len(test_cases)*100:.0f}%")


def test_cost_estimation():
    """估算成本节省"""
    print("\n" + "=" * 60)
    print("成本节省估算")
    print("=" * 60)
    
    # 假设每天1000条新闻
    daily_news = 1000
    
    # 价格（每百万token）
    gemini_flash_lite_input = 0.10
    gemini_flash_lite_output = 0.40
    
    print(f"\n假设: 每天处理 {daily_news} 条新闻")
    print(f"模型: Gemini 2.5 Flash Lite (${gemini_flash_lite_input}/${gemini_flash_lite_output} per 1M tokens)")
    
    # 优化1: 分类置信度阈值
    print(f"\n{'='*60}")
    print("优化1: 分类置信度阈值 (0.75 → 0.60)")
    print(f"{'='*60}")
    
    classify_before_rate = 0.30  # 30%需要LLM
    classify_after_rate = 0.18   # 18%需要LLM（降低40%）
    classify_tokens_in = 500
    classify_tokens_out = 100
    
    classify_cost_before = (
        daily_news * classify_before_rate * 
        (classify_tokens_in * gemini_flash_lite_input + classify_tokens_out * gemini_flash_lite_output) / 1_000_000
    )
    classify_cost_after = (
        daily_news * classify_after_rate * 
        (classify_tokens_in * gemini_flash_lite_input + classify_tokens_out * gemini_flash_lite_output) / 1_000_000
    )
    
    print(f"  LLM调用率: {classify_before_rate*100:.0f}% → {classify_after_rate*100:.0f}%")
    print(f"  优化前: ${classify_cost_before:.4f}/天")
    print(f"  优化后: ${classify_cost_after:.4f}/天")
    print(f"  节省: ${classify_cost_before - classify_cost_after:.4f}/天 ({(classify_cost_before - classify_cost_after)/classify_cost_before*100:.0f}%)")
    
    # 优化4: 风险评估快速检查
    print(f"\n{'='*60}")
    print("优化4: 风险评估快速检查")
    print(f"{'='*60}")
    
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
    
    print(f"  批次数: {risk_batches_before} → {risk_batches_after}")
    print(f"  优化前: ${risk_cost_before:.4f}/天")
    print(f"  优化后: ${risk_cost_after:.4f}/天")
    print(f"  节省: ${risk_cost_before - risk_cost_after:.4f}/天 ({(risk_cost_before - risk_cost_after)/risk_cost_before*100:.0f}%)")
    
    # 总计
    print(f"\n{'='*60}")
    print("总计")
    print(f"{'='*60}")
    
    total_before = classify_cost_before + risk_cost_before
    total_after = classify_cost_after + risk_cost_after
    total_saved = total_before - total_after
    
    print(f"  优化前: ${total_before:.4f}/天")
    print(f"  优化后: ${total_after:.4f}/天")
    print(f"  节省: ${total_saved:.4f}/天 ({total_saved/total_before*100:.0f}%)")
    print(f"\n  月度节省: ${total_saved * 30:.2f}")
    print(f"  年度节省: ${total_saved * 365:.2f}")


def show_config():
    """显示优化配置"""
    print("\n" + "=" * 60)
    print("优化配置")
    print("=" * 60)
    
    print("\n环境变量配置:")
    print("  # 分类置信度阈值（从0.75降到0.60）")
    print("  export CLASSIFY_CONFIDENCE_THRESHOLD=0.60")
    print("\n  # 启用风险评估快速检查")
    print("  export RISK_ENABLE_QUICK_CHECK=true")
    
    print("\n代码位置:")
    print("  - config/settings.py: 配置定义")
    print("  - preprocessing/classify.py: 分类逻辑")
    print("  - workflows/risk_assessment.py: 风险评估逻辑")
    
    print("\n回滚方案:")
    print("  # 如果需要回滚到原有逻辑")
    print("  export CLASSIFY_CONFIDENCE_THRESHOLD=0.75")
    print("  export RISK_ENABLE_QUICK_CHECK=false")


if __name__ == "__main__":
    print("\n🔍 LLM成本优化测试（简化版）\n")
    
    try:
        test_risk_quick_check_logic()
        test_cost_estimation()
        show_config()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成")
        print("=" * 60)
        print("\n详细说明请查看: LLM_COST_OPTIMIZATION.md")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
