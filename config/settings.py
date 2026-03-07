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
    # 使用 localhost:51264 访问（FreshRSS 容器端口映射）
    FRESHRSS_URL = os.getenv(
        "FRESHRSS_URL",
        "http://localhost:51264/api/greader.php/reader/api/0/stream/contents/user/-/state/com.google/reading-list"
    )
    FRESHRSS_AUTH_URL = os.getenv(
        "FRESHRSS_AUTH_URL",
        "http://localhost:51264/api/greader.php/accounts/ClientLogin"
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
    # 默认使用最新的便宜模型作为主 Gemini 模型，除非通过环境变量覆盖
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    # Gemini Flash 便宜模型（用于分类和风险评估）
    GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash-lite")

    # API 超时配置
    _timeout = int(os.getenv("API_TIMEOUT", "60"))
    API_TIMEOUT = _timeout if _timeout > 0 else 60

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

    # SMTP配置（从环境变量读取）
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    SMTP_FROM = os.getenv("SMTP_FROM", "")
    SMTP_TO = os.getenv("SMTP_TO", "")  # 多个收件人用逗号分隔
    # 测试模式收件人（仅在 CLI 传入 --test 时生效）
    # 优先使用 TEST_EMAIL，其次尝试 TEST-EMAIL（兼容部分部署方式）
    TEST_EMAIL = os.getenv("TEST_EMAIL", os.getenv("TEST-EMAIL", ""))

    # 国际新闻保留策略
    low_water = int(os.getenv("INTL_KEEP_LOW_WATERMARK", "10"))  # 少于等于这个数：全留
    ratio = float(os.getenv("INTL_KEEP_RATIO", "0.2"))  # 多的时候：按比例留
    min_keep = int(os.getenv("INTL_MIN_KEEP", "10"))  # 下限
    max_keep = int(os.getenv("INTL_MAX_KEEP", "50"))  # 上限

    # 头条新闻保留策略（动态控制数量）
    # 基准：1小时（每小时报）的配置
    HEADLINE_BASE_HOURS = int(os.getenv("HEADLINE_BASE_HOURS", "1"))  # 基准时间改为1小时
    HEADLINE_BASE_LOW_WATERMARK = int(os.getenv("HEADLINE_BASE_LOW_WATERMARK", "10"))  # 1小时：10条以下全留
    HEADLINE_BASE_MAX_KEEP = int(os.getenv("HEADLINE_BASE_MAX_KEEP", "20"))  # 1小时：最多20条
    
    # 固定参数（不随时间变化）
    HEADLINE_KEEP_RATIO = float(os.getenv("HEADLINE_KEEP_RATIO", "0.6"))  # 保留比例 60%（提高到60%）
    HEADLINE_MIN_KEEP = int(os.getenv("HEADLINE_MIN_KEEP", "8"))  # 最少保留 8 条

    # 分类置信度阈值（高于此值使用规则分类，低于此值使用 LLM）
    # 优化：从0.75降到0.60，减少LLM调用（规则分类准确率足够高）
    # 参考：https://www.evidentlyai.com/classification-metrics/classification-threshold
    # 成本影响：预计减少30-40%的分类LLM调用
    CLASSIFY_CONFIDENCE_THRESHOLD = float(os.getenv("CLASSIFY_CONFIDENCE_THRESHOLD", "0.60"))

    # 头条排序配置
    HEADLINE_ENABLE_LLM_SCORING = os.getenv("HEADLINE_ENABLE_LLM_SCORING", "true").lower() == "true"
    HEADLINE_ENABLE_LEARNING = os.getenv("HEADLINE_ENABLE_LEARNING", "true").lower() == "true"
    HEADLINE_BLACKLIST_MAX_SIZE = int(os.getenv("HEADLINE_BLACKLIST_MAX_SIZE", "100"))  # 最多100个关键词
    HEADLINE_BLACKLIST_MIN_FREQ = float(os.getenv("HEADLINE_BLACKLIST_MIN_FREQ", "0.3"))  # 最低频率0.3
    HEADLINE_BLACKLIST_DECAY = float(os.getenv("HEADLINE_BLACKLIST_DECAY", "0.95"))  # 衰减因子0.95
    
    # 批量处理优化配置
    # Gemini 2.5 Flash Lite支持1M tokens上下文窗口，可以处理更大批次
    # 风险评估prompt更简单，可以增加批次大小
    RISK_BATCH_SIZE = int(os.getenv("RISK_BATCH_SIZE", "200"))  # 从隐式100增加到200
    CLASSIFY_BATCH_SIZE = int(os.getenv("CLASSIFY_BATCH_SIZE", "100"))  # 保持100
    SCORING_BATCH_SIZE = int(os.getenv("SCORING_BATCH_SIZE", "100"))  # 保持100

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

        # 验证 FreshRSS 配置（如果需要使用）
        if not cls.FRESHRSS_EMAIL or not cls.FRESHRSS_PASSWORD:
            errors.append("FRESHRSS_EMAIL 或 FRESHRSS_PASSWORD 未设置")

        # 验证超时配置
        if cls.API_TIMEOUT <= 0:
            errors.append(f"API_TIMEOUT 必须大于 0，当前值: {cls.API_TIMEOUT}")

        if errors:
            raise ValueError(f"配置错误: {', '.join(errors)}")

        return True


# 创建全局配置实例
settings = Settings()
