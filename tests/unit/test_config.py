"""
测试配置模块
"""

import pytest
from config import settings, Settings


def test_settings_instance():
    """测试配置实例存在"""
    assert settings is not None
    assert isinstance(settings, Settings)


def test_settings_has_required_attributes():
    """测试配置包含必要的属性"""
    assert hasattr(settings, "DEEPSEEK_API_URL")
    assert hasattr(settings, "GEMINI_API_URL")
    assert hasattr(settings, "API_TIMEOUT")
    assert hasattr(settings, "DATA_DIR")
    assert hasattr(settings, "LOGS_DIR")


def test_settings_directories():
    """测试目录配置"""
    assert settings.DATA_DIR.name == "data"
    assert settings.LOGS_DIR.name == "logs"


def test_ensure_directories():
    """测试目录创建"""
    settings.ensure_directories()
    assert settings.DATA_DIR.exists()
    assert settings.LOGS_DIR.exists()


def test_default_values():
    """测试默认值"""
    assert settings.API_TIMEOUT == 60
    assert settings.DEFAULT_TEMPERATURE == 0.3
    assert settings.DEFAULT_MAX_TOKENS == 4000
