# 链接问题调试指南

## 问题描述

邮件中"查看原文 →"没有显示实际的URL链接。

## 可能的原因

### 1. 源数据中链接为空

**检查方法**：
```bash
# 运行时查看日志
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=50 --test 2>&1 | grep "链接:"
```

**日志示例**：
```
邮件项目 - 标题: 美国对伊朗高级将领实施斩首行动, 链接: https://example.com/news/1
```

如果看到 `链接: ` 或 `链接: #`，说明源数据中没有链接。

---

### 2. RSS源没有提供链接

**检查方法**：
查看 `ingestion/RSSclient.py` 中的数据提取逻辑。

**解决方案**：
确保RSS解析时正确提取了 `link` 字段：
```python
item_data = {
    "title": entry.get("title", ""),
    "link": entry.get("link", ""),  # 确保这行存在
    "summaryText": entry.get("summary", ""),
    # ...
}
```

---

### 3. 邮件客户端不显示链接

**检查方法**：
1. 用浏览器打开 `test_alert_email.html`
2. 检查HTML源代码中是否有 `href="..."`

**HTML示例**：
```html
<a class="link" href="https://example.com/news/1" target="_blank">查看原文 →</a>
```

如果HTML中有链接但邮件客户端不显示，可能是邮件客户端的安全设置问题。

---

## 调试步骤

### 步骤 1: 检查测试数据

```bash
# 运行独立测试
python standalone_test.py

# 用浏览器打开 test_alert_email.html
# 检查链接是否可点击
```

**预期结果**：
- 链接应该是蓝色
- 鼠标悬停时应该显示URL
- 点击应该打开新标签页

---

### 步骤 2: 检查真实数据

```bash
# 运行真实新闻测试（降低阈值）
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=50 --test

# 查看日志中的链接信息
grep "邮件项目" logs/main_workflow.log
```

**预期日志**：
```
邮件项目 - 标题: 某某新闻, 链接: https://...
```

如果看到 `链接: ` 或 `链接: #`，说明源数据没有链接。

---

### 步骤 3: 检查RSS源数据

在 `workflows/main_workflow.py` 中添加调试日志：

```python
# 在 run_realtime_workflow() 中添加
for item, score in items_with_scores:
    if score >= importance_threshold:
        link = item.get("link", "")
        logger.info(f"高分新闻链接: {link}")  # 添加这行
        # ...
```

重新运行并查看日志。

---

### 步骤 4: 检查邮件HTML

如果收到了邮件但链接不可点击：

1. 在邮件客户端中查看HTML源代码
2. 搜索 `href=`
3. 检查链接是否完整

**可能的问题**：
- 链接被邮件客户端过滤（安全设置）
- 链接格式不正确（缺少 `http://` 或 `https://`）
- 链接被转义错误

---

## 解决方案

### 方案 1: 确保RSS源提供链接

检查 `ingestion/RSSclient.py`：

```python
def fetch_rss(url):
    # ...
    for entry in feed.entries:
        item = {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),  # 确保提取链接
            "summaryText": entry.get("summary", ""),
            # ...
        }
```

---

### 方案 2: 使用备用链接

如果RSS源没有提供链接，可以使用搜索链接：

```python
# 在 run_realtime_workflow() 中
link = item.get("link", "")
if not link or link.strip() == "":
    # 使用Google搜索作为备用
    import urllib.parse
    search_query = urllib.parse.quote(title)
    link = f"https://www.google.com/search?q={search_query}"
```

---

### 方案 3: 显示原文标题

如果链接确实不可用，可以在邮件中显示原文标题：

```python
# 在邮件模板中
if link and link != '#':
    html += f'<div><a class="link" href="{link}" target="_blank">查看原文 →</a></div>'
else:
    html += f'<div class="original-title">原文标题: {news.get("original_title", "")}</div>'
```

---

## 快速测试

### 测试 1: 独立测试（有链接）

```bash
python standalone_test.py
# 用浏览器打开 test_alert_email.html
# 点击"查看原文 →"应该能打开链接
```

### 测试 2: 真实数据测试

```bash
# 降低阈值，增加时间范围
python workflows/main_workflow.py --mode=realtime --hours=24 --threshold=50 --test

# 检查邮箱中的邮件
# 点击"查看原文 →"
```

---

## 常见问题

### Q1: 测试数据有链接，但真实数据没有？

A: RSS源可能没有提供链接字段。检查 `ingestion/RSSclient.py` 的数据提取逻辑。

### Q2: HTML中有链接，但邮件客户端不显示？

A: 可能是邮件客户端的安全设置。尝试：
1. 在邮件客户端中允许显示外部链接
2. 将发件人添加到白名单
3. 使用其他邮件客户端测试

### Q3: 链接显示为 "#"？

A: 源数据中链接为空。使用方案2（备用链接）或方案3（显示原文标题）。

---

## 总结

链接问题的排查顺序：
1. ✅ 测试数据（standalone_test.py）
2. ✅ 真实数据日志
3. ✅ RSS源数据提取
4. ✅ 邮件HTML源代码
5. ✅ 邮件客户端设置

大多数情况下，问题出在RSS源没有提供链接字段。
