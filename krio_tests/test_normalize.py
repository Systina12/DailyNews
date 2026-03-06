"""
测试数据标准化功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocessing.normalize import normalize_items, normalize_link


def test_normalize_link():
    """测试链接提取功能"""
    print("=" * 80)
    print("测试 normalize_link() 函数")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "canonical 数组",
            "item": {"canonical": [{"href": "https://example.com/1"}]},
            "expected": "https://example.com/1"
        },
        {
            "name": "alternate 数组",
            "item": {"alternate": [{"href": "https://example.com/2"}]},
            "expected": "https://example.com/2"
        },
        {
            "name": "link 字段",
            "item": {"link": "https://example.com/3"},
            "expected": "https://example.com/3"
        },
        {
            "name": "优先级测试",
            "item": {
                "canonical": [{"href": "https://canonical.com"}],
                "alternate": [{"href": "https://alternate.com"}],
                "link": "https://link.com"
            },
            "expected": "https://canonical.com"
        },
    ]
    
    passed = 0
    for test in test_cases:
        result = normalize_link(test["item"])
        if result == test["expected"]:
            print(f"✓ {test['name']}: {result}")
            passed += 1
        else:
            print(f"✗ {test['name']}: 期望 {test['expected']}, 实际 {result}")
    
    print(f"\n{passed}/{len(test_cases)} 测试通过\n")
    return passed == len(test_cases)


def test_normalize_items():
    """测试批量标准化功能"""
    print("=" * 80)
    print("测试 normalize_items() 函数")
    print("=" * 80)
    
    # 模拟 RSS 数据
    data = {
        "items": [
            {
                "title": "新闻1",
                "canonical": [{"href": "https://example.com/news1"}],
                # 没有 link 字段
            },
            {
                "title": "新闻2",
                "alternate": [{"href": "https://example.com/news2"}],
                "link": ""  # link 为空
            },
            {
                "title": "新闻3",
                "link": "https://example.com/news3"  # 已有 link
            },
            {
                "title": "新闻4",
                "canonical": [{"href": "https://example.com/news4"}],
                "link": "https://example.com/news4"  # link 与 canonical 相同
            },
        ]
    }
    
    # 标准化
    result = normalize_items(data)
    
    # 验证
    items = result["items"]
    
    print("\n标准化结果：")
    for i, item in enumerate(items, 1):
        link = item.get("link", "")
        print(f"  新闻{i}: {link}")
    
    # 检查
    checks = [
        (items[0].get("link") == "https://example.com/news1", "新闻1 链接应该从 canonical 提取"),
        (items[1].get("link") == "https://example.com/news2", "新闻2 链接应该从 alternate 提取"),
        (items[2].get("link") == "https://example.com/news3", "新闻3 链接应该保持不变"),
        (items[3].get("link") == "https://example.com/news4", "新闻4 链接应该保持不变"),
    ]
    
    passed = sum(1 for check, _ in checks if check)
    
    print(f"\n验证结果：")
    for check, desc in checks:
        print(f"  {'✓' if check else '✗'} {desc}")
    
    print(f"\n{passed}/{len(checks)} 检查通过\n")
    return passed == len(checks)


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("数据标准化功能测试")
    print("=" * 80 + "\n")
    
    test1 = test_normalize_link()
    test2 = test_normalize_items()
    
    print("=" * 80)
    if test1 and test2:
        print("✓ 所有测试通过")
        print("=" * 80)
        return 0
    else:
        print("✗ 部分测试失败")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit(main())
