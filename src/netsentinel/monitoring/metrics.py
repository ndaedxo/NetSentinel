#!/usr/bin/env python3
"""
Metrics Collection for NetSentinel
Prometheus-compatible metrics collection and export
"""

import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Metric type enumeration"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricLabel:
    """Metric label"""

    name: str
    value: str


@dataclass
class MetricValue:
    """Metric value with labels"""

    labels: List[MetricLabel] = field(default_factory=list)
    value: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class Metric:
    """Metric definition"""

    name: str
    type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    values: List[MetricValue] = field(default_factory=list)
    help_text: str = ""


class MetricsCollector:
    """
    Metrics collector for NetSentinel
    Collects and manages various types of metrics
    """

    def __init__(self, service_name: str = "netsentinel"):
        self.service_name = service_name
        self.metrics: Dict[str, Metric] = {}
        self.metric_lock = threading.Lock()
        self.logger = logging.getLogger(f"{__name__}.MetricsCollector")

        # Initialize default metrics
        self._initialize_default_metrics()

    def _initialize_default_metrics(self) -> None:
        """Initialize default system metrics"""
        # Request metrics
        self.create_counter(
            name="requests_total",
            description="Total number of requests",
            labels=["method", "endpoint", "status_code"],
        )

        self.create_histogram(
            name="request_duration_seconds",
            description="Request duration in seconds",
            labels=["method", "endpoint"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # Event metrics
        self.create_counter(
            name="events_processed_total",
            description="Total number of events processed",
            labels=["event_type", "status"],
        )

        self.create_histogram(
            name="event_processing_duration_seconds",
            description="Event processing duration in seconds",
            labels=["event_type"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )

        # Alert metrics
        self.create_counter(
            name="alerts_created_total",
            description="Total number of alerts created",
            labels=["severity", "source"],
        )

        self.create_gauge(
            name="alerts_active",
            description="Number of active alerts",
            labels=["severity"],
        )

        # System metrics
        self.create_gauge(
            name="system_memory_usage_bytes", description="System memory usage in bytes"
        )

        self.create_gauge(
            name="system_cpu_usage_percent", description="System CPU usage percentage"
        )

    def create_counter(
        self, name: str, description: str, labels: List[str] = None
    ) -> None:
        """Create a counter metric"""
        metric = Metric(
            name=name,
            type=MetricType.COUNTER,
            description=description,
            labels=labels or [],
            help_text=description,
        )

        with self.metric_lock:
            self.metrics[name] = metric

        self.logger.debug(f"Created counter metric: {name}")

    def create_gauge(
        self, name: str, description: str, labels: List[str] = None
    ) -> None:
        """Create a gauge metric"""
        metric = Metric(
            name=name,
            type=MetricType.GAUGE,
            description=description,
            labels=labels or [],
            help_text=description,
        )

        with self.metric_lock:
            self.metrics[name] = metric

        self.logger.debug(f"Created gauge metric: {name}")

    def create_histogram(
        self,
        name: str,
        description: str,
        labels: List[str] = None,
        buckets: List[float] = None,
    ) -> None:
        """Create a histogram metric"""
        metric = Metric(
            name=name,
            type=MetricType.HISTOGRAM,
            description=description,
            labels=labels or [],
            help_text=description,
        )

        # Store buckets as a special label
        if buckets:
            metric.labels.append(f"buckets={','.join(map(str, buckets))}")

        with self.metric_lock:
            self.metrics[name] = metric

        self.logger.debug(f"Created histogram metric: {name}")

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Dict[str, str] = None
    ) -> None:
        """Increment a counter metric"""
        with self.metric_lock:
            if name not in self.metrics:
                self.logger.warning(f"Counter metric {name} not found")
                return

            metric = self.metrics[name]
            if metric.type != MetricType.COUNTER:
                self.logger.warning(f"Metric {name} is not a counter")
                return

            # Create label list
            label_list = [MetricLabel(k, v) for k, v in (labels or {}).items()]

            # Find existing value or create new one
            existing_value = None
            for value_obj in metric.values:
                if self._labels_match(value_obj.labels, label_list):
                    existing_value = value_obj
                    break

            if existing_value:
                existing_value.value += value
            else:
                metric.values.append(MetricValue(labels=label_list, value=value))

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set a gauge metric value"""
        with self.metric_lock:
            if name not in self.metrics:
                self.logger.warning(f"Gauge metric {name} not found")
                return

            metric = self.metrics[name]
            if metric.type != MetricType.GAUGE:
                self.logger.warning(f"Metric {name} is not a gauge")
                return

            # Create label list
            label_list = [MetricLabel(k, v) for k, v in (labels or {}).items()]

            # Find existing value or create new one
            existing_value = None
            for value_obj in metric.values:
                if self._labels_match(value_obj.labels, label_list):
                    existing_value = value_obj
                    break

            if existing_value:
                existing_value.value = value
                existing_value.timestamp = time.time()
            else:
                metric.values.append(MetricValue(labels=label_list, value=value))

    def observe_histogram(
        self, name: str, value: float, labels: Dict[str, str] = None
    ) -> None:
        """Observe a histogram metric value"""
        with self.metric_lock:
            if name not in self.metrics:
                self.logger.warning(f"Histogram metric {name} not found")
                return

            metric = self.metrics[name]
            if metric.type != MetricType.HISTOGRAM:
                self.logger.warning(f"Metric {name} is not a histogram")
                return

            # Create label list
            label_list = [MetricLabel(k, v) for k, v in (labels or {}).items()]

            # Find existing value or create new one
            existing_value = None
            for value_obj in metric.values:
                if self._labels_match(value_obj.labels, label_list):
                    existing_value = value_obj
                    break

            if existing_value:
                # For histogram, we might want to track multiple observations
                # For simplicity, we'll just update the value
                existing_value.value = value
                existing_value.timestamp = time.time()
            else:
                metric.values.append(MetricValue(labels=label_list, value=value))

    def _labels_match(
        self, labels1: List[MetricLabel], labels2: List[MetricLabel]
    ) -> bool:
        """Check if two label lists match"""
        if len(labels1) != len(labels2):
            return False

        # Sort by name for comparison
        sorted1 = sorted(labels1, key=lambda x: x.name)
        sorted2 = sorted(labels2, key=lambda x: x.name)

        return all(
            l1.name == l2.name and l1.value == l2.value
            for l1, l2 in zip(sorted1, sorted2)
        )

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name"""
        return self.metrics.get(name)

    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all metrics"""
        return self.metrics.copy()

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []

        with self.metric_lock:
            for metric_name, metric in self.metrics.items():
                # Add help text
                lines.append(f"# HELP {metric_name} {metric.help_text}")
                lines.append(f"# TYPE {metric_name} {metric.type.value}")

                # Add metric values
                for value in metric.values:
                    if value.labels:
                        label_str = ",".join(
                            [f'{label.name}="{label.value}"' for label in value.labels]
                        )
                        lines.append(f"{metric_name}{{{label_str}}} {value.value}")
                    else:
                        lines.append(f"{metric_name} {value.value}")

                lines.append("")  # Empty line between metrics

        return "\n".join(lines)

    def get_metric_statistics(self) -> Dict[str, Any]:
        """Get metric statistics"""
        with self.metric_lock:
            stats = {
                "total_metrics": len(self.metrics),
                "metrics_by_type": {},
                "total_values": 0,
            }

            for metric in self.metrics.values():
                metric_type = metric.type.value
                stats["metrics_by_type"][metric_type] = (
                    stats["metrics_by_type"].get(metric_type, 0) + 1
                )
                stats["total_values"] += len(metric.values)

            return stats


class PrometheusMetrics:
    """
    Prometheus-compatible metrics exporter
    """

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(f"{__name__}.PrometheusMetrics")

    def get_metrics_endpoint(self) -> str:
        """Get metrics endpoint content"""
        return self.metrics_collector.export_prometheus()

    def register_custom_metrics(self) -> None:
        """Register custom NetSentinel metrics"""
        # Threat detection metrics
        self.metrics_collector.create_counter(
            name="threats_detected_total",
            description="Total number of threats detected",
            labels=["threat_type", "severity", "source"],
        )

        self.metrics_collector.create_histogram(
            name="threat_detection_duration_seconds",
            description="Threat detection processing time",
            labels=["detection_method"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )

        # Firewall metrics
        self.metrics_collector.create_counter(
            name="firewall_rules_applied_total",
            description="Total number of firewall rules applied",
            labels=["rule_type", "action"],
        )

        self.metrics_collector.create_gauge(
            name="firewall_rules_active",
            description="Number of active firewall rules",
            labels=["rule_type"],
        )

        # ML model metrics
        self.metrics_collector.create_histogram(
            name="ml_model_inference_duration_seconds",
            description="ML model inference time",
            labels=["model_name", "model_version"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )

        self.metrics_collector.create_gauge(
            name="ml_model_accuracy",
            description="ML model accuracy score",
            labels=["model_name", "model_version"],
        )

        # Database metrics
        self.metrics_collector.create_counter(
            name="database_queries_total",
            description="Total number of database queries",
            labels=["database", "operation", "status"],
        )

        self.metrics_collector.create_histogram(
            name="database_query_duration_seconds",
            description="Database query duration",
            labels=["database", "operation"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
        )

        # Cache metrics
        self.metrics_collector.create_counter(
            name="cache_operations_total",
            description="Total number of cache operations",
            labels=["cache_name", "operation", "status"],
        )

        self.metrics_collector.create_gauge(
            name="cache_hit_ratio", description="Cache hit ratio", labels=["cache_name"]
        )

        self.logger.info("Custom NetSentinel metrics registered")


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(service_name: str = None) -> MetricsCollector:
    """Get the global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(service_name or "netsentinel")
    return _metrics_collector


def track_function_metrics(func_name: str = None):
    """Decorator for tracking function metrics"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Track success
                metrics.increment_counter(
                    "function_calls_total",
                    labels={
                        "function": func_name or func.__name__,
                        "status": "success",
                    },
                )
                metrics.observe_histogram(
                    "function_duration_seconds",
                    duration,
                    labels={"function": func_name or func.__name__},
                )

                return result
            except Exception as e:
                duration = time.time() - start_time

                # Track error
                metrics.increment_counter(
                    "function_calls_total",
                    labels={"function": func_name or func.__name__, "status": "error"},
                )
                metrics.observe_histogram(
                    "function_duration_seconds",
                    duration,
                    labels={"function": func_name or func.__name__},
                )

                raise

        return wrapper

    return decorator
