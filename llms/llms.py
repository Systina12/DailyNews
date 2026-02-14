import requests
from .tokens import get_deepseek_token, get_gemini_token
from .exceptions import ContentFilteredException
from utils.deepseek_check import check_deepseek_response
from config import settings
from utils.logger import get_logger

logger = get_logger("llms")


class LLMClient:
#openai兼容，sb儿子总不至于用A家模型吧

    def __init__(self, timeout=None):
        self.deepseek_api_url = settings.DEEPSEEK_API_URL
        self.gemini_api_url = settings.GEMINI_API_URL
        self.timeout = timeout or settings.API_TIMEOUT
        logger.info(f"LLMClient 初始化完成，超时设置: {self.timeout}秒")

    def request_deepseek(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        if not prompt:
            raise ValueError("prompt 不能为空")

        headers = {
            "Authorization": f"Bearer {get_deepseek_token()}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",#显式指定，代码就这样了不做切换了,不认为儿子会用reasoner模型
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        try:
            response = requests.post(self.deepseek_api_url, headers=headers, json=data, timeout=self.timeout)

            # 检查 HTTP 400 状态码
            if response.status_code == 400:
                raise ContentFilteredException("HTTP 400 状态码")

            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 检查内容安全
            check_result = check_deepseek_response(content, response.status_code)
            if check_result["is_filtered"]:
                raise ContentFilteredException(check_result["reason"])

            return content

        except ContentFilteredException:
            raise
        except requests.exceptions.Timeout:
            raise RuntimeError(f"DeepSeek API 请求超时 (>{self.timeout}秒)")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("无法连接到 DeepSeek API")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                raise ContentFilteredException(f"HTTP 400: {str(e)}")
            raise RuntimeError(f"DeepSeek API 请求失败: {e}")
        except requests.exceptions.JSONDecodeError:
            raise RuntimeError("DeepSeek API 返回的数据格式错误")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"DeepSeek API 返回数据结构异常: {e}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"DeepSeek API 请求错误: {e}")

    def request_gemini(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        if not prompt:
            raise ValueError("prompt 不能为空")

        headers = {
            "Authorization": f"Bearer {get_gemini_token()}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "gemini-2.0-flash-exp",#理论上来说模型名写在init好
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,#翻译可以适当再低一点
            "max_tokens": max_tokens,
            "stream": False
        }

        try:
            response = requests.post(self.gemini_api_url, headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Gemini API 请求超时 (>{self.timeout}秒)")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("无法连接到 Gemini API")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Gemini API 请求失败: {e}")
        except requests.exceptions.JSONDecodeError:
            raise RuntimeError("Gemini API 返回的数据格式错误")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Gemini API 返回数据结构异常: {e}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Gemini API 请求错误: {e}")

    def request_with_fallback(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, primary: str = "deepseek"):
        """
        请求 LLM，如果主模型触发风控则自动 fallback 到备用模型

        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            primary: 主模型，"deepseek" 或 "gemini"

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
        if primary not in ["deepseek", "gemini"]:
            raise ValueError(f"primary 必须是 'deepseek' 或 'gemini'，当前值: {primary}")

        # 确定主模型和备用模型
        if primary == "deepseek":
            primary_func = self.request_deepseek
            fallback_func = self.request_gemini
            fallback_name = "gemini"
        else:
            primary_func = self.request_gemini
            fallback_func = self.request_deepseek
            fallback_name = "deepseek"

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
            # 主模型触发风控，fallback 到备用模型
            print(f"⚠ {primary} 触发内容安全机制: {e.reason}")
            print(f"→ 自动切换到 {fallback_name}")

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