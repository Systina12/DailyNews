"""
诊断链接问题

检查：
1. RSS数据中是否有link字段
2. 链接是否被正确传递
3. HTML是否正确生成
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.RSSclient import RSSClient
from utils.logger import get_logger

logger = get_logger("diagnose")

print("=" * 60)
print("链接问题诊断")
print("=" * 60)

# 1. 获取RSS数据
print("\n[步骤1] 获取RSS数据...")
try:
    rss = RSSClient()
    data = rss.get_news(hours=1, n=10)  # 只取10条
    items = data.get("items", [])
    print(f"✓ 成功获取 {len(items)} 条新闻")
except Exception as e:
    print(f"✗ 获取RSS数据失败: {e}")
    sys.exit(1)

# 2. 检查link字段
print("\n[步骤2] 检查link字段...")
has_link_count = 0
no_link_count = 0

for i, item in enumerate(items[:5], 1):  # 只检查前5条
    title = item.get("title", "")[:50]
    link = item.get("canonical", [{}])[0].get("href", "") if item.get("canonical") else ""
    
    # FreshRSS可能使用不同的字段名
    if not link:
        link = item.get("alternate", [{}])[0].get("href", "") if item.get("alternate") else ""
    
    print(f"\n新闻 {i}:")
    print(f"  标题: {title}")
    print(f"  链接: {link if link else '(无)'}")
    
    if link:
        has_link_count += 1
    else:
        no_link_count += 1
        # 显示完整的item结构
        print(f"  完整数据: {list(item.keys())}")

print(f"\n统计:")
print(f"  有链接: {has_link_count} 条")
print(f"  无链接: {no_link_count} 条")

# 3. 检查数据结构
print("\n[步骤3] 检查数据结构...")
if items:
    sample = items[0]
    print(f"字段列表: {list(sample.keys())}")
    
    # 查找可能的链接字段
    link_fields = []
    for key in sample.keys():
        if 'link' in key.lower() or 'url' in key.lower() or 'href' in key.lower():
            link_fields.append(key)
    
    if link_fields:
        print(f"可能的链接字段: {link_fields}")
        for field in link_fields:
            print(f"  {field}: {sample.get(field)}")
    else:
        print("未找到明显的链接字段")
        
    # 检查canonical和alternate
    if 'canonical' in sample:
        print(f"canonical: {sample.get('canonical')}")
    if 'alternate' in sample:
        print(f"alternate: {sample.get('alternate')}")

# 4. 建议
print("\n" + "=" * 60)
print("诊断结果")
print("=" * 60)

if no_link_count == 0:
    print("\n✓ 所有新闻都有链接")
    print("\n可能的问题：")
    print("1. 链接字段名不对（不是'link'）")
    print("2. 数据处理过程中丢失了链接")
    print("3. 邮件客户端过滤了链接")
elif has_link_count == 0:
    print("\n✗ 所有新闻都没有链接")
    print("\n解决方案：")
    print("1. 检查RSS源是否提供链接")
    print("2. 使用Google搜索作为备用（已实现）")
else:
    print(f"\n⚠ 部分新闻有链接（{has_link_count}/{has_link_count + no_link_count}）")
    print("\n建议：")
    print("1. 检查为什么部分新闻没有链接")
    print("2. 使用Google搜索作为备用（已实现）")

print("\n下一步：")
print("1. 如果RSS数据有链接，检查数据处理流程")
print("2. 如果RSS数据没有链接，使用备用方案（Google搜索）")
print("3. 运行真实测试：python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=50 --test")
print("4. 查看日志：grep '构建邮件项' logs/main_workflow.log")
