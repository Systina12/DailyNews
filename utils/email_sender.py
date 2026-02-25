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


def send_html_email(subject: str, html_body: str):
    """
    发送 HTML 邮件（SMTP）

    依赖环境变量/配置：
      SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
      SMTP_FROM, SMTP_TO, SMTP_USE_TLS, SMTP_USE_SSL
    """
    if not html_body:
        raise ValueError("html_body 不能为空")

    host = getattr(settings, "SMTP_HOST", None)
    port = int(getattr(settings, "SMTP_PORT", 0) or 0)
    username = getattr(settings, "SMTP_USERNAME", "")
    password = getattr(settings, "SMTP_PASSWORD", "")
    mail_from = getattr(settings, "SMTP_FROM", "")
    mail_to = _parse_recipients(getattr(settings, "SMTP_TO", ""))


    if not host or not port:
        raise ValueError("SMTP_HOST/SMTP_PORT 未配置")
    if not mail_from or not mail_to:
        raise ValueError("SMTP_FROM/SMTP_TO 未配置")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = mail_from
    msg["To"] = ", ".join(mail_to)

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    logger.info(f"准备发送邮件: host={host}, port={port}, to={len(mail_to)}")

    server = None
    try:
        server = smtplib.SMTP_SSL(host, port, timeout=settings.API_TIMEOUT)
        if username:
            server.login(username, password)
        server.send_message(msg)
        logger.info("邮件发送成功")
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass
