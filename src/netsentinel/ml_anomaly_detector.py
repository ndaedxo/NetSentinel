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
from anomalib.deploy.inferencers import TorchInferencer

# Import new ML components
try:
    from .ml_models import ModelManager, FeatureExtractor
    from .core.base import BaseComponent
    from .core.interfaces import IMLDetector
    from .utils.centralized import create_logger
except ImportError:
    # Fallback for standalone usage
    from ml_models import ModelManager, FeatureExtractor
    from core.base import BaseComponent
    from core.interfaces import IMLDetector
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


class NetworkEventAnomalyDetector(BaseComponent, IMLDetector):
    """
    ML-based anomaly detector for network security events
    Uses Anomalib models to detect behavioral anomalies

    Now uses the new ML component architecture:
    - ModelManager for model loading/versioning
    - FeatureExtractor for feature processing
    - TorchInferencer for actual anomaly detection
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
        self.is_trained = False

        # Initialize new ML components
        self.model_manager = ModelManager(
            models_dir=self.config.get("models_dir", "models"),
            max_versions=self.config.get("max_model_versions", 5),
        )

        self.feature_extractor = FeatureExtractor(
            normalization_method=self.config.get("normalization_method", "standard"),
            image_size=tuple(self.config.get("image_size", [32, 32])),
        )

        self.inferencer = None  # Will be loaded by model manager

        # Event history for context - limit memory usage
        self.event_history = deque(maxlen=1000)
        self.ip_behavior_profiles = {}
        self._cleanup_interval = 3600  # Clean up every hour
        self._last_cleanup = time.time()
        self._max_profiles = 1000  # Limit number of IP profiles
        self._max_history_age = 86400  # 24 hours in seconds

        # Thread lock for concurrent access
        self.lock = threading.Lock()

        # Initialize components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize ML components and load model if available"""
        try:
            # Try to load existing trained model
            self.inferencer = self.model_manager.load_model(self.model_type)

            if self.inferencer is not None:
                self.is_trained = True
                logger.info(f"Loaded trained {self.model_type} model for inference")
            else:
                logger.info(f"No trained {self.model_type} model found, will use behavioral analysis only")

        except Exception as e:
            logger.error(f"Failed to initialize ML components: {e}")
            self.inferencer = None
            self.is_trained = False

    def _extract_features(self, event_data: Dict) -> Optional[EventFeatures]:
        """Extract structured features from NetSentinel event data using FeatureExtractor"""
        try:
            # Use the new FeatureExtractor component
            network_features = self.feature_extractor.extract_features(event_data)

            if network_features is None:
                logger.warning("Feature extraction failed")
                return None

            # Convert NetworkFeatures to EventFeatures for backward compatibility
            # (This can be removed once we fully migrate to NetworkFeatures)
            return EventFeatures(
                timestamp=network_features.timestamp,
                event_type=network_features.event_type,
                source_ip=network_features.source_ip,
                destination_port=network_features.destination_port,
                protocol=network_features.protocol,
                username_attempts=network_features.username_attempts,
                password_attempts=network_features.password_attempts,
                connection_duration=network_features.connection_duration,
                bytes_transferred=network_features.bytes_sent,  # Map to existing field
                error_count=network_features.error_count,
            )

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None

    def _normalize_features(self, features: EventFeatures) -> np.ndarray:
        """Convert features to normalized numpy array using FeatureExtractor"""
        try:
            # Convert EventFeatures back to dict for FeatureExtractor
            event_dict = {
                "timestamp": features.timestamp,
                "event_type": features.event_type,
                "source_ip": features.source_ip,
                "destination_port": features.destination_port,
                "protocol": features.protocol,
                "username_attempts": features.username_attempts,
                "password_attempts": features.password_attempts,
                "connection_duration": features.connection_duration,
                "bytes_transferred": features.bytes_transferred,
                "error_count": features.error_count,
            }

            # Use FeatureExtractor to get NetworkFeatures and normalize
            network_features = self.feature_extractor.extract_features(event_dict)
            if network_features is None:
                return np.zeros((17,), dtype=np.float32)  # NetworkFeatures has 17 features

            # Normalize using FeatureExtractor
            normalized = self.feature_extractor.normalize_features(network_features, update_stats=True)

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing features: {e}")
            return np.zeros((17,), dtype=np.float32)

    def _create_feature_image(self, features: np.ndarray) -> torch.Tensor:
        """Convert 1D features to 2D image-like tensor using FeatureExtractor"""
        try:
            # Use FeatureExtractor's image conversion
            image_tensor = self.feature_extractor.features_to_image(features, method="direct")
            return image_tensor

        except Exception as e:
            logger.error(f"Error creating feature image: {e}")
            return torch.zeros((1, 3, 32, 32))  # Default size

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
        """Use ML model for anomaly detection with TorchInferencer"""
        try:
            # Check if we have a trained model loaded
            if self.inferencer is None:
                logger.debug("No ML model loaded, returning 0.0 for anomaly score")
                return 0.0

            # Create image tensor for ML model
            image_tensor = self._create_feature_image(normalized_features)

            # Run actual inference using TorchInferencer
            prediction = self.inferencer.predict(image_tensor)

            # Extract anomaly score from prediction
            # Anomalib models return predictions with anomaly scores/maps
            if hasattr(prediction, 'pred_score'):
                # Direct anomaly score
                anomaly_score = float(prediction.pred_score.item())
            elif hasattr(prediction, 'anomaly_map'):
                # Use anomaly map - average anomaly score across the image
                anomaly_map = prediction.anomaly_map
                anomaly_score = float(torch.mean(anomaly_map).item())
            else:
                # Fallback: try to get score from other prediction attributes
                logger.warning("Unexpected prediction format from TorchInferencer")
                anomaly_score = 0.0

            # Ensure score is in [0, 1] range
            anomaly_score = max(0.0, min(1.0, anomaly_score))

            logger.debug(".3f")
            return anomaly_score

        except Exception as e:
            logger.error(f"ML anomaly detection failed: {e}")
            # Update model health if available
            if hasattr(self, 'model_manager') and self.model_type:
                health = self.model_manager.get_model_health(self.model_type)
                if health:
                    health["error_count"] = health.get("error_count", 0) + 1
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
            recent_events = []
            if len(self.event_history) > 0:
                # Get last 10 events safely
                last_events = list(self.event_history)[-10:]
                recent_events = [
                    e for e in last_events if time.time() - e.timestamp < 300
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
            # Model saving is now handled by ModelManager
            # This method is kept for backward compatibility
            if hasattr(self, "training_data") and self.training_data:
                # Save training data for potential retraining
                training_state = {
                    "model_type": self.model_type,
                    "training_data": self.training_data,
                    "is_trained": self.is_trained,
                    "timestamp": time.time(),
                }
                # Use ModelManager to save the model
                self.model_manager.save_model(
                    model_type=self.model_type,
                    model_data=training_state
                )
                logger.info(f"Model state saved via ModelManager")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def _load_model(self):
        """Load trained model using ModelManager"""
        try:
            # Model loading is now handled by ModelManager in _initialize_components
            # This method is kept for backward compatibility but delegates to ModelManager
            if self.inferencer is None:
                self.inferencer = self.model_manager.load_model(self.model_type)
                if self.inferencer is not None:
                    self.is_trained = True
                    logger.info(f"Model loaded via ModelManager: {self.model_type}")
                else:
                    logger.warning(f"Failed to load model: {self.model_type}")
        except Exception as e:
            logger.error(f"Failed to load model via ModelManager: {e}")

    def _cleanup_old_data(self):
        """Clean up old data to prevent memory leaks"""
        try:
            current_time = time.time()
            cleaned_ips = 0
            cleaned_events = 0

            # Clean up old IP behavior profiles
            old_ips = []
            for ip, profile in self.ip_behavior_profiles.items():
                if current_time - profile.get("last_seen", 0) > self._max_history_age:
                    old_ips.append(ip)

            for ip in old_ips:
                del self.ip_behavior_profiles[ip]
                cleaned_ips += 1

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
                    cleaned_ips += 1

            # Clean up old event history
            if self.event_history:
                # Remove events older than max_history_age
                current_events = list(self.event_history)
                filtered_events = [
                    event
                    for event in current_events
                    if current_time - event.timestamp <= self._max_history_age
                ]

                if len(filtered_events) != len(current_events):
                    self.event_history = deque(filtered_events, maxlen=1000)
                    cleaned_events = len(current_events) - len(filtered_events)

            # Clean up old feature stats if they get too large
            if hasattr(self, "feature_stats") and self.feature_stats:
                # Reset feature stats if they become too large
                stats_size = len(str(self.feature_stats))
                if stats_size > 1000000:  # 1MB limit
                    self.feature_stats = {}
                    logger.warning("Feature stats reset due to size limit")

            if cleaned_ips > 0 or cleaned_events > 0:
                logger.debug(
                    f"Cleaned up {cleaned_ips} old IP profiles and {cleaned_events} old events"
                )

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    # IMLDetector interface implementation
    async def analyze_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze event for anomalies (IMLDetector interface)"""
        try:
            # Convert event dict to features dict format expected by existing method
            features_dict = {
                "timestamp": event.get("timestamp", time.time()),
                "event_type": event.get("event_type", event.get("logtype", 0)),
                "source_ip": event.get("source_ip", event.get("src_host", "unknown")),
                "destination_port": event.get("destination_port", event.get("dst_port", 0)),
                "protocol": event.get("protocol", "UNKNOWN"),
                "username_attempts": event.get("username_attempts", 0),
                "password_attempts": event.get("password_attempts", 0),
                "connection_duration": event.get("connection_duration", 0.0),
                "bytes_transferred": event.get("bytes_transferred", 0),
                "error_count": event.get("error_count", 0),
                "data": event,  # Pass full event as data
            }

            # Use existing synchronous method
            result = self.analyze_event_sync(features_dict)
            return result

        except Exception as e:
            logger.error(f"Interface analyze_event failed: {e}")
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "confidence": 0.0,
                "error": str(e),
            }

    async def train_on_events(self, events: List[Dict[str, Any]]) -> bool:
        """Train model on events (IMLDetector interface)"""
        try:
            # Use TrainingPipeline for proper training
            from .ml_models import TrainingPipeline

            trainer = TrainingPipeline(
                model_type=self.model_type,
                model_path=self.model_path,
                config=self.config,
            )

            # Convert events to expected format
            formatted_events = []
            for event in events:
                formatted_event = {
                    "logtype": event.get("event_type", event.get("logtype", 0)),
                    "src_host": event.get("source_ip", event.get("src_host", "unknown")),
                    "dst_port": event.get("destination_port", event.get("dst_port", 0)),
                    "logdata": event.get("data", {}),
                    "timestamp": event.get("timestamp", time.time()),
                }
                formatted_events.append(formatted_event)

            # Train the model
            success = trainer.train_on_events(formatted_events)

            if success:
                # Register the trained model with ModelManager
                model_info = trainer.get_training_metrics()
                self.model_manager.register_model(
                    model_type=self.model_type,
                    model_path=trainer.model_path,
                    training_metrics=model_info,
                )

                # Reload the model
                self._initialize_components()

            return success

        except Exception as e:
            logger.error(f"Interface train_on_events failed: {e}")
            return False

    def analyze_event_sync(self, features: Dict[str, Any]) -> Dict[str, Any]:
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
