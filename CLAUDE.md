# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DZTnews is a Python-based intelligent news aggregation and summarization system that:
1. Fetches RSS feeds from FreshRSS
2. Applies multi-stage content filters (Russia-related content, entertainment/sports)
3. Deduplicates news items
4. Assesses DeepSeek content safety risk using Gemini
5. Generates HTML news summaries using DeepSeek (with automatic Gemini fallback)

The system features automatic fallback mechanisms to handle content moderation triggers, ensuring reliable news summary generation.

## Environment Setup

This project uses `uv` for dependency management:

```bash
# Install dependencies
uv sync

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

## Running the Application

```bash
# Run the complete workflow
python workflows/main_workflow.py

# Or run individual workflows
python -c "from workflows.news_pipeline import run_news_pipeline; run_news_pipeline()"
python -c "from workflows.risk_assessment import run_risk_assessment_pipeline; run_risk_assessment_pipeline(data)"
python -c "from workflows.summary_generation import run_summary_generation_pipeline; run_summary_generation_pipeline(data)"
```

The main workflow will:
1. Fetch and preprocess 24h news
2. Assess content safety risk
3. Generate HTML summaries (saved to `data/` directory)

## Architecture

### Data Flow Pipeline

```
FreshRSS → Filter → Dedupe → Classify → Risk Assessment → Summary Generation
                                              ↓                    ↓
                                           Gemini          DeepSeek (→ Gemini fallback)
```

### 1. Ingestion Layer (`ingestion/`)

**RSSClient** (`RSSclient.py`):
- Fetches news from FreshRSS API using Google Reader compatibility layer
- Session-based authentication with GoogleLogin format
- `get_24h_news()`: Retrieves last 24 hours using `ot` (older than) timestamp
- Returns JSON with items array

### 2. NLP Processing Layer (`preprocessing/`)

**注意**：此目录原名为 `nlp/`，已重命名为 `preprocessing/` 以更准确地描述其功能。

**Filters** (`filters.py`):
- `filter_ru()`: Removes items with "俄罗斯" label
- `filter_high_risk_items()`: Filters high-risk news items
- `filter_low_risk_items()`: Filters low-risk news items

**Deduplication** (`dedupe.py`):
- `normalize_title()`: Strips brackets, prefixes (突发/breaking), normalizes whitespace
- `dedupe_items()`: Uses normalized titles as deduplication keys

**Classification** (`classify.py`):
- `Classify._process_headlines()`: Filters entertainment/sports content
  - Blocks keywords: music, sports events, TV shows, interviews
  - Blocks CBS video URLs and transcript pages
  - Filters date-prefixed titles from CBS/BBC
- Returns structured dict with section="headline" and processed items

### 3. Configuration Management (`config/`)

**Settings** (`settings.py`):
- Centralized configuration management using environment variables
- `Settings` class with all configuration parameters
- `settings` global instance for easy access
- Key configurations:
  - FreshRSS credentials and URLs
  - LLM API endpoints and tokens
  - Timeout and request parameters
  - Directory paths (data, logs)
  - Log levels and formats
- Methods:
  - `ensure_directories()`: Creates necessary directories
  - `validate()`: Validates required configurations

**Usage**:
```python
from config import settings

# Access configuration
api_url = settings.DEEPSEEK_API_URL
timeout = settings.API_TIMEOUT

