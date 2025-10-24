#!/usr/bin/env python3
"""
Event Analyzer for NetSentinel
Performs threat analysis and scoring on events
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import statistics

try:
    from ..core.base import BaseProcessor
    from ..core.models import StandardEvent, StandardAlert, ThreatLevel, create_alert
    from ..core.error_handler import handle_errors, create_error_context
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseProcessor
    from core.models import StandardEvent, StandardAlert, ThreatLevel, create_alert
    from core.error_handler import handle_errors, create_error_context

logger = logging.getLogger(__name__)


@dataclass
class AnalyzerConfig:
    """Configuration for EventAnalyzer"""

    name: str = "event_analyzer"
    ml_enabled: bool = True
    rule_engine_enabled: bool = True
    max_analysis_time: float = 10.0


@dataclass
class AnalysisResult:
    """Result of event analysis"""

    event: StandardEvent
    threat_score: float
    threat_level: ThreatLevel
    confidence: float
    indicators: List[str]
    analysis_time: float
    rule_matches: List[str]
    ml_analysis: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event.id,
            "threat_score": self.threat_score,
            "threat_level": self.threat_level.value,
            "confidence": self.confidence,
            "indicators": self.indicators,
            "analysis_time": self.analysis_time,
            "rule_matches": self.rule_matches,
            "ml_analysis": self.ml_analysis,
        }


class EventAnalyzer(BaseProcessor):
    """Analyzes events for threats and generates alerts"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__("event_analyzer", config, logger)

        # Analysis configuration
        self.threat_thresholds = {
            ThreatLevel.LOW: 0.0,
            ThreatLevel.MEDIUM: 3.0,
            ThreatLevel.HIGH: 6.0,
            ThreatLevel.CRITICAL: 8.0,
        }

        # Event history for correlation with bounded memory usage
        self.event_history = deque(maxlen=1000)
        self.ip_behavior_profiles = defaultdict(
            lambda: {
                "event_count": 0,
                "last_seen": 0,
                "threat_score_sum": 0.0,
                "event_types": set(),
                "suspicious_activities": deque(
                    maxlen=100
                ),  # Limit suspicious activities
            }
        )
        self._max_profiles = 1000  # Limit number of IP profiles
        self._cleanup_interval = 3600  # Clean up every hour
        self._last_cleanup = time.time()

        # Analysis rules
        self.analysis_rules = self._initialize_analysis_rules()

        # ML analysis (if available)
        self.ml_enabled = self.config.get("ml_enabled", True)
        self.ml_analyzer = None

        if self.ml_enabled:
            self._initialize_ml_analyzer()

    def _initialize_ml_analyzer(self):
        """Initialize ML analyzer for anomaly detection"""
        try:
            from ..ml_anomaly_detector import NetworkEventAnomalyDetector

            self.ml_analyzer = NetworkEventAnomalyDetector(
                model_type=self.config.get("ml_model_type", "fastflow"),
                model_path=self.config.get("ml_model_path"),
                config=self.config.get("ml_config", {}),
            )

            self.logger.info("ML analyzer initialized successfully")

        except ImportError as e:
            self.logger.warning(f"ML analyzer not available: {e}")
            self.ml_enabled = False
        except Exception as e:
            self.logger.error(f"Failed to initialize ML analyzer: {e}")
            self.ml_enabled = False

    def _initialize_analysis_rules(self) -> List[Dict[str, Any]]:
        """Initialize analysis rules"""
        return [
            {
                "name": "ssh_brute_force",
                "condition": lambda event: (
                    event.event_type == "4002"
                    and "logdata" in event.data
                    and isinstance(event.data["logdata"], dict)
                    and "USERNAME" in event.data["logdata"]
                ),
                "score": 5.0,
                "indicators": ["brute_force_attempt"],
            },
            {
                "name": "suspicious_username",
                "condition": lambda event: (
                    "logdata" in event.data
                    and isinstance(event.data["logdata"], dict)
                    and "USERNAME" in event.data["logdata"]
                    and event.data["logdata"]["USERNAME"]
                    in ["admin", "root", "administrator", "test"]
                ),
                "score": 3.0,
                "indicators": ["suspicious_username"],
            },
            {
                "name": "high_frequency_events",
                "condition": lambda event: self._check_high_frequency(event),
                "score": 4.0,
                "indicators": ["high_frequency"],
            },
            {
                "name": "unusual_event_pattern",
                "condition": lambda event: self._check_unusual_pattern(event),
                "score": 6.0,
                "indicators": ["unusual_pattern"],
            },
        ]

    async def _initialize(self):
        """Initialize analyzer"""
        self.logger.info("Event analyzer initialized")

    async def _start_internal(self):
        """Start analyzer"""
        self.logger.info("Event analyzer started")

    async def _stop_internal(self):
        """Stop analyzer"""
        self.logger.info("Event analyzer stopped")

    async def _process_item(self, item: StandardEvent):
        """Process a single event"""
        try:
            start_time = time.time()

            # Perform analysis
            result = await self._analyze_event(item)

            # Update metrics
            analysis_time = time.time() - start_time
            result.analysis_time = analysis_time

            # Store in history
            self.event_history.append(result)

            # Update IP behavior profile
            self._update_ip_profile(item, result)

            # Periodic cleanup to prevent memory leaks
            if time.time() - self._last_cleanup > self._cleanup_interval:
                self._cleanup_old_data()
                self._last_cleanup = time.time()

            # Log analysis result
            self.logger.info(
                f"Event {item.id} analyzed: score={result.threat_score:.2f}, "
                f"level={result.threat_level.value}, time={analysis_time:.3f}s"
            )

            # If high threat, create alert
            if result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                await self._create_threat_alert(result)

        except Exception as e:
            context = create_error_context(
                "analyze_event", "event_analyzer", additional_data={"event_id": item.id}
            )
            handle_errors(e, context)

    async def _analyze_event(self, event: StandardEvent) -> AnalysisResult:
        """Analyze a single event for threats"""
        # Rule-based analysis
        rule_score, rule_matches, indicators = self._rule_based_analysis(event)

        # ML-based analysis
        ml_score, ml_analysis = await self._ml_analysis(event)

        # Combine scores
        total_score = rule_score + ml_score

        # Determine threat level
        threat_level = self._determine_threat_level(total_score)

        # Calculate confidence
        confidence = self._calculate_confidence(rule_score, ml_score, len(rule_matches))

        return AnalysisResult(
            event=event,
            threat_score=total_score,
            threat_level=threat_level,
            confidence=confidence,
            indicators=indicators,
            analysis_time=0.0,  # Will be set by caller
            rule_matches=rule_matches,
            ml_analysis=ml_analysis,
        )

    def _rule_based_analysis(
        self, event: StandardEvent
    ) -> Tuple[float, List[str], List[str]]:
        """Perform rule-based analysis"""
        score = 0.0
        matches = []
        indicators = []

        for rule in self.analysis_rules:
            try:
                if rule["condition"](event):
                    score += rule["score"]
                    matches.append(rule["name"])
                    indicators.extend(rule["indicators"])
            except Exception as e:
                self.logger.error(f"Error in rule {rule['name']}: {e}")

        return score, matches, indicators

    async def _ml_analysis(
        self, event: StandardEvent
    ) -> Tuple[float, Optional[Dict[str, Any]]]:
        """Perform ML-based analysis"""
        if not self.ml_enabled or not self.ml_analyzer:
            return 0.0, None

        try:
            # Convert event to ML features
            features = self._extract_ml_features(event)

            # Get ML analysis (synchronous call)
            ml_result = self.ml_analyzer.analyze_event(features)

            if ml_result and ml_result.get("is_anomaly", False):
                score = ml_result.get("anomaly_score", 0.0) * 10  # Scale to 0-10
                return score, ml_result

        except Exception as e:
            self.logger.error(f"ML analysis error: {e}")

        return 0.0, None

    def _extract_ml_features(self, event: StandardEvent) -> Dict[str, Any]:
        """Extract features for ML analysis"""
        features = {
            "timestamp": event.timestamp,
            "event_type": event.event_type,
            "source_ip": event.source,
            "severity": event.severity,
            "data": event.data,
        }

        # Extract additional features from logdata
        if "logdata" in event.data and isinstance(event.data["logdata"], dict):
            logdata = event.data["logdata"]
            features.update(
                {
                    "has_username": "USERNAME" in logdata,
                    "has_password": "PASSWORD" in logdata,
                    "username": logdata.get("USERNAME", ""),
                    "user_agent": logdata.get("USERAGENT", ""),
                    "path": logdata.get("PATH", ""),
                    "method": logdata.get("REQUEST_TYPE", ""),
                }
            )

        return features

    def _determine_threat_level(self, score: float) -> ThreatLevel:
        """Determine threat level based on score"""
        for level, threshold in sorted(
            self.threat_thresholds.items(), key=lambda x: x[1], reverse=True
        ):
            if score >= threshold:
                return level
        return ThreatLevel.LOW

    def _calculate_confidence(
        self, rule_score: float, ml_score: float, rule_count: int
    ) -> float:
        """Calculate analysis confidence"""
        # Base confidence on number of indicators and score consistency
        base_confidence = min(rule_count * 0.2, 0.8)  # Up to 80% from rules

        # Add ML confidence if available
        if ml_score > 0:
            base_confidence += 0.2

        # Consistency bonus
        if rule_score > 0 and ml_score > 0:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    def _check_high_frequency(self, event: StandardEvent) -> bool:
        """Check for high frequency events from same IP"""
        ip = event.source
        profile = self.ip_behavior_profiles[ip]

        # Check events in last 5 minutes
        recent_events = [
            e
            for e in self.event_history
            if e.event.source == ip and time.time() - e.event.timestamp < 300
        ]

        return len(recent_events) > 10

    def _check_unusual_pattern(self, event: StandardEvent) -> bool:
        """Check for unusual event patterns"""
        # Check for rapid succession of different event types
        ip = event.source
        profile = self.ip_behavior_profiles[ip]

        # If we've seen multiple event types from this IP recently
        if len(profile["event_types"]) > 3:
            return True

        # Check for suspicious activities
        if len(profile["suspicious_activities"]) > 2:
            return True

        return False

    def _update_ip_profile(self, event: StandardEvent, result: AnalysisResult):
        """Update IP behavior profile"""
        ip = event.source
        profile = self.ip_behavior_profiles[ip]

        profile["event_count"] += 1
        profile["last_seen"] = time.time()
        profile["threat_score_sum"] += result.threat_score
        profile["event_types"].add(event.event_type)

        if result.threat_score > 5.0:
            profile["suspicious_activities"].append(
                {
                    "timestamp": time.time(),
                    "event_type": event.event_type,
                    "threat_score": result.threat_score,
                }
            )

    async def _create_threat_alert(self, result: AnalysisResult):
        """Create alert for high-threat event"""
        try:
            alert = create_alert(
                title=f"Threat Detected: {result.event.event_type}",
                description=f"High-threat activity detected with score {result.threat_score:.2f}",
                severity=result.threat_level.value,
                source="event_analyzer",
                event_data=result.event.data,
                tags=result.indicators + ["threat_detected"],
            )

            # Store alert (this would integrate with alert manager)
            self.logger.info(f"Created threat alert: {alert.id}")

        except Exception as e:
            self.logger.error(f"Failed to create threat alert: {e}")

    async def get_analysis_metrics(self) -> Dict[str, Any]:
        """Get analyzer-specific metrics"""
        base_metrics = self.get_metrics()

        # Calculate threat level distribution
        threat_levels = defaultdict(int)
        for result in self.event_history:
            threat_levels[result.threat_level.value] += 1

        # Calculate average threat score
        avg_threat_score = 0.0
        if self.event_history:
            avg_threat_score = statistics.mean(
                [r.threat_score for r in self.event_history]
            )

        analyzer_metrics = {
            **base_metrics,
            "threat_level_distribution": dict(threat_levels),
            "average_threat_score": avg_threat_score,
            "ip_profiles_count": len(self.ip_behavior_profiles),
            "analysis_rules_count": len(self.analysis_rules),
            "ml_enabled": self.ml_enabled,
            "event_history_size": len(self.event_history),
        }

        return analyzer_metrics

    def _cleanup_old_data(self):
        """Clean up old data to prevent memory leaks"""
        try:
            current_time = time.time()

            # Clean up old IP profiles
            old_ips = []
            for ip, profile in self.ip_behavior_profiles.items():
                if current_time - profile.get("last_seen", 0) > 86400:  # 24 hours
                    old_ips.append(ip)

            for ip in old_ips:
                del self.ip_behavior_profiles[ip]

            # If we still have too many profiles, remove oldest ones
            if len(self.ip_behavior_profiles) > self._max_profiles:
                sorted_profiles = sorted(
                    self.ip_behavior_profiles.items(),
                    key=lambda x: x[1].get("last_seen", 0),
                )
                excess_count = len(self.ip_behavior_profiles) - self._max_profiles
                for ip, _ in sorted_profiles[:excess_count]:
                    del self.ip_behavior_profiles[ip]

            self.logger.debug(f"Cleaned up {len(old_ips)} old IP profiles")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
