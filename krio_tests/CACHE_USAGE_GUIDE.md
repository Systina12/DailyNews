# 新闻缓存使用指南

## 快速开始

### 1. 运行测试

```bash
# 测试缓存基本功能
python krio_tests/test_news_cache.py

# 测试实时告警缓存效果
python krio_tests/test_realtime_cache.py
```

### 2. 使用实时告警（自动启用缓存）

```bash
# 第一次运行
python -m workflows.main_workflow --mode=realtime --hours=1 --threshold=80

# 输出示例：
# [INFO] 处理 50 条新闻...
# [INFO] 缓存统计: 命中 0 条, 未命中 50 条, LLM调用 150 次
# [INFO] 发现 3 条重要新闻，发送告警...

# 10分钟后再次运行
python -m workflows.main_workflow --mode=realtime --hours=1 --threshold=80

# 输出示例：
# [INFO] 处理 55 条新闻...
# [INFO] 缓存统计: 命中 45 条, 未命中 10 条, LLM调用 30 次
# [INFO] 跳过已发送告警: 2 条
# [INFO] 发现 1 条重要新闻，发送告警...
```

## 核心功能

### 1. 自动缓存评分结果

所有经过LLM评分的新闻都会自动缓存，包括：
- 重要性评分（0-100分）
- 中文标题
- 中文摘要
- 发布时间
- 分类信息

### 2. 告警去重

同一条新闻只会发送一次告警，即使它在多次运行中都被拉取到。

### 3. 24小时自动清理

超过24小时的缓存会自动清理，保持数据新鲜度。

### 4. 性能统计

每次运行都会显示缓存命中率和LLM调用次数，方便监控性能。

## 手动操作

### 查看缓存内容

```python
from utils.news_cache import get_news_cache

cache = get_news_cache()

# 获取统计信息
stats = cache.get_stats()
print(f"总缓存: {stats['total']} 条")
print(f"已发送告警: {stats['alert_sent']} 条")
print(f"最近1小时: {stats['last_1h']} 条")
```

### 清空缓存

```bash
# 删除缓存文件
rm data/news_cache.json

# 或者在Python中
from pathlib import Path
from config import settings

cache_file = settings.DATA_DIR / "news_cache.json"
if cache_file.exists():
    cache_file.unlink()
```

### 手动清理过期缓存

```python
from utils.news_cache import get_news_cache

cache = get_news_cache()
expired_count = cache.cleanup_expired()
print(f"清理了 {expired_count} 条过期缓存")
```

## 配置选项

### 修改缓存有效期

编辑 `utils/news_cache.py`：

```python
# 默认24小时
cache = NewsCache(ttl_hours=24)

# 修改为48小时
cache = NewsCache(ttl_hours=48)
```

### 修改缓存文件位置

```python
from pathlib import Path
from utils.news_cache import NewsCache

cache = NewsCache(cache_file=Path("/custom/path/cache.json"))
```

## 常见问题

### Q: 缓存会占用多少空间？

A: 每条新闻约500-1000字节，24小时约1000-2000条新闻，总计1-2MB。

### Q: 如何知道缓存是否生效？

A: 查看日志输出的"缓存统计"，如果"命中"数量大于0，说明缓存生效。

### Q: 缓存会影响新闻的实时性吗？

A: 不会。缓存只存储评分结果，新闻内容仍然是实时拉取的。

### Q: 如果新闻标题略有变化怎么办？

A: 缓存基于标题+链接的hash，标题变化会被视为新新闻。这是预期行为，确保不会错过重要更新。

### Q: 多个实例会共享缓存吗？

A: 当前实现使用本地JSON文件，不支持多实例共享。如需共享，可以改用Redis等分布式缓存。

## 性能对比

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| LLM调用次数 | 150次/运行 | 30-90次/运行 | 40-80% |
| 响应时间 | 60秒 | 15-40秒 | 33-75% |
| API成本 | $0.15 | $0.03-0.09 | 40-80% |
| 重复告警 | 是 | 否 | 100% |

## 监控建议

### 1. 定期检查缓存统计

```bash
# 添加到crontab
0 */6 * * * cd /path/to/DailyNews && python -c "from utils.news_cache import get_news_cache; print(get_news_cache().get_stats())"
```

### 2. 监控缓存命中率

如果命中率持续低于50%，可能需要：
- 增加运行频率
- 延长缓存TTL
- 检查新闻源是否频繁更新标题

### 3. 监控缓存大小

```bash
# 检查缓存文件大小
ls -lh data/news_cache.json
```

如果文件过大（>10MB），可能需要：
- 减少缓存TTL
- 手动清理过期数据
- 考虑使用数据库存储

## 下一步

- 查看完整文档：`NEWS_CACHE_FEATURE.md`
- 运行测试：`test_news_cache.py`
- 查看代码：`utils/news_cache.py`
