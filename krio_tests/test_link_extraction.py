"""
测试链接提取功能
"""

def _extract_link(item):
    """
    从新闻 item 中提取链接
    优先级：canonical > alternate > link
    """
    link = ""
    
    # 1. 尝试从 canonical 数组提取
    canonical = item.get("canonical")
    if isinstance(canonical, list) and canonical:
        link = canonical[0].get("href", "") or ""
    
    # 2. 如果没有，尝试从 alternate 数组提取
    if not link:
        alternate = item.get("alternate")
        if isinstance(alternate, list) and alternate:
            link = alternate[0].get("href", "") or ""
    
    # 3. 最后尝试直接的 link 字段
    if not link:
        link = item.get("link", "") or ""
    
    return link


def test_link_extraction():
    """测试各种情况下的链接提取"""
    
    print("=" * 80)
    print("测试链接提取功能")
    print("=" * 80)
    
    # 测试用例
    test_cases = [
        {
            "name": "情况1: 只有 canonical 数组",
            "item": {
                "title": "测试新闻1",
                "canonical": [{"href": "https://example.com/news1"}]
            },
            "expected": "https://example.com/news1"
        },
        {
            "name": "情况2: 只有 alternate 数组",
            "item": {
                "title": "测试新闻2",
                "alternate": [{"href": "https://example.com/news2"}]
            },
            "expected": "https://example.com/news2"
        },
        {
            "name": "情况3: 只有 link 字段",
            "item": {
                "title": "测试新闻3",
                "link": "https://example.com/news3"
            },
            "expected": "https://example.com/news3"
        },
        {
            "name": "情况4: canonical 优先于 alternate",
            "item": {
                "title": "测试新闻4",
                "canonical": [{"href": "https://example.com/canonical"}],
                "alternate": [{"href": "https://example.com/alternate"}]
            },
            "expected": "https://example.com/canonical"
        },
        {
            "name": "情况5: alternate 优先于 link",
            "item": {
                "title": "测试新闻5",
                "alternate": [{"href": "https://example.com/alternate"}],
                "link": "https://example.com/link"
            },
            "expected": "https://example.com/alternate"
        },
        {
            "name": "情况6: 所有字段都为空",
            "item": {
                "title": "测试新闻6"
            },
            "expected": ""
        },
        {
            "name": "情况7: canonical 数组为空",
            "item": {
                "title": "测试新闻7",
                "canonical": [],
                "link": "https://example.com/link"
            },
            "expected": "https://example.com/link"
        },
        {
            "name": "情况8: canonical 数组中 href 为空",
            "item": {
                "title": "测试新闻8",
                "canonical": [{"href": ""}],
                "alternate": [{"href": "https://example.com/alternate"}]
            },
            "expected": "https://example.com/alternate"
        },
    ]
    
    # 运行测试
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = _extract_link(test["item"])
        expected = test["expected"]
        
        if result == expected:
            print(f"\n✓ {test['name']}")
            print(f"  结果: {result if result else '(空)'}")
            passed += 1
        else:
            print(f"\n✗ {test['name']}")
            print(f"  期望: {expected if expected else '(空)'}")
            print(f"  实际: {result if result else '(空)'}")
            failed += 1
    
    # 总结
    print("\n" + "=" * 80)
    print(f"测试总结: {passed} 通过, {failed} 失败")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = test_link_extraction()
    exit(0 if success else 1)
