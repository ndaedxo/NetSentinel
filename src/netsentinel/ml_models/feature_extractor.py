#!/usr/bin/env python3
"""
Feature Extractor for NetSentinel ML Components

Handles feature extraction, normalization, and conversion to image format
for anomaly detection models.
"""

import time
import numpy as np
import torch
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
import logging
from collections import defaultdict, deque

# Import new core components
try:
    from ..core.base import BaseComponent
    from ..utils.centralized import create_logger
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from utils.centralized import create_logger

logger = create_logger("feature_extractor", level="INFO")


@dataclass
class NetworkFeatures:
    """Structured representation of network event features"""

    # Basic event information
    timestamp: float
    event_type: int
    source_ip: str
    destination_ip: str = ""
    destination_port: int = 0
    protocol: str = "UNKNOWN"

    # Authentication features
    username_attempts: int = 0
    password_attempts: int = 0
    auth_success: bool = False

    # Connection features
    connection_duration: float = 0.0
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0

    # Error and status features
    error_count: int = 0
    response_code: int = 0
    session_id: str = ""

    # Derived features
    time_of_day: int = 0  # 0-23
    day_of_week: int = 0  # 0-6
    is_weekend: bool = False
    ip_numeric: int = 0  # Numeric representation of IP

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    def to_numpy_array(self) -> np.ndarray:
        """Convert to numpy array for ML processing"""
        # Convert categorical features to numeric
        protocol_map = {
            "UNKNOWN": 0, "TCP": 1, "UDP": 2, "HTTP": 3, "HTTPS": 4,
            "SSH": 5, "FTP": 6, "SMTP": 7, "DNS": 8, "MySQL": 9
        }

        # Create feature vector
        features = np.array([
            self.event_type,
            self.destination_port,
            protocol_map.get(self.protocol, 0),
            self.username_attempts,
            self.password_attempts,
            int(self.auth_success),
            self.connection_duration,
            self.bytes_sent,
            self.bytes_received,
            self.packets_sent,
            self.packets_received,
            self.error_count,
            self.response_code,
            self.time_of_day,
            self.day_of_week,
            int(self.is_weekend),
            self.ip_numeric,
        ], dtype=np.float32)

        return features

    @property
    def protocol_map(self):
        """Protocol mapping for consistency"""
        return {
            "UNKNOWN": 0, "TCP": 1, "UDP": 2, "HTTP": 3, "HTTPS": 4,
            "SSH": 5, "FTP": 6, "SMTP": 7, "DNS": 8, "MySQL": 9
        }


