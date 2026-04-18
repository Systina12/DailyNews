# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

DZTnews is a Python-based intelligent news aggregation and summarization system that fetches RSS feeds from FreshRSS, filters/deduplicates content, assesses DeepSeek content safety risk using Gemini, and generates HTML news summaries using DeepSeek (with automatic Gemini fallback).

## Environment Setup

```bash
uv sync
.venv\Scripts\activate  # Windows / source .venv/bin/activate on Linux/Mac
```

## Running

```bash
# Full pipeline
python workflows/main_workflow.py

# Individual stages
python -c "from workflows.news_pipeline import run_news_pipeline; run_news_pipeline()"
python -c "from workflows.risk_assessment import run_risk_assessment_pipeline; run_risk_assessment_pipeline(data)"
python -c "from workflows.summary_generation import run_summary_generation_pipeline; run_summary_generation_pipeline(data)"
```

## Architecture

### Data Flow

```
FreshRSS → Filter → Dedupe → Classify → Risk Assessment → Summary Generation
                                              ↓                    ↓
                                           Gemini          DeepSeek (→ Gemini fallback)
```

### Layers

**`ingestion/RSSclient.py`** — Fetches last 24h news from FreshRSS via Google Reader API. Session-based auth.

**`preprocessing/`** — Three-stage pipeline:
- `filters.py`: Removes Russia-labeled items (`filter_ru()`), filters by risk level
- `dedupe.py`: Deduplicates by normalized title (strips brackets, 突发 prefix)
- `classify.py`: Removes entertainment/sports; returns `{section: "headline", items: [...]}`

**`config/settings.py`** — `Settings` class backed by env vars; `settings` global instance. Covers FreshRSS credentials, LLM endpoints, timeouts, paths.

**`llms/`** — Core LLM integration:
- `llms.py`: `LLMClient` with `request_deepseek()` (OpenAI-compatible API), `request_gemini()` (google.genai SDK), and `request_with_fallback()` returning `{content, model_used, is_fallback, filter_reason}`
- `build_prompt.py`: `build_ds_risk_prompt()` and `build_headline_prompt(risk_filter="low"|"high")` using module-level template constants
- `exceptions.py`: `ContentFilteredException` (HTTP 400 / empty response from DeepSeek), plus `LLMAPIError` subclasses

**`utils/`** — `deepseek_check.py` detects content filtering; `risk.py` parses Gemini's `编号:low/high` format and annotates items with `ds_risk`; `logger.py` provides `get_logger(name)`.

**`monitoring/metrics.py`** — `MetricsCollector` tracks API calls, fallbacks, risk distribution. `metrics.print_summary()` called at end of main workflow.

**`workflows/`** — Orchestration:
- `news_pipeline.py` → `risk_assessment.py` → `summary_generation.py` → `main_workflow.py`
- Low-risk items: DeepSeek with Gemini fallback; high-risk items: Gemini directly
- Output: HTML files saved to `data/` with timestamps

### Two-Tier Risk Strategy

1. **Predictive**: Gemini pre-classifies items likely to trigger DeepSeek moderation (`ds_risk: high`)
2. **Reactive**: `ContentFilteredException` triggers automatic Gemini fallback for false negatives

This optimizes cost (DeepSeek preferred) while guaranteeing output.

## Testing

```bash
pytest                          # all tests
pytest tests/unit/test_config.py  # single file
pytest -v                       # verbose
```

Tests live in `tests/unit/`. Config in `pyproject.toml`.

## Environment Variables

- `DEEPSEEK_TOKEN`
- `GEMINI_TOKEN`

## Known Limitations

- FreshRSS credentials are hardcoded in `ingestion/RSSclient.py`
- No retry logic for transient API failures (only content filtering fallback)
