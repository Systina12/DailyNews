# 头条智能系统完整说明

## 系统架构

头条智能系统由四个核心模块组成：

1. **混合分类器**（规则 + LLM）
2. **动态水位控制**（平方根缩放）
3. **智能排序**（LLM 评分）
4. **自动学习黑名单**（长期优化）

---

## 1. 混合分类器（规则 + LLM）

### 问题
纯关键词匹配"比较捞"，容易误判和漏判。

### 解决方案
**两阶段分类**：
- 规则分类（快速）：基于关键词匹配，返回置信度
- LLM 分类（精准）：处理低置信度的新闻

### 工作流程
```
新闻 → 硬排除（娱乐/体育）
     ↓
     规则分类 → 置信度 ≥ 0.75？
                ├─ 是 → 直接分类
                └─ 否 → LLM 批量分类（20条/批）
```

### 配置参数
```bash
# 分类置信度阈值
CLASSIFY_CONFIDENCE_THRESHOLD=0.75

# Gemini Flash 便宜模型
GEMINI_FLASH_MODEL=gemini-2.5-flash-lite
```

### 代码位置
- `preprocessing/classify.py` - `Classify._process_headlines()`
- `llms/llms.py` - `LLMClient.request_gemini_flash()`

---

## 2. 动态水位控制（平方根缩放）

### 问题
- 8小时报的头条过多（80+条），显得很杂
- 阅读耐心不会线性增长

### 解决方案
**平方根函数实现次线性增长**：
```
水位线 = 基准值 × √(实际小时数 / 基准小时数)
```

### 效果对比
| 时间 | 线性增长 | 平方根增长 | 降低幅度 |
|------|---------|-----------|---------|
| 1小时 | 10条 | 10条 | - |
| 4小时 | 40条 | 20条 | 50% |
| 8小时 | 80条 | 28条 | 65% |
| 24小时 | 240条 | 49条 | 80% |

### 保留策略
```
数量 ≤ 低水位 → 全部保留
数量 > 低水位 → 按比例保留（60%），但不少于8条，不超过最大值
```

### 配置参数
```bash
# 基准：1小时（每小时报）
HEADLINE_BASE_HOURS=1
HEADLINE_BASE_LOW_WATERMARK=10  # 低水位
HEADLINE_BASE_MAX_KEEP=20       # 最大保留

# 固定参数
HEADLINE_KEEP_RATIO=0.6         # 保留比例 60%
HEADLINE_MIN_KEEP=8             # 最少保留 8 条
```

### 代码位置
- `workflows/news_pipeline.py` - `_calculate_headline_limits()`
- `workflows/news_pipeline.py` - `_apply_headline_limit()`

---

## 3. 智能排序（LLM 评分）

### 问题
"对老虎禁食"这种新闻不应该是头条。

### 解决方案
**三层策略**：

#### 第一层：硬规则过滤（快速）
黑名单关键词：
```python
hard_blacklist = {
    "zoo", "pet", "horoscope", "celebrity", "fashion", "beauty", "recipe",
    "动物园", "宠物", "星座", "明星", "时尚", "美容", "食谱",
    "зоопарк", "питомц", "гороскоп", "рецепт"
}
```

#### 第二层：LLM 批量评分（准确）
使用 Gemini Flash 对新闻评分（0-100分）：
- 战争/军事冲突：80-100分
- 政治重大事件：70-90分
- 经济危机、灾难：70-90分
- 一般政治/经济：50-70分
- 社会/科技新闻：40-60分
- 娱乐八卦：10-30分
- 动物趣闻、美容：0-20分

#### 第三层：Fallback（关键词评分）
如果 LLM 失败，使用关键词评分：
```python
high_importance = {
    "war": +30, "attack": +25, "missile": +25,
    "president": +15, "election": +15,
    "crisis": +15, "collapse": +20
}

low_importance = {
    "celebrity": -15, "fashion": -15, "beauty": -15,
    "zoo": -15, "pet": -10, "recipe": -15
}
```

### 配置参数
```bash
# 启用 LLM 评分
HEADLINE_ENABLE_LLM_SCORING=true
```

### 代码位置
- `workflows/news_pipeline.py` - `_prioritize_headlines()`
- `workflows/news_pipeline.py` - `_score_with_llm()`

---

## 4. 自动学习黑名单（长期优化）

### 问题
黑名单可能越积越多，最终需要引入数据库。

### 解决方案
**四重机制防止无限增长**：

#### 机制1：频率衰减
每次运行，所有关键词频率 × 0.95：
```python
for kw in blacklist:
    blacklist[kw] *= 0.95
```

#### 机制2：高频准入
只有出现在 >50% 低分新闻中的关键词才加入：
```python
if freq > 0.5:
    blacklist[kw] = freq
```

