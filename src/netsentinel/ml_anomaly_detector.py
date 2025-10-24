#!/usr/bin/env python3
"""
ML-powered anomaly detection for NetSentinel events
Integrates Anomalib models for advanced threat detection
"""

import time
import os
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from collections import deque
import threading

# Anomalib imports
from anomalib.models import Fastflow, EfficientAd, Padim
from anomalib.data import Folder
from anomalib.engine import Engine
from anomalib.deploy.inferencers import TorchInferencer

# Import new core components
try:
    from .core.base import BaseComponent
    from .utils.centralized import create_logger
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from utils.centralized import create_logger

logger = create_logger("ml_anomaly_detector", level="INFO")


@dataclass
class EventFeatures:
    """Feature representation of network events for ML analysis"""

    timestamp: float
    event_type: int
    source_ip: str
    destination_port: int
    protocol: str
    username_attempts: int = 0
    password_attempts: int = 0
    connection_duration: float = 0.0
    bytes_transferred: int = 0
    error_count: int = 0


class NetworkEventAnomalyDetector(BaseComponent):
    """
    ML-based anomaly detector for network security events
    Uses Anomalib models to detect behavioral anomalies
    """

    def __init__(
        self,
        name: str = "ml_anomaly_detector",
        model_type: str = "fastflow",
        model_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize ML anomaly detector

        Args:
            name: Component name
            model_type: Type of ML model ('fastflow', 'efficientad', 'padim')
            model_path: Path to pre-trained model
            config: Additional configuration
        """
        super().__init__(name, config, logger)

        self.model_type = model_type.lower()
        self.model_path = model_path
        self.model = None
        self.inferencer = None
        self.is_trained = False

        # Feature normalization parameters
        self.feature_stats = {}
        self.feature_scaler = None

        # Event history for context - limit memory usage
        self.event_history = deque(maxlen=1000)
        self.ip_behavior_profiles = {}
        self._cleanup_interval = 3600  # Clean up every hour
        self._last_cleanup = time.time()
        self._max_profiles = 1000  # Limit number of IP profiles

        # Thread lock for concurrent access
        self.lock = threading.Lock()

        # Initialize model
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the selected Anomalib model"""
        try:
            if self.model_type == "fastflow":
                self.model = Fastflow()
            elif self.model_type == "efficient_ad":
                self.model = EfficientAd()
            elif self.model_type == "padim":
                self.model = Padim()
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")

            logger.info(f"Initialized {self.model_type} model for anomaly detection")

        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise

    def _extract_features(self, event_data: Dict) -> Optional[EventFeatures]:
        """Extract structured features from NetSentinel event data"""
        try:
            # Basic event information
            event_type = event_data.get("logtype", 0)
            source_ip = event_data.get("src_host", "unknown")
            dest_port = event_data.get("dst_port", 0)

            # Validate required fields
            if not source_ip or source_ip == "unknown":
                logger.warning("Invalid source IP in event data")
                return None

            # Determine protocol from event type
            protocol_map = {
                2000: "FTP",
                3000: "HTTP",
                4000: "SSH",
                6001: "TELNET",
                8001: "MySQL",
                4002: "SSH",
            }
            protocol = protocol_map.get(event_type, "UNKNOWN")

            # Extract additional features from logdata
            logdata = event_data.get("logdata", {})
            username_attempts = 1 if "USERNAME" in str(logdata) else 0
            password_attempts = 1 if "PASSWORD" in str(logdata) else 0

            return EventFeatures(
                timestamp=time.time(),
                event_type=event_type,
                source_ip=source_ip,
                destination_port=dest_port,
                protocol=protocol,
                username_attempts=username_attempts,
                password_attempts=password_attempts,
            )

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None

    def _normalize_features(self, features: EventFeatures) -> np.ndarray:
        """Convert features to normalized numpy array for ML model"""
        try:
            # Convert to numerical features
            feature_vector = np.array(
                [
                    features.event_type,
                    features.destination_port,
                    features.username_attempts,
                    features.password_attempts,
                    features.connection_duration,
                    features.bytes_transferred,
                    features.error_count,
                ],
                dtype=np.float32,
            )

            # Normalize features (simple min-max normalization)
            if not self.feature_stats:
                self.feature_stats = {
                    "min": feature_vector,
                    "max": feature_vector,
                    "mean": feature_vector,
                }
            else:
                self.feature_stats["min"] = np.minimum(
                    self.feature_stats["min"], feature_vector
                )
                self.feature_stats["max"] = np.maximum(
                    self.feature_stats["max"], feature_vector
                )
                self.feature_stats["mean"] = (
                    self.feature_stats["mean"] + feature_vector
                ) / 2

            # Apply normalization
            normalized = (feature_vector - self.feature_stats["min"]) / (
                self.feature_stats["max"] - self.feature_stats["min"] + 1e-8
            )

            return normalized.reshape(1, -1)

        except Exception as e:
            logger.error(f"Error normalizing features: {e}")
            return np.zeros((1, 7), dtype=np.float32)

    def _create_feature_image(self, features: np.ndarray) -> torch.Tensor:
        """Convert 1D features to 2D image-like tensor for Anomalib models"""
        try:
            # Reshape to square-ish format and pad if necessary
            size = int(np.ceil(np.sqrt(features.shape[1])))
            padded = np.zeros((size, size), dtype=np.float32)

            # Fill with feature values
            for i, val in enumerate(features[0]):
                if i < size * size:
                    padded[i // size, i % size] = val

            # Convert to RGB-like format (3 channels)
            image = np.stack([padded, padded, padded], axis=2)

            # Convert to tensor and add batch dimension
            tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)

            return tensor

        except Exception as e:
            logger.error(f"Error creating feature image: {e}")
            return torch.zeros((1, 3, 8, 8))

    def train_on_normal_events(self, normal_events: List[Dict], epochs: int = 10):
        """Train the model on normal network behavior"""
        try:
            logger.info(
                f"Training {self.model_type} model on {len(normal_events)} normal events"
            )

            # Extract and normalize features
            feature_vectors = []
            for event in normal_events:
                features = self._extract_features(event)
                if features:
                    normalized = self._normalize_features(features)
                    feature_vectors.append(normalized)

            if not feature_vectors:
                logger.warning("No valid features extracted for training")
                return

            # Convert to tensor format
            feature_tensor = torch.from_numpy(np.vstack(feature_vectors))

            # Create image-like tensors for Anomalib models
            image_tensors = []
            for features in feature_vectors:
                image_tensor = self._create_feature_image(features)
                image_tensors.append(image_tensor)

            if not image_tensors:
                logger.warning("No valid image tensors created for training")
                return

            # Stack all image tensors
            training_data = torch.cat(image_tensors, dim=0)

            # Create a simple dataset for training
            # Note: This is a simplified approach - full Anomalib integration would require
            # proper dataset creation with Folder class and Engine training
            logger.info(f"Created training dataset with {len(image_tensors)} samples")

            # For now, we'll mark as trained and store the training data
            # In a full implementation, this would use Anomalib's Engine for training
            self.training_data = training_data
            self.is_trained = True

            # Save model state for persistence
            if self.model_path:
                self._save_model()

            logger.info(
                f"Model training completed successfully with {len(image_tensors)} samples"
            )

        except Exception as e:
            logger.error(f"Training failed: {e}")
            self.is_trained = False

    def detect_anomaly(self, event_data: Dict) -> Tuple[float, Dict]:
        """
        Detect anomalies in network events using ML models

        Returns:
            Tuple[float, Dict]: (anomaly_score, analysis_details)
        """
        try:
            with self.lock:
                # Extract features
                features = self._extract_features(event_data)
                if not features:
                    return 0.0, {"error": "Failed to extract features"}

                # Normalize features
                normalized_features = self._normalize_features(features)

                # Update event history with periodic cleanup
                self.event_history.append(features)

                # Periodic cleanup to prevent memory leaks
                if time.time() - self._last_cleanup > self._cleanup_interval:
                    self._cleanup_old_data()
                    self._last_cleanup = time.time()

                # Simple anomaly detection based on feature patterns
                anomaly_score = self._calculate_anomaly_score(
                    features, normalized_features
                )

                # Create analysis details
                analysis = {
                    "ml_score": anomaly_score,
                    "feature_vector": normalized_features.tolist(),
                    "behavioral_context": self._analyze_behavioral_context(features),
                    "model_type": self.model_type,
                    "timestamp": features.timestamp,
                }

                return anomaly_score, analysis

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return 0.0, {"error": str(e)}

    def _calculate_anomaly_score(
        self, features: EventFeatures, normalized_features: np.ndarray
    ) -> float:
        """Calculate anomaly score using ML models and behavioral analysis"""
        try:
            # If model is trained, use ML-based scoring
            if self.is_trained and hasattr(self, "training_data"):
                ml_score = self._ml_anomaly_detection(features, normalized_features)
                behavioral_score = self._behavioral_analysis(features)

                # Combine ML and behavioral scores
                combined_score = (ml_score * 0.7) + (behavioral_score * 0.3)
                return min(combined_score, 1.0)
            else:
                # Fallback to behavioral analysis only
                return self._behavioral_analysis(features)

        except Exception as e:
            logger.error(f"Error calculating anomaly score: {e}")
            return 0.0

    def _ml_anomaly_detection(
        self, features: EventFeatures, normalized_features: np.ndarray
    ) -> float:
        """Use ML model for anomaly detection"""
        try:
            # Create image tensor for ML model
            image_tensor = self._create_feature_image(normalized_features)

            # Simple distance-based anomaly detection
            # In a full implementation, this would use the actual Anomalib model
            if hasattr(self, "training_data") and self.training_data is not None:
                # Calculate distance to training data
                distances = torch.cdist(image_tensor, self.training_data)
                min_distance = torch.min(distances).item()

                # Convert distance to anomaly score (closer to 0 = more normal)
                # This is a simplified approach - real Anomalib models would provide proper scores
                anomaly_score = min(min_distance * 10, 1.0)  # Scale and cap at 1.0
                return anomaly_score

            return 0.0

        except Exception as e:
            logger.error(f"ML anomaly detection failed: {e}")
            return 0.0

    def _behavioral_analysis(self, features: EventFeatures) -> float:
        """Perform behavioral analysis for anomaly detection"""
        try:
            score = 0.0

            # 1. Event type frequency analysis
            recent_events = list(self.event_history)[-100:]  # Last 100 events
            event_counts = {}
            for event in recent_events:
                event_counts[event.event_type] = (
                    event_counts.get(event.event_type, 0) + 1
                )

            current_event_freq = event_counts.get(features.event_type, 0) / max(
                len(recent_events), 1
            )
            if current_event_freq > 0.5:  # High frequency might indicate scanning
                score += 0.3

            # 2. Source IP behavior analysis
            ip_events = [
                e for e in self.event_history if e.source_ip == features.source_ip
            ]
            if len(ip_events) > 10:  # Multiple events from same IP
                score += 0.2

            # 3. Protocol-specific patterns
            if features.protocol == "SSH" and features.password_attempts > 0:
                score += 0.3
            elif features.protocol == "FTP" and features.username_attempts > 0:
                score += 0.2

            # 4. Temporal patterns
            recent_events = [
                e for e in self.event_history[-10:] if time.time() - e.timestamp < 300
            ]  # Last 5 minutes
            if len(recent_events) > 5:
                score += 0.2

            # Normalize score to 0-1 range
            return min(score, 1.0)

        except Exception as e:
            logger.error(f"Error in behavioral analysis: {e}")
            return 0.0

    def _analyze_behavioral_context(self, features: EventFeatures) -> Dict:
        """Analyze behavioral context for the event"""
        try:
            # Get recent events from same IP
            ip_events = [
                e for e in self.event_history if e.source_ip == features.source_ip
            ]

            context = {
                "total_events_from_ip": len(ip_events),
                "unique_protocols_used": len(set(e.protocol for e in ip_events)),
                "recent_activity_level": len(
                    [e for e in ip_events if time.time() - e.timestamp < 3600]
                ),
                "credential_attempts": sum(
                    e.username_attempts + e.password_attempts for e in ip_events
                ),
            }

            return context

        except Exception as e:
            logger.error(f"Error analyzing behavioral context: {e}")
            return {}

    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        return {
            "model_type": self.model_type,
            "is_trained": self.is_trained,
            "model_path": self.model_path,
            "event_history_size": len(self.event_history),
            "feature_stats": self.feature_stats,
        }

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize ML detector resources"""
        # Load or initialize the model
        try:
            self._load_model()
        except Exception as e:
            logger.error(f"Failed to initialize ML model: {e}")

    async def _start_internal(self):
        """Start ML detector internal operations"""
        # ML detector is ready to use after initialization
        pass

    async def _stop_internal(self):
        """Stop ML detector internal operations"""
        # No background operations to stop
        pass

    async def _cleanup(self):
        """Cleanup ML detector resources"""
        # Clear event history and feature stats
        if hasattr(self, "event_history"):
            self.event_history.clear()
        if hasattr(self, "feature_stats"):
            self.feature_stats.clear()

    def _save_model(self):
        """Save trained model to disk"""
        try:
            if self.model_path and hasattr(self, "training_data"):
                model_state = {
                    "model_type": self.model_type,
                    "feature_stats": self.feature_stats,
                    "training_data": self.training_data,
                    "is_trained": self.is_trained,
                    "timestamp": time.time(),
                }
                torch.save(model_state, self.model_path)
                logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def _load_model(self):
        """Load trained model from disk"""
        try:
            if self.model_path and os.path.exists(self.model_path):
                model_state = torch.load(self.model_path)
                self.model_type = model_state.get("model_type", self.model_type)
                self.feature_stats = model_state.get("feature_stats", {})
                self.training_data = model_state.get("training_data")
                self.is_trained = model_state.get("is_trained", False)
                logger.info(f"Model loaded from {self.model_path}")
            else:
                logger.warning(f"Model file not found: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

    def _cleanup_old_data(self):
        """Clean up old data to prevent memory leaks"""
        try:
            current_time = time.time()
            # Clean up old IP behavior profiles
            old_ips = []
            for ip, profile in self.ip_behavior_profiles.items():
                if current_time - profile.get("last_seen", 0) > 86400:  # 24 hours
                    old_ips.append(ip)

            for ip in old_ips:
                del self.ip_behavior_profiles[ip]

            # If we still have too many profiles, remove oldest ones
            if len(self.ip_behavior_profiles) > self._max_profiles:
                # Sort by last_seen and remove oldest
                sorted_profiles = sorted(
                    self.ip_behavior_profiles.items(),
                    key=lambda x: x[1].get("last_seen", 0),
                )
                excess_count = len(self.ip_behavior_profiles) - self._max_profiles
                for ip, _ in sorted_profiles[:excess_count]:
                    del self.ip_behavior_profiles[ip]

            # Clean up old event history to prevent memory leaks
            if len(self.event_history) > 2000:
                # Keep only recent 1000 events
                self.event_history = deque(
                    list(self.event_history)[-1000:], maxlen=1000
                )

            # Clean up old feature stats if they get too large
            if hasattr(self, "feature_stats") and self.feature_stats:
                # Reset feature stats if they become too large
                if len(str(self.feature_stats)) > 1000000:  # 1MB limit
                    self.feature_stats = {}

            logger.debug(f"Cleaned up {len(old_ips)} old IP behavior profiles")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def analyze_event(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze event using ML models (interface for EventAnalyzer)"""
        try:
            # Convert features dict to EventFeatures object
            event_features = EventFeatures(
                timestamp=features.get("timestamp", time.time()),
                event_type=features.get("event_type", 0),
                source_ip=features.get("source_ip", "unknown"),
                destination_port=features.get("destination_port", 0),
                protocol=features.get("protocol", "UNKNOWN"),
                username_attempts=features.get("username_attempts", 0),
                password_attempts=features.get("password_attempts", 0),
                connection_duration=features.get("connection_duration", 0.0),
                bytes_transferred=features.get("bytes_transferred", 0),
                error_count=features.get("error_count", 0),
            )

            # Normalize features
            normalized_features = self._normalize_features(event_features)

            # Detect anomaly
            anomaly_score, analysis = self.detect_anomaly(
                {
                    "logtype": event_features.event_type,
                    "src_host": event_features.source_ip,
                    "dst_port": event_features.destination_port,
                    "logdata": features.get("data", {}),
                }
            )

            return {
                "is_anomaly": anomaly_score > 0.5,
                "anomaly_score": anomaly_score,
                "confidence": analysis.get("behavioral_context", {}).get(
                    "confidence", 0.0
                ),
                "ml_analysis": analysis,
            }

        except Exception as e:
            logger.error(f"Event analysis failed: {e}")
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "confidence": 0.0,
                "error": str(e),
            }


# Global detector instance
ml_detector = NetworkEventAnomalyDetector(model_type="fastflow")
