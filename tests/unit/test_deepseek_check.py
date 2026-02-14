"""
测试 DeepSeek 内容安全检测工具
"""

import pytest
from utils.deepseek_check import is_content_filtered, check_deepseek_response


class TestIsContentFiltered:
    """测试 is_content_filtered 函数"""

    def test_http_400_status(self):
        """测试 HTTP 400 状态码"""
        assert is_content_filtered("some content", status_code=400) is True

    def test_none_response(self):
        """测试 None 响应"""
        assert is_content_filtered(None) is True

    def test_empty_string(self):
        """测试空字符串"""
        assert is_content_filtered("") is True
        assert is_content_filtered("   ") is True

    def test_valid_response(self):
        """测试有效响应"""
        assert is_content_filtered("valid content") is False
        assert is_content_filtered("valid content", status_code=200) is False


class TestCheckDeepseekResponse:
    """测试 check_deepseek_response 函数"""

    def test_http_400_status(self):
        """测试 HTTP 400 状态码"""
        result = check_deepseek_response("content", status_code=400)
        assert result["is_filtered"] is True
        assert result["reason"] == "HTTP 400 状态码"
        assert result["safe_to_use"] is False

    def test_none_response(self):
        """测试 None 响应"""
        result = check_deepseek_response(None)
        assert result["is_filtered"] is True
        assert result["reason"] == "响应为 None"
        assert result["safe_to_use"] is False

    def test_empty_text(self):
        """测试空文本"""
        result = check_deepseek_response("")
        assert result["is_filtered"] is True
        assert result["reason"] == "响应文本为空"
        assert result["safe_to_use"] is False

    def test_valid_response(self):
        """测试有效响应"""
        result = check_deepseek_response("valid content")
        assert result["is_filtered"] is False
        assert result["reason"] == "正常响应"
        assert result["safe_to_use"] is True
        assert result["response_length"] == 13

    def test_with_error_message(self):
        """测试带错误信息"""
        result = check_deepseek_response("content", error_message="API Error")
        assert result["is_filtered"] is True
        assert "API Error" in result["reason"]
        assert result["safe_to_use"] is False
