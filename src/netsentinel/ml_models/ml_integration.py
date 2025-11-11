#!/usr/bin/env python3
"""
ML Integration Module for NetSentinel

Connects ML predictions with threat detection and alerting systems
"""

import time
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from collections import defaultdict

# Import new core components
try:
    from ..core.base import BaseComponent
    from ..core.models import StandardEvent, StandardAlert, ThreatLevel
    from ..utils.centralized import create_logger
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from core.models import StandardEvent, StandardAlert, ThreatLevel
    from utils.centralized import create_logger

logger = create_logger("ml_integration", level="INFO")


@dataclass
class MLAlert:
    """ML-generated alert"""

    alert_id: str
    event: StandardEvent
    ml_prediction: Dict[str, Any]
    threat_score: float
    confidence: float
    indicators: List[str]
    model_type: str
    timestamp: float
    explanation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "event_id": self.event.id if self.event else None,
            "ml_prediction": self.ml_prediction,
            "threat_score": self.threat_score,
            "confidence": self.confidence,
            "indicators": self.indicators,
            "model_type": self.model_type,
            "timestamp": self.timestamp,
            "explanation": self.explanation,
        }


@dataclass
class RetrainingTrigger:
    """Trigger for model retraining"""

    trigger_id: str
    model_type: str
    trigger_reason: str
    trigger_score: float
    dataset_info: Dict[str, Any]
    timestamp: float
    priority: int  # 1-5, higher is more urgent

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trigger_id": self.trigger_id,
            "model_type": self.model_type,
            "trigger_reason": self.trigger_reason,
            "trigger_score": self.trigger_score,
            "dataset_info": self.dataset_info,
            "timestamp": self.timestamp,
            "priority": self.priority,
        }


