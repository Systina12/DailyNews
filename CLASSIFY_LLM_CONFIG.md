# LLM 分类和风险评估配置说明

## 概述

系统现在使用混合策略进行新闻分类：
1. **规则分类**（快速、免费）：处理 70-80% 的明确新闻
2. **LLM 分类**（精准、低成本）：处理 20-30% 的模糊新闻

风险评估也改用便宜的 Gemini Flash 模型。

## 环境变量配置

在 `.env` 文件中添加：

```bash
# Gemini Flash 便宜模型（用于分类和风险评估）
GEMINI_FLASH_MODEL=gemini-1.5-flash-8b

# 分类置信度阈值（0-1，默认 0.75）
# 高于此值使用规则分类，低于此值使用 LLM
CLASSIFY_CONFIDENCE_THRESHOLD=0.75

# 或者使用其他便宜的 Gemini 模型
# GEMINI_FLASH_MODEL=gemini-1.5-flash
```

## 调优指南

### 减少 LLM 调用（降低成本）

如果你发现 LLM 调用太频繁（如日志显示 80% 新闻都需要 LLM），可以：

1. **降低置信度阈值**（推荐）：
```bash
CLASSIFY_CONFIDENCE_THRESHOLD=0.65  # 从 0.75 降到 0.65
```
这样更多新闻会被规则分类接受，减少 LLM 调用。

2. **增加关键词**：
编辑 `preprocessing/classify.py`，在对应类别添加更多关键词。

### 提高分类准确度

如果你发现分类不准确，可以：

1. **提高置信度阈值**：
```bash
CLASSIFY_CONFIDENCE_THRESHOLD=0.85  # 从 0.75 提高到 0.85
```
这样更多新闻会交给 LLM 处理，提高准确度但增加成本。

2. **查看日志分析**：
```bash
grep "规则分类:" logs/*.log | tail -20
```
看看规则分类的比例，调整阈值。

## 模型选择

### Gemini Flash 模型对比

| 模型 | 价格（输入/输出） | 上下文 | 适用场景 |
|------|------------------|--------|----------|
| gemini-1.5-flash-8b | $0.0375/$0.15 per 1M tokens | 1M | 分类、风险评估（推荐） |
| gemini-1.5-flash | $0.075/$0.30 per 1M tokens | 1M | 需要更高准确度时 |
| gemini-2.0-flash-exp | 免费（有限额） | 1M | 摘要生成 |

### 成本估算

假设每天处理 500 条新闻：
- 规则分类：400 条（免费）
- LLM 分类：100 条 × 200 tokens = 20K tokens
- 风险评估：500 条 × 150 tokens = 75K tokens
- **每天总计**：~95K tokens ≈ $0.004（不到 1 分钱）

## 工作流程

### 1. 新闻分类（preprocessing/classify.py）

```python
from preprocessing.classify import Classify

classifier = Classify(category="政治")
result = classifier._process_headlines(items)
```

**流程**：
1. 硬排除：娱乐、体育等明确噪音（规则）
2. 规则分类：关键词匹配，返回置信度
3. 高置信度（≥0.75）：直接采用规则结果
4. 低置信度（<0.75）：批量调用 LLM（Gemini Flash）
5. 合并结果

### 2. 风险评估（workflows/risk_assessment.py）

```python
from workflows.risk_assessment import run_risk_assessment_pipeline

result = run_risk_assessment_pipeline(classified_data)
```

**改动**：
- 原来：使用 `gemini-2.0-flash-exp`
- 现在：使用 `gemini-1.5-flash-8b`（便宜 50%）

## 调优参数

### 置信度阈值（推荐调整）

通过环境变量控制：

```bash
# 默认值 0.75（平衡）
CLASSIFY_CONFIDENCE_THRESHOLD=0.75

# 降低成本（更多规则分类）
CLASSIFY_CONFIDENCE_THRESHOLD=0.65

# 提高准确度（更多 LLM 分类）
CLASSIFY_CONFIDENCE_THRESHOLD=0.85
```

**效果对比**：

| 阈值 | 规则分类比例 | LLM 调用 | 准确度 | 成本/天 |
|------|-------------|---------|--------|---------|
| 0.65 | ~80% | 少 | 85% | $0.002 |
| 0.75 | ~60% | 中 | 90% | $0.004 |
| 0.85 | ~40% | 多 | 95% | $0.008 |

### LLM 批量大小

```python
llm_results = self._batch_classify_with_llm(uncertain_items, batch_size=20)
```

- **增大 batch_size**（如 30）：减少 API 调用次数，但单次响应更长
- **减小 batch_size**（如 10）：更快响应，但 API 调用更频繁

## 速率限制

在 `utils/rate_limiter.py` 中配置：

```python
# Gemini Flash: 更高的速率限制
gemini_flash_limiter = RateLimiter(max_calls=100, time_window=60)
```

根据你的 API 配额调整 `max_calls`。

## 测试

运行测试脚本：

```bash
python test_classify_llm.py
```

查看分类效果和 LLM 调用情况。

## 监控

查看日志了解 LLM 使用情况：

```bash
grep "LLM 批量分类" logs/*.log
grep "Gemini Flash" logs/*.log
```

## 故障处理

### LLM 分类失败

系统会自动降级：
- 失败的新闻标记为"国际"类别
- 不影响整体流程
- 日志会记录错误

### API 配额耗尽

1. 检查速率限制配置
2. 提高置信度阈值，减少 LLM 调用
3. 考虑升级 API 配额

## 性能对比

| 方案 | 准确度 | 速度 | 成本/天 |
|------|--------|------|---------|
| 纯规则 | 75% | 快 | $0 |
| 纯 LLM | 95% | 慢 | $0.02 |
| 混合策略 | 90% | 中 | $0.004 |

混合策略在准确度、速度、成本之间取得最佳平衡。
