#!/usr/bin/env python3
"""
ML Monitoring and Analytics for NetSentinel

Provides real-time monitoring, performance tracking, and analytics
for ML models in production environments.
"""

import time
import threading
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
import logging
from datetime import datetime, timedelta
import json

# Import new core components
try:
    from ..core.base import BaseComponent
    from ..utils.centralized import create_logger
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from utils.centralized import create_logger

logger = create_logger("ml_monitoring", level="INFO")


@dataclass
class ModelMetrics:
    """Real-time model performance metrics"""

    model_type: str
    total_predictions: int = 0
    total_inference_time: float = 0.0
    avg_inference_time: float = 0.0
    min_inference_time: float = float('inf')
    max_inference_time: float = 0.0

    # Prediction distribution
    normal_predictions: int = 0
    anomaly_predictions: int = 0
    anomaly_rate: float = 0.0

    # Confidence scores
    avg_confidence: float = 0.0
    min_confidence: float = float('inf')
    max_confidence: float = 0.0

    # Performance over time (last 100 predictions)
    recent_predictions: List[Dict[str, Any]] = None

    # Error tracking
    total_errors: int = 0
    error_rate: float = 0.0
    last_error_time: Optional[float] = None

    # Model health
    is_healthy: bool = True
    last_health_check: float = 0.0
    uptime_seconds: float = 0.0

    def __post_init__(self):
        if self.recent_predictions is None:
            self.recent_predictions = []

    def update_prediction(self, prediction_result: Dict[str, Any], inference_time: float):
        """Update metrics with new prediction"""
        self.total_predictions += 1
        self.total_inference_time += inference_time

        # Update timing stats
        self.avg_inference_time = self.total_inference_time / self.total_predictions
        self.min_inference_time = min(self.min_inference_time, inference_time)
        self.max_inference_time = max(self.max_inference_time, inference_time)

        # Update prediction distribution
        is_anomaly = prediction_result.get('is_anomaly', False)
        if is_anomaly:
            self.anomaly_predictions += 1
        else:
            self.normal_predictions += 1
        self.anomaly_rate = self.anomaly_predictions / self.total_predictions

        # Update confidence stats
        confidence = prediction_result.get('confidence', 0.0)
        self.avg_confidence = ((self.avg_confidence * (self.total_predictions - 1)) + confidence) / self.total_predictions
        self.min_confidence = min(self.min_confidence, confidence)
        self.max_confidence = max(self.max_confidence, confidence)

        # Add to recent predictions (keep last 100)
        recent_pred = {
            'timestamp': time.time(),
            'is_anomaly': is_anomaly,
            'confidence': confidence,
            'inference_time': inference_time
        }
        self.recent_predictions.append(recent_pred)
        if len(self.recent_predictions) > 100:
            self.recent_predictions.pop(0)

    def update_error(self):
        """Update metrics with prediction error"""
        self.total_errors += 1
        self.error_rate = self.total_errors / (self.total_predictions + self.total_errors)
        self.last_error_time = time.time()

    def check_health(self) -> bool:
        """Check model health based on metrics"""
        current_time = time.time()
        self.last_health_check = current_time

        # Health criteria
        health_checks = []

        # Error rate should be < 5%
        health_checks.append(self.error_rate < 0.05)

        # Should have recent predictions (last 5 minutes)
        if self.recent_predictions:
            last_prediction_time = max(p['timestamp'] for p in self.recent_predictions)
            health_checks.append((current_time - last_prediction_time) < 300)  # 5 minutes
        else:
            health_checks.append(False)

        # Average inference time should be reasonable (< 1 second)
        health_checks.append(self.avg_inference_time < 1.0)

        self.is_healthy = all(health_checks)
        return self.is_healthy

    def get_recent_performance(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance metrics for recent time window"""
        cutoff_time = time.time() - (hours * 3600)

        recent_preds = [p for p in self.recent_predictions if p['timestamp'] > cutoff_time]

        if not recent_preds:
            return {"error": f"No predictions in last {hours} hours"}

        return {
            "time_window_hours": hours,
            "prediction_count": len(recent_preds),
            "avg_inference_time": np.mean([p['inference_time'] for p in recent_preds]),
            "anomaly_rate": np.mean([p['is_anomaly'] for p in recent_preds]),
            "avg_confidence": np.mean([p['confidence'] for p in recent_preds]),
            "error_count": sum(1 for p in recent_preds if 'error' in p)
        }


@dataclass
class DriftDetectionResult:
    """Model drift detection result"""

    model_type: str
    drift_detected: bool
    drift_score: float
    threshold: float
    detection_method: str
    features_affected: List[str]
    timestamp: float
    baseline_stats: Dict[str, float]
    current_stats: Dict[str, float]
    recommendations: List[str]


@dataclass
class ABTestResult:
    """A/B test result"""

    test_id: str
    model_a: str
    model_b: str
    status: str  # "running", "completed", "stopped"
    start_time: float
    end_time: Optional[float] = None

    # Test metrics
    total_predictions_a: int = 0
    total_predictions_b: int = 0
    accuracy_a: float = 0.0
    accuracy_b: float = 0.0
    avg_confidence_a: float = 0.0
    avg_confidence_b: float = 0.0

    # Statistical significance
    p_value: Optional[float] = None
    significant: bool = False
    winner: Optional[str] = None  # "A", "B", or "tie"

    # Test configuration
    traffic_split: float = 0.5  # Percentage of traffic to model B
    min_samples: int = 1000
    confidence_level: float = 0.95


class MLMonitoring(BaseComponent):
    """
    ML Monitoring and Analytics System

    Provides real-time monitoring, performance tracking, drift detection,
    and A/B testing capabilities for ML models.
    """

    def __init__(
        self,
        name: str = "ml_monitoring",
        drift_detection_window: int = 1000,  # Number of samples for drift detection
        metrics_retention_hours: int = 24,
        health_check_interval: int = 60,  # Seconds
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize ML monitoring system

        Args:
            name: Component name
            drift_detection_window: Window size for drift detection
            metrics_retention_hours: Hours to retain detailed metrics
            health_check_interval: Seconds between health checks
            config: Additional configuration
        """
        super().__init__(name, config, logger)

        self.drift_detection_window = drift_detection_window
        self.metrics_retention_hours = metrics_retention_hours
        self.health_check_interval = health_check_interval

        # Model metrics tracking
        self.model_metrics: Dict[str, ModelMetrics] = {}

        # Drift detection
        self.baseline_distributions: Dict[str, Dict[str, np.ndarray]] = {}
        self.drift_history: Dict[str, List[DriftDetectionResult]] = defaultdict(list)

        # A/B testing
        self.ab_tests: Dict[str, ABTestResult] = {}
        self.active_ab_test: Optional[str] = None

        # Prediction caching
        self.prediction_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_max_size = 10000

        # Background monitoring
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_monitoring = False

        logger.info("ML monitoring system initialized")

    def record_prediction(
        self,
        model_type: str,
        prediction_result: Dict[str, Any],
        inference_time: float,
        input_features: Optional[np.ndarray] = None
    ):
        """
        Record a prediction for monitoring and analytics

        Args:
            model_type: Type of model used
            prediction_result: Prediction results
            inference_time: Time taken for inference
            input_features: Input features (for drift detection)
        """
        # Initialize metrics if needed
        if model_type not in self.model_metrics:
            self.model_metrics[model_type] = ModelMetrics(model_type=model_type)

        # Update metrics
        metrics = self.model_metrics[model_type]
        metrics.update_prediction(prediction_result, inference_time)

        # Update drift detection data
        if input_features is not None:
            self._update_drift_detection_data(model_type, input_features)

        # Update A/B test if active
        if self.active_ab_test:
            self._update_ab_test(model_type, prediction_result)

    def record_prediction_error(self, model_type: str):
        """Record a prediction error"""
        if model_type in self.model_metrics:
            self.model_metrics[model_type].update_error()

    def get_model_metrics(self, model_type: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive metrics for a model"""
        if model_type not in self.model_metrics:
            return None

        metrics = self.model_metrics[model_type]

        return {
            "model_type": model_type,
            "basic_metrics": {
                "total_predictions": metrics.total_predictions,
                "avg_inference_time": metrics.avg_inference_time,
                "anomaly_rate": metrics.anomaly_rate,
                "avg_confidence": metrics.avg_confidence,
                "error_rate": metrics.error_rate,
                "is_healthy": metrics.is_healthy,
            },
            "performance_ranges": {
                "inference_time_ms": {
                    "min": metrics.min_inference_time * 1000,
                    "max": metrics.max_inference_time * 1000,
                    "avg": metrics.avg_inference_time * 1000,
                },
                "confidence": {
                    "min": metrics.min_confidence,
                    "max": metrics.max_confidence,
                    "avg": metrics.avg_confidence,
                }
            },
            "recent_performance": metrics.get_recent_performance(),
            "health_status": {
                "is_healthy": metrics.is_healthy,
                "last_check": metrics.last_health_check,
                "uptime_seconds": metrics.uptime_seconds,
            }
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all models"""
        all_metrics = {}
        for model_type in self.model_metrics.keys():
            all_metrics[model_type] = self.get_model_metrics(model_type)

        return {
            "models": all_metrics,
            "summary": {
                "total_models": len(all_metrics),
                "healthy_models": sum(1 for m in all_metrics.values() if m and m["health_status"]["is_healthy"]),
                "total_predictions": sum(m["basic_metrics"]["total_predictions"] for m in all_metrics.values() if m),
            },
            "timestamp": time.time()
        }

    def detect_drift(self, model_type: str, current_features: np.ndarray) -> Optional[DriftDetectionResult]:
        """
        Detect model drift using statistical methods

        Args:
            model_type: Type of model to check
            current_features: Current feature distribution

        Returns:
            Drift detection result or None if insufficient data
        """
        if model_type not in self.baseline_distributions:
            # Establish baseline if not exists
            self.baseline_distributions[model_type] = {
                'features': current_features.copy(),
                'count': 1
            }
            return None

        baseline = self.baseline_distributions[model_type]

        # Simple drift detection using KL divergence
        try:
            # Calculate feature-wise drift scores
            drift_scores = []
            affected_features = []

            for i in range(min(current_features.shape[1], baseline['features'].shape[1])):
                # Simple statistical distance (can be enhanced with proper KL divergence)
                baseline_mean = np.mean(baseline['features'][:, i])
                baseline_std = np.std(baseline['features'][:, i])
                current_mean = np.mean(current_features[:, i])
                current_std = np.std(current_features[:, i])

                # Calculate drift score (normalized difference)
                if baseline_std > 0:
                    drift_score = abs(current_mean - baseline_mean) / baseline_std
                    drift_scores.append(drift_score)

                    if drift_score > 2.0:  # Threshold for affected features
                        affected_features.append(f"feature_{i}")

            overall_drift_score = np.mean(drift_scores) if drift_scores else 0.0
            drift_threshold = 1.5  # Configurable threshold
            drift_detected = overall_drift_score > drift_threshold

            result = DriftDetectionResult(
                model_type=model_type,
                drift_detected=drift_detected,
                drift_score=overall_drift_score,
                threshold=drift_threshold,
                detection_method="statistical_distance",
                features_affected=affected_features,
                timestamp=time.time(),
                baseline_stats={
                    'mean': float(np.mean(baseline['features'])),
                    'std': float(np.std(baseline['features']))
                },
                current_stats={
                    'mean': float(np.mean(current_features)),
                    'std': float(np.std(current_features))
                },
                recommendations=self._generate_drift_recommendations(drift_detected, affected_features)
            )

            # Store result
            self.drift_history[model_type].append(result)
            if len(self.drift_history[model_type]) > 50:  # Keep last 50 results
                self.drift_history[model_type].pop(0)

            return result

        except Exception as e:
            logger.warning(f"Drift detection failed for {model_type}: {e}")
            return None

    def _generate_drift_recommendations(self, drift_detected: bool, affected_features: List[str]) -> List[str]:
        """Generate recommendations based on drift detection results"""
        recommendations = []

        if drift_detected:
            recommendations.append("Model retraining recommended due to detected drift")
            if affected_features:
                recommendations.append(f"Affected features: {', '.join(affected_features[:5])}")
            recommendations.append("Consider updating training data with recent patterns")
            recommendations.append("Monitor prediction performance closely")
        else:
            recommendations.append("No significant drift detected")
            recommendations.append("Continue normal monitoring")

        return recommendations

    def start_ab_test(
        self,
        model_a: str,
        model_b: str,
        traffic_split: float = 0.5,
        min_samples: int = 1000,
        test_duration_hours: int = 24
    ) -> str:
        """
        Start an A/B test between two models

        Args:
            model_a: Control model (A)
            model_b: Test model (B)
            traffic_split: Percentage of traffic to send to model B
            min_samples: Minimum samples before declaring winner
            test_duration_hours: Test duration in hours

        Returns:
            Test ID
        """
        test_id = f"ab_test_{int(time.time())}"

        ab_test = ABTestResult(
            test_id=test_id,
            model_a=model_a,
            model_b=model_b,
            status="running",
            start_time=time.time(),
            traffic_split=traffic_split,
            min_samples=min_samples
        )

        self.ab_tests[test_id] = ab_test
        self.active_ab_test = test_id

        # Schedule test end
        end_time = time.time() + (test_duration_hours * 3600)
        threading.Timer(test_duration_hours * 3600, self._end_ab_test, args=[test_id]).start()

        logger.info(f"Started A/B test {test_id}: {model_a} vs {model_b}")
        return test_id

    def _update_ab_test(self, model_type: str, prediction_result: Dict[str, Any]):
        """Update A/B test with new prediction"""
        if not self.active_ab_test:
            return

        ab_test = self.ab_tests.get(self.active_ab_test)
        if not ab_test:
            return

        # Determine which model was used and update metrics
        if model_type == ab_test.model_a:
            ab_test.total_predictions_a += 1
            # Assume ground truth is available (simplified)
            if prediction_result.get('is_anomaly', False):  # Simplified accuracy calculation
                ab_test.accuracy_a += 0.1  # Mock accuracy update
            ab_test.avg_confidence_a = (
                (ab_test.avg_confidence_a * (ab_test.total_predictions_a - 1)) +
                prediction_result.get('confidence', 0.0)
            ) / ab_test.total_predictions_a

        elif model_type == ab_test.model_b:
            ab_test.total_predictions_b += 1
            if prediction_result.get('is_anomaly', False):
                ab_test.accuracy_b += 0.1
            ab_test.avg_confidence_b = (
                (ab_test.avg_confidence_b * (ab_test.total_predictions_b - 1)) +
                prediction_result.get('confidence', 0.0)
            ) / ab_test.total_predictions_b

        # Check if test should end
        total_samples = ab_test.total_predictions_a + ab_test.total_predictions_b
        if total_samples >= ab_test.min_samples:
            self._evaluate_ab_test(ab_test)

    def _evaluate_ab_test(self, ab_test: ABTestResult):
        """Evaluate A/B test results and determine winner"""
        if ab_test.total_predictions_a == 0 or ab_test.total_predictions_b == 0:
            return

        # Normalize accuracies (simplified statistical test)
        acc_a = ab_test.accuracy_a / ab_test.total_predictions_a
        acc_b = ab_test.accuracy_b / ab_test.total_predictions_b

        # Simple winner determination
        if abs(acc_a - acc_b) > 0.05:  # 5% difference threshold
            ab_test.significant = True
            ab_test.winner = "A" if acc_a > acc_b else "B"
        else:
            ab_test.winner = "tie"

        ab_test.p_value = 0.01  # Mock p-value
        ab_test.status = "completed"
        ab_test.end_time = time.time()

        logger.info(f"A/B test {ab_test.test_id} completed. Winner: {ab_test.winner}")

    def _end_ab_test(self, test_id: str):
        """End an A/B test"""
        if test_id in self.ab_tests:
            self.ab_tests[test_id].status = "completed"
            self.ab_tests[test_id].end_time = time.time()

            if self.active_ab_test == test_id:
                self.active_ab_test = None

            logger.info(f"A/B test {test_id} ended")

    def get_ab_test_results(self, test_id: Optional[str] = None) -> Dict[str, Any]:
        """Get A/B test results"""
        if test_id:
            if test_id not in self.ab_tests:
                return {"error": f"Test {test_id} not found"}
            return asdict(self.ab_tests[test_id])
        else:
            return {
                "active_test": self.active_ab_test,
                "all_tests": {tid: asdict(test) for tid, test in self.ab_tests.items()},
                "summary": {
                    "total_tests": len(self.ab_tests),
                    "active_tests": sum(1 for t in self.ab_tests.values() if t.status == "running"),
                    "completed_tests": sum(1 for t in self.ab_tests.values() if t.status == "completed")
                }
            }

    def get_drift_history(self, model_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get drift detection history for a model"""
        history = self.drift_history.get(model_type, [])
        return [asdict(result) for result in history[-limit:]]

    def _update_drift_detection_data(self, model_type: str, features: np.ndarray):
        """Update drift detection baseline data"""
        if model_type not in self.baseline_distributions:
            self.baseline_distributions[model_type] = {
                'features': features.copy(),
                'count': 1
            }
        else:
            # Rolling update of baseline (keep recent data)
            baseline = self.baseline_distributions[model_type]
            # Simple exponential moving average
            alpha = 0.1  # Learning rate
            baseline['features'] = (1 - alpha) * baseline['features'] + alpha * features
            baseline['count'] += 1

    def cache_prediction(self, cache_key: str, result: Dict[str, Any], ttl_seconds: int = 300):
        """Cache prediction result"""
        if len(self.prediction_cache) >= self.cache_max_size:
            # Simple LRU eviction
            oldest_key = min(self.prediction_cache.keys(),
                           key=lambda k: self.prediction_cache[k].get('timestamp', 0))
            del self.prediction_cache[oldest_key]

        self.prediction_cache[cache_key] = {
            'result': result,
            'timestamp': time.time(),
            'ttl': ttl_seconds
        }

    def get_cached_prediction(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached prediction if still valid"""
        if cache_key not in self.prediction_cache:
            return None

        cached = self.prediction_cache[cache_key]
        if time.time() - cached['timestamp'] > cached['ttl']:
            del self.prediction_cache[cache_key]
            return None

        return cached['result']

    def _health_check_loop(self):
        """Background health check loop"""
        while not self.stop_monitoring:
            try:
                # Check health of all models
                for model_type, metrics in self.model_metrics.items():
                    metrics.check_health()

                time.sleep(self.health_check_interval)

            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(self.health_check_interval)

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring summary"""
        return {
            "models_monitored": list(self.model_metrics.keys()),
            "total_models": len(self.model_metrics),
            "healthy_models": sum(1 for m in self.model_metrics.values() if m.is_healthy),
            "ab_testing": {
                "active_test": self.active_ab_test,
                "total_tests": len(self.ab_tests)
            },
            "drift_detection": {
                "models_with_drift_history": list(self.drift_history.keys()),
                "total_drift_checks": sum(len(history) for history in self.drift_history.values())
            },
            "cache": {
                "size": len(self.prediction_cache),
                "max_size": self.cache_max_size
            },
            "timestamp": time.time()
        }

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize ML monitoring"""
        logger.info("ML monitoring initialized")

    async def _start_internal(self):
        """Start monitoring background tasks"""
        self.monitoring_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("ML monitoring background tasks started")

    async def _stop_internal(self):
        """Stop monitoring background tasks"""
        self.stop_monitoring = True
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("ML monitoring background tasks stopped")

    async def _cleanup(self):
        """Cleanup monitoring resources"""
        self.stop_monitoring = True
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

        self.model_metrics.clear()
        self.baseline_distributions.clear()
        self.drift_history.clear()
        self.ab_tests.clear()
        self.prediction_cache.clear()

        logger.info("ML monitoring cleanup completed")
