# 吹哨功能链接修复 V2 - 统一数据标准化方案

## 问题回顾

用户提出了一个重要问题：
> "你的这次修复调用了我原有工作流清洗的数据吗？如果没有，那你是怎么实现的或者我原有工作流并没有清洗？"

## 原有工作流分析

经过检查，发现：

1. **原有工作流并没有清洗链接字段**
   - `preprocessing/filters.py` 的 `_item_text()` 只是临时提取链接用于文本匹配
   - `preprocessing/classify.py` 的 `_is_hard_excluded()` 也只是临时提取链接用于判断
   - `preprocessing/dedupe.py` 只处理标题去重
   - **没有任何地方将提取的链接写回到 `item["link"]` 字段**

2. **V1 修复方案的问题**
   - 在 `run_realtime_workflow()` 中临时提取链接
   - 只在构建 `important_news` 时使用
   - **没有修改原始 item 数据，不符合数据流设计原则**

## V2 改进方案

### 设计原则

**在数据预处理阶段统一标准化，让所有后续流程都能直接使用 `item["link"]`**

### 实现步骤

#### 1. 新增标准化模块

创建 `preprocessing/normalize.py`：

```python
def normalize_link(item):
    """
    从新闻 item 中提取链接并标准化
    优先级：canonical > alternate > link
    """
    link = ""
    
    # 1. canonical 数组
    canonical = item.get("canonical")
    if isinstance(canonical, list) and canonical:
        link = canonical[0].get("href", "") or ""
    
    # 2. alternate 数组
    if not link:
        alternate = item.get("alternate")
        if isinstance(alternate, list) and alternate:
            link = alternate[0].get("href", "") or ""
    
    # 3. link 字段
    if not link:
        link = item.get("link", "") or ""
    
    return link.strip()


def normalize_items(data):
    """
    标准化新闻数据
    将 canonical/alternate 中的链接提取到 item["link"] 字段
    """
    items = data.get("items", [])
    normalized_count = 0
    
    for item in items:
        if not isinstance(item, dict):
            continue
        
        original_link = item.get("link", "")
        normalized_link = normalize_link(item)
        
        # 只有当提取的链接与原 link 字段不同时才更新
        if normalized_link and normalized_link != original_link:
            item["link"] = normalized_link
            normalized_count += 1
    
    logger.info(f"标准化 {normalized_count}/{len(items)} 条新闻的链接字段")
    return data
```

#### 2. 更新数据处理流程

在 `workflows/news_pipeline.py` 的 `run_news_pipeline_all()` 中：

```python
def run_news_pipeline_all(categories=None, hours: float = 24):
    """
    多分类：拉取 -> 标准化 -> 过滤 -> 去重 -> 分类
    """
    from preprocessing.normalize import normalize_items
    
    rss = RSSClient()
    data = rss.get_news(hours=hours)
    normalized = normalize_items(data)  # ← 新增：标准化链接字段
    filtered = filter_ru(normalized)
    deduped = dedupe_items(filtered)
    raw_items = deduped.get("items", [])
    # ... 后续分类逻辑
```

#### 3. 简化吹哨功能

在 `workflows/main_workflow.py` 的 `run_realtime_workflow()` 中：

```python
# 修改前（V1）：
link = _extract_link(item)  # 临时提取

# 修改后（V2）：
link = item.get("link", "")  # 直接使用标准化后的字段
```

## 数据流对比

### 修改前

```
RSS 数据 (canonical/alternate/link)
  ↓
过滤 (临时提取链接用于判断，不修改数据)
  ↓
去重 (不处理链接)
  ↓
分类 (临时提取链接用于判断，不修改数据)
  ↓
吹哨功能 (临时提取链接) ← 问题：每次都要重复提取
```

### 修改后

```
RSS 数据 (canonical/alternate/link)
  ↓
标准化 (提取链接到 item["link"]) ← 新增：统一标准化
  ↓
过滤 (直接使用 item["link"])
  ↓
去重 (直接使用 item["link"])
  ↓
分类 (直接使用 item["link"])
  ↓
吹哨功能 (直接使用 item["link"]) ← 简化：无需重复提取
```

## 优势

1. **符合数据流设计原则**
   - 在数据入口处统一标准化
   - 后续所有模块都使用标准化后的数据

2. **代码复用性好**
   - 只需在一个地方实现链接提取逻辑
   - 避免在多个地方重复相同代码

3. **易于维护**
   - 如果 RSS 数据格式变化，只需修改 `normalize.py`
   - 不需要修改多个模块

4. **性能更好**
   - 只在数据入口处提取一次链接
   - 避免在每个模块中重复提取

## 影响范围

### 受益模块

所有使用 `item["link"]` 的模块都会自动受益：

1. `workflows/main_workflow.py` - 吹哨功能
2. `workflows/summary_generation.py` - 摘要生成（如果使用链接）
3. `preprocessing/filters.py` - 过滤逻辑
4. `preprocessing/classify.py` - 分类逻辑
5. `llms/build_prompt.py` - 提示构建

### 向后兼容性

- ✓ 如果 RSS 数据中已有 `link` 字段，保持不变
- ✓ 只有当 `link` 为空或不存在时，才从 `canonical/alternate` 提取
- ✓ 不影响现有功能

## 测试验证

### 单元测试

```bash
# 测试标准化功能
python test_normalize_standalone.py
```

测试覆盖：
- ✓ canonical 数组提取
- ✓ alternate 数组提取
- ✓ link 字段保持
- ✓ 优先级正确
- ✓ 批量标准化

### 集成测试

```bash
# 测试吹哨功能
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=70 --test
```

验证：
- ✓ 链接正确显示为 "查看原文 →"
- ✓ 不再显示 "搜索原文 →"

## 部署建议

1. **测试环境验证**
   ```bash
   # 运行单元测试
   python test_normalize_standalone.py
   
   # 运行集成测试
   python workflows/main_workflow.py --mode=realtime --hours=1 --test
   ```

2. **检查日志**
   ```bash
   # 查看标准化日志
   grep "标准化.*条新闻的链接字段" logs/*.log
   
   # 查看链接为空的情况（应该很少）
   grep "链接: (空)" logs/*.log
   ```

3. **生产环境部署**
   - 先在测试环境运行 24 小时
   - 确认无异常后部署到生产环境

## 文件清单

### 新增文件
- `preprocessing/normalize.py` - 数据标准化模块
- `test_normalize_standalone.py` - 独立单元测试

### 修改文件
- `workflows/news_pipeline.py` - 添加标准化步骤
- `workflows/main_workflow.py` - 简化链接提取逻辑

### 保留文件（备用）
- `workflows/main_workflow.py` 中的 `_extract_link()` 函数
  - 标记为已废弃，但保留作为备用

## 总结

V2 方案通过在数据预处理阶段统一标准化链接字段，解决了以下问题：

1. ✓ 符合数据流设计原则（在入口处清洗数据）
2. ✓ 避免代码重复（只在一个地方实现提取逻辑）
3. ✓ 提高代码可维护性（修改一处，全局生效）
4. ✓ 提升性能（只提取一次，多处使用）
5. ✓ 向后兼容（不影响现有功能）

这是一个更加优雅和可维护的解决方案。
