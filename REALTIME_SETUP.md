# 实时监控吹哨功能 - 快速设置指南

## 功能说明

每15分钟自动检测重要新闻（战争、重大政治事件等），发现高分新闻立即发送邮件通知。

## 快速开始

### 1. 手动测试

```bash
# 测试最近1小时的新闻，阈值80分
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=80
```

### 2. 配置定时任务

#### Linux/Mac (Crontab)

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每15分钟运行）
*/15 * * * * cd /path/to/DailyNews && python workflows/main_workflow.py --mode=realtime --hours=0.25 --threshold=80 >> logs/realtime.log 2>&1
```

#### Windows (任务计划程序)

1. 打开"任务计划程序"
2. 创建基本任务 → 名称："DailyNews实时监控"
3. 触发器：重复任务 → 间隔：15分钟
4. 操作：启动程序
   - 程序：`python`
   - 参数：`workflows/main_workflow.py --mode=realtime --hours=0.25 --threshold=80`
   - 起始于：`D:\project\sb\DailyNews`

## 参数说明

```bash
--mode=realtime    # 实时监控模式（必需）
--hours=0.25       # 拉取最近15分钟的新闻
--threshold=80     # 重要性阈值（80分以上才通知）
```

### 阈值建议

- `--threshold=90` - 非常严格，只通知战争、重大政治事件
- `--threshold=80` - 严格，通知重要新闻（推荐）
- `--threshold=70` - 适中，包含较重要的新闻

## 邮件示例

当检测到重要新闻时，你会收到类似这样的邮件：

```
主题：🚨 重要新闻提醒 (14:30) - 2条

┌─────────────────────────────────────────┐
│ [95分] [头条]                            │
│ 巴基斯坦宣布与阿富汗进入公开战争状态     │
│ 查看原文 →                               │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ [85分] [国际]                            │
│ 乌克兰向俄罗斯发射新型导弹               │
│ 查看原文 →                               │
└─────────────────────────────────────────┘
```

## 评分标准

- 战争/军事冲突：80-100分
- 政治重大事件：70-90分
- 经济重大事件：70-90分
- 灾难事故：70-90分
- 一般新闻：40-60分
- 娱乐八卦：10-30分

## 查看日志

```bash
# 实时查看日志
tail -f logs/realtime.log

# 搜索重要新闻
grep "发现重要新闻" logs/realtime.log
```

## 故障排查

### 没有收到邮件？

1. 检查 SMTP 配置（`config/settings.py`）
2. 查看日志是否有错误
3. 检查垃圾邮件箱

### 评分不准确？

1. 调整 `--threshold` 参数
2. 查看日志中的评分结果
3. 修改评分标准（`workflows/news_pipeline.py` 中的 `_score_with_llm()`）

## 更多信息

详细文档：`krio_tests/REALTIME_WHISTLE_BUGFIX.md`