#### 机制3：低频清理
频率 <0.3 的关键词被删除：
```python
if blacklist[kw] < 0.3:
    del blacklist[kw]
```

#### 机制4：数量限制
最多保留 100 个关键词（按频率排序）：
```python
if len(blacklist) > 100:
    blacklist = dict(sorted_items[:100])
```

### 学习流程
```
LLM 评分 → 提取低分新闻（<40分）
         ↓
         提取关键词 → 计算出现频率
         ↓
         更新黑名单：
         1. 所有现有关键词 × 0.95（衰减）
         2. 新关键词频率 >0.5 → 加入
         3. 关键词频率 <0.3 → 删除
         4. 总数 >100 → 保留前100
         ↓
         保存到 data/headline_blacklist.json
```

### 配置参数
```bash
# 启用自动学习
HEADLINE_ENABLE_LEARNING=true

# 黑名单参数
HEADLINE_BLACKLIST_MAX_SIZE=100      # 最多100个关键词
HEADLINE_BLACKLIST_MIN_FREQ=0.3      # 最低频率0.3
HEADLINE_BLACKLIST_DECAY=0.95        # 衰减因子0.95
```

### 代码位置
- `workflows/news_pipeline.py` - `_update_blacklist_from_low_scores()`
- `workflows/news_pipeline.py` - `_extract_keywords()`
- `workflows/news_pipeline.py` - `_load_learned_blacklist()`
- `workflows/news_pipeline.py` - `_save_learned_blacklist()`

---

## 完整工作流程

```
1. 拉取新闻（hours 小时）
   ↓
2. 俄罗斯源激进过滤（filter_ru）
   ↓
3. 去重（dedupe_items）
   ↓
4. 混合分类（规则 + LLM）
   ├─ 头条
   ├─ 政治
   ├─ 财经
   ├─ 科技
   └─ 国际
   ↓
5. 头条特殊处理：
   ├─ 动态计算水位（平方根缩放）
   ├─ 智能排序（LLM 评分 + 黑名单过滤）
   ├─ 自动学习黑名单（从低分新闻）
   ├─ 按比例保留（60%）
   └─ 下放多余头条到其他分类
   ↓
6. 输出各分类新闻
```

---

## 配置文件示例

```bash
# config/settings.py 或环境变量

# ===== LLM 配置 =====
GEMINI_FLASH_MODEL=gemini-2.5-flash-lite
CLASSIFY_CONFIDENCE_THRESHOLD=0.75

# ===== 头条水位线（平方根缩放）=====
HEADLINE_BASE_HOURS=1                # 基准时间：1小时
HEADLINE_BASE_LOW_WATERMARK=10       # 1小时：低水位10条
HEADLINE_BASE_MAX_KEEP=20            # 1小时：最大20条
HEADLINE_KEEP_RATIO=0.6              # 保留比例60%
HEADLINE_MIN_KEEP=8                  # 最少保留8条

# ===== 头条排序和学习 =====
HEADLINE_ENABLE_LLM_SCORING=true     # 启用LLM评分
HEADLINE_ENABLE_LEARNING=true        # 启用自动学习
HEADLINE_BLACKLIST_MAX_SIZE=100      # 黑名单最多100个
HEADLINE_BLACKLIST_MIN_FREQ=0.3      # 最低频率0.3
HEADLINE_BLACKLIST_DECAY=0.95        # 衰减因子0.95
```

---

## 测试

运行测试脚本：
```bash
python test_headline_learning.py
```

测试内容：
1. 关键词提取
2. 黑名单学习
3. 黑名单清理
4. 头条排序（黑名单过滤）

---

## 文件清单

### 核心代码
- `preprocessing/classify.py` - 混合分类器
- `workflows/news_pipeline.py` - 头条处理流程
- `llms/llms.py` - LLM 客户端
- `config/settings.py` - 配置管理

### 文档
- `CLASSIFY_LLM_CONFIG.md` - 混合分类器说明
- `HEADLINE_LIMIT_CONFIG.md` - 动态水位说明
- `HEADLINE_SQRT_SCALING.md` - 平方根缩放说明
- `HEADLINE_IMPORTANCE_SCORING.md` - 智能排序说明
- `HEADLINE_LLM_LEARNING.md` - 自动学习黑名单说明
- `HEADLINE_SYSTEM_OVERVIEW.md` - 本文档（系统总览）

### 测试
- `test_classify_llm.py` - 混合分类器测试
- `test_headline_learning.py` - 黑名单学习测试

---

## 总结

这套系统实现了：
1. ✅ 混合分类（规则 + LLM）- 提高分类准确性
2. ✅ 动态水位（平方根缩放）- 控制头条数量
3. ✅ 智能排序（LLM 评分）- 让"头条"更"头条"
4. ✅ 自动学习（黑名单机制）- 长期优化，防止无限增长

最终目标：**让"头条"更"头条"** ✨
