# DZTnews - 智能新闻聚合与摘要系统

DZTnews 是一个基于 Python 的智能新闻聚合和摘要系统，能够自动从 FreshRSS 获取新闻、过滤内容、评估风险，并使用 LLM 生成高质量的中文新闻摘要。

## 主要特性

- 🔄 **自动新闻聚合**：从 FreshRSS 自动获取 24 小时内的新闻
- 🎯 **智能内容过滤**：过滤俄罗斯相关内容、娱乐体育新闻等
- 🔍 **去重处理**：基于标题规范化的智能去重
- 🛡️ **风险评估**：使用 Gemini 预测 DeepSeek 内容安全风险
- 🤖 **智能摘要生成**：使用 DeepSeek/Gemini 生成 HTML 格式新闻摘要
- 🔄 **自动 Fallback**：DeepSeek 触发风控时自动切换到 Gemini
- 📊 **监控指标**：实时跟踪 API 调用、Fallback 率等指标
- 📝 **完整日志**：详细的日志记录，便于调试和分析

## 系统架构

```
FreshRSS → 过滤 → 去重 → 分类 → 风险评估 → 摘要生成
                                    ↓              ↓
                                 Gemini    DeepSeek (→ Gemini fallback)
```

## 安装

### 环境要求

- Python 3.8+
- uv (Python 包管理器)

### 安装步骤

1. 克隆仓库

```bash
git clone <repository-url>
cd DZTnews
```

2. 安装依赖

```bash
uv sync
```

3. 激活虚拟环境

```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

4. 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
# 必需
export DEEPSEEK_TOKEN="your-deepseek-api-token"
export GEMINI_TOKEN="your-gemini-api-token"

# 可选
export FRESHRSS_EMAIL="your-email"
export FRESHRSS_PASSWORD="your-password"
export FRESHRSS_URL="your-freshrss-url"
export LOG_LEVEL="INFO"
```

## 使用方法

### 快速开始

运行完整工作流：

```bash
python workflows/main_workflow.py
```

这将执行：
1. 获取和预处理 24 小时新闻
2. 评估内容安全风险
3. 生成 HTML 摘要（保存到 `data/` 目录）

### 分步执行

```python
from workflows.news_pipeline import run_news_pipeline
from workflows.risk_assessment import run_risk_assessment_pipeline
from workflows.summary_generation import run_summary_generation_pipeline

# 步骤 1: 获取和预处理新闻
classified = run_news_pipeline()

# 步骤 2: 评估风险
risk_data = run_risk_assessment_pipeline(classified)

# 步骤 3: 生成摘要
summaries = run_summary_generation_pipeline(risk_data)
```

### 使用 Fallback API

```python
from llms.llms import LLMClient

client = LLMClient()

# 自动 fallback 请求
response = client.request_with_fallback(
    prompt="请总结这条新闻...",
    primary="deepseek"
)

print(f"使用的模型: {response['model_used']}")
print(f"是否 fallback: {response['is_fallback']}")
print(f"内容: {response['content']}")
```

## 配置

### 配置文件

配置位于 `config/settings.py`，支持通过环境变量覆盖：

```python
from config import settings

# 访问配置
print(settings.DEEPSEEK_API_URL)
print(settings.API_TIMEOUT)
```

### 主要配置项

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| DEEPSEEK_TOKEN | DEEPSEEK_TOKEN | - | DeepSeek API Token（必需）|
| GEMINI_TOKEN | GEMINI_TOKEN | - | Gemini API Token（必需）|
| API_TIMEOUT | API_TIMEOUT | 60 | API 请求超时（秒）|
| LOG_LEVEL | LOG_LEVEL | INFO | 日志级别 |
| DEFAULT_TEMPERATURE | DEFAULT_TEMPERATURE | 0.3 | LLM 温度参数 |
| DEFAULT_MAX_TOKENS | DEFAULT_MAX_TOKENS | 4000 | LLM 最大 token 数 |

## 测试

运行测试：

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行特定测试文件
pytest tests/unit/test_config.py

# 显示详细输出
pytest -v

# 显示覆盖率
pytest --cov=. --cov-report=html
```

## 项目结构

```
DZTnews/
├── config/              # 配置管理
├── ingestion/           # 数据获取
├── preprocessing/       # 数据预处理
├── llms/                # LLM 集成
├── utils/               # 工具函数
├── workflows/           # 业务流程
├── monitoring/          # 监控指标
├── tests/               # 测试
├── data/                # 数据输出
└── logs/                # 日志输出
```

详细架构说明请参考 [CLAUDE.md](CLAUDE.md)。

## 监控和指标

系统自动收集以下指标：

- API 调用次数和成功率
- Fallback 触发次数和比率
- 风险评估结果分布
- 运行时长

查看指标摘要：

```python
from monitoring import metrics

# 运行工作流后
metrics.print_summary()
```

## 日志

日志文件位于 `logs/` 目录，按日期命名（如 `2026-02-14.log`）。

日志级别：
- DEBUG: 详细调试信息
- INFO: 一般信息（默认）
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

## 故障排除

### DeepSeek API 调用失败

**问题**：`ContentFilteredException: DeepSeek 触发内容安全机制`

**解决**：系统会自动 fallback 到 Gemini，无需手动处理。如果频繁触发，可以检查风险评估的准确性。

### 环境变量未设置

**问题**：`ValueError: 配置错误: DEEPSEEK_TOKEN 未设置`

**解决**：确保设置了必需的环境变量：

```bash
export DEEPSEEK_TOKEN="your-token"
export GEMINI_TOKEN="your-token"
```

### FreshRSS 连接失败

**问题**：`RuntimeError: 无法连接到 FreshRSS 服务器`

**解决**：
1. 检查 FreshRSS URL 是否正确
2. 检查网络连接
3. 验证凭证是否有效

## 开发

### 添加新的过滤器

在 `preprocessing/filters.py` 中添加：

```python
def filter_custom(data):
    """自定义过滤器"""
    items = data.get("items", [])
    filtered = [item for item in items if custom_condition(item)]
    data["items"] = filtered
    return data
```

### 添加新的工作流

在 `workflows/` 目录下创建新文件：

```python
from utils.logger import get_logger

logger = get_logger("custom_workflow")

def run_custom_workflow(data):
    logger.info("开始执行自定义工作流")
    # 实现逻辑
    return result
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[添加许可证信息]

## 联系方式

[添加联系方式]
