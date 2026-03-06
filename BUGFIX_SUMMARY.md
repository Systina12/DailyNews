# Main Workflow Bug 修复总结

## 修复的问题

### 1. 导入私有函数 ❌
**问题**: 在 `run_realtime_workflow()` 中导入私有函数 `_score_with_llm`
```python
# 错误
from workflows.news_pipeline import _score_with_llm
```

**修复**: 在 `news_pipeline.py` 中创建公开接口
```python
# news_pipeline.py 新增
def score_news_importance(items, llm_client):
    """公开接口：使用 LLM 批量评分新闻重要性"""
    return _score_with_llm(items, llm_client)

# main_workflow.py 修改
from workflows.news_pipeline import score_news_importance
items_with_scores = score_news_importance(items, llm_client)
```

### 2. HTML 模板花括号问题 ❌
**问题**: CSS 中的 `{}` 在 f-string 中需要转义为 `{{}}`，但这样会导致可读性差
```python
# 错误 - 花括号冲突
html = f"""
<style>
    body {{ font-family: Arial; }}  # 需要双花括号
</style>
"""
```

**修复**: 使用字符串拼接代替 f-string
```python
# 正确 - 使用列表拼接
html_parts = []
html_parts.append("""
<style>
    body { font-family: Arial; }  # 单花括号即可
</style>
""")
html_parts.append(f"<p>{variable}</p>")  # 需要变量时才用 f-string
return ''.join(html_parts)
```

### 3. 缺少 HTML 转义 ❌
**问题**: 新闻标题和摘要可能包含 HTML 特殊字符，导致邮件显示错误
```python
# 错误 - 未转义
<div class="title">{news['title']}</div>
```

**修复**: 转义 HTML 特殊字符
```python
# 正确 - 转义特殊字符
title = news['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
<div class="title">{title}</div>
```

### 4. 缺少 test_mode 参数 ❌
**问题**: `run_realtime_workflow()` 不支持测试模式
```python
# 错误 - 硬编码 test_mode=False
send_html_email(subject=subject, html_body=html_body, test_mode=False)
```

**修复**: 添加 test 参数并传递
```python
# 函数签名
def run_realtime_workflow(categories=None, hours: float = 1, 
                         importance_threshold: int = 80, test: bool = False):

# 使用参数
send_html_email(subject=subject, html_body=html_body, test_mode=test)

# CLI 调用
run_realtime_workflow(categories=cats, hours=args.hours, 
                     importance_threshold=args.threshold, test=args.test)
```

### 5. 异常处理不完整 ❌
**问题**: 邮件发送失败时没有详细的错误信息
```python
# 错误 - 只记录简单错误
except Exception as e:
    logger.error(f"发送通知邮件失败: {e}")
```

**修复**: 添加完整的堆栈跟踪
```python
# 正确 - 记录完整堆栈
except Exception as e:
    logger.error(f"发送通知邮件失败: {e}")
    import traceback
    logger.error(traceback.format_exc())
```

### 6. 日志信息不完整 ❌
**问题**: 空分类时没有日志记录
```python
# 错误 - 静默跳过
if not items:
    continue
```

**修复**: 添加日志记录
```python
# 正确 - 记录日志
if not items:
    logger.info(f"[{cat}] 无新闻，跳过评分")
    continue
```

## 修复后的完整流程

### 1. 公开接口（news_pipeline.py）
```python
def score_news_importance(items, llm_client):
    """公开接口：使用 LLM 批量评分新闻重要性"""
    return _score_with_llm(items, llm_client)
```

### 2. 实时监控（main_workflow.py）
```python
def run_realtime_workflow(categories=None, hours: float = 1, 
                         importance_threshold: int = 80, test: bool = False):
    # 1. 拉取和分类
    blocks = run_news_pipeline_all(categories=categories, hours=hours)
    
    # 2. LLM 评分
    from llms.llms import LLMClient
    from workflows.news_pipeline import score_news_importance
    
    llm_client = LLMClient()
    important_news = []
    
    for block in blocks:
        items = block.get("items") or []
        if not items:
            logger.info(f"[{cat}] 无新闻，跳过评分")
            continue
        
        items_with_scores = score_news_importance(items, llm_client)
        
        # 筛选高分新闻
        for item, score in items_with_scores:
            if score >= importance_threshold:
                important_news.append({...})
    
    # 3. 发送通知
    if important_news:
        html_body = _build_alert_email(important_news, importance_threshold)
        send_html_email(subject=subject, html_body=html_body, test_mode=test)
```

### 3. 邮件模板（main_workflow.py）
```python
def _build_alert_email(important_news, threshold):
    html_parts = []
    
    # CSS 使用单花括号
    html_parts.append("""
    <style>
        body { font-family: Arial; }
    </style>
    """)
    
    # 动态内容使用字符串拼接
    html_parts.append("<p>检测到 " + str(len(important_news)) + " 条新闻</p>")
    
    # 转义 HTML 特殊字符
    for news in sorted_news:
        title = news['title'].replace('&', '&amp;').replace('<', '&lt;')
        html_parts.append(f"<div>{title}</div>")
    
    return ''.join(html_parts)
```

## 测试验证

### 1. 语法检查
```bash
python -m py_compile workflows/main_workflow.py
python -m py_compile workflows/news_pipeline.py
```

### 2. 功能测试
```bash
# 测试模式（发送到 TEST_EMAIL）
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=80 --test

# 正式模式
python workflows/main_workflow.py --mode=realtime --hours=0.25 --threshold=80
```

## 影响范围

### 修改的文件
1. `workflows/news_pipeline.py` - 新增公开接口 `score_news_importance()`
2. `workflows/main_workflow.py` - 修复所有问题

### 向后兼容性
- ✅ 所有修改都是向后兼容的
- ✅ 不影响现有的 `run_main_workflow()` 和 `run_hourly_workflow()`
- ✅ 只增强了 `run_realtime_workflow()` 的功能

## 使用示例

### 手动测试
```bash
# 测试模式（邮件发送到 TEST_EMAIL）
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=80 --test

# 正式模式
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=80
```

### Crontab 配置
```bash
# 每15分钟运行（测试模式）
*/15 * * * * cd /path/to/DailyNews && python workflows/main_workflow.py --mode=realtime --hours=0.25 --threshold=80 --test >> logs/realtime.log 2>&1

# 每15分钟运行（正式模式）
*/15 * * * * cd /path/to/DailyNews && python workflows/main_workflow.py --mode=realtime --hours=0.25 --threshold=80 >> logs/realtime.log 2>&1
```

## 总结

修复了6个明显的bug：
1. ✅ 导入私有函数 → 创建公开接口
2. ✅ HTML 花括号冲突 → 使用字符串拼接
3. ✅ 缺少 HTML 转义 → 转义特殊字符
4. ✅ 缺少 test_mode → 添加参数支持
5. ✅ 异常处理不完整 → 添加堆栈跟踪
6. ✅ 日志信息不完整 → 添加详细日志

现在代码更加健壮、可维护、易于调试！
