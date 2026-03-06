# 如何测试实时监控吹哨功能

## 问题
重要新闻不是随时都有，怎么测试功能是否正常？

## 解决方案

### 🚀 最快测试（推荐）

```bash
# 1. 生成邮件 HTML（不需要任何配置）
python standalone_test.py

# 2. 用浏览器打开生成的文件
# 文件：test_alert_email.html
```

**查看内容**：
- 4 条模拟重要新闻
- 评分：95、88、82、81 分
- 红色警告样式
- 完整的标题、摘要、链接

---

### 📧 测试邮件发送

```bash
# 发送测试邮件到 TEST_EMAIL
python quick_test.py --send
```

**前提条件**：
- 配置 SMTP（`config/settings.py`）
- 设置 TEST_EMAIL 环境变量

---

### 🔍 测试真实新闻（降低阈值）

```bash
# 降低阈值到 50 分（正常是 80 分）
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=50 --test
```

**说明**：
- 使用真实新闻
- 降低阈值以便触发通知
- 测试完整流程

---

## 测试步骤

### 第一次测试
```bash
# 验证邮件格式
python standalone_test.py
# 用浏览器打开 test_alert_email.html
```

### 第二次测试
```bash
# 验证邮件发送
python quick_test.py --send
# 检查 TEST_EMAIL 邮箱
```

### 第三次测试
```bash
# 验证完整流程
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=50 --test
# 检查日志和邮箱
```

---

## 测试文件说明

| 文件 | 用途 | 依赖 | 速度 |
|------|------|------|------|
| `standalone_test.py` | 验证邮件格式 | 无 | 最快 ⭐⭐⭐ |
| `quick_test.py` | 验证邮件发送 | SMTP配置 | 快 ⭐⭐ |
| `test_realtime_alert.py` | 完整测试 | 全部 | 慢 ⭐ |

---

## 常见问题

### Q: 没有收到邮件？
A: 检查 SMTP 配置和 TEST_EMAIL 环境变量

### Q: 降低阈值后还是没有新闻？
A: 增加时间范围 `--hours=24` 或使用模拟数据

### Q: 如何验证邮件格式？
A: 运行 `python standalone_test.py`，用浏览器打开生成的 HTML

---

## 详细文档

完整测试指南：`TESTING_GUIDE.md`
