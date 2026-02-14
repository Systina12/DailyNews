"""
监控和指标收集模块
"""

from datetime import datetime
from typing import Dict, Any
from collections import defaultdict
from utils.logger import get_logger

logger = get_logger("monitoring")


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.start_time = datetime.now()

    def record_event(self, event_type: str, data: Dict[str, Any] = None):
        """
        记录事件

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data or {}
        }
        self.metrics[event_type].append(event)
        logger.debug(f"记录事件: {event_type}")

    def increment_counter(self, counter_name: str, value: int = 1):
        """
        增加计数器

        Args:
            counter_name: 计数器名称
            value: 增加的值
        """
        self.counters[counter_name] += value
        logger.debug(f"计数器 {counter_name}: {self.counters[counter_name]}")

    def record_fallback(self, reason: str, primary_model: str, fallback_model: str):
        """
        记录 fallback 事件

        Args:
            reason: fallback 原因
            primary_model: 主模型
            fallback_model: fallback 模型
        """
        self.record_event("fallback", {
            "reason": reason,
            "primary_model": primary_model,
            "fallback_model": fallback_model
        })
        self.increment_counter("fallback_total")
        self.increment_counter(f"fallback_{primary_model}_to_{fallback_model}")

    def record_api_call(self, model: str, success: bool, duration: float = None):
        """
        记录 API 调用

        Args:
            model: 模型名称
            success: 是否成功
            duration: 调用时长（秒）
        """
        self.record_event("api_call", {
            "model": model,
            "success": success,
            "duration": duration
        })
        self.increment_counter(f"api_call_{model}_total")
        if success:
            self.increment_counter(f"api_call_{model}_success")
        else:
            self.increment_counter(f"api_call_{model}_failure")

    def record_risk_assessment(self, total: int, low: int, high: int):
        """
        记录风险评估结果

        Args:
            total: 总数
            low: 低风险数量
            high: 高风险数量
        """
        self.record_event("risk_assessment", {
            "total": total,
            "low": low,
            "high": high,
            "low_ratio": low / total if total > 0 else 0,
            "high_ratio": high / total if total > 0 else 0
        })

    def get_summary(self) -> Dict[str, Any]:
        """
        获取指标摘要

        Returns:
            dict: 指标摘要
        """
        runtime = (datetime.now() - self.start_time).total_seconds()

        fallback_events = self.metrics.get("fallback", [])
        fallback_rate = (
            len(fallback_events) / self.counters.get("api_call_deepseek_total", 1)
            if self.counters.get("api_call_deepseek_total", 0) > 0
            else 0
        )

        return {
            "runtime_seconds": runtime,
            "counters": dict(self.counters),
            "fallback_rate": fallback_rate,
            "total_events": sum(len(events) for events in self.metrics.values()),
            "event_types": list(self.metrics.keys())
        }

    def print_summary(self):
        """打印指标摘要"""
        summary = self.get_summary()

        logger.info("=" * 60)
        logger.info("指标摘要")
        logger.info("=" * 60)
        logger.info(f"运行时长: {summary['runtime_seconds']:.2f} 秒")
        logger.info(f"总事件数: {summary['total_events']}")
        logger.info(f"Fallback 率: {summary['fallback_rate']:.2%}")
        logger.info("\n计数器:")
        for name, value in sorted(summary['counters'].items()):
            logger.info(f"  {name}: {value}")
        logger.info("=" * 60)


# 全局指标收集器实例
metrics = MetricsCollector()