# Ensure directories exist
settings.ensure_directories()
```

### 4. LLM Integration Layer (`llms/`)

**LLMClient** (`llms.py`):
- `request_deepseek()`: Calls deepseek-chat model with content safety detection
  - Automatically detects HTTP 400, empty responses, empty text
  - Throws `ContentFilteredException` when content moderation triggers
- `request_gemini()`: Calls gemini-2.0-flash-exp model
- `request_with_fallback()`: Smart request with automatic fallback
  - Primary model: DeepSeek or Gemini
  - Auto-switches to backup model if content filtering detected
  - Returns dict with `content`, `model_used`, `is_fallback`, `filter_reason`

**Prompt Building** (`build_prompt.py`):
Refactored with clean separation of concerns:
- **Utility Functions**:
  - `_clean_text()`: Text normalization
  - `_extract_summary()`: Handles dict/string summary extraction
  - `_filter_by_risk()`: Filters items by risk level
- **Prompt Templates**:
  - `RISK_ASSESSMENT_TEMPLATE`: DeepSeek risk evaluation prompt
  - `HEADLINE_TEMPLATE`: HTML news summary generation prompt
- **Builder Functions**:
  - `build_ds_risk_prompt()`: Creates risk assessment prompts
  - `build_headline_prompt(risk_filter="low"|"high")`: Creates summary prompts for specific risk levels

**Token Management** (`tokens.py`):
- `get_deepseek_token()`: Reads `DEEPSEEK_TOKEN` from environment
- `get_gemini_token()`: Reads `GEMINI_TOKEN` from environment

**Exceptions** (`exceptions.py`):
- `ContentFilteredException`: DeepSeek content safety trigger
- `LLMAPIError`: Base class for LLM API errors
- `LLMTimeoutError`: API timeout errors
- `LLMConnectionError`: Connection errors
- `LLMResponseError`: Response parsing errors

### 5. Utilities Layer (`utils/`)

**DeepSeek Content Safety Detection** (`deepseek_check.py`):
- `is_content_filtered()`: Simple boolean check for content filtering
  - Detects HTTP 400, None responses, empty text
- `check_deepseek_response()`: Detailed response analysis
  - Returns dict with `is_filtered`, `reason`, `safe_to_use`, `response_length`

**Risk Parsing** (`risk.py`):
- `parse_risk_response()`: Parses "编号:low/high" format from Gemini
- `annotate_risk_levels()`: Adds `ds_risk` field to news items

**Logger** (`logger.py`):
- `setup_logger()`: Configures logger with file and console output
- `get_logger(name)`: Returns named logger instance
- Features:
  - Automatic log file creation by date
  - Configurable log levels
  - UTF-8 encoding support
  - Prevents duplicate handlers

**Usage**:
```python
from utils.logger import get_logger

logger = get_logger("my_module")
logger.info("Processing started")
logger.error("Error occurred", exc_info=True)
```

### 6. Monitoring Layer (`monitoring/`)

**MetricsCollector** (`metrics.py`):
- Collects and tracks system metrics during workflow execution
- Key features:
  - Event recording with timestamps
  - Counter tracking (API calls, fallbacks, etc.)
  - Fallback rate calculation
  - Risk assessment statistics
- Methods:
  - `record_event()`: Records timestamped events
  - `increment_counter()`: Increments named counters
  - `record_fallback()`: Tracks fallback events
  - `record_api_call()`: Tracks API call success/failure
  - `record_risk_assessment()`: Tracks risk distribution
  - `get_summary()`: Returns metrics summary
  - `print_summary()`: Prints formatted metrics report

**Usage**:
```python
from monitoring import metrics

# Record events
metrics.record_api_call("deepseek", success=True, duration=1.5)
metrics.record_fallback("HTTP 400", "deepseek", "gemini")

# Print summary at end of workflow
metrics.print_summary()
```

### 7. Workflow Layer (`workflows/`)

**News Pipeline** (`news_pipeline.py`):
- `run_news_pipeline()`: Executes ingestion → filter → dedupe → classify
- Returns classified news data ready for risk assessment

**Risk Assessment** (`risk_assessment.py`):
- `run_risk_assessment_pipeline()`: Uses Gemini to predict DeepSeek content safety risk
- Annotates each news item with `ds_risk: "low"|"high"`
- Returns risk-annotated data

**Summary Generation** (`summary_generation.py`):
- `run_summary_generation_pipeline()`: Generates HTML summaries
  - Low-risk news: DeepSeek with automatic Gemini fallback
  - High-risk news: Direct Gemini generation
- Returns dict with `low_risk_summary`, `high_risk_summary`, and metadata

**Main Workflow** (`main_workflow.py`):
- `run_main_workflow()`: Orchestrates complete pipeline
- Saves HTML summaries to `data/` directory with timestamps
- Provides progress logging and error handling

## Key Design Patterns

### Automatic Fallback Mechanism

The system uses a two-tier safety approach:

1. **Predictive Risk Assessment**: Gemini evaluates which news items might trigger DeepSeek's content moderation
2. **Reactive Fallback**: If DeepSeek still triggers (false negative), automatically switches to Gemini

This ensures 100% summary generation success rate while optimizing for DeepSeek usage (lower cost).

### Content Safety Detection

Three indicators of DeepSeek content filtering:
- HTTP 400 status code
- Empty/None response
- Empty text content

When detected, `ContentFilteredException` is raised and caught by fallback logic.

## Testing

### Test Structure

```
tests/
├── unit/                    # 单元测试
│   ├── test_config.py      # 配置模块测试
│   ├── test_deepseek_check.py  # 内容安全检测测试
│   └── test_preprocessing.py   # 预处理模块测试
├── integration/             # 集成测试
└── fixtures/                # 测试数据
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/
```

### Test Configuration

Test configuration is in `pyproject.toml`:
- Test discovery patterns
- Coverage settings
- Excluded paths

## Environment Variables

Required:
- `DEEPSEEK_TOKEN`: DeepSeek API authentication token
- `GEMINI_TOKEN`: Gemini API authentication token

## Project Structure

```
DZTnews/
├── config/             # 配置管理
│   ├── __init__.py
│   └── settings.py     # 统一配置（支持环境变量）
├── ingestion/          # RSS feed fetching
│   └── RSSclient.py    # 使用配置和日志
├── preprocessing/      # 数据预处理（原 nlp/）
│   ├── filters.py      # 内容过滤
│   ├── dedupe.py       # 去重
│   └── classify.py     # 分类
├── llms/               # LLM integrations
│   ├── llms.py         # LLMClient with fallback support
│   ├── tokens.py       # Token management
│   ├── build_prompt.py # Prompt builders (refactored)
│   ├── exceptions.py   # 自定义异常类
│   └── __init__.py
├── utils/              # Utility functions
│   ├── deepseek_check.py  # Content safety detection
│   ├── risk.py            # Risk parsing utilities
│   └── logger.py          # 日志配置
├── workflows/          # Orchestration workflows
│   ├── news_pipeline.py      # Ingestion + preprocessing
│   ├── risk_assessment.py    # Risk evaluation
│   ├── summary_generation.py # HTML summary generation
│   └── main_workflow.py      # Complete pipeline (with monitoring)
├── monitoring/         # 监控和指标
│   ├── __init__.py
│   └── metrics.py      # 指标收集器
├── tests/              # 测试
│   ├── __init__.py
│   ├── unit/           # 单元测试
│   │   ├── test_config.py
│   │   ├── test_deepseek_check.py
│   │   └── test_preprocessing.py
│   ├── integration/    # 集成测试
│   └── fixtures/       # 测试数据
├── data/               # Output directory for HTML summaries
├── logs/               # 日志输出目录
├── .gitignore          # Git ignore rules
├── CLAUDE.md           # This file
├── README.md           # User documentation
├── pyproject.toml      # Project dependencies and pytest config
└── uv.lock             # Dependency lock file
```

## Usage Examples

### Basic Usage

```python
from workflows.main_workflow import run_main_workflow

