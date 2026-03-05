# 快速开始指南

## 运行系统

### 1. 每小时报（1小时新闻）
```bash
python workflows/main_workflow.py --hours 1
```

预期效果：
- 头条：10-20条（低水位10，最大20）
- 其他分类：正常数量

---

### 2. 每8小时报
```bash
python workflows/main_workflow.py --hours 8
```

预期效果：
- 头条：28-56条（√8 = 2.8倍基准）
- 比线性增长降低65%（80条 → 28条）

---

### 3. 每日报（24小时新闻）
```bash
python workflows/main_workflow.py --hours 24
```

预期效果：
- 头条：49-98条（√24 = 4.9倍基准）
- 比线性增长降低80%（240条 → 49条）

---

## 测试系统

### 测试混合分类器
```bash
python test_classify_llm.py
```

测试内容：
- 规则分类置信度
- LLM 批量分类
- 混合策略效果

---

### 测试黑名单学习
```bash
python test_headline_learning.py
```

测试内容：
- 关键词提取
- 黑名单学习
- 频率衰减
- 低频清理
- 数量限制

---

## 查看结果

### 输出文件
```bash
ls -lh data/summary_*.html
```

文件命名格式：
```
summary_头条_2026-02-27_143025.html
summary_政治_2026-02-27_143025.html
summary_财经_2026-02-27_143025.html
...
```

---

### 黑名单文件
```bash
cat data/headline_blacklist.json
```

格式：
```json
{
  "动物园": 0.85,
  "宠物": 0.72,
  "美容": 0.65,
  ...
}
```

---

## 调整参数

### 环境变量方式
```bash
# 调整保留比例（默认60%）
export HEADLINE_KEEP_RATIO=0.7

# 调整衰减因子（默认0.95）
export HEADLINE_BLACKLIST_DECAY=0.90

# 运行
python workflows/main_workflow.py --hours 8
```

---

### 修改配置文件
编辑 `config/settings.py`：

```python
# 头条保留比例（60% → 70%）
HEADLINE_KEEP_RATIO = float(os.getenv("HEADLINE_KEEP_RATIO", "0.7"))

# 黑名单衰减因子（0.95 → 0.90）
HEADLINE_BLACKLIST_DECAY = float(os.getenv("HEADLINE_BLACKLIST_DECAY", "0.90"))
```

---

## 监控系统

### 查看日志
```bash
# 实时查看
tail -f logs/main_workflow.log

# 搜索关键信息
grep "头条" logs/main_workflow.log
grep "黑名单" logs/main_workflow.log
grep "LLM" logs/main_workflow.log
```

---

### 关键日志信息

#### 动态水位
```
头条动态水位：8小时 = √8.0 = 2.83倍基准 → 低水位 28, 最大保留 56
```

#### 头条保留
```
头条数量 45 > 低水位 28，按比例保留 27 条（60%），下放 18 条
```

#### 规则分类
```
规则分类: 120 条确定，35 条需要 LLM 判断
```

#### LLM 分类
```
LLM 批量分类 35 条新闻...
✓ LLM 分类完成，解析 35 条结果
LLM 分类后: 从 35 条中新增 12 条，总计 132 条
```

#### 黑名单学习
```
从 8 条低分新闻中学习黑名单...
新增黑名单: 动物园 (频率: 0.75)
清理低频关键词: 3 个 - ['旧词1', '旧词2', '旧词3']...
黑名单更新: 新增 2, 更新 5, 删除 3, 总计 45 个关键词
```

---

## 常见问题

### Q1: 头条数量还是太多？
调整保留比例：
```bash
export HEADLINE_KEEP_RATIO=0.5  # 降低到50%
```

---

### Q2: 黑名单增长太快？
调整衰减因子（更激进）：
```bash
export HEADLINE_BLACKLIST_DECAY=0.90  # 从0.95降到0.90
```

或调整最低频率（更严格）：
```bash
export HEADLINE_BLACKLIST_MIN_FREQ=0.4  # 从0.3提高到0.4
```

---

### Q3: LLM 评分不准确？
检查 prompt 和评分标准：
- 文件：`workflows/news_pipeline.py`
- 函数：`_score_with_llm()`
- 调整评分标准和示例

---

### Q4: 想禁用某个功能？
```bash
# 禁用 LLM 评分（使用关键词评分）
export HEADLINE_ENABLE_LLM_SCORING=false

# 禁用自动学习
export HEADLINE_ENABLE_LEARNING=false
```

---

## 性能优化

### 批量大小
默认：20条/批

调整方法：
```python
# workflows/news_pipeline.py
def _score_with_llm(items, llm_client):
    batch_size = 30  # 改为30条/批
```

---

### API 超时
```bash
export API_TIMEOUT=120  # 从60秒增加到120秒
```

---

## 文档索引

- `IMPLEMENTATION_SUMMARY.md` - 实现总结（推荐先看）
- `HEADLINE_SYSTEM_OVERVIEW.md` - 系统总览
- `CLASSIFY_LLM_CONFIG.md` - 混合分类器
- `HEADLINE_LIMIT_CONFIG.md` - 动态水位
- `HEADLINE_SQRT_SCALING.md` - 平方根缩放
- `HEADLINE_IMPORTANCE_SCORING.md` - 智能排序
- `HEADLINE_LLM_LEARNING.md` - 自动学习黑名单
- `QUICK_START.md` - 本文档（快速开始）

---

## 下一步

1. **运行测试**：
   ```bash
   python test_headline_learning.py
   ```

2. **实际运行**：
   ```bash
   python workflows/main_workflow.py --hours 1
   ```

3. **查看结果**：
   ```bash
   ls -lh data/
   cat data/headline_blacklist.json
   ```

4. **观察日志**：
   ```bash
   tail -f logs/main_workflow.log
   ```

5. **调整参数**（如需要）

---

## 支持

如有问题，查看：
1. 日志文件：`logs/main_workflow.log`
2. 文档：`IMPLEMENTATION_SUMMARY.md`
3. 代码：`workflows/news_pipeline.py`

---

**祝使用愉快！** 🎉
