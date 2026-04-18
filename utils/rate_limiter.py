"""
速率限制器模块

用于控制 API 调用频率，避免触发速率限制
"""
import time
from collections import deque
from threading import Lock
from utils.logger import get_logger

logger = get_logger("rate_limiter")


class RateLimiter:
    """
    简单的速率限制器

    使用滑动窗口算法限制请求频率
    """

    def __init__(self, max_calls: int, time_window: float):
        """
        Args:
            max_calls: 时间窗口内允许的最大调用次数
            time_window: 时间窗口大小（秒）
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.lock = Lock()
        logger.debug(f"RateLimiter 初始化: {max_calls} 次/{time_window} 秒")

    def acquire(self):
        """
        获取调用许可，如果超过速率限制则等待

        这个方法会阻塞直到可以进行调用
        """
        sleep_time = 0
        with self.lock:
            now = time.time()

            # 移除时间窗口外的调用记录
            while self.calls and self.calls[0] <= now - self.time_window:
                self.calls.popleft()

            # 如果达到限制，计算等待时间
            if len(self.calls) >= self.max_calls:
                sleep_time = self.calls[0] + self.time_window - now
                if sleep_time > 0:
                    logger.debug(f"达到速率限制，等待 {sleep_time:.2f} 秒")
                else:
                    sleep_time = 0

            # 记录本次调用
            self.calls.append(now)

        # 在锁外等待，避免阻塞其他线程
        if sleep_time > 0:
            time.sleep(sleep_time)

    def __enter__(self):
        """支持 with 语句"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句"""
        return False


# 预定义的速率限制器
# DeepSeek: 假设限制为 60 次/分钟
deepseek_limiter = RateLimiter(max_calls=50, time_window=60)

# Gemini: 假设限制为 60 次/分钟
gemini_limiter = RateLimiter(max_calls=50, time_window=60)

# Gemini Flash: 更高的速率限制（便宜模型通常限制更宽松）
gemini_flash_limiter = RateLimiter(max_calls=100, time_window=60)

# Grok: 简单速率限制
grok_limiter = RateLimiter(max_calls=50, time_window=60)
