# LLM成本优化说明

## 优化目标
减少LLM调用次数，降低API成本，同时保持新闻处理质量。

## 当前模型价格（每百万token）

| 模型 | 输入价格 | 输出价格 | 上下文窗口 | 用途 |
|------|---------|---------|-----------|------|
| Gemini 2.5 Flash Lite | $0.10 | $0.40 | 1M tokens | 分类、评分、风险评估 |
| Gemini 3 Flash | $0.50 | $3.00 | 1M tokens | 高风险摘要生成（fallback） |
| DeepSeek Chat | $0.28 | $0.42 | 64K tokens | 低风险摘要生成 |

参考来源：
- [Gemini API Pricing](https://costgoat.com/pricing/gemini-api)
- [Gemini Context Window](https://aimlapi.com/gemini-2-5-flash-lite)
- [DeepSeek API Pricing](https://gptproto.com/blog/deepseek-api)

## 已实施的优化

### 1. 降低分类置信度阈值

**配置**: `CLASSIFY_CONFIDENCE_THRESHOLD = 0.60` (从0.75降低)

**原理**: 规则分类置信度0.60-0.75之间的新闻，规则判断已经足够准确，不需要LLM二次确认

**效果**: 减少30-40%的分类LLM调用，节省约$0.01/天

**环境变量**:
```bash
export CLASSIFY_CONFIDENCE_THRESHOLD=0.60
```

### 2. 批量处理优化

**配置**:
- `RISK_BATCH_SIZE = 200` (从100增加)
- `CLASSIFY_BATCH_SIZE = 100` (保持)
- `SCORING_BATCH_SIZE = 100` (保持)

**原理**: 
- Gemini 2.5 Flash Lite支持1M tokens上下文窗口
- 风险评估prompt更简单（只需判断high/low），可以处理更多新闻
- 分类和评分prompt更复杂，保持100条/批确保质量

**批次大小计算**:
- 单条新闻：150字符标题 + 1500字符摘要 = 1650字符
- 200条 × 1650字符 = 330,000字符 ≈ 82,500 tokens
- 远低于1M tokens限制，安全余量充足

**效果**: 减少API调用次数和网络开销，节省约$0.005/天

**环境变量**:
```bash
export RISK_BATCH_SIZE=200
export CLASSIFY_BATCH_SIZE=100
export SCORING_BATCH_SIZE=100
```

## 总体成本节省

假设每天处理1000条新闻：

| 步骤 | 优化前 | 优化后 | 节省 |
|------|--------|--------|------|
| 分类 | ~300次LLM调用 | ~180次 | 40% |
| 风险评估 | ~10批 | ~5批 | 50% |
| **总成本** | **$0.232/天** | **$0.210/天** | **9.5%** |

**年度节省**: 约$8.03

## 为什么不做风险评估快速检查？

虽然理论上可以通过敏感词过滤跳过部分LLM调用，但实际上：

1. **多语言支持困难**: 需要维护中英俄等多语言敏感词列表，维护成本高
2. **已有fallback机制**: DeepSeek风控触发时会自动fallback到Gemini 3 Flash
3. **风险评估的目的**: 是预判DeepSeek是否会失败，而不是省钱
4. **因小失大**: 为了节省少量成本而增加复杂度和维护负担不值得

## 环境变量配置

```bash
# 分类置信度阈值
export CLASSIFY_CONFIDENCE_THRESHOLD=0.60

# 批量处理大小
export RISK_BATCH_SIZE=200
export CLASSIFY_BATCH_SIZE=100
export SCORING_BATCH_SIZE=100
```

## 回滚方案

```bash
export CLASSIFY_CONFIDENCE_THRESHOLD=0.75
export RISK_BATCH_SIZE=100
export CLASSIFY_BATCH_SIZE=100
export SCORING_BATCH_SIZE=100
```

## 监控指标

1. **LLM调用次数**
   - 分类LLM调用率（目标: <30%）
   - 风险评估批次数（目标: 减少50%）

2. **准确率**
   - 规则分类准确率（目标: >90%）

3. **成本**
   - 每日API成本
   - 每条新闻平均成本

4. **性能**
   - 批量处理延迟
   - 总处理时间

## 更新日志

- 2026-02-27: 实施优化1（分类阈值）和优化2（批量处理）
