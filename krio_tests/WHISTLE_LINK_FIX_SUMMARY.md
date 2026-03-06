# 吹哨功能链接修复 - 快速参考

## 问题
吹哨功能生成的 HTML 邮件中所有新闻都没有原文链接。

## 原因
RSS 数据中链接存储在 `canonical` 或 `alternate` 数组中，而不是直接的 `link` 字段。代码只检查了 `link` 字段，导致链接为空。

## 修复
在 `workflows/main_workflow.py` 中：

1. 添加了 `_extract_link()` 辅助函数（第 143-167 行）
2. 更新了 `run_realtime_workflow()` 使用该函数（第 223 行）
3. 增强了日志记录，显示链接信息（第 291 行）

## 测试
```bash
# 运行单元测试
python test_link_extraction.py

# 运行集成测试（测试模式）
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=70 --test
```

## 验证
检查生成的邮件 HTML：
- ✓ 链接应该显示为 "查看原文 →"
- ✗ 不应该显示 "搜索原文 →"（说明链接为空）

## 监控
```bash
# 查找链接为空的情况
grep "链接: (空)" logs/*.log

# 查找使用 Google 搜索的情况
grep "新闻链接为空，使用Google搜索" logs/*.log
```

## 相关文件
- `workflows/main_workflow.py` - 主修复文件
- `test_link_extraction.py` - 单元测试
- `WHISTLE_LINK_FIX.md` - 详细文档

## 状态
- ✓ 代码修复完成
- ✓ 单元测试通过
- ⏳ 待集成测试
- ⏳ 待部署
