# 实时监控吹哨功能 - 测试指南

## 问题：如何测试重要新闻功能？

重要新闻不是随时都有，但我们需要验证功能是否正常工作。

## 解决方案：多种测试方法

### 方法 1：独立测试（最简单）⭐⭐⭐

使用独立脚本，不依赖任何外部模块，快速验证邮件生成。

```bash
# 生成邮件 HTML
python standalone_test.py

# 用浏览器打开 test_alert_email.html 查看效果
```

**优点**：
- ✅ 最快（几秒钟）
- ✅ 不需要安装依赖
- ✅ 不需要配置 SMTP
- ✅ 不需要真实新闻
- ✅ 可以验证邮件格式

**输出**：
- 生成 `test_alert_email.html` 文件
- 显示 4 条模拟重要新闻
- 评分：95、88、82、81 分

---

### 方法 2：快速测试（推荐）⭐⭐

使用模拟数据，快速验证邮件生成和发送功能。

```bash
# 1. 生成邮件 HTML（不发送）
python quick_test.py

# 2. 查看邮件效果
# 用浏览器打开 test_alert_email.html

# 3. 发送测试邮件到 TEST_EMAIL
python quick_test.py --send

# 4. 发送到正式邮箱（谨慎使用）
python quick_test.py --send --no-test-mode
```

**优点**：
- ✅ 快速（几秒钟）
- ✅ 不需要真实新闻
- ✅ 可以验证邮件格式
- ✅ 可以测试 SMTP 配置

---

### 方法 3：降低阈值测试

使用真实新闻，但降低阈值以便触发通知。

```bash
# 降低阈值到 50 分（正常是 80 分）
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=50 --test

# 更低的阈值（40 分）
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=40 --test
```

**优点**：
- ✅ 使用真实新闻
- ✅ 测试完整流程
- ✅ 验证 LLM 评分

**缺点**：
- ⚠ 可能收到不重要的新闻通知
- ⚠ 需要等待新闻拉取

---

### 方法 4：完整测试套件

使用测试脚本进行全面测试。

```bash
# 1. 模拟数据测试（快速）
python test_realtime_alert.py --mode=mock

# 2. 真实新闻测试（降低阈值）
python test_realtime_alert.py --mode=real --threshold=50

# 3. 发送测试邮件
python test_realtime_alert.py --mode=mock --send-email

# 4. 完整测试（包含邮件发送）
python test_realtime_alert.py --mode=all --threshold=50 --send-email
```

**测试内容**：
- ✅ LLM 评分功能
- ✅ 邮件 HTML 生成
- ✅ 邮件发送
- ✅ 真实新闻处理

---

### 方法 5：手动注入测试数据

修改代码临时注入高分新闻。

```python
# 在 run_realtime_workflow() 中添加测试数据
if test:  # 测试模式
    # 注入模拟高分新闻
    important_news.append({
        "category": "测试",
        "score": 95,
        "title": "这是一条测试新闻",
        "link": "https://example.com",
        "summary": "用于测试吹哨功能",
        "published": datetime.now().isoformat(),
    })
```

**优点**：
- ✅ 完全可控
- ✅ 可以测试边界情况

**缺点**：
- ⚠ 需要修改代码
- ⚠ 容易忘记删除

---

## 推荐测试流程

### 第一次测试（验证基本功能）

```bash
# 步骤 1: 独立测试（最简单）
python standalone_test.py

# 步骤 2: 用浏览器打开 test_alert_email.html
# 检查邮件格式是否正确
# - 红色警告样式
# - 显示评分（95分、88分等）
# - 显示分类（头条、国际等）
# - 显示标题和摘要
# - 链接可点击

# 步骤 3: 如果格式正确，继续测试邮件发送
python quick_test.py --send

# 步骤 4: 检查 TEST_EMAIL 邮箱
# 确认收到邮件且格式正确
```

### 第二次测试（验证完整流程）

```bash
# 步骤 1: 降低阈值测试真实新闻
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=50 --test

# 步骤 2: 查看日志
# 检查是否有新闻被评分
# 检查是否有高分新闻被检测到

# 步骤 3: 检查邮箱
# 如果有高分新闻，应该收到邮件
```

### 第三次测试（正式部署前）

```bash
# 步骤 1: 使用正常阈值测试
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=80 --test

# 步骤 2: 等待真实重要新闻
# 或者在有重要新闻时手动运行

# 步骤 3: 验证通知及时性
# 确认在重要新闻发生后能及时收到通知
```

---

## 测试检查清单

### 邮件格式测试 ✓

