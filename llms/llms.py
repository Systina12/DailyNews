import time
import requests
try:
    from google import genai
except ImportError:  # pragma: no cover - optional when running Grok-only
    genai = None

from .tokens import get_deepseek_token, get_gemini_token, get_grok_token
from .exceptions import ContentFilteredException
from utils.deepseek_check import check_deepseek_response
from config import settings
from utils.logger import get_logger
from utils.rate_limiter import deepseek_limiter, gemini_limiter, gemini_flash_limiter, grok_limiter

logger = get_logger("llms")


class LLMClient:
#openai兼容，sb儿子总不至于用A家模型吧

    def __init__(self, timeout=None):
        self.deepseek_api_url = settings.DEEPSEEK_API_URL
        self.grok_api_url = settings.GROK_API_URL
        self.timeout = timeout or settings.API_TIMEOUT

        if settings.GROK_ONLY:
            self.gemini_client = None
        else:
            if genai is None:
                raise ImportError("google-genai is required unless GROK_ONLY=true")
            self.gemini_client = genai.Client(api_key=get_gemini_token())

        logger.info(f"LLMClient 初始化完成，超时设置: {self.timeout}秒")

    def request_deepseek(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        if not prompt:
            raise ValueError("prompt 不能为空")
        
        # 检查 prompt 长度（粗略估计：1 token ≈ 4 字符）
        estimated_tokens = len(prompt) // 4
        if estimated_tokens > 30000:  # DeepSeek 上下文限制
            logger.warning(f"Prompt 过长，估计 {estimated_tokens} tokens，可能超过限制")

        headers = {
            "Authorization": f"Bearer {get_deepseek_token()}",
            "Content-Type": "application/json"
        }

        data = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        max_retries = 3
        retry_delay = 1  # 秒

        for attempt in range(max_retries):
            # 应用速率限制
            deepseek_limiter.acquire()
            try:
                response = requests.post(self.deepseek_api_url, headers=headers, json=data, timeout=self.timeout)

                # 检查 HTTP 400 状态码（内容过滤）
                if response.status_code == 400:
                    try:
                        error_body = response.json()
                        error_msg = error_body.get("error", {}).get("message", "未知错误")
                    except:
                        error_msg = response.text or "无响应体"
                    raise ContentFilteredException(f"HTTP 400 - {error_msg}")

                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # 检查内容安全（不传status_code，因为已经通过了raise_for_status）
                check_result = check_deepseek_response(content)
                if check_result["is_filtered"]:
                    raise ContentFilteredException(check_result["reason"])

                return content

            except ContentFilteredException as e:
                # 内容过滤不重试，记录日志
                logger.warning(f"DeepSeek 触发内容安全机制: {e.reason}")
                raise
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"DeepSeek API 超时，重试 {attempt + 1}/{max_retries - 1}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(f"DeepSeek API 请求超时 (>{self.timeout}秒)")
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    logger.warning(f"DeepSeek API 连接失败，重试 {attempt + 1}/{max_retries - 1}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError("无法连接到 DeepSeek API")
            except requests.exceptions.HTTPError as e:
                # HTTP 错误不重试（除了 5xx）
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    logger.warning(f"DeepSeek API 服务器错误，重试 {attempt + 1}/{max_retries - 1}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(f"DeepSeek API 请求失败: {e}")
            except requests.exceptions.JSONDecodeError:
                raise RuntimeError("DeepSeek API 返回的数据格式错误")
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"DeepSeek API 返回数据结构异常: {e}")
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"DeepSeek API 请求错误，重试 {attempt + 1}/{max_retries - 1}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(f"DeepSeek API 请求错误: {e}")

    def request_grok(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        if not prompt:
            raise ValueError("prompt 不能为空")

        headers = {
            "Authorization": f"Bearer {get_grok_token()}",
            "Content-Type": "application/json"
        }
        data = {
            "model": settings.GROK_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            grok_limiter.acquire()
            try:
                response = requests.post(self.grok_api_url, headers=headers, json=data, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"Grok API 超时，重试 {attempt + 1}/{max_retries - 1}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(f"Grok API 请求超时 (>{self.timeout}秒)")
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    logger.warning(f"Grok API 连接失败，重试 {attempt + 1}/{max_retries - 1}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError("无法连接到 Grok API")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    logger.warning(f"Grok API 服务器错误，重试 {attempt + 1}/{max_retries - 1}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(f"Grok API 请求失败: {e}")
            except requests.exceptions.JSONDecodeError:
                raise RuntimeError("Grok API 返回的数据格式错误")
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Grok API 返回数据结构异常: {e}")
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Grok API 请求错误，重试 {attempt + 1}/{max_retries - 1}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(f"Grok API 请求错误: {e}")

    def request_gemini(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        if not prompt:
            raise ValueError("prompt 不能为空")
        if settings.GROK_ONLY:
            return self.request_grok(prompt, temperature, max_tokens)
        if self.gemini_client is None:
            raise ImportError("google-genai is required for Gemini requests")
        
        # 检查 prompt 长度
        estimated_tokens = len(prompt) // 4
        if estimated_tokens > 1000000:  # Gemini 2.0 上下文限制
            logger.warning(f"Prompt 过长，估计 {estimated_tokens} tokens，可能超过限制")

        max_retries = 3
        retry_delay = 1  # 秒

        for attempt in range(max_retries):
            # 应用速率限制
            gemini_limiter.acquire()
            try:
                # 生成内容
                response = self.gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                )

                return response.text

            except Exception as e:
                error_msg = str(e).lower()

                # 认证错误不重试
                if "api key" in error_msg or "authentication" in error_msg:
                    raise RuntimeError("Gemini API 认证失败，请检查 API Key")

                # 可重试的错误
                if attempt < max_retries - 1:
                    if "timeout" in error_msg or "connection" in error_msg or "503" in error_msg or "500" in error_msg:
                        logger.warning(f"Gemini API 临时错误，重试 {attempt + 1}/{max_retries - 1}: {error_msg}")
                        time.sleep(retry_delay * (attempt + 1))
                        continue

                # 最后一次尝试失败或不可重试的错误
                if "timeout" in error_msg:
                    raise RuntimeError(f"Gemini API 请求超时 (>{self.timeout}秒)")
                elif "connection" in error_msg:
                    raise RuntimeError("无法连接到 Gemini API")
                else:
                    raise RuntimeError(f"Gemini API 请求错误: {str(e)}")

    def request_gemini_flash(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """
        请求 Gemini Flash 便宜模型（用于分类、风险评估等简单任务）
        
        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            str: 模型响应内容
        """
        if not prompt:
            raise ValueError("prompt 不能为空")
        if settings.GROK_ONLY:
            return self.request_grok(prompt, temperature, max_tokens)
        if self.gemini_client is None:
            raise ImportError("google-genai is required for Gemini requests")
        
        # 检查 prompt 长度
        estimated_tokens = len(prompt) // 4
        if estimated_tokens > 1000000:  # Gemini Flash 上下文限制
            logger.warning(f"Prompt 过长，估计 {estimated_tokens} tokens，可能超过限制")

        max_retries = 3
        retry_delay = 1  # 秒

        for attempt in range(max_retries):
            # 应用速率限制
            gemini_flash_limiter.acquire()
            try:
                # 生成内容
                response = self.gemini_client.models.generate_content(
                    model=settings.GEMINI_FLASH_MODEL,
                    contents=prompt,
                )

                return response.text

            except Exception as e:
                error_msg = str(e).lower()

                # 认证错误不重试
                if "api key" in error_msg or "authentication" in error_msg:
                    raise RuntimeError("Gemini Flash API 认证失败，请检查 API Key")

                # 可重试的错误
                if attempt < max_retries - 1:
                    if "timeout" in error_msg or "connection" in error_msg or "503" in error_msg or "500" in error_msg:
                        logger.warning(f"Gemini Flash API 临时错误，重试 {attempt + 1}/{max_retries - 1}: {error_msg}")
                        time.sleep(retry_delay * (attempt + 1))
                        continue

                # 最后一次尝试失败或不可重试的错误
                if "timeout" in error_msg:
                    raise RuntimeError(f"Gemini Flash API 请求超时 (>{self.timeout}秒)")
                elif "connection" in error_msg:
                    raise RuntimeError("无法连接到 Gemini Flash API")
                else:
                    raise RuntimeError(f"Gemini Flash API 请求错误: {str(e)}")

    def request_with_fallback(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, primary: str = "deepseek"):
        """
        请求 LLM，如果主模型触发风控则自动 fallback 到备用模型

        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            primary: 主模型，"deepseek"、"gemini" 或 "grok"

        Returns:
            dict: 响应结果
                {
                    "content": str,           # 响应内容
                    "model_used": str,        # 实际使用的模型
                    "is_fallback": bool,      # 是否使用了 fallback
                    "filter_reason": str      # 如果触发风控，原因是什么
                }

        Raises:
            ValueError: 参数错误
            RuntimeError: 两个模型都失败时抛出
        """
        if primary not in ["deepseek", "gemini", "grok"]:
            raise ValueError(f"primary 必须是 'deepseek'、'gemini' 或 'grok'，当前值: {primary}")

        if settings.GROK_ONLY:
            content = self.request_grok(prompt, temperature, max_tokens)
            return {
                "content": content,
                "model_used": "grok",
                "is_fallback": False,
                "filter_reason": None
            }

        # 确定主模型和备用模型
        if primary == "deepseek":
            primary_func = self.request_deepseek
            fallback_func = self.request_gemini
            fallback_name = "gemini"
        elif primary == "gemini":
            primary_func = self.request_gemini
            fallback_func = self.request_deepseek
            fallback_name = "deepseek"
        else:
            primary_func = self.request_grok
            fallback_func = None
            fallback_name = None

        # 尝试主模型
        try:
            content = primary_func(prompt, temperature, max_tokens)
            return {
                "content": content,
                "model_used": primary,
                "is_fallback": False,
                "filter_reason": None
            }
        except ContentFilteredException as e:
            if fallback_func is None:
                raise

            # 主模型触发风控，fallback 到备用模型
            logger.warning(f"⚠ {primary} 触发内容安全机制: {e.reason}")
            logger.info(f"→ 自动切换到 {fallback_name}")

            try:
                content = fallback_func(prompt, temperature, max_tokens)
                return {
                    "content": content,
                    "model_used": fallback_name,
                    "is_fallback": True,
                    "filter_reason": e.reason
                }
            except Exception as fallback_error:
                raise RuntimeError(
                    f"{primary} 触发风控，{fallback_name} 也失败了: {fallback_error}"
                )