class FeatureExtractor(BaseComponent):
    """
    Extracts and normalizes features from network events for ML processing

    Handles:
    - Feature extraction from raw event data
    - Feature normalization and scaling
    - Conversion to image format for Anomalib
    - Feature statistics tracking
    """

    def __init__(
        self,
        name: str = "feature_extractor",
        normalization_method: str = "standard",
        image_size: Tuple[int, int] = (32, 32),
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize feature extractor

        Args:
            name: Component name
            normalization_method: Method for feature normalization ('standard', 'minmax', 'robust')
            image_size: Size for feature-to-image conversion
            config: Additional configuration
        """
        super().__init__(name, config, logger)

        self.normalization_method = normalization_method
        self.image_size = image_size

        # Feature statistics for normalization
        self.feature_stats = {}
        self.feature_history = defaultdict(lambda: deque(maxlen=1000))

        # Normalization parameters
        self.scaler_mean = None
        self.scaler_std = None
        self.scaler_min = None
        self.scaler_max = None

        # Feature importance weights (learned or predefined)
        self.feature_weights = self._get_default_feature_weights()

        # Protocol mapping
        self.protocol_mapping = {
            2000: "FTP", 3000: "HTTP", 4000: "SSH", 6001: "TELNET",
            8001: "MySQL", 4002: "SSH", 5001: "SMTP", 53: "DNS",
        }

    def _get_default_feature_weights(self) -> Dict[str, float]:
        """Get default feature importance weights"""
        return {
            "event_type": 1.0,
            "destination_port": 0.8,
            "protocol": 0.7,
            "username_attempts": 1.0,
            "password_attempts": 1.0,
            "auth_success": 0.9,
            "connection_duration": 0.6,
            "bytes_sent": 0.5,
            "bytes_received": 0.5,
            "packets_sent": 0.4,
            "packets_received": 0.4,
            "error_count": 0.9,
            "response_code": 0.7,
            "time_of_day": 0.3,
            "day_of_week": 0.2,
            "is_weekend": 0.2,
            "ip_numeric": 0.1,
        }

    def extract_features(self, event_data: Dict[str, Any]) -> Optional[NetworkFeatures]:
        """
        Extract features from raw event data

        Args:
            event_data: Raw event dictionary

        Returns:
            NetworkFeatures object or None if extraction fails
        """
        try:
            # Basic event information
            event_type = event_data.get("logtype", 0)
            source_ip = event_data.get("src_host", "unknown")
            dest_ip = event_data.get("dst_host", "")
            dest_port = event_data.get("dst_port", 0)

            # Determine protocol
            protocol = self._determine_protocol(event_type, dest_port)

            # Extract authentication features
            logdata = event_data.get("logdata", {})
            username_attempts = 1 if "USERNAME" in str(logdata) else 0
            password_attempts = 1 if "PASSWORD" in str(logdata) else 0
            auth_success = self._determine_auth_success(logdata)

            # Extract connection features
            connection_duration = event_data.get("duration", 0.0)
            bytes_sent = event_data.get("bytes_sent", 0)
            bytes_received = event_data.get("bytes_received", 0)
            packets_sent = event_data.get("packets_sent", 0)
            packets_received = event_data.get("packets_received", 0)

            # Error and status features
            error_count = event_data.get("error_count", 0)
            response_code = logdata.get("response_code", 0) if isinstance(logdata, dict) else 0
            session_id = event_data.get("session_id", "")

            # Temporal features
            timestamp = event_data.get("timestamp", time.time())
            time_of_day, day_of_week, is_weekend = self._extract_temporal_features(timestamp)

            # IP numeric representation
            ip_numeric = self._ip_to_numeric(source_ip)

            # Create NetworkFeatures object
            features = NetworkFeatures(
                timestamp=timestamp,
                event_type=event_type,
                source_ip=source_ip,
                destination_ip=dest_ip,
                destination_port=dest_port,
                protocol=protocol,
                username_attempts=username_attempts,
                password_attempts=password_attempts,
                auth_success=auth_success,
                connection_duration=connection_duration,
                bytes_sent=bytes_sent,
                bytes_received=bytes_received,
                packets_sent=packets_sent,
                packets_received=packets_received,
                error_count=error_count,
                response_code=response_code,
                session_id=session_id,
                time_of_day=time_of_day,
                day_of_week=day_of_week,
                is_weekend=is_weekend,
                ip_numeric=ip_numeric,
            )

            # Update feature statistics
            self._update_feature_stats(features)

            return features

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    def _determine_protocol(self, event_type: int, dest_port: int) -> str:
        """Determine protocol from event type and port"""
        # Try event type first
        if event_type in self.protocol_mapping:
            return self.protocol_mapping[event_type]

        # Try port-based detection
        port_protocol_map = {
            22: "SSH", 23: "TELNET", 25: "SMTP", 53: "DNS",
            80: "HTTP", 443: "HTTPS", 21: "FTP", 3306: "MySQL",
        }

        return port_protocol_map.get(dest_port, "UNKNOWN")

    def _determine_auth_success(self, logdata: Any) -> bool:
        """Determine if authentication was successful"""
        if not isinstance(logdata, dict):
            return False

        # Look for success indicators
        success_indicators = ["LOGIN_SUCCESS", "AUTH_SUCCESS", "SUCCESS"]
        failure_indicators = ["LOGIN_FAILED", "AUTH_FAILED", "FAILED", "INVALID"]

        logdata_str = str(logdata).upper()

        # Check for failure first (more reliable)
        for indicator in failure_indicators:
            if indicator in logdata_str:
                return False

        # Check for success
        for indicator in success_indicators:
            if indicator in logdata_str:
                return True

        return False

    def _extract_temporal_features(self, timestamp: float) -> Tuple[int, int, bool]:
        """Extract temporal features from timestamp"""
        from datetime import datetime

        dt = datetime.fromtimestamp(timestamp)
        time_of_day = dt.hour
        day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
        is_weekend = day_of_week >= 5  # Saturday or Sunday

        return time_of_day, day_of_week, is_weekend

    def _ip_to_numeric(self, ip: str) -> int:
        """Convert IP address to numeric representation"""
        try:
            parts = ip.split('.')
            if len(parts) == 4:
                return sum(int(part) * (256 ** (3 - i)) for i, part in enumerate(parts))
            return 0
        except (ValueError, AttributeError):
            return 0

    def _update_feature_stats(self, features: NetworkFeatures):
        """Update feature statistics for normalization"""
        feature_dict = features.to_dict()

        # Update feature history
        for key, value in feature_dict.items():
            if isinstance(value, (int, float)):
                self.feature_history[key].append(value)

        # Recalculate statistics periodically
        if len(self.feature_history["event_type"]) % 100 == 0:
            self._recalculate_statistics()

    def _recalculate_statistics(self):
        """Recalculate feature statistics"""
        try:
            self.feature_stats = {}

            for feature_name, history in self.feature_history.items():
                if not history:
                    continue

                values = np.array(list(history))
                self.feature_stats[feature_name] = {
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "median": float(np.median(values)),
                }

        except Exception as e:
            logger.error(f"Failed to recalculate statistics: {e}")

    def normalize_features(
        self, features: NetworkFeatures, update_stats: bool = True
    ) -> np.ndarray:
        """
        Normalize features using configured method

        Args:
            features: NetworkFeatures to normalize
            update_stats: Whether to update running statistics

        Returns:
            Normalized feature array
        """
        try:
            # Convert to numpy array
            feature_array = features.to_numpy_array()

            if update_stats:
                self._update_feature_stats(features)

            # Apply normalization
            if self.normalization_method == "standard":
                normalized = self._standard_normalization(feature_array)
            elif self.normalization_method == "minmax":
                normalized = self._minmax_normalization(feature_array)
            elif self.normalization_method == "robust":
                normalized = self._robust_normalization(feature_array)
            else:
                logger.warning(f"Unknown normalization method: {self.normalization_method}")
                normalized = feature_array

            return normalized

        except Exception as e:
            logger.error(f"Feature normalization failed: {e}")
            return np.zeros(17, dtype=np.float32)  # Return zero vector

    def _standard_normalization(self, features: np.ndarray) -> np.ndarray:
        """Apply standard (z-score) normalization"""
        if not self.feature_stats:
            return features

        normalized = features.copy()

        for i, feature_name in enumerate(NetworkFeatures.__dataclass_fields__.keys()):
            if feature_name in self.feature_stats and i < len(features):
                stats = self.feature_stats[feature_name]
                mean = stats["mean"]
                std = stats["std"]

                if std > 0:
                    normalized[i] = (features[i] - mean) / std
                else:
                    normalized[i] = 0.0

        return normalized

    def _minmax_normalization(self, features: np.ndarray) -> np.ndarray:
        """Apply min-max normalization"""
        if not self.feature_stats:
            return features

        normalized = features.copy()

        for i, feature_name in enumerate(NetworkFeatures.__dataclass_fields__.keys()):
            if feature_name in self.feature_stats and i < len(features):
                stats = self.feature_stats[feature_name]
                min_val = stats["min"]
                max_val = stats["max"]

                if max_val > min_val:
                    normalized[i] = (features[i] - min_val) / (max_val - min_val)
                else:
                    normalized[i] = 0.0

        return normalized

    def _robust_normalization(self, features: np.ndarray) -> np.ndarray:
        """Apply robust normalization using median and IQR"""
        if not self.feature_stats:
            return features

        normalized = features.copy()

        for i, feature_name in enumerate(NetworkFeatures.__dataclass_fields__.keys()):
            if feature_name in self.feature_stats and i < len(features):
                stats = self.feature_stats[feature_name]
                median = stats["median"]
                # Approximate IQR (this could be improved with actual IQR calculation)
                iqr = (stats["max"] - stats["min"]) * 0.5

                if iqr > 0:
                    normalized[i] = (features[i] - median) / iqr
                else:
                    normalized[i] = 0.0

        return normalized

    def features_to_image(
        self, features: np.ndarray, method: str = "direct"
    ) -> torch.Tensor:
        """
        Convert normalized features to image tensor for Anomalib

        Args:
            features: Normalized feature array
            method: Conversion method ('direct', 'histogram', 'positional')

        Returns:
            Image tensor for Anomalib models
        """
        try:
            if method == "direct":
                return self._direct_image_conversion(features)
            elif method == "histogram":
                return self._histogram_image_conversion(features)
            elif method == "positional":
                return self._positional_image_conversion(features)
            else:
                logger.warning(f"Unknown conversion method: {method}")
                return self._direct_image_conversion(features)

        except Exception as e:
            logger.error(f"Feature to image conversion failed: {e}")
            return torch.zeros((1, 3, self.image_size[0], self.image_size[1]))

    def _direct_image_conversion(self, features: np.ndarray) -> torch.Tensor:
        """Direct mapping of features to image pixels"""
        height, width = self.image_size
        image = np.zeros((height, width, 3), dtype=np.float32)

        # Map features to RGB channels
        num_features = len(features)

        for i, feature_value in enumerate(features):
            if i >= height * width:
                break

            row = i // width
            col = i % width

            # Map to RGB based on feature value
            intensity = max(0.0, min(1.0, feature_value))  # Clamp to [0, 1]
            image[row, col] = [intensity, intensity, intensity]

        # Convert to tensor with batch and channel dimensions
        tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)

        return tensor

    def _histogram_image_conversion(self, features: np.ndarray) -> torch.Tensor:
        """Convert features to image using histogram representation"""
        height, width = self.image_size
        image = np.zeros((height, width, 3), dtype=np.float32)

        # Create histogram-like representation
        num_bins = min(width, len(features))

        for channel in range(3):
            start_idx = channel * (len(features) // 3)
            end_idx = (channel + 1) * (len(features) // 3)

            channel_features = features[start_idx:end_idx]
            if len(channel_features) == 0:
                continue

            # Create histogram
            hist, bin_edges = np.histogram(channel_features, bins=num_bins, range=(-3, 3))

            # Normalize histogram
            if hist.max() > 0:
                hist = hist / hist.max()

            # Map to image row
            row = channel * (height // 3)
            image[row, :len(hist)] = hist.reshape(1, -1, 1)

        tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)
        return tensor

    def _positional_image_conversion(self, features: np.ndarray) -> torch.Tensor:
        """Convert features to image using positional encoding"""
        height, width = self.image_size
        image = np.zeros((height, width, 3), dtype=np.float32)

        # Use positional encoding to map features to spatial positions
        num_features = len(features)

        for i, feature_value in enumerate(features):
            # Create positional coordinates
            x = (i % int(np.sqrt(num_features))) * (width // int(np.sqrt(num_features)))
            y = (i // int(np.sqrt(num_features))) * (height // int(np.sqrt(num_features)))

            # Clamp coordinates
            x = min(x, width - 1)
            y = min(y, height - 1)

            # Map feature value to RGB
            intensity = max(0.0, min(1.0, (feature_value + 3) / 6))  # Map [-3, 3] to [0, 1]
            image[y, x] = [intensity, intensity, intensity]

        tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)
        return tensor

    def get_feature_statistics(self) -> Dict[str, Any]:
        """Get current feature statistics"""
        return {
            "normalization_method": self.normalization_method,
            "image_size": self.image_size,
            "feature_stats": self.feature_stats,
            "history_sizes": {k: len(v) for k, v in self.feature_history.items()},
            "feature_weights": self.feature_weights,
        }

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize feature extractor resources"""
        logger.info("Feature extractor initialized")

    async def _start_internal(self):
        """Start feature extractor internal operations"""
        # No background operations needed
        pass

    async def _stop_internal(self):
        """Stop feature extractor internal operations"""
        # No background operations to stop
        pass

    async def _cleanup(self):
        """Cleanup feature extractor resources"""
        # Clear feature history and statistics
        self.feature_history.clear()
        self.feature_stats.clear()
        logger.info("Feature extractor cleanup completed")
