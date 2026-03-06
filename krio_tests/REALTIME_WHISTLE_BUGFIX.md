# 实时监控吹哨功能 Bug 修复

## 问题描述

`run_realtime_workflow()` 函数原本设计用于"每15分钟检测重要新闻并发送通知"，但实际实现中：

1. **缺少评分逻辑** - 只拉取和分类新闻，没有评估重要性
2. **缺少通知功能** - 没有检测高分新闻并发送邮件
3. **缺少阈值配置** - 无法自定义重要性阈值
4. **功能不完整** - 注释说"后续接入吹哨逻辑"，但一直未实现

## 修复内容

### 1. 新增 LLM 评分功能

```python
# 修复前：只拉取和分类
blocks = run_news_pipeline_all(categories=categories, hours=hours)
# 没有后续处理

# 修复后：拉取、分类、评分
blocks = run_news_pipeline_all(categories=categories, hours=hours)

from llms.llms import LLMClient
from workflows.news_pipeline import _score_with_llm

llm_client = LLMClient()
for block in blocks:
    items = block.get("items") or []
    items_with_scores = _score_with_llm(items, llm_client)
    # 筛选高分新闻...
```

### 2. 新增重要新闻检测

```python
# 筛选高分新闻（≥threshold）
important_news = []
for item, score in items_with_scores:
    if score >= importance_threshold:
        important_news.append({
            "category": cat,
            "score": score,
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "summary": item.get("summaryText", "")[:200],
            "published": item.get("published", ""),
        })
        logger.warning(f"⚠ 发现重要新闻 [{cat}] {score}分: {item.get('title', '')[:50]}")
```

### 3. 新增邮件通知功能

```python
if important_news:
    # 构建邮件内容
    html_body = _build_alert_email(important_news, importance_threshold)
    
    # 发送邮件
    hour_cn = datetime.now().strftime("%H:%M")
    subject = f"🚨 重要新闻提醒 ({hour_cn}) - {len(important_news)}条"
    
    send_html_email(subject=subject, html_body=html_body, test_mode=False)
    logger.info(f"✓ 重要新闻通知已发送")
```

### 4. 新增邮件模板函数

```python
def _build_alert_email(important_news, threshold):
    """构建重要新闻提醒邮件的 HTML"""
    # 生成美观的 HTML 邮件
    # - 红色警告样式
    # - 显示评分和分类
    # - 按评分排序
    # - 包含标题、摘要、链接
```

### 5. 新增 CLI 参数

```python
p.add_argument(
    "--threshold",
    type=int,
    default=80,
    help="实时监控模式的重要性阈值（默认 80 分），只在 --mode=realtime 时生效",
)
```

## 使用方法

### 手动测试

```bash
# 拉取最近1小时的新闻，检测80分以上的重要新闻
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=80

# 拉取最近15分钟的新闻，检测90分以上的重要新闻（更严格）
python workflows/main_workflow.py --mode=realtime --hours=0.25 --threshold=90
```

### Crontab 配置（每15分钟）

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每15分钟运行一次）
*/15 * * * * cd /path/to/DailyNews && python workflows/main_workflow.py --mode=realtime --hours=0.25 --threshold=80 >> logs/realtime.log 2>&1
```

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每15分钟
4. 操作：启动程序
   - 程序：`python`
   - 参数：`workflows/main_workflow.py --mode=realtime --hours=0.25 --threshold=80`
   - 起始于：`D:\path\to\DailyNews`

## 邮件示例

```
主题：🚨 重要新闻提醒 (14:30) - 2条

