# utils/email_sender.py
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.logger import get_logger
from config import settings

logger = get_logger("email_sender")


def _parse_recipients(to_value: str) -> list[str]:
    if not to_value:
        return []
    return [x.strip() for x in to_value.split(",") if x.strip()]


def send_html_email(subject: str, html_body: str, test_mode: bool = False):
    """
    发送 HTML 邮件（SMTP）

    依赖环境变量/配置：
      SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
      SMTP_FROM, SMTP_TO, SMTP_USE_TLS, SMTP_USE_SSL
    """
    if not html_body:
        raise ValueError("html_body 不能为空")

    host = getattr(settings, "SMTP_HOST", None)
    port = getattr(settings, "SMTP_PORT", 0)
    username = getattr(settings, "SMTP_USERNAME", "")
    password = getattr(settings, "SMTP_PASSWORD", "")
    mail_from = getattr(settings, "SMTP_FROM", "")

    # 正常收件人列表
    mail_to_normal = _parse_recipients(getattr(settings, "SMTP_TO", ""))

    # 测试模式收件人（从 TEST_EMAIL / TEST-EMAIL 环境变量读取）
    test_email = getattr(settings, "TEST_EMAIL", "") or ""
    mail_to_test = _parse_recipients(test_email)

    # 根据 test_mode 决定实际收件人
    if test_mode:
        if not mail_to_test:
            raise ValueError("测试模式已启用，但 TEST_EMAIL/TEST-EMAIL 未配置")
        mail_to = mail_to_test
        logger.info(f"测试模式启用，邮件仅发送到 TEST_EMAIL，count={len(mail_to)}")
    else:
        mail_to = mail_to_normal

    if not host or not port:
        raise ValueError("SMTP_HOST/SMTP_PORT 未配置")
    if not mail_from:
        raise ValueError("SMTP_FROM 未配置")
    if not mail_to:
        # 根据模式给出更明确的错误提示
        if test_mode:
            raise ValueError("测试模式：TEST_EMAIL/TEST-EMAIL 解析后为空")
        raise ValueError("SMTP_TO 未配置")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = mail_from
    # 不设置 To 字段，使用 BCC 方式发送，收件人之间互相看不到
    
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    logger.info(f"准备发送邮件: host={host}, port={port}, to={len(mail_to)}")

    server = None
    try:
        server = smtplib.SMTP_SSL(host, port, timeout=settings.API_TIMEOUT)
        if username:
            server.login(username, password)
        # 直接传入收件人列表，实现 BCC 效果
        server.sendmail(mail_from, mail_to, msg.as_string())
        logger.info("邮件发送成功")
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        raise
    finally:
        if server:
            try:
                server.quit()
            except Exception as e:
                logger.warning(f"关闭 SMTP 连接时出错: {e}")
