import os


def get_deepseek_token():
    """从环境变量中读取DeepSeek token"""
    token = os.getenv('DEEPSEEK_TOKEN')
    if not token:
        raise ValueError("DEEPSEEK_TOKEN 环境变量未设置")
    return token


def get_gemini_token():
    """从环境变量中读取Gemini token"""
    token = os.getenv('GEMINI_TOKEN')
    if not token:
        raise ValueError("GEMINI_TOKEN 环境变量未设置")
    return token