class MLIntegration(BaseComponent):
    """
    ML Integration System

    Connects ML predictions with NetSentinel's threat detection and alerting systems
    """

    def __init__(
        self,
        name: str = "ml_integration",
        alert_threshold: float = 0.7,
        retraining_triggers_enabled: bool = True,
        incident_reporting_enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize ML integration

        Args:
            name: Component name
            alert_threshold: Threshold for triggering alerts from ML predictions
            retraining_triggers_enabled: Whether to enable automatic retraining triggers
            incident_reporting_enabled: Whether to enable ML insights in incident reports
            config: Additional configuration
        """
        super().__init__(name, config, logger)

        self.alert_threshold = alert_threshold
        self.retraining_triggers_enabled = retraining_triggers_enabled
        self.incident_reporting_enabled = incident_reporting_enabled

        # Integration components (will be set by external systems)
        self.ml_monitoring = None
        self.model_manager = None
        self.alert_manager = None
        self.incident_manager = None

        # Alert tracking
        self.ml_alerts: Dict[str, MLAlert] = {}
        self.alert_callbacks: List[Callable] = []

        # Retraining triggers
        self.retraining_triggers: Dict[str, RetrainingTrigger] = {}
        self.retraining_callbacks: List[Callable] = []

        # Incident reporting
        self.incident_insights: Dict[str, Dict[str, Any]] = {}

        # Integration stats
        self.integration_stats = {
            "total_predictions_processed": 0,
            "alerts_generated": 0,
            "retraining_triggers_created": 0,
            "incidents_enhanced": 0,
        }

    def set_ml_monitoring(self, ml_monitoring):
        """Set ML monitoring component"""
        self.ml_monitoring = ml_monitoring
        logger.info("ML monitoring component connected")

    def set_model_manager(self, model_manager):
        """Set model manager component"""
        self.model_manager = model_manager
        logger.info("Model manager component connected")

    def set_alert_manager(self, alert_manager):
        """Set alert manager component"""
        self.alert_manager = alert_manager
        logger.info("Alert manager component connected")

    def set_incident_manager(self, incident_manager):
        """Set incident manager component"""
        self.incident_manager = incident_manager
        logger.info("Incident manager component connected")

    def add_alert_callback(self, callback: Callable):
        """Add callback for ML-generated alerts"""
        self.alert_callbacks.append(callback)

    def add_retraining_callback(self, callback: Callable):
        """Add callback for retraining triggers"""
        self.retraining_callbacks.append(callback)

    def process_ml_prediction(
        self,
        event: StandardEvent,
        ml_result: Dict[str, Any],
        model_type: str
    ) -> Optional[MLAlert]:
        """
        Process ML prediction and integrate with threat detection

        Args:
            event: The network event
            ml_result: ML prediction result
            model_type: Type of ML model used

        Returns:
            MLAlert if alert threshold is exceeded, None otherwise
        """
        try:
            self.integration_stats["total_predictions_processed"] += 1

            # Check if prediction meets alert threshold
            confidence = ml_result.get('confidence', 0.0)
            anomaly_score = ml_result.get('anomaly_score', 0.0)
            is_anomaly = ml_result.get('is_anomaly', False)

            # Calculate threat score based on ML prediction
            threat_score = self._calculate_threat_score(ml_result)

            # Generate alert if threshold exceeded
            if confidence >= self.alert_threshold and is_anomaly:
                alert = self._create_ml_alert(event, ml_result, model_type, threat_score)
                self.ml_alerts[alert.alert_id] = alert

                # Send to alert manager
                if self.alert_manager:
                    self._send_to_alert_manager(alert)

                # Trigger callbacks
                for callback in self.alert_callbacks:
                    try:
                        asyncio.create_task(callback(alert))
                    except Exception as e:
                        logger.warning(f"Alert callback failed: {e}")

                self.integration_stats["alerts_generated"] += 1
                logger.info(f"ML alert generated: {alert.alert_id} (threat_score: {threat_score:.2f})")

                return alert

            # Check for retraining triggers
            if self.retraining_triggers_enabled:
                retraining_trigger = self._check_retraining_triggers(model_type, ml_result)
                if retraining_trigger:
                    self.retraining_triggers[retraining_trigger.trigger_id] = retraining_trigger

                    # Trigger callbacks
                    for callback in self.retraining_callbacks:
                        try:
                            asyncio.create_task(callback(retraining_trigger))
                        except Exception as e:
                            logger.warning(f"Retraining callback failed: {e}")

                    self.integration_stats["retraining_triggers_created"] += 1
                    logger.info(f"Retraining trigger created: {retraining_trigger.trigger_id}")

            return None

        except Exception as e:
            logger.error(f"Error processing ML prediction: {e}")
            return None

    def _calculate_threat_score(self, ml_result: Dict[str, Any]) -> float:
        """Calculate threat score from ML prediction"""
        confidence = ml_result.get('confidence', 0.0)
        anomaly_score = ml_result.get('anomaly_score', 0.0)

        # Base score from confidence
        threat_score = confidence * 10.0

        # Boost based on anomaly score
        if anomaly_score > 0.8:
            threat_score *= 1.5
        elif anomaly_score > 0.6:
            threat_score *= 1.2

        # Cap at 10.0
        return min(threat_score, 10.0)

    def _create_ml_alert(
        self,
        event: StandardEvent,
        ml_result: Dict[str, Any],
        model_type: str,
        threat_score: float
    ) -> MLAlert:
        """Create ML alert from prediction"""
        import uuid

        alert_id = f"ml_alert_{uuid.uuid4().hex[:8]}"

        # Generate indicators based on ML result
        indicators = self._generate_ml_indicators(ml_result, model_type)

        return MLAlert(
            alert_id=alert_id,
            event=event,
            ml_prediction=ml_result,
            threat_score=threat_score,
            confidence=ml_result.get('confidence', 0.0),
            indicators=indicators,
            model_type=model_type,
            timestamp=time.time(),
            explanation=ml_result.get('explanation')
        )

    def _generate_ml_indicators(self, ml_result: Dict[str, Any], model_type: str) -> List[str]:
        """Generate indicators from ML prediction"""
        indicators = [f"ML_{model_type.upper()}_ANOMALY"]

        confidence = ml_result.get('confidence', 0.0)
        if confidence > 0.9:
            indicators.append("HIGH_CONFIDENCE_ANOMALY")
        elif confidence > 0.7:
            indicators.append("MEDIUM_CONFIDENCE_ANOMALY")

        anomaly_score = ml_result.get('anomaly_score', 0.0)
        if anomaly_score > 0.8:
            indicators.append("HIGH_ANOMALY_SCORE")

        # Add explanation-based indicators if available
        explanation = ml_result.get('explanation', {})
        if explanation:
            top_features = explanation.get('top_contributing_features', [])
            for feature in top_features[:3]:  # Top 3 features
                indicators.append(f"ML_FEATURE_{feature.upper()}")

        return indicators

    def _send_to_alert_manager(self, ml_alert: MLAlert):
        """Send ML alert to alert manager"""
        try:
            if self.alert_manager:
                # Convert ML alert to standard alert format
                alert_data = {
                    "alert_id": ml_alert.alert_id,
                    "title": f"ML Anomaly Detection - {ml_alert.model_type}",
                    "description": f"ML model {ml_alert.model_type} detected anomaly with confidence {ml_alert.confidence:.2f}",
                    "severity": "HIGH" if ml_alert.confidence > 0.8 else "MEDIUM",
                    "source": "ML_ANALYSIS",
                    "event_id": ml_alert.event.id if ml_alert.event else None,
                    "indicators": ml_alert.indicators,
                    "ml_prediction": ml_alert.ml_prediction,
                    "threat_score": ml_alert.threat_score,
                    "timestamp": ml_alert.timestamp,
                }

                # Send to alert manager (assuming it has a create_alert method)
                if hasattr(self.alert_manager, 'create_alert'):
                    self.alert_manager.create_alert(alert_data)
                elif hasattr(self.alert_manager, 'add_alert'):
                    self.alert_manager.add_alert(alert_data)
                else:
                    logger.warning("Alert manager does not have expected alert creation method")

        except Exception as e:
            logger.error(f"Failed to send alert to alert manager: {e}")

    def _check_retraining_triggers(self, model_type: str, ml_result: Dict[str, Any]) -> Optional[RetrainingTrigger]:
        """Check if retraining should be triggered"""
        try:
            # Check model performance metrics
            if self.ml_monitoring:
                metrics = self.ml_monitoring.get_model_metrics(model_type)
                if metrics:
                    error_rate = metrics.get("basic_metrics", {}).get("error_rate", 0.0)

                    # Trigger retraining if error rate is high
                    if error_rate > 0.1:  # 10% error rate threshold
                        import uuid
                        trigger_id = f"retrain_{uuid.uuid4().hex[:8]}"

                        return RetrainingTrigger(
                            trigger_id=trigger_id,
                            model_type=model_type,
                            trigger_reason="high_error_rate",
                            trigger_score=error_rate,
                            dataset_info={"estimated_size": 1000, "data_quality": "unknown"},
                            timestamp=time.time(),
                            priority=4 if error_rate > 0.2 else 3
                        )

            # Check for drift detection
            if self.ml_monitoring and hasattr(self.ml_monitoring, 'detect_drift'):
                # Simulate drift check (would use actual feature data in production)
                import numpy as np
                mock_features = np.random.randn(10, 17).astype(np.float32)
                drift_result = self.ml_monitoring.detect_drift(model_type, mock_features)

                if drift_result and drift_result.drift_detected:
                    import uuid
                    trigger_id = f"drift_retrain_{uuid.uuid4().hex[:8]}"

                    return RetrainingTrigger(
                        trigger_id=trigger_id,
                        model_type=model_type,
                        trigger_reason="model_drift",
                        trigger_score=drift_result.drift_score,
                        dataset_info={"drift_score": drift_result.drift_score, "affected_features": drift_result.features_affected},
                        timestamp=time.time(),
                        priority=5 if drift_result.drift_score > 2.0 else 3
                    )

            return None

        except Exception as e:
            logger.warning(f"Error checking retraining triggers: {e}")
            return None

    def add_incident_insights(self, incident_id: str, event: StandardEvent, ml_result: Dict[str, Any]):
        """Add ML insights to incident report"""
        if not self.incident_reporting_enabled:
            return

        try:
            insights = {
                "ml_analysis": ml_result,
                "threat_contribution": self._calculate_threat_score(ml_result),
                "anomaly_patterns": self._extract_anomaly_patterns(ml_result),
                "recommended_actions": self._generate_recommended_actions(ml_result),
                "confidence_level": ml_result.get('confidence', 0.0),
                "model_used": ml_result.get('model_type', 'unknown'),
                "analysis_timestamp": time.time(),
            }

            self.incident_insights[incident_id] = insights
            self.integration_stats["incidents_enhanced"] += 1

            logger.info(f"ML insights added to incident {incident_id}")

        except Exception as e:
            logger.error(f"Error adding incident insights: {e}")

    def get_incident_insights(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get ML insights for an incident"""
        return self.incident_insights.get(incident_id)

    def _extract_anomaly_patterns(self, ml_result: Dict[str, Any]) -> List[str]:
        """Extract anomaly patterns from ML result"""
        patterns = []

        anomaly_score = ml_result.get('anomaly_score', 0.0)
        if anomaly_score > 0.8:
            patterns.append("High anomaly score detected")
        elif anomaly_score > 0.6:
            patterns.append("Moderate anomaly score detected")

        explanation = ml_result.get('explanation', {})
        if explanation:
            top_features = explanation.get('top_contributing_features', [])
            if 'error_count' in top_features:
                patterns.append("High error rate pattern")
            if 'auth' in str(top_features).lower():
                patterns.append("Authentication anomaly pattern")
            if 'unusual_time' in str(top_features).lower():
                patterns.append("Unusual timing pattern")

        return patterns

    def _generate_recommended_actions(self, ml_result: Dict[str, Any]) -> List[str]:
        """Generate recommended actions based on ML result"""
        actions = []

        confidence = ml_result.get('confidence', 0.0)
        if confidence > 0.9:
            actions.append("Immediate investigation required - high confidence anomaly")
        elif confidence > 0.7:
            actions.append("Review event for potential security concern")

        explanation = ml_result.get('explanation', {})
        if explanation:
            top_features = explanation.get('top_contributing_features', [])
            if 'error_count' in top_features:
                actions.append("Check system error logs")
            if 'auth' in str(top_features).lower():
                actions.append("Review authentication attempts")
            if any('port' in f.lower() for f in top_features):
                actions.append("Verify network port usage")

        actions.append("Consider updating ML model with recent data")
        return actions

    def get_ml_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent ML alerts"""
        alerts = list(self.ml_alerts.values())
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        return [alert.to_dict() for alert in alerts[:limit]]

    def get_retraining_triggers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent retraining triggers"""
        triggers = list(self.retraining_triggers.values())
        triggers.sort(key=lambda x: x.timestamp, reverse=True)
        return [trigger.to_dict() for trigger in triggers[:limit]]

    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            **self.integration_stats,
            "active_alerts": len(self.ml_alerts),
            "pending_retraining_triggers": len(self.retraining_triggers),
            "enhanced_incidents": len(self.incident_insights),
            "timestamp": time.time()
        }

    def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old alerts and triggers"""
        cutoff_time = time.time() - (max_age_hours * 3600)

        # Clean old alerts
        old_alerts = [aid for aid, alert in self.ml_alerts.items() if alert.timestamp < cutoff_time]
        for aid in old_alerts:
            del self.ml_alerts[aid]

        # Clean old triggers
        old_triggers = [tid for tid, trigger in self.retraining_triggers.items() if trigger.timestamp < cutoff_time]
        for tid in old_triggers:
            del self.retraining_triggers[tid]

        logger.info(f"Cleaned up {len(old_alerts)} old alerts and {len(old_triggers)} old triggers")

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize ML integration"""
        logger.info("ML integration initialized")

    async def _start_internal(self):
        """Start integration operations"""
        # Start cleanup task
        asyncio.create_task(self._periodic_cleanup())

    async def _stop_internal(self):
        """Stop integration operations"""
        pass

    async def _cleanup(self):
        """Cleanup integration resources"""
        self.ml_alerts.clear()
        self.retraining_triggers.clear()
        self.incident_insights.clear()

    async def _periodic_cleanup(self):
        """Periodic cleanup of old data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Clean every hour
                self.cleanup_old_data()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(3600)
