"""
测试预处理模块
"""

import pytest
from preprocessing.dedupe import normalize_title, dedupe_items


class TestNormalizeTitle:
    """测试标题规范化"""

    def test_remove_brackets(self):
        """测试移除括号"""
        assert normalize_title("【突发】新闻标题") == "新闻标题"
        assert normalize_title("[Breaking] News Title") == "news title"

    def test_remove_prefix(self):
        """测试移除前缀"""
        assert normalize_title("突发：新闻标题") == "新闻标题"
        assert normalize_title("Breaking: News Title") == "news title"
        assert normalize_title("更新-新闻标题") == "新闻标题"

    def test_normalize_whitespace(self):
        """测试空格规范化"""
        assert normalize_title("新闻  标题   测试") == "新闻 标题 测试"

    def test_lowercase(self):
        """测试转小写"""
        assert normalize_title("NEWS TITLE") == "news title"

    def test_empty_string(self):
        """测试空字符串"""
        assert normalize_title("") == ""
        assert normalize_title(None) == ""


class TestDedupeItems:
    """测试去重功能"""

    def test_dedupe_identical_titles(self):
        """测试去重相同标题"""
        data = {
            "items": [
                {"title": "新闻标题1", "id": 1},
                {"title": "新闻标题1", "id": 2},
                {"title": "新闻标题2", "id": 3}
            ]
        }
        result = dedupe_items(data)
        assert len(result["items"]) == 2
        assert result["items"][0]["id"] == 1
        assert result["items"][1]["id"] == 3

    def test_dedupe_normalized_titles(self):
        """测试去重规范化后相同的标题"""
        data = {
            "items": [
                {"title": "【突发】新闻标题", "id": 1},
                {"title": "突发：新闻标题", "id": 2},
                {"title": "新闻标题", "id": 3}
            ]
        }
        result = dedupe_items(data)
        assert len(result["items"]) == 1
        assert result["items"][0]["id"] == 1

    def test_empty_items(self):
        """测试空列表"""
        data = {"items": []}
        result = dedupe_items(data)
        assert len(result["items"]) == 0
