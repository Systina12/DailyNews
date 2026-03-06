# 吹哨功能链接丢失问题修复

## 问题描述

在实时监控"吹哨"功能（`run_realtime_workflow`）生成的 HTML 邮件中，所有新闻都没有原文链接，导致用户无法点击查看原文。

## 根本原因

RSS 数据中的链接字段结构复杂，有三种可能的存储方式：

1. `canonical` 数组：`[{"href": "https://..."}]`
2. `alternate` 数组：`[{"href": "https://..."}]`
3. `link` 字段：`"https://..."`

在 `run_realtime_workflow` 函数中，代码只是简单地使用 `item.get("link", "")`，这导致：
- 如果链接存储在 `canonical` 或 `alternate` 数组中，`link` 字段为空
- 提取到的链接为空字符串
- 邮件中显示"搜索原文"而不是"查看原文"

## 修复方案

### 1. 新增链接提取辅助函数

在 `workflows/main_workflow.py` 中添加 `_extract_link()` 函数：

```python
def _extract_link(item):
    """
    从新闻 item 中提取链接
    优先级：canonical > alternate > link
    """
    link = ""
    
    # 1. 尝试从 canonical 数组提取
    canonical = item.get("canonical")
    if isinstance(canonical, list) and canonical:
        link = canonical[0].get("href", "") or ""
    
    # 2. 如果没有，尝试从 alternate 数组提取
    if not link:
        alternate = item.get("alternate")
        if isinstance(alternate, list) and alternate:
            link = alternate[0].get("href", "") or ""
    
    # 3. 最后尝试直接的 link 字段
    if not link:
        link = item.get("link", "") or ""
    
    return link
```

### 2. 更新 `run_realtime_workflow` 函数

将原来的：
```python
link = item.get("link", "")
```

改为：
```python
link = _extract_link(item)  # 使用辅助函数提取链接
```

### 3. 增强日志记录

在发现重要新闻时，记录链接信息：
```python
logger.warning(f"⚠ 发现重要新闻 [{cat}] {score}分: {chinese_title[:50]}, 链接: {link[:50] if link else '(空)'}")
```

## 测试验证

### 单元测试

创建了 `test_link_extraction.py` 测试各种情况：

```bash
python test_link_extraction.py
```

测试覆盖：
- ✓ 只有 canonical 数组
- ✓ 只有 alternate 数组
- ✓ 只有 link 字段
- ✓ canonical 优先于 alternate
- ✓ alternate 优先于 link
- ✓ 所有字段都为空
- ✓ canonical 数组为空
- ✓ canonical 数组中 href 为空

### 集成测试

使用真实数据测试：

```bash
# 测试模式（发送到 TEST_EMAIL）
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=70 --test

# 检查生成的邮件 HTML
# 确认链接正确显示为 "查看原文 →" 而不是 "搜索原文 →"
```

## 代码对比

### 修复前

```python
# 直接获取 link 字段（可能为空）
link = item.get("link", "")

important_news.append({
    "category": cat,
    "score": score,
    "title": chinese_title,
    "original_title": title,
    "link": link,  # 可能为空
    "summary": refined_summary,
    "published": item.get("published", ""),
})
```

### 修复后

```python
# 使用辅助函数提取链接（优先级：canonical > alternate > link）
link = _extract_link(item)

important_news.append({
    "category": cat,
    "score": score,
    "title": chinese_title,
    "original_title": title,
    "link": link,  # 正确提取的链接
    "summary": refined_summary,
    "published": item.get("published", ""),
})

# 增强日志
logger.warning(f"⚠ 发现重要新闻 [{cat}] {score}分: {chinese_title[:50]}, 链接: {link[:50] if link else '(空)'}")
```

## 相关代码

其他地方已经正确处理了链接提取：

1. `preprocessing/filters.py` - `_item_text()` 函数
2. `preprocessing/classify.py` - `_is_hard_excluded()` 方法
3. `llms/build_prompt.py` - `_extract_link()` 函数

这些地方都使用了相同的优先级逻辑：`canonical > alternate > link`

## 影响范围

- ✓ 修复了实时监控邮件中的链接问题
- ✓ 不影响其他功能（主工作流、风险评估、摘要生成）
- ✓ 向后兼容（如果 RSS 数据中有 `link` 字段，仍然可以正常工作）

## 部署建议

1. 更新代码后，先运行单元测试：
   ```bash
   python test_link_extraction.py
   ```

2. 使用测试模式验证：
   ```bash
   python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=70 --test
   ```

3. 检查测试邮件中的链接是否正确

4. 确认无误后，部署到生产环境

## 监控建议

在日志中搜索以下关键词来监控链接问题：

```bash
# 查找链接为空的情况
grep "链接: (空)" logs/*.log

# 查找使用 Google 搜索的情况（说明链接为空）
grep "新闻链接为空，使用Google搜索" logs/*.log
```

如果频繁出现链接为空的情况，可能需要：
1. 检查 RSS 源的数据格式
2. 更新链接提取逻辑
3. 联系 RSS 源提供商

## 总结

通过添加 `_extract_link()` 辅助函数，统一了链接提取逻辑，解决了吹哨功能中链接丢失的问题。修复后，用户可以直接点击"查看原文"链接访问新闻原文。

修复文件：
- `workflows/main_workflow.py` - 添加 `_extract_link()` 函数，更新 `run_realtime_workflow()`
- `test_link_extraction.py` - 新增单元测试

测试状态：✓ 通过
部署状态：待部署