内容：
┌─────────────────────────────────────────┐
│ 🚨 重要新闻提醒                          │
│ 检测到 2 条重要性评分 ≥80 的新闻        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ [95分] [头条]                            │
│ 巴基斯坦宣布与阿富汗进入公开战争状态     │
│ 巴基斯坦政府宣布与阿富汗塔利班政权...    │
│ 查看原文 →                               │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ [85分] [国际]                            │
│ 乌克兰向俄罗斯发射新型导弹               │
│ 乌克兰军方使用新型远程导弹对俄罗斯...    │
│ 查看原文 →                               │
└─────────────────────────────────────────┘
```

## 评分标准

LLM 评分标准（0-100分）：

- **战争/军事冲突**：80-100分
- **政治重大事件**（选举、辞职、政变）：70-90分
- **经济重大事件**（崩溃、危机）：70-90分
- **灾难事故**：70-90分
- **一般新闻**：40-60分
- **娱乐八卦**：10-30分
- **日常琐事**：0-20分

## 参数调优

### 阈值建议

```bash
--threshold=90  # 非常严格，只通知战争、重大政治事件
--threshold=80  # 严格，通知重要新闻（推荐）
--threshold=70  # 适中，包含较重要的新闻
--threshold=60  # 宽松，包含一般重要新闻
```

### 时间窗口建议

```bash
--hours=0.25   # 15分钟（推荐用于 crontab 每15分钟）
--hours=0.5    # 30分钟
--hours=1      # 1小时（推荐用于手动测试）
--hours=2      # 2小时
```

## 日志示例

```
2026-03-06 14:30:15 [INFO] 开始实时监控工作流（realtime），多分类: ['头条', '政治', '财经', '科技', '国际']，hours=0.25，阈值=80
2026-03-06 14:30:20 [INFO] [头条] 评分 15 条新闻...
2026-03-06 14:30:25 [INFO] ✓ LLM 评分完成，解析 15 条结果
2026-03-06 14:30:25 [WARNING] ⚠ 发现重要新闻 [头条] 95分: 巴基斯坦宣布与阿富汗进入公开战争状态
2026-03-06 14:30:30 [INFO] [国际] 评分 8 条新闻...
2026-03-06 14:30:35 [WARNING] ⚠ 发现重要新闻 [国际] 85分: 乌克兰向俄罗斯发射新型导弹
2026-03-06 14:30:40 [INFO] 发现 2 条重要新闻，准备发送通知...
2026-03-06 14:30:45 [INFO] ✓ 重要新闻通知已发送
2026-03-06 14:30:45 [INFO] ============================================================
2026-03-06 14:30:45 [INFO] realtime 监控结果：
2026-03-06 14:30:45 [INFO]   [头条]: 15 条
2026-03-06 14:30:45 [INFO]   [政治]: 5 条
2026-03-06 14:30:45 [INFO]   [财经]: 3 条
2026-03-06 14:30:45 [INFO]   [科技]: 2 条
2026-03-06 14:30:45 [INFO]   [国际]: 8 条
2026-03-06 14:30:45 [INFO]   重要新闻: 2 条
2026-03-06 14:30:45 [INFO] ============================================================
```

## 测试验证

运行测试脚本：

```bash
python test_realtime_whistle.py
```

测试内容：
- ✓ 邮件HTML构建逻辑
- ✓ 阈值过滤
- ✓ 按评分排序

## 性能考虑

### API 调用成本

- 使用 `gemini-flash` 模型评分（便宜）
- 批量评分（20条/批）
- 每15分钟运行一次，每次约评分30-50条新闻
- 预计成本：每月 < $1

### 优化建议

1. **调整批量大小**：在 `_score_with_llm()` 中修改 `batch_size`
2. **缓存评分结果**：避免重复评分相同新闻
3. **调整时间窗口**：减少 `--hours` 参数以减少新闻数量

## 故障排查

### 问题1：没有收到邮件

检查：
1. SMTP 配置是否正确（`config/settings.py`）
2. 是否有高分新闻（查看日志）
3. 邮件是否被过滤到垃圾箱

### 问题2：评分不准确

调整：
1. 修改 `_score_with_llm()` 中的评分标准
2. 调整 `--threshold` 参数
3. 查看日志中的评分结果

### 问题3：运行太慢

优化：
1. 减少 `--hours` 参数（减少新闻数量）
2. 增加批量大小（`batch_size`）
3. 只监控部分分类（`--categories="头条,国际"`）

## 总结

修复后的功能：
- ✓ 完整的实时监控流程
- ✓ LLM 智能评分
- ✓ 高分新闻检测
- ✓ 自动邮件通知
- ✓ 可配置阈值
- ✓ 美观的邮件模板
- ✓ 详细的日志记录

现在可以真正实现"每15分钟检测重要新闻并发送通知"的功能了！
