import time
import requests
from config import settings
from utils.logger import get_logger

logger = get_logger("ingestion")


class RSSClient:
    def __init__(self, timeout=None):
        self.newsapi = settings.FRESHRSS_URL
        self.auth_url = settings.FRESHRSS_AUTH_URL
        self.timeout = timeout or settings.API_TIMEOUT
        logger.info(f"RSSClient 初始化，超时设置: {self.timeout}秒")
        self.session = self._get_session()


    def _get_session(self):
        session = requests.Session()
        auth_token = self._get_freshrss_auth()
        session.headers.update({"Authorization": auth_token})
        logger.debug("FreshRSS 会话创建成功")
        return session


    def _get_freshrss_auth(self):
        logger.info("开始 FreshRSS 认证")

        params = {
            "Email": settings.FRESHRSS_EMAIL,
            "Passwd": settings.FRESHRSS_PASSWORD,
        }

        try:
            resp = requests.get(self.auth_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error(f"FreshRSS 认证超时 (>{self.timeout}秒)")
            raise RuntimeError(f"FreshRSS 认证超时 (>{self.timeout}秒)")
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到 FreshRSS 服务器")
            raise RuntimeError("无法连接到 FreshRSS 服务器")
        except requests.exceptions.HTTPError as e:
            logger.error(f"FreshRSS 认证失败: {e}")
            raise RuntimeError(f"FreshRSS 认证失败: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"FreshRSS 认证请求错误: {e}")
            raise RuntimeError(f"FreshRSS 认证请求错误: {e}")

        for line in resp.text.splitlines():
            if line.startswith("Auth="):
                raw = line.split("=", 1)[1]
                logger.info("FreshRSS 认证成功")
                return f"GoogleLogin auth={raw}"

        logger.error("FreshRSS Auth token 未找到")
        raise RuntimeError("FreshRSS Auth token 未找到")


    def get_24h_news(self):
        timestamp = int(time.time() - 86400)
        logger.info(f"开始获取 24 小时新闻，时间戳: {timestamp}")

        params = {
            "output": "json",
            "n": 999999999999999,
            "ot": timestamp,
        }

        try:
            resp = self.session.get(self.newsapi, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            item_count = len(data.get("items", []))
            logger.info(f"成功获取 {item_count} 条新闻")
            return data
        except requests.exceptions.Timeout:
            logger.error(f"获取新闻超时 (>{self.timeout}秒)")
            raise RuntimeError(f"获取新闻超时 (>{self.timeout}秒)")
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到 FreshRSS 服务器")
            raise RuntimeError("无法连接到 FreshRSS 服务器")
        except requests.exceptions.HTTPError as e:
            logger.error(f"获取新闻失败: {e}")
            raise RuntimeError(f"获取新闻失败: {e}")
        except requests.exceptions.JSONDecodeError:
            logger.error("FreshRSS 返回的数据格式错误")
            raise RuntimeError("FreshRSS 返回的数据格式错误")
        except requests.exceptions.RequestException as e:
            logger.error(f"获取新闻请求错误: {e}")
            raise RuntimeError(f"获取新闻请求错误: {e}")



