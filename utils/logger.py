"""
日志配置模块
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(
    name: str = "DZTnews",
    log_level: str = "INFO",
    log_dir: Path = None,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    配置并返回日志记录器

    Args:
        name: 日志记录器名称
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日志文件目录
        log_to_file: 是否输出到文件
        log_to_console: 是否输出到控制台

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件输出
    if log_to_file and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(exist_ok=True, parents=True)

        # 按日期创建日志文件
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称，如果为None则返回根记录器

    Returns:
        logging.Logger: 日志记录器
    """
    if name:
        return logging.getLogger(f"DZTnews.{name}")
    return logging.getLogger("DZTnews")


# 创建默认日志记录器
default_logger = setup_logger(
    name="DZTnews",
    log_level="INFO",
    log_dir=Path(__file__).parent.parent / "logs",
    log_to_file=True,
    log_to_console=True
)
