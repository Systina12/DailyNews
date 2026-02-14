"""
LLM 相关异常定义
"""


class ContentFilteredException(Exception):
    """DeepSeek 内容安全机制触发异常"""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(f"DeepSeek 触发内容安全机制: {reason}")


class LLMAPIError(Exception):
    """LLM API 调用错误基类"""
    pass


class LLMTimeoutError(LLMAPIError):
    """LLM API 请求超时"""
    pass


class LLMConnectionError(LLMAPIError):
    """LLM API 连接错误"""
    pass


class LLMResponseError(LLMAPIError):
    """LLM API 响应错误"""
    pass
