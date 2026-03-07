#!/usr/bin/env python3
"""诊断环境变量和配置加载"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("环境变量诊断")
print("=" * 60)

# 1. 检查环境变量
print("\n1. 原始环境变量:")
print(f"FRESHRSS_URL = {os.getenv('FRESHRSS_URL', '未设置')}")
print(f"FRESHRSS_AUTH_URL = {os.getenv('FRESHRSS_AUTH_URL', '未设置')}")
print(f"FRESHRSS_EMAIL = {os.getenv('FRESHRSS_EMAIL', '未设置')}")
print(f"FRESHRSS_PASSWORD = {'***' if os.getenv('FRESHRSS_PASSWORD') else '未设置'}")

# 2. 检查配置文件加载
print("\n2. 配置文件加载:")
try:
    from config import settings
    print(f"settings.FRESHRSS_URL = {settings.FRESHRSS_URL}")
    print(f"settings.FRESHRSS_AUTH_URL = {settings.FRESHRSS_AUTH_URL}")
    print(f"settings.FRESHRSS_EMAIL = {settings.FRESHRSS_EMAIL}")
    print(f"settings.FRESHRSS_PASSWORD = {'***' if settings.FRESHRSS_PASSWORD else '未设置'}")
except Exception as e:
    print(f"加载配置失败: {e}")

# 3. 测试连接
print("\n3. 测试连接:")
try:
    from ingestion.RSSclient import RSSClient
    print("创建 RSSClient...")
    client = RSSClient()
    print(f"✓ RSSClient 创建成功")
    print(f"  使用的 URL: {client.newsapi}")
    print(f"  使用的 Auth URL: {client.auth_url}")
except Exception as e:
    print(f"✗ 创建 RSSClient 失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 检查 .env 文件
print("\n4. 检查 .env 文件:")
env_files = [
    project_root / ".env",
    project_root / "DailyNews" / ".env",
    Path.home() / ".env",
]
for env_file in env_files:
    if env_file.exists():
        print(f"✓ 找到: {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("FRESHRSS"):
                    # 隐藏密码
                    if "PASSWORD" in line:
                        print(f"  {line.split('=')[0]}=***")
                    else:
                        print(f"  {line}")
    else:
        print(f"✗ 未找到: {env_file}")

print("\n" + "=" * 60)
