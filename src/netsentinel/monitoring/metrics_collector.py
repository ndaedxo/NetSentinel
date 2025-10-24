#!/usr/bin/env python3
"""
Prometheus Metrics Collector for NetSentinel
Implements comprehensive metrics collection with proper labeling and cardinality control
Designed for maintainability and preventing code debt
"""

import time
import threading
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, Counter
import asyncio

# Prometheus imports
try:
    from prometheus_client import (
        Counter as PromCounter,
        Histogram as PromHistogram,
        Gauge as PromGauge,
        Summary as PromSummary,
        Info as PromInfo,
        start_http_server,
        CollectorRegistry,
        REGISTRY,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Fallback implementations
    class PromCounter:
        def __init__(self, *args, **kwargs):
            self._value = 0

        def inc(self, *args, **kwargs):
            self._value += 1

        def labels(self, **kwargs):
            return self

    class PromHistogram:
        def __init__(self, *args, **kwargs):
            self._value = 0

        def observe(self, *args, **kwargs):
            pass

        def labels(self, **kwargs):
            return self

    class PromGauge:
        def __init__(self, *args, **kwargs):
            self._value = 0

        def set(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

        def dec(self, *args, **kwargs):
            pass

        def labels(self, **kwargs):
            return self

    class PromSummary:
        def __init__(self, *args, **kwargs):
            self._value = 0

        def observe(self, *args, **kwargs):
            pass

        def labels(self, **kwargs):
            return self

    class PromInfo:
        def __init__(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

    def start_http_server(*args, **kwargs):
        pass

    class CollectorRegistry:
        pass

    REGISTRY = CollectorRegistry()

from ..core.exceptions import NetSentinelException
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("metrics_collector", level="INFO")
structured_logger = get_structured_logger("metrics_collector")


class MetricType(Enum):
    """Metric type enumeration"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    INFO = "info"


@dataclass
class MetricLabel:
    """Metric label"""

    name: str
    value: str

    def __post_init__(self):
        # Validate label name
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Label name must be a non-empty string")

        # Validate label value
        if not isinstance(self.value, str):
            self.value = str(self.value)


@dataclass
class MetricConfig:
    """Metric configuration"""

    name: str
    description: str
    metric_type: MetricType
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms
    quantiles: Optional[List[float]] = None  # For summaries
    max_cardinality: int = 1000  # Prevent cardinality explosion

    def __post_init__(self):
        # Validate metric name
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Metric name must be a non-empty string")

        # Validate description
        if not self.description or not isinstance(self.description, str):
            raise ValueError("Metric description must be a non-empty string")


class MetricCollector:
    """Base metric collector"""

    def __init__(self, config: MetricConfig):
        self.config = config
        self._lock = threading.RLock()
        self._cardinality_tracker: Dict[str, int] = defaultdict(int)
        self._created_at = time.time()

        # Create Prometheus metric
        self._prom_metric = self._create_prometheus_metric()

        logger.info(f"Created metric collector: {config.name}")

    def _create_prometheus_metric(self):
        """Create Prometheus metric"""
        if not PROMETHEUS_AVAILABLE:
            return None

        try:
            if self.config.metric_type == MetricType.COUNTER:
                return PromCounter(
                    self.config.name,
                    self.config.description,
                    self.config.labels,
                    registry=REGISTRY,
                )
            elif self.config.metric_type == MetricType.GAUGE:
                return PromGauge(
                    self.config.name,
                    self.config.description,
                    self.config.labels,
                    registry=REGISTRY,
                )
            elif self.config.metric_type == MetricType.HISTOGRAM:
                return PromHistogram(
                    self.config.name,
                    self.config.description,
                    self.config.labels,
                    buckets=self.config.buckets,
                    registry=REGISTRY,
                )
            elif self.config.metric_type == MetricType.SUMMARY:
                return PromSummary(
                    self.config.name,
                    self.config.description,
                    self.config.labels,
                    registry=REGISTRY,
                )
            elif self.config.metric_type == MetricType.INFO:
                return PromInfo(
                    self.config.name, self.config.description, registry=REGISTRY
                )
        except Exception as e:
            logger.error(f"Failed to create Prometheus metric {self.config.name}: {e}")
            return None

    def _check_cardinality(self, label_values: Dict[str, str]) -> bool:
        """Check if adding this label combination would exceed cardinality limit"""
        with self._lock:
            # Create cardinality key
            cardinality_key = "|".join(
                f"{k}={v}" for k, v in sorted(label_values.items())
            )

            # Check if we're at the limit
            if len(self._cardinality_tracker) >= self.config.max_cardinality:
                if cardinality_key not in self._cardinality_tracker:
                    logger.warning(
                        f"Cardinality limit reached for metric {self.config.name}"
                    )
                    return False

            # Track cardinality
            self._cardinality_tracker[cardinality_key] += 1
            return True

    def _validate_labels(self, label_values: Dict[str, str]) -> bool:
        """Validate label values"""
        # Check if all required labels are provided
        for label in self.config.labels:
            if label not in label_values:
                logger.warning(
                    f"Missing required label '{label}' for metric {self.config.name}"
                )
                return False

        # Check for extra labels
        for label in label_values:
            if label not in self.config.labels:
                logger.warning(f"Extra label '{label}' for metric {self.config.name}")
                return False

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get collector statistics"""
        with self._lock:
            return {
                "name": self.config.name,
                "type": self.config.metric_type.value,
                "cardinality": len(self._cardinality_tracker),
                "max_cardinality": self.config.max_cardinality,
                "created_at": self._created_at,
                "labels": self.config.labels,
            }


class CounterCollector(MetricCollector):
    """Counter metric collector"""

    def __init__(self, config: MetricConfig):
        super().__init__(config)
        self._counters: Dict[str, float] = defaultdict(float)

    def inc(self, value: float = 1.0, **label_values: str) -> None:
        """Increment counter"""
        if not self._validate_labels(label_values):
            return

        if not self._check_cardinality(label_values):
            return

        try:
            with self._lock:
                # Update internal counter
                counter_key = "|".join(
                    f"{k}={v}" for k, v in sorted(label_values.items())
                )
                self._counters[counter_key] += value

                # Update Prometheus metric
                if self._prom_metric:
                    self._prom_metric.labels(**label_values).inc(value)

        except Exception as e:
            logger.error(f"Failed to increment counter {self.config.name}: {e}")

    def get_value(self, **label_values: str) -> float:
        """Get counter value"""
        with self._lock:
            counter_key = "|".join(f"{k}={v}" for k, v in sorted(label_values.items()))
            return self._counters.get(counter_key, 0.0)


class GaugeCollector(MetricCollector):
    """Gauge metric collector"""

    def __init__(self, config: MetricConfig):
        super().__init__(config)
        self._gauges: Dict[str, float] = defaultdict(float)

    def set(self, value: float, **label_values: str) -> None:
        """Set gauge value"""
        if not self._validate_labels(label_values):
            return

        if not self._check_cardinality(label_values):
            return

        try:
            with self._lock:
                # Update internal gauge
                gauge_key = "|".join(
                    f"{k}={v}" for k, v in sorted(label_values.items())
                )
                self._gauges[gauge_key] = value

                # Update Prometheus metric
                if self._prom_metric:
                    self._prom_metric.labels(**label_values).set(value)

        except Exception as e:
            logger.error(f"Failed to set gauge {self.config.name}: {e}")

    def inc(self, value: float = 1.0, **label_values: str) -> None:
        """Increment gauge"""
        if not self._validate_labels(label_values):
            return

        if not self._check_cardinality(label_values):
            return

        try:
            with self._lock:
                gauge_key = "|".join(
                    f"{k}={v}" for k, v in sorted(label_values.items())
                )
                self._gauges[gauge_key] += value

                if self._prom_metric:
                    self._prom_metric.labels(**label_values).inc(value)

        except Exception as e:
            logger.error(f"Failed to increment gauge {self.config.name}: {e}")

    def dec(self, value: float = 1.0, **label_values: str) -> None:
        """Decrement gauge"""
        if not self._validate_labels(label_values):
            return

        if not self._check_cardinality(label_values):
            return

        try:
            with self._lock:
                gauge_key = "|".join(
                    f"{k}={v}" for k, v in sorted(label_values.items())
                )
                self._gauges[gauge_key] -= value

                if self._prom_metric:
                    self._prom_metric.labels(**label_values).dec(value)

        except Exception as e:
            logger.error(f"Failed to decrement gauge {self.config.name}: {e}")

    def get_value(self, **label_values: str) -> float:
        """Get gauge value"""
        with self._lock:
            gauge_key = "|".join(f"{k}={v}" for k, v in sorted(label_values.items()))
            return self._gauges.get(gauge_key, 0.0)


class HistogramCollector(MetricCollector):
    """Histogram metric collector"""

    def __init__(self, config: MetricConfig):
        super().__init__(config)
        self._histograms: Dict[str, List[float]] = defaultdict(list)

    def observe(self, value: float, **label_values: str) -> None:
        """Observe value in histogram"""
        if not self._validate_labels(label_values):
            return

        if not self._check_cardinality(label_values):
            return

        try:
            with self._lock:
                # Update internal histogram
                histogram_key = "|".join(
                    f"{k}={v}" for k, v in sorted(label_values.items())
                )
                self._histograms[histogram_key].append(value)

                # Update Prometheus metric
                if self._prom_metric:
                    self._prom_metric.labels(**label_values).observe(value)

        except Exception as e:
            logger.error(f"Failed to observe histogram {self.config.name}: {e}")

    def get_statistics(self, **label_values: str) -> Dict[str, float]:
        """Get histogram statistics"""
        with self._lock:
            histogram_key = "|".join(
                f"{k}={v}" for k, v in sorted(label_values.items())
            )
            values = self._histograms.get(histogram_key, [])

            if not values:
                return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
            }


class SummaryCollector(MetricCollector):
    """Summary metric collector"""

    def __init__(self, config: MetricConfig):
        super().__init__(config)
        self._summaries: Dict[str, List[float]] = defaultdict(list)

    def observe(self, value: float, **label_values: str) -> None:
        """Observe value in summary"""
        if not self._validate_labels(label_values):
            return

        if not self._check_cardinality(label_values):
            return

        try:
            with self._lock:
                # Update internal summary
                summary_key = "|".join(
                    f"{k}={v}" for k, v in sorted(label_values.items())
                )
                self._summaries[summary_key].append(value)

                # Update Prometheus metric
                if self._prom_metric:
                    self._prom_metric.labels(**label_values).observe(value)

        except Exception as e:
            logger.error(f"Failed to observe summary {self.config.name}: {e}")

    def get_statistics(self, **label_values: str) -> Dict[str, float]:
        """Get summary statistics"""
        with self._lock:
            summary_key = "|".join(f"{k}={v}" for k, v in sorted(label_values.items()))
            values = self._summaries.get(summary_key, [])

            if not values:
                return {"count": 0, "sum": 0, "avg": 0}

            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
            }


class InfoCollector(MetricCollector):
    """Info metric collector"""

    def __init__(self, config: MetricConfig):
        super().__init__(config)
        self._info: Dict[str, str] = {}

    def info(self, **label_values: str) -> None:
        """Set info values"""
        try:
            with self._lock:
                self._info.update(label_values)

                # Update Prometheus metric
                if self._prom_metric:
                    self._prom_metric.info(label_values)

        except Exception as e:
            logger.error(f"Failed to set info {self.config.name}: {e}")

    def get_info(self) -> Dict[str, str]:
        """Get info values"""
        with self._lock:
            return self._info.copy()


class MetricsCollector:
    """Centralized metrics collector"""

    def __init__(self):
        self.collectors: Dict[str, MetricCollector] = {}
        self._lock = threading.RLock()
        self._http_server_started = False

    def create_counter(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        max_cardinality: int = 1000,
    ) -> CounterCollector:
        """Create counter metric"""
        config = MetricConfig(
            name=name,
            description=description,
            metric_type=MetricType.COUNTER,
            labels=labels or [],
            max_cardinality=max_cardinality,
        )

        with self._lock:
            if name in self.collectors:
                raise ValueError(f"Metric '{name}' already exists")

            collector = CounterCollector(config)
            self.collectors[name] = collector

            logger.info(f"Created counter metric: {name}")
            return collector

    def create_gauge(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        max_cardinality: int = 1000,
    ) -> GaugeCollector:
        """Create gauge metric"""
        config = MetricConfig(
            name=name,
            description=description,
            metric_type=MetricType.GAUGE,
            labels=labels or [],
            max_cardinality=max_cardinality,
        )

        with self._lock:
            if name in self.collectors:
                raise ValueError(f"Metric '{name}' already exists")

            collector = GaugeCollector(config)
            self.collectors[name] = collector

            logger.info(f"Created gauge metric: {name}")
            return collector

    def create_histogram(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None,
        max_cardinality: int = 1000,
    ) -> HistogramCollector:
        """Create histogram metric"""
        config = MetricConfig(
            name=name,
            description=description,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or [],
            buckets=buckets,
            max_cardinality=max_cardinality,
        )

        with self._lock:
            if name in self.collectors:
                raise ValueError(f"Metric '{name}' already exists")

            collector = HistogramCollector(config)
            self.collectors[name] = collector

            logger.info(f"Created histogram metric: {name}")
            return collector

    def create_summary(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        quantiles: Optional[List[float]] = None,
        max_cardinality: int = 1000,
    ) -> SummaryCollector:
        """Create summary metric"""
        config = MetricConfig(
            name=name,
            description=description,
            metric_type=MetricType.SUMMARY,
            labels=labels or [],
            quantiles=quantiles,
            max_cardinality=max_cardinality,
        )

        with self._lock:
            if name in self.collectors:
                raise ValueError(f"Metric '{name}' already exists")

            collector = SummaryCollector(config)
            self.collectors[name] = collector

            logger.info(f"Created summary metric: {name}")
            return collector

    def create_info(
        self, name: str, description: str, max_cardinality: int = 1000
    ) -> InfoCollector:
        """Create info metric"""
        config = MetricConfig(
            name=name,
            description=description,
            metric_type=MetricType.INFO,
            max_cardinality=max_cardinality,
        )

        with self._lock:
            if name in self.collectors:
                raise ValueError(f"Metric '{name}' already exists")

            collector = InfoCollector(config)
            self.collectors[name] = collector

            logger.info(f"Created info metric: {name}")
            return collector

    def get_collector(self, name: str) -> Optional[MetricCollector]:
        """Get metric collector"""
        with self._lock:
            return self.collectors.get(name)

    def start_http_server(self, port: int = 8000) -> None:
        """Start Prometheus HTTP server"""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus not available, cannot start HTTP server")
            return

        if self._http_server_started:
            logger.warning("HTTP server already started")
            return

        try:
            start_http_server(port, registry=REGISTRY)
            self._http_server_started = True
            logger.info(f"Started Prometheus HTTP server on port {port}")
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")

    def get_all_statistics(self) -> Dict[str, Any]:
        """Get statistics for all collectors"""
        with self._lock:
            return {
                name: collector.get_statistics()
                for name, collector in self.collectors.items()
            }

    def cleanup_old_metrics(self, max_age_seconds: int = 3600) -> None:
        """Cleanup old metrics to prevent memory leaks"""
        with self._lock:
            current_time = time.time()
            for collector in self.collectors.values():
                # This would be implemented based on specific collector type
                pass


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