- [ ] HTML 格式正确（用浏览器打开 test_alert_email.html）
- [ ] 显示评分（95分、85分等）
- [ ] 显示分类（头条、国际等）
- [ ] 显示标题（完整且正确）
- [ ] 显示摘要（前200字符）
- [ ] 链接可点击
- [ ] 样式美观（红色警告风格）
- [ ] 按评分排序（高分在前）

### 邮件发送测试 ✓

- [ ] 能发送到 TEST_EMAIL（测试模式）
- [ ] 能发送到 SMTP_TO（正式模式）
- [ ] 邮件主题正确（包含时间和数量）
- [ ] 邮件内容完整
- [ ] 不会进入垃圾邮件

### LLM 评分测试 ✓

- [ ] 战争新闻得高分（80-100）
- [ ] 政治重大事件得高分（70-90）
- [ ] 娱乐八卦得低分（10-30）
- [ ] 动物趣闻得低分（10-30）
- [ ] 评分合理且稳定

### 完整流程测试 ✓

- [ ] 能拉取真实新闻
- [ ] 能正确分类
- [ ] 能批量评分
- [ ] 能筛选高分新闻
- [ ] 能生成邮件
- [ ] 能发送通知
- [ ] 日志记录完整

---

## 常见问题

### Q1: 没有收到测试邮件？

**检查**：
1. SMTP 配置是否正确（`config/settings.py`）
2. TEST_EMAIL 环境变量是否设置
3. 查看日志中的错误信息
4. 检查垃圾邮件箱

**解决**：
```bash
# 查看详细错误
python quick_test.py --send 2>&1 | tee test.log
```

### Q2: 降低阈值后还是没有新闻？

**原因**：
- 最近1小时可能没有新闻
- 新闻评分都很低

**解决**：
```bash
# 增加时间范围到 24 小时
python workflows/main_workflow.py --mode=realtime --hours=24 --threshold=40 --test

# 或者使用模拟数据
python test_realtime_alert.py --mode=mock --send-email
```

### Q3: 如何验证 LLM 评分是否准确？

**方法**：
```bash
# 运行完整测试，查看评分结果
python test_realtime_alert.py --mode=mock

# 检查输出中的评分
# 战争新闻应该 80-100 分
# 动物园新闻应该 10-30 分
```

### Q4: 如何测试 crontab 配置？

**方法**：
```bash
# 1. 手动运行 crontab 命令
cd /path/to/DailyNews && python workflows/main_workflow.py --mode=realtime --hours=0.25 --threshold=80 --test

# 2. 检查日志
tail -f logs/realtime.log

# 3. 等待 15 分钟，检查是否自动运行
```

---

## 测试脚本说明

### standalone_test.py（最简单）⭐⭐⭐

**用途**：快速验证邮件 HTML 生成

**优点**：
- 最快（几秒钟）
- 不需要任何依赖
- 不需要配置
- 完全独立

**使用**：
```bash
python standalone_test.py
# 然后用浏览器打开 test_alert_email.html
```

### quick_test.py（推荐）⭐⭐

**用途**：快速验证邮件生成和发送

**优点**：
- 快速（几秒钟）
- 不需要真实新闻
- 不需要 LLM API

**使用**：
```bash
python quick_test.py              # 生成 HTML
python quick_test.py --send       # 发送测试邮件
```

### test_realtime_alert.py（完整）⭐

**用途**：完整测试所有功能

**优点**：
- 测试 LLM 评分
- 测试真实新闻
- 测试完整流程

**使用**：
```bash
python test_realtime_alert.py --mode=mock              # 模拟数据
python test_realtime_alert.py --mode=real --threshold=50  # 真实新闻
python test_realtime_alert.py --mode=all --send-email     # 完整测试
```

---

## 总结

**最简单的测试方法**（不需要任何配置）：
```bash
python standalone_test.py
# 用浏览器打开 test_alert_email.html
```

**快速测试邮件发送**：
```bash
python quick_test.py --send
```

**最完整的测试方法**：
```bash
python test_realtime_alert.py --mode=all --threshold=50 --send-email
```

**正式部署前的测试**：
```bash
# 1. 独立测试（验证邮件格式）
python standalone_test.py

# 2. 快速测试（验证邮件发送）
python quick_test.py --send

# 3. 降低阈值测试真实新闻
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=50 --test

# 4. 正常阈值测试（等待重要新闻）
python workflows/main_workflow.py --mode=realtime --hours=1 --threshold=80 --test
```

现在你可以在没有重要新闻的情况下，完整测试吹哨功能了！🎉
