"""
配置管理模块

支持从环境变量和配置文件读取配置
"""

import os
from pathlib import Path


class Settings:
    """应用配置类"""

    # 项目根目录
    BASE_DIR = Path(__file__).parent.parent

    # FreshRSS 配置
    FRESHRSS_URL = os.getenv(
        "FRESHRSS_URL",
        "http://172.18.0.6/api/greader.php/reader/api/0/stream/contents/user/-/state/com.google/reading-list"
    )
    FRESHRSS_AUTH_URL = os.getenv(
        "FRESHRSS_AUTH_URL",
        "http://172.18.0.6/api/greader.php/accounts/ClientLogin"
    )
    FRESHRSS_EMAIL = os.getenv("FRESHRSS_EMAIL", "")
    FRESHRSS_PASSWORD = os.getenv("FRESHRSS_PASSWORD", "")

    # deepseek API 配置
    DEEPSEEK_API_URL = os.getenv(
        "DEEPSEEK_API_URL",
        "https://api.deepseek.com/v1/chat/completions"
    )
    DEEPSEEK_TOKEN = os.getenv("DEEPSEEK_TOKEN", "")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Gemini 配置（使用 google.genai SDK，不需要 API URL）
    GEMINI_TOKEN = os.getenv("GEMINI_TOKEN", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

    # API 超时配置
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "60"))

    # 数据目录
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"

    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # 新闻过滤配置
    RUSSIA_LABEL = "user/-/label/俄罗斯"

    # LLM 请求配置
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.3"))
    DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "4000"))

    #SMTP配置
    SMTP_HOST = "SMTP_HOST",
    SMTP_PORT = "SMTP_PORT","587"
    SMTP_USERNAME = "SMTP_USERNAME"
    SMTP_PASSWORD = "SMTP_PASSWORD"
    SMTP_USE_TLS = True
    SMTP_USE_SSL = False
    SMTP_FROM = "SMTP_FROM"
    SMTP_TO ="SMTP_TO"

    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)

    @classmethod
    def validate(cls):
        """验证必要的配置是否存在"""
        errors = []

        if not cls.DEEPSEEK_TOKEN:
            errors.append("DEEPSEEK_TOKEN 未设置")

        if not cls.GEMINI_TOKEN:
            errors.append("GEMINI_TOKEN 未设置")

        if errors:
            raise ValueError(f"配置错误: {', '.join(errors)}")

        return True


# 创建全局配置实例
settings = Settings()
