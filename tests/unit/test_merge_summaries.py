"""
测试摘要合并工具
"""

import pytest
from utils.merge_summaries import (
    extract_html_content,
    renumber_references,
    merge_summaries
)


class TestExtractHtmlContent:
    """测试HTML内容提取"""

    def test_extract_title_and_date(self):
        """测试提取标题和日期"""
        html = "<h1>2026-02-14 头条</h1><p>内容</p>"
        result = extract_html_content(html)
        assert result["title"] == "2026-02-14 头条"
        assert result["date"] == "2026-02-14"

    def test_extract_paragraphs(self):
        """测试提取段落"""
        html = "<h1>标题</h1><p>段落1</p><p>段落2</p>"
        result = extract_html_content(html)
        assert len(result["paragraphs"]) == 2
        assert result["paragraphs"][0] == "段落1"
        assert result["paragraphs"][1] == "段落2"

    def test_extract_max_ref_num(self):
        """测试提取最大引用编号"""
        html = '<p>新闻<a href="#ref1">[1]</a>和<a href="#ref3">[3]</a></p>'
        result = extract_html_content(html)
        assert result["max_ref_num"] == 3


class TestRenumberReferences:
    """测试引用重新编号"""

    def test_renumber_with_offset(self):
        """测试带偏移量的重新编号"""
        paragraph = '新闻<a href="#ref1">[1]</a>和<a href="#ref2">[2]</a>'
        result = renumber_references(paragraph, 5)
        assert '<a href="#ref6">[6]</a>' in result
        assert '<a href="#ref7">[7]</a>' in result

    def test_no_references(self):
        """测试没有引用的段落"""
        paragraph = "没有引用的段落"
        result = renumber_references(paragraph, 5)
        assert result == paragraph


class TestMergeSummaries:
    """测试摘要合并"""

    def test_merge_both_summaries(self):
        """测试合并两个摘要"""
        low = "<h1>2026-02-14 头条</h1><p>低风险新闻<a href=\"#ref1\">[1]</a></p>"
        high = "<h1>2026-02-14 头条</h1><p>高风险新闻<a href=\"#ref1\">[1]</a></p>"

        result = merge_summaries(low, high)

        assert "2026-02-14 头条" in result
        assert "低风险新闻" in result
        assert "高风险新闻" in result
        # 高风险的引用应该被重新编号
        assert '<a href="#ref2">[2]</a>' in result

    def test_merge_only_low(self):
        """测试只有低风险摘要"""
        low = "<h1>2026-02-14 头条</h1><p>低风险新闻</p>"
        result = merge_summaries(low, None)
        assert result == low

    def test_merge_only_high(self):
        """测试只有高风险摘要"""
        high = "<h1>2026-02-14 头条</h1><p>高风险新闻</p>"
        result = merge_summaries(None, high)
        assert result == high

    def test_merge_empty(self):
        """测试两个都为空"""
        result = merge_summaries(None, None)
        assert result == ""

    def test_merge_with_section_headers(self):
        """测试带分节标题的合并"""
        low = "<h1>2026-02-14 头条</h1><p>低风险新闻</p>"
        high = "<h1>2026-02-14 头条</h1><p>高风险新闻</p>"

        result = merge_summaries(low, high, add_section_headers=True)

        assert "【主要新闻】" in result
        assert "【其他新闻】" in result

    def test_merge_without_section_headers(self):
        """测试不带分节标题的合并"""
        low = "<h1>2026-02-14 头条</h1><p>低风险新闻</p>"
        high = "<h1>2026-02-14 头条</h1><p>高风险新闻</p>"

        result = merge_summaries(low, high, add_section_headers=False)

        assert "【主要新闻】" not in result
        assert "【其他新闻】" not in result
