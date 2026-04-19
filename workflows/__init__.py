"""
工作流模块
"""

from .news_pipeline import run_news_pipeline
from .risk_assessment import run_risk_assessment_pipeline
from .summary_generation import run_summary_generation_pipeline

__all__ = [
    "run_news_pipeline",
    "run_risk_assessment_pipeline",
    "run_summary_generation_pipeline",
    "run_main_workflow"
]


def __getattr__(name):
    """懒加载入口工作流，避免 `python -m workflows.main_workflow` 触发重复导入警告。"""
    if name == "run_main_workflow":
        from .main_workflow import run_main_workflow

        return run_main_workflow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
