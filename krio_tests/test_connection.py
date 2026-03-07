#!/usr/bin/env python3
"""测试 FreshRSS 连接"""

import socket
import urllib.request
import urllib.error

print("=" * 60)
print("FreshRSS 连接测试")
print("=" * 60)

# 测试不同的连接方式
test_urls = [
    ("容器名", "http://1Panel-freshrss-WMI"),
    ("Docker IP", "http://172.18.0.6"),
    ("localhost", "http://localhost:51264"),
    ("127.0.0.1", "http://127.0.0.1:51264"),
]

for name, base_url in test_urls:
    print(f"\n测试 {name}: {base_url}")
    
    # 1. DNS 解析测试
    try:
        host = base_url.split("//")[1].split(":")[0].split("/")[0]
        if host not in ["localhost", "127.0.0.1"]:
            ip = socket.gethostbyname(host)
            print(f"  ✓ DNS 解析成功: {host} -> {ip}")
        else:
            print(f"  ✓ 本地地址: {host}")
    except socket.gaierror:
        print(f"  ✗ DNS 解析失败: 无法解析 {host}")
        continue
    except Exception as e:
        print(f"  ✗ DNS 解析错误: {e}")
        continue
    
    # 2. HTTP 连接测试
    try:
        url = f"{base_url}/api/greader.php/accounts/ClientLogin"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"  ✓ HTTP 连接成功: {response.status}")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"  ✓ HTTP 连接成功 (403 需要认证)")
        else:
            print(f"  ⚠ HTTP 错误: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"  ✗ 连接失败: {e.reason}")
    except Exception as e:
        print(f"  ✗ 连接错误: {e}")

print("\n" + "=" * 60)
print("建议:")
print("  - 如果在宿主机运行: 使用 localhost:51264")
print("  - 如果在 Docker 容器内运行: 使用容器名或 Docker IP")
print("=" * 60)
