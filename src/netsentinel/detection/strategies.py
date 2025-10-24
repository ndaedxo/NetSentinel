#!/usr/bin/env python3
"""
Detection Strategy Pattern Implementation for NetSentinel
Implements different detection strategies (rule-based, ML-based, hybrid)
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ..core.exceptions import NetSentinelException, ProcessingError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("detection_strategies", level="INFO")
structured_logger = get_structured_logger("detection_strategies")


class DetectionResult:
    """Detection result"""

    def __init__(
        self,
        is_anomaly: bool,
        confidence: float,
        score: float,
        method: str,
        details: Dict[str, Any] = None,
    ):
        self.is_anomaly = is_anomaly
        self.confidence = confidence
        self.score = score
        self.method = method
        self.details = details or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "is_anomaly": self.is_anomaly,
            "confidence": self.confidence,
            "score": self.score,
            "method": self.method,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class DetectionStrategy(ABC):
    """Base detection strategy"""

    def __init__(self, name: str):
        self.name = name
        self.logger = create_logger(f"detection_{name}", level="INFO")

    @abstractmethod
    async def detect(self, event_data: Dict[str, Any]) -> DetectionResult:
        """Detect anomalies in event data"""
        pass

    @abstractmethod
    async def train(self, training_data: List[Dict[str, Any]]) -> None:
        """Train the detection model"""
        pass

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {"name": self.name, "type": self.__class__.__name__}


class RuleBasedDetection(DetectionStrategy):
    """Rule-based detection strategy"""

    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None):
        super().__init__("rule_based")
        self.rules = rules or []
        self.rule_stats = {}

    async def detect(self, event_data: Dict[str, Any]) -> DetectionResult:
        """Detect anomalies using rules"""
        start_time = time.time()

        try:
            total_score = 0.0
            triggered_rules = []

            for rule in self.rules:
                if self._evaluate_rule(rule, event_data):
                    score = rule.get("score", 1.0)
                    total_score += score
                    triggered_rules.append(
                        {
                            "rule_id": rule.get("id", "unknown"),
                            "description": rule.get("description", ""),
                            "score": score,
                        }
                    )

            # Determine if anomaly
            threshold = 0.5  # Configurable threshold
            is_anomaly = total_score >= threshold
            confidence = min(total_score, 1.0)

            # Update statistics
            rule_id = f"rule_{len(triggered_rules)}"
            self.rule_stats[rule_id] = self.rule_stats.get(rule_id, 0) + 1

            processing_time = time.time() - start_time

            return DetectionResult(
                is_anomaly=is_anomaly,
                confidence=confidence,
                score=total_score,
                method="rule_based",
                details={
                    "triggered_rules": triggered_rules,
                    "processing_time": processing_time,
                    "total_rules": len(self.rules),
                },
            )

        except Exception as e:
            self.logger.error(f"Rule-based detection failed: {e}")
            return DetectionResult(
                is_anomaly=False,
                confidence=0.0,
                score=0.0,
                method="rule_based",
                details={"error": str(e)},
            )

    def _evaluate_rule(self, rule: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Evaluate a single rule"""
        try:
            conditions = rule.get("conditions", [])

            for condition in conditions:
                field = condition.get("field")
                operator = condition.get("operator")
                value = condition.get("value")

                if field not in event_data:
                    continue

                event_value = event_data[field]

                if not self._evaluate_condition(event_value, operator, value):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Rule evaluation failed: {e}")
            return False

    def _evaluate_condition(
        self, event_value: Any, operator: str, expected_value: Any
    ) -> bool:
        """Evaluate a single condition"""
        try:
            if operator == "equals":
                return event_value == expected_value
            elif operator == "not_equals":
                return event_value != expected_value
            elif operator == "greater_than":
                return float(event_value) > float(expected_value)
            elif operator == "less_than":
                return float(event_value) < float(expected_value)
            elif operator == "contains":
                return str(expected_value) in str(event_value)
            elif operator == "not_contains":
                return str(expected_value) not in str(event_value)
            elif operator == "in":
                return event_value in expected_value
            elif operator == "not_in":
                return event_value not in expected_value
            else:
                self.logger.warning(f"Unknown operator: {operator}")
                return False

        except Exception as e:
            self.logger.error(f"Condition evaluation failed: {e}")
            return False

    async def train(self, training_data: List[Dict[str, Any]]) -> None:
        """Train rule-based detection (extract patterns)"""
        try:
            # Extract common patterns from training data
            patterns = self._extract_patterns(training_data)

            # Create rules from patterns
            self.rules = self._create_rules_from_patterns(patterns)

            self.logger.info(
                f"Trained rule-based detection with {len(self.rules)} rules"
            )

        except Exception as e:
            self.logger.error(f"Rule-based training failed: {e}")

    def _extract_patterns(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract patterns from training data"""
        patterns = {}

        # Simple pattern extraction
        for event in data:
            for key, value in event.items():
                if key not in patterns:
                    patterns[key] = {"values": [], "counts": {}}

                patterns[key]["values"].append(value)
                patterns[key]["counts"][value] = (
                    patterns[key]["counts"].get(value, 0) + 1
                )

        return patterns

    def _create_rules_from_patterns(
        self, patterns: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create rules from extracted patterns"""
        rules = []

        for field, pattern in patterns.items():
            # Create rule for unusual values
            common_values = sorted(
                pattern["counts"].items(), key=lambda x: x[1], reverse=True
            )[
                :5
            ]  # Top 5 most common values

            if len(common_values) > 0:
                rule = {
                    "id": f"unusual_{field}",
                    "description": f"Unusual value in {field}",
                    "score": 0.5,
                    "conditions": [
                        {
                            "field": field,
                            "operator": "not_in",
                            "value": [value for value, count in common_values],
                        }
                    ],
                }
                rules.append(rule)

        return rules


class MLBasedDetection(DetectionStrategy):
    """ML-based detection strategy"""

    def __init__(self, model_type: str = "isolation_forest"):
        super().__init__("ml_based")
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.is_trained = False

    async def detect(self, event_data: Dict[str, Any]) -> DetectionResult:
        """Detect anomalies using ML model"""
        start_time = time.time()

        try:
            if not self.is_trained:
                return DetectionResult(
                    is_anomaly=False,
                    confidence=0.0,
                    score=0.0,
                    method="ml_based",
                    details={"error": "Model not trained"},
                )

            # Extract features
            features = self._extract_features(event_data)

            if not features:
                return DetectionResult(
                    is_anomaly=False,
                    confidence=0.0,
                    score=0.0,
                    method="ml_based",
                    details={"error": "No features extracted"},
                )

            # Scale features
            features_scaled = self.scaler.transform([features])

            # Predict anomaly
            if self.model_type == "isolation_forest":
                score = self.model.decision_function(features_scaled)[0]
                is_anomaly = self.model.predict(features_scaled)[0] == -1
                confidence = abs(score)
            else:
                # Default to isolation forest
                score = self.model.decision_function(features_scaled)[0]
                is_anomaly = self.model.predict(features_scaled)[0] == -1
                confidence = abs(score)

            processing_time = time.time() - start_time

            return DetectionResult(
                is_anomaly=is_anomaly,
                confidence=confidence,
                score=score,
                method="ml_based",
                details={
                    "model_type": self.model_type,
                    "features_used": len(features),
                    "processing_time": processing_time,
                },
            )

        except Exception as e:
            self.logger.error(f"ML-based detection failed: {e}")
            return DetectionResult(
                is_anomaly=False,
                confidence=0.0,
                score=0.0,
                method="ml_based",
                details={"error": str(e)},
            )

    async def train(self, training_data: List[Dict[str, Any]]) -> None:
        """Train ML model"""
        try:
            # Extract features from training data
            features_matrix = []
            for event in training_data:
                features = self._extract_features(event)
                if features:
                    features_matrix.append(features)

            if not features_matrix:
                raise ValueError("No features extracted from training data")

            # Convert to numpy array
            X = np.array(features_matrix)

            # Scale features
            X_scaled = self.scaler.fit_transform(X)

            # Train model
            if self.model_type == "isolation_forest":
                self.model = IsolationForest(
                    contamination=0.1, random_state=42  # 10% contamination
                )
                self.model.fit(X_scaled)
            else:
                # Default to isolation forest
                self.model = IsolationForest(contamination=0.1, random_state=42)
                self.model.fit(X_scaled)

            self.is_trained = True
            self.logger.info(f"Trained ML model with {len(features_matrix)} samples")

        except Exception as e:
            self.logger.error(f"ML training failed: {e}")
            self.is_trained = False

    def _extract_features(self, event_data: Dict[str, Any]) -> List[float]:
        """Extract numerical features from event data"""
        features = []

        # Extract numerical features
        for key, value in event_data.items():
            if isinstance(value, (int, float)):
                features.append(float(value))
            elif isinstance(value, str):
                # Convert string to numerical features
                features.append(len(value))  # String length
                features.append(hash(value) % 1000)  # Hash value
            elif isinstance(value, bool):
                features.append(1.0 if value else 0.0)
            elif isinstance(value, list):
                features.append(len(value))  # List length
            elif isinstance(value, dict):
                features.append(len(value))  # Dict size

        return features


class HybridDetection(DetectionStrategy):
    """Hybrid detection strategy combining multiple methods"""

    def __init__(
        self, strategies: List[DetectionStrategy], weights: Optional[List[float]] = None
    ):
        super().__init__("hybrid")
        self.strategies = strategies
        self.weights = weights or [1.0] * len(strategies)

        if len(self.weights) != len(self.strategies):
            self.weights = [1.0] * len(self.strategies)

    async def detect(self, event_data: Dict[str, Any]) -> DetectionResult:
        """Detect anomalies using hybrid approach"""
        start_time = time.time()

        try:
            results = []

            # Run all strategies
            for strategy in self.strategies:
                try:
                    result = await strategy.detect(event_data)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Strategy {strategy.name} failed: {e}")
                    continue

            if not results:
                return DetectionResult(
                    is_anomaly=False,
                    confidence=0.0,
                    score=0.0,
                    method="hybrid",
                    details={"error": "No strategies succeeded"},
                )

            # Combine results
            combined_score = 0.0
            total_weight = 0.0
            anomaly_count = 0

            for i, result in enumerate(results):
                weight = self.weights[i] if i < len(self.weights) else 1.0
                combined_score += result.score * weight
                total_weight += weight

                if result.is_anomaly:
                    anomaly_count += 1

            # Normalize score
            if total_weight > 0:
                combined_score /= total_weight

            # Determine if anomaly
            threshold = 0.5
            is_anomaly = combined_score >= threshold
            confidence = min(combined_score, 1.0)

            processing_time = time.time() - start_time

            return DetectionResult(
                is_anomaly=is_anomaly,
                confidence=confidence,
                score=combined_score,
                method="hybrid",
                details={
                    "strategy_results": [result.to_dict() for result in results],
                    "anomaly_count": anomaly_count,
                    "total_strategies": len(self.strategies),
                    "processing_time": processing_time,
                },
            )

        except Exception as e:
            self.logger.error(f"Hybrid detection failed: {e}")
            return DetectionResult(
                is_anomaly=False,
                confidence=0.0,
                score=0.0,
                method="hybrid",
                details={"error": str(e)},
            )

    async def train(self, training_data: List[Dict[str, Any]]) -> None:
        """Train all strategies"""
        try:
            # Train each strategy
            for strategy in self.strategies:
                try:
                    await strategy.train(training_data)
                except Exception as e:
                    self.logger.error(f"Strategy {strategy.name} training failed: {e}")

            self.logger.info(
                f"Trained hybrid detection with {len(self.strategies)} strategies"
            )

        except Exception as e:
            self.logger.error(f"Hybrid training failed: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get hybrid detection statistics"""
        base_stats = super().get_statistics()
        base_stats["strategies"] = [
            strategy.get_statistics() for strategy in self.strategies
        ]
        base_stats["weights"] = self.weights
        return base_stats


class DetectionFactory:
    """Factory for creating detection strategies"""

    @staticmethod
    def create_strategy(strategy_type: str, **kwargs) -> DetectionStrategy:
        """Create detection strategy"""
        if strategy_type == "rule_based":
            return RuleBasedDetection(**kwargs)
        elif strategy_type == "ml_based":
            return MLBasedDetection(**kwargs)
        elif strategy_type == "hybrid":
            strategies = kwargs.get("strategies", [])
            weights = kwargs.get("weights")
            return HybridDetection(strategies, weights)
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

    @staticmethod
    def create_hybrid_strategy(
        rule_based_rules: Optional[List[Dict[str, Any]]] = None,
        ml_model_type: str = "isolation_forest",
        weights: Optional[List[float]] = None,
    ) -> HybridDetection:
        """Create hybrid strategy with default components"""
        rule_strategy = RuleBasedDetection(rule_based_rules)
        ml_strategy = MLBasedDetection(ml_model_type)

        return HybridDetection([rule_strategy, ml_strategy], weights)
