#!/usr/bin/env python3
"""
Performance Monitor for NetSentinel
Tracks performance metrics and provides optimization insights
"""

import asyncio
import time
import psutil
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data"""

    name: str
    value: float
    timestamp: float
    component: str
    operation: str
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""

    metric_name: str
    threshold_value: float
    comparison: str  # 'gt', 'lt', 'eq'
    severity: str  # 'warning', 'critical'
    action: Optional[Callable] = None


class PerformanceMonitor:
    """
    Monitors performance metrics across NetSentinel components
    Provides real-time performance tracking and alerting
    """

    def __init__(self, max_metrics: int = 10000, collection_interval: int = 60):
        self.max_metrics = max_metrics
        self.collection_interval = collection_interval
        self.metrics: deque = deque(maxlen=max_metrics)
        self.thresholds: List[PerformanceThreshold] = []
        self.alerts: List[Dict[str, Any]] = []
        self.running = False
        self.collection_task = None
        self.logger = logging.getLogger(f"{__name__}.PerformanceMonitor")

        # Performance counters
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        self.gauges = defaultdict(float)

        # System metrics
        self.system_metrics = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_usage": 0.0,
            "network_io": {"bytes_sent": 0, "bytes_recv": 0},
        }

    async def start(self) -> None:
        """Start performance monitoring"""
        if self.running:
            return

        self.running = True
        self.collection_task = asyncio.create_task(self._collection_loop())
        self.logger.info("Performance monitor started")

    async def stop(self) -> None:
        """Stop performance monitoring"""
        if not self.running:
            return

        self.running = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Performance monitor stopped")

    async def _collection_loop(self) -> None:
        """Main collection loop"""
        while self.running:
            try:
                await self._collect_system_metrics()
                await self._check_thresholds()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                self.logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics"""
        try:
            # CPU usage
            self.system_metrics["cpu_percent"] = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            self.system_metrics["memory_percent"] = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            self.system_metrics["disk_usage"] = (disk.used / disk.total) * 100

            # Network I/O
            network = psutil.net_io_counters()
            self.system_metrics["network_io"] = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
            }

            # Record system metrics
            await self.record_metric(
                "system.cpu_percent", self.system_metrics["cpu_percent"]
            )
            await self.record_metric(
                "system.memory_percent", self.system_metrics["memory_percent"]
            )
            await self.record_metric(
                "system.disk_usage", self.system_metrics["disk_usage"]
            )

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")

    async def record_metric(
        self,
        name: str,
        value: float,
        component: str = "system",
        operation: str = "monitor",
        tags: Dict[str, str] = None,
    ) -> None:
        """Record a performance metric"""
        try:
            metric = PerformanceMetric(
                name=name,
                value=value,
                timestamp=time.time(),
                component=component,
                operation=operation,
                tags=tags or {},
            )

            self.metrics.append(metric)

            # Update counters and gauges
            self.counters[f"{name}.count"] += 1
            self.gauges[name] = value

            # Check thresholds
            await self._check_metric_thresholds(metric)

        except Exception as e:
            self.logger.error(f"Error recording metric {name}: {e}")

    async def record_timing(
        self,
        name: str,
        duration: float,
        component: str = "system",
        operation: str = "timing",
        tags: Dict[str, str] = None,
    ) -> None:
        """Record a timing metric"""
        await self.record_metric(
            f"{name}.duration", duration, component, operation, tags
        )

        # Update timing statistics
        self.timers[name].append(duration)
        if len(self.timers[name]) > 1000:  # Keep only recent timings
            self.timers[name] = self.timers[name][-1000:]

    async def record_counter(
        self,
        name: str,
        increment: int = 1,
        component: str = "system",
        operation: str = "counter",
        tags: Dict[str, str] = None,
    ) -> None:
        """Record a counter metric"""
        self.counters[f"{name}.count"] += increment
        await self.record_metric(
            f"{name}.count", self.counters[f"{name}.count"], component, operation, tags
        )

    def add_threshold(self, threshold: PerformanceThreshold) -> None:
        """Add performance threshold"""
        self.thresholds.append(threshold)
        self.logger.debug(f"Added threshold for {threshold.metric_name}")

    async def _check_thresholds(self) -> None:
        """Check all performance thresholds"""
        for threshold in self.thresholds:
            try:
                await self._check_threshold(threshold)
            except Exception as e:
                self.logger.error(
                    f"Error checking threshold {threshold.metric_name}: {e}"
                )

    async def _check_metric_thresholds(self, metric: PerformanceMetric) -> None:
        """Check thresholds for a specific metric"""
        for threshold in self.thresholds:
            if threshold.metric_name == metric.name:
                await self._check_threshold(threshold, metric)

    async def _check_threshold(
        self, threshold: PerformanceThreshold, metric: PerformanceMetric = None
    ) -> None:
        """Check a specific threshold"""
        # Get current metric value
        if metric:
            value = metric.value
        else:
            value = self.gauges.get(threshold.metric_name, 0.0)

        # Check threshold condition
        exceeded = False
        if threshold.comparison == "gt" and value > threshold.threshold_value:
            exceeded = True
        elif threshold.comparison == "lt" and value < threshold.threshold_value:
            exceeded = True
        elif threshold.comparison == "eq" and value == threshold.threshold_value:
            exceeded = True

        if exceeded:
            await self._handle_threshold_exceeded(threshold, value)

    async def _handle_threshold_exceeded(
        self, threshold: PerformanceThreshold, value: float
    ) -> None:
        """Handle threshold exceeded"""
        alert = {
            "timestamp": time.time(),
            "metric_name": threshold.metric_name,
            "threshold_value": threshold.threshold_value,
            "actual_value": value,
            "severity": threshold.severity,
            "comparison": threshold.comparison,
        }

        self.alerts.append(alert)

        # Execute threshold action if defined
        if threshold.action:
            try:
                if asyncio.iscoroutinefunction(threshold.action):
                    await threshold.action(alert)
                else:
                    threshold.action(alert)
            except Exception as e:
                self.logger.error(f"Error executing threshold action: {e}")

        self.logger.warning(
            f"Performance threshold exceeded: {threshold.metric_name} = {value}"
        )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        if not self.metrics:
            return {"message": "No metrics available"}

        # Calculate summary statistics
        metric_names = set(metric.name for metric in self.metrics)
        summary = {}

        for name in metric_names:
            values = [metric.value for metric in self.metrics if metric.name == name]
            if values:
                summary[name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "latest": values[-1],
                }

        return summary

    def get_timing_statistics(self) -> Dict[str, Any]:
        """Get timing statistics"""
        stats = {}
        for name, timings in self.timers.items():
            if timings:
                stats[name] = {
                    "count": len(timings),
                    "min": min(timings),
                    "max": max(timings),
                    "avg": sum(timings) / len(timings),
                    "p95": self._percentile(timings, 95),
                    "p99": self._percentile(timings, 99),
                }
        return stats

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        return self.system_metrics.copy()

    def get_alerts(self, since: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get performance alerts"""
        if since:
            return [alert for alert in self.alerts if alert["timestamp"] >= since]
        return self.alerts.copy()

    def clear_alerts(self) -> None:
        """Clear performance alerts"""
        self.alerts.clear()
        self.logger.info("Performance alerts cleared")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            "metrics_count": len(self.metrics),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timing_stats": self.get_timing_statistics(),
            "system_metrics": self.get_system_metrics(),
            "alerts_count": len(self.alerts),
            "thresholds_count": len(self.thresholds),
        }


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


async def record_metric(
    name: str,
    value: float,
    component: str = "system",
    operation: str = "monitor",
    tags: Dict[str, str] = None,
) -> None:
    """Record a metric using the global monitor"""
    monitor = get_performance_monitor()
    await monitor.record_metric(name, value, component, operation, tags)


async def record_timing(
    name: str,
    duration: float,
    component: str = "system",
    operation: str = "timing",
    tags: Dict[str, str] = None,
) -> None:
    """Record a timing metric using the global monitor"""
    monitor = get_performance_monitor()
    await monitor.record_timing(name, duration, component, operation, tags)