# Run complete pipeline
result = run_main_workflow()

# Access results
print(result["summaries"]["low_risk_summary"])  # HTML content
print(result["summaries"]["meta"]["low_risk_model"])  # "deepseek" or "gemini"
print(result["summaries"]["meta"]["low_risk_fallback"])  # True if fallback occurred
```

### Advanced Usage

```python
from llms.llms import LLMClient

client = LLMClient()

# Request with automatic fallback
response = client.request_with_fallback(
    prompt="Summarize this news...",
    primary="deepseek"
)

if response["is_fallback"]:
    print(f"Fallback triggered: {response['filter_reason']}")
    print(f"Used {response['model_used']} instead")
```

### Manual Workflow Steps

```python
from workflows.news_pipeline import run_news_pipeline
from workflows.risk_assessment import run_risk_assessment_pipeline
from workflows.summary_generation import run_summary_generation_pipeline

# Step 1: Get and preprocess news
classified = run_news_pipeline()

# Step 2: Assess risk
risk_data = run_risk_assessment_pipeline(classified)

# Step 3: Generate summaries
summaries = run_summary_generation_pipeline(risk_data)
```

## Implementation Notes

### Why Two-Stage Risk Management?

1. **Predictive (Gemini Risk Assessment)**: Reduces unnecessary DeepSeek API calls for high-risk content
2. **Reactive (Automatic Fallback)**: Handles false negatives where risk assessment misses sensitive content

This hybrid approach optimizes cost (prefer cheaper DeepSeek) while ensuring reliability (fallback to Gemini).

### Prompt Template Design

Prompts are separated as module-level constants for easy maintenance:
- `RISK_ASSESSMENT_TEMPLATE`: Focuses on DeepSeek-specific failure modes
- `HEADLINE_TEMPLATE`: Emphasizes factual, neutral news summarization

### Error Handling Strategy

- `ContentFilteredException`: Specific exception for content moderation triggers
- `RuntimeError`: General API failures (timeout, connection, etc.)
- `ValueError`: Input validation errors

## Known Limitations

- FreshRSS credentials are hardcoded in `RSSclient.py` (should use environment variables)
- No test suite currently exists
- Risk assessment accuracy depends on Gemini's understanding of DeepSeek's moderation rules
- No retry logic for transient API failures (only content filtering fallback)

## Future Enhancements

- Add configuration file for FreshRSS credentials
- Implement comprehensive test suite
- Add metrics tracking (fallback rate, risk assessment accuracy)
- Support for multiple news categories beyond headlines
- Implement caching for risk assessments
- Add retry logic with exponential backoff for API failures
