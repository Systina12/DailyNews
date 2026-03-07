#!/usr/bin/env python3
"""
测试小时报HTML样式优化和链接去重功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.merge_summaries import merge_summaries
from utils.link_processor import process_summary_links


def test_html_styling():
    """测试HTML样式生成"""
    print("=" * 60)
    print("测试1: HTML样式生成")
    print("=" * 60)
    
    # 模拟低风险摘要
    low_summary = """<h1>2026-03-06 头条</h1>
<p>中国经济持续增长，GDP增速达到5.2%[1]。</p>
<p>科技创新推动产业升级，新能源汽车销量创新高[2]。</p>"""
    
    # 模拟高风险摘要
    high_summary = """<h1>2026-03-06 头条</h1>
<p>国际局势紧张，多国加强军事部署[1]。</p>"""
    
    # 合并摘要
    merged = merge_summaries(
        low_risk_summary=low_summary,
        high_risk_summary=high_summary,
        date="2026-03-06",
        category="头条",
        add_section_headers=True
    )
    
    # 检查是否包含完整HTML结构
    checks = [
        ("<!DOCTYPE html>", "HTML文档声明"),
        ("<style>", "CSS样式"),
        ("font-family", "字体设置"),
        (".container", "容器样式"),
        ("max-width", "最大宽度"),
        ("border-radius", "圆角"),
        ("box-shadow", "阴影"),
        ("<h2>【ds新闻】</h2>", "低风险标题"),
        ("<h2>【gemini新闻】</h2>", "高风险标题"),
        (".footer", "页脚样式"),
    ]
    
    passed = 0
    for check, desc in checks:
        if check in merged:
            print(f"✓ {desc}")
            passed += 1
        else:
            print(f"✗ {desc} - 未找到: {check}")
    
    print(f"\n样式检查: {passed}/{len(checks)} 通过")
    
    # 保存HTML文件用于查看
    output_path = os.path.join(os.path.dirname(__file__), "test_styled_output.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(merged)
    print(f"\n✓ HTML已保存到: {output_path}")
    print("  可以在浏览器中打开查看效果")
    
    return passed == len(checks)


def test_link_deduplication():
    """测试链接去重功能"""
    print("\n" + "=" * 60)
    print("测试2: 链接去重")
    print("=" * 60)
    
    # 模拟包含重复引用的HTML
    html_with_duplicates = """<p>这是一条新闻[1]，继续报道[1]，更多细节[2]。</p>
<p>另一条新闻[3]，相关报道[3]，补充信息[3]。</p>"""
    
    # 模拟引用列表
    refs = [
        {"n": 1, "url": "https://example.com/news1", "title": "新闻1"},
        {"n": 2, "url": "https://example.com/news2", "title": "新闻2"},
        {"n": 3, "url": "https://example.com/news3", "title": "新闻3"},
    ]
    
    # 处理链接
    processed = process_summary_links(html_with_duplicates, refs)
    
    print("\n原始HTML:")
    print(html_with_duplicates)
    print("\n处理后HTML:")
    print(processed)
    
    # 检查每个段落中的链接数量
    import re
    paragraphs = re.findall(r"<p>(.*?)</p>", processed, re.DOTALL)
    
    all_passed = True
    for i, p in enumerate(paragraphs, 1):
        links = re.findall(r'<sup><a[^>]*>\[\d+\]</a></sup>', p)
        unique_links = list(dict.fromkeys(links))  # 保持顺序去重
        
        print(f"\n段落{i}:")
        print(f"  链接数: {len(links)}")
        print(f"  去重后: {len(unique_links)}")
        
        if len(links) == len(unique_links):
            print(f"  ✓ 无重复链接")
        else:
            print(f"  ✗ 存在重复链接")
            all_passed = False
    
    return all_passed


def test_only_low_risk():
    """测试只有低风险新闻的情况"""
    print("\n" + "=" * 60)
    print("测试3: 只有低风险新闻")
    print("=" * 60)
    
    low_summary = """<h1>2026-03-06 财经</h1>
<p>股市上涨，投资者信心增强[1]。</p>"""
    
    merged = merge_summaries(
        low_risk_summary=low_summary,
        high_risk_summary=None,
        date="2026-03-06",
        category="财经",
        add_section_headers=True
    )
    
    # 检查是否包含完整HTML结构
    has_html = "<!DOCTYPE html>" in merged
    has_style = "<style>" in merged
    no_gemini_section = "<h2>【gemini新闻】</h2>" not in merged
    
    print(f"包含HTML结构: {'✓' if has_html else '✗'}")
    print(f"包含CSS样式: {'✓' if has_style else '✗'}")
    print(f"不包含gemini章节: {'✓' if no_gemini_section else '✗'}")
    
    return has_html and has_style and no_gemini_section


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("小时报HTML样式优化测试")
    print("=" * 60 + "\n")
    
    results = []
    
    # 测试1: HTML样式
    try:
        results.append(("HTML样式生成", test_html_styling()))
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        results.append(("HTML样式生成", False))
    
    # 测试2: 链接去重
    try:
        results.append(("链接去重", test_link_deduplication()))
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        results.append(("链接去重", False))
    
    # 测试3: 只有低风险
    try:
        results.append(("只有低风险新闻", test_only_low_risk()))
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        results.append(("只有低风险新闻", False))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\n总计: {total_passed}/{len(results)} 测试通过")
    
    return total_passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
