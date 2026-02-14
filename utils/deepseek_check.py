"""
DeepSeek 内容安全检测工具
"""


def is_content_filtered(response_text, status_code=None):
    """
    判断 DeepSeek 是否触发内容安全机制

    触发风控的标志：
    - HTTP 400 状态码
    - 响应为空（None 或空字符串）
    - 响应文本为空白字符

    Args:
        response_text: DeepSeek 返回的文本内容
        status_code: HTTP 状态码（可选）

    Returns:
        bool: True 表示触发风控，False 表示正常响应
    """
    # 检查 400 状态码
    if status_code == 400:
        return True

    # 检查空返回
    if response_text is None:
        return True

    # 检查空文本
    if isinstance(response_text, str) and not response_text.strip():
        return True

    return False


def check_deepseek_response(response_text, status_code=None, error_message=None):
    """
    检查 DeepSeek 响应状态（详细版本）

    Args:
        response_text: DeepSeek 返回的文本内容
        status_code: HTTP 状态码（可选）
        error_message: 错误信息（可选）

    Returns:
        dict: 检查结果
            {
                "is_filtered": bool,      # 是否触发风控
                "reason": str,            # 触发原因
                "safe_to_use": bool,      # 响应是否可用
                "response_length": int    # 响应长度
            }
    """
    result = {
        "is_filtered": False,
        "reason": None,
        "safe_to_use": True,
        "response_length": 0
    }

    # 检查 400 状态码
    if status_code == 400:
        result["is_filtered"] = True
        result["reason"] = "HTTP 400 状态码"
        result["safe_to_use"] = False
        return result

    # 检查空返回
    if response_text is None:
        result["is_filtered"] = True
        result["reason"] = "响应为 None"
        result["safe_to_use"] = False
        return result

    # 检查空文本
    if isinstance(response_text, str):
        stripped = response_text.strip()
        result["response_length"] = len(stripped)

        if not stripped:
            result["is_filtered"] = True
            result["reason"] = "响应文本为空"
            result["safe_to_use"] = False
            return result

    # 检查错误信息
    if error_message:
        result["is_filtered"] = True
        result["reason"] = f"API 错误: {error_message}"
        result["safe_to_use"] = False
        return result

    # 正常响应
    result["reason"] = "正常响应"
    return result
