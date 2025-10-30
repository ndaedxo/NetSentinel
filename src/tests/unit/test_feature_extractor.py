#!/usr/bin/env python3
"""
Unit tests for FeatureExtractor component
"""

import pytest
import time
import numpy as np
from unittest.mock import Mock, patch

# Conditional imports for ML dependencies
try:
    import torch
    from netsentinel.ml_models.feature_extractor import FeatureExtractor, NetworkFeatures

    ML_AVAILABLE = True
except ImportError:
    torch = None
    FeatureExtractor = None
    NetworkFeatures = None
    ML_AVAILABLE = False


@pytest.mark.skipif(not ML_AVAILABLE, reason="ML dependencies not available")
class TestFeatureExtractor:
    """Comprehensive test suite for FeatureExtractor"""

    def test_extractor_initialization_defaults(self):
        """Test feature extractor initialization with defaults"""
        extractor = FeatureExtractor()

        assert extractor.normalization_method == "standard"
        assert extractor.image_size == (32, 32)
        assert isinstance(extractor.feature_stats, dict)
        assert isinstance(extractor.feature_history, dict)
        assert extractor.scaler_mean is None

    def test_extractor_initialization_custom_params(self):
        """Test feature extractor initialization with custom parameters"""
        extractor = FeatureExtractor(
            normalization_method="minmax",
            image_size=(64, 64),
            config={"custom_param": "value"}
        )

        assert extractor.normalization_method == "minmax"
        assert extractor.image_size == (64, 64)

    def test_network_features_dataclass(self):
        """Test NetworkFeatures dataclass functionality"""
        features = NetworkFeatures(
            timestamp=1234567890.0,
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
            username_attempts=1,
            password_attempts=0,
        )

        # Test conversion methods
        data_dict = features.to_dict()
        assert data_dict["event_type"] == 4002
        assert data_dict["protocol"] == "SSH"

        # Test numpy conversion
        features_array = features.to_numpy_array()
        assert isinstance(features_array, np.ndarray)
        assert features_array.shape[0] == 17  # Number of features

    def test_feature_extraction_complete_event(self):
        """Test feature extraction with complete event data"""
        extractor = FeatureExtractor()

        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_host": "192.168.1.200",
            "dst_port": 22,
            "logdata": {
                "USERNAME": "admin",
                "PASSWORD": "secret",
                "response_code": 200,
            },
            "timestamp": 1234567890.0,
            "duration": 5.5,
            "bytes_sent": 1024,
            "bytes_received": 2048,
            "packets_sent": 10,
            "packets_received": 8,
            "error_count": 0,
        }

        features = extractor.extract_features(event_data)

        assert features is not None
        assert features.event_type == 4002
        assert features.source_ip == "192.168.1.100"
        assert features.destination_port == 22
        assert features.protocol == "SSH"
        assert features.username_attempts == 1
        assert features.password_attempts == 1
        assert features.auth_success == False  # No success indicator
        assert features.connection_duration == 5.5
        assert features.error_count == 0

    def test_feature_extraction_minimal_event(self):
        """Test feature extraction with minimal event data"""
        extractor = FeatureExtractor()

        event_data = {
            "logtype": 3000,
            "src_host": "192.168.1.100",
        }

        features = extractor.extract_features(event_data)

        assert features is not None
        assert features.event_type == 3000
        assert features.protocol == "HTTP"  # From event type mapping
        assert features.username_attempts == 0
        assert features.password_attempts == 0

    def test_protocol_determination(self):
        """Test protocol determination logic"""
        extractor = FeatureExtractor()

        # Test event type mapping
        assert extractor._determine_protocol(4002, 22) == "SSH"
        assert extractor._determine_protocol(3000, 80) == "HTTP"
        assert extractor._determine_protocol(9999, 443) == "HTTPS"  # Port-based

        # Test port-based fallback
        assert extractor._determine_protocol(9999, 3306) == "MySQL"

    def test_auth_success_detection(self):
        """Test authentication success detection"""
        extractor = FeatureExtractor()

        # Test success detection
        logdata_success = {"LOGIN_SUCCESS": "true"}
        assert extractor._determine_auth_success(logdata_success) == True

        # Test failure detection
        logdata_failure = {"LOGIN_FAILED": "invalid password"}
        assert extractor._determine_auth_success(logdata_failure) == False

        # Test no auth data
        logdata_empty = {}
        assert extractor._determine_auth_success(logdata_empty) == False

    def test_temporal_feature_extraction(self):
        """Test temporal feature extraction"""
        extractor = FeatureExtractor()

        # Test with known timestamp (e.g., Monday, 10 AM)
        monday_10am = 1609459200.0  # 2021-01-01 10:00:00 UTC (Friday)
        hour, day_of_week, is_weekend = extractor._extract_temporal_features(monday_10am)

        assert isinstance(hour, int)
        assert isinstance(day_of_week, int)
        assert isinstance(is_weekend, bool)
        assert 0 <= hour <= 23
        assert 0 <= day_of_week <= 6

    def test_ip_numeric_conversion(self):
        """Test IP address to numeric conversion"""
        extractor = FeatureExtractor()

        # Test valid IP
        numeric = extractor._ip_to_numeric("192.168.1.100")
        assert isinstance(numeric, int)
        assert numeric > 0

        # Test invalid IP
        numeric_invalid = extractor._ip_to_numeric("invalid")
        assert numeric_invalid == 0

    def test_feature_normalization_standard(self):
        """Test standard (z-score) normalization"""
        extractor = FeatureExtractor()
        extractor.normalization_method = "standard"

        # Create test features
        features = NetworkFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
        )

        # Build some statistics first
        extractor._update_feature_stats(features)
        extractor._recalculate_statistics()

        # Normalize
        normalized = extractor.normalize_features(features)
        assert isinstance(normalized, np.ndarray)
        assert normalized.shape[0] == 17

    def test_feature_normalization_minmax(self):
        """Test min-max normalization"""
        extractor = FeatureExtractor()
        extractor.normalization_method = "minmax"

        features = NetworkFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
        )

        normalized = extractor.normalize_features(features)
        assert isinstance(normalized, np.ndarray)

    def test_feature_normalization_robust(self):
        """Test robust normalization"""
        extractor = FeatureExtractor()
        extractor.normalization_method = "robust"

        features = NetworkFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
        )

        normalized = extractor.normalize_features(features)
        assert isinstance(normalized, np.ndarray)

    def test_image_conversion_direct(self):
        """Test direct feature to image conversion"""
        extractor = FeatureExtractor()

        features = np.random.rand(17).astype(np.float32)

        image_tensor = extractor.features_to_image(features, method="direct")

        assert isinstance(image_tensor, torch.Tensor)
        assert image_tensor.shape[0] == 1  # batch
        assert image_tensor.shape[1] == 3  # RGB channels
        assert image_tensor.shape[2] == 32  # height
        assert image_tensor.shape[3] == 32  # width

    def test_image_conversion_histogram(self):
        """Test histogram-based feature to image conversion"""
        extractor = FeatureExtractor()

        features = np.random.rand(17).astype(np.float32)

        image_tensor = extractor.features_to_image(features, method="histogram")

        assert isinstance(image_tensor, torch.Tensor)
        assert image_tensor.shape[0] == 1
        assert image_tensor.shape[1] == 3

    def test_image_conversion_positional(self):
        """Test positional feature to image conversion"""
        extractor = FeatureExtractor()

        features = np.random.rand(17).astype(np.float32)

        image_tensor = extractor.features_to_image(features, method="positional")

        assert isinstance(image_tensor, torch.Tensor)
        assert image_tensor.shape[0] == 1
        assert image_tensor.shape[1] == 3

    def test_statistics_tracking(self):
        """Test feature statistics tracking"""
        extractor = FeatureExtractor()

        # Add multiple feature samples
        for i in range(10):
            features = NetworkFeatures(
                timestamp=time.time(),
                event_type=4000 + i,
                source_ip=f"192.168.1.{i}",
                destination_port=22 + i,
                protocol="SSH",
            )
            extractor._update_feature_stats(features)

        # Force statistics recalculation
        extractor._recalculate_statistics()

        # Check that statistics were computed
        assert len(extractor.feature_stats) > 0
        assert "event_type" in extractor.feature_stats

        stats = extractor.feature_stats["event_type"]
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats

    def test_get_feature_statistics(self):
        """Test feature statistics retrieval"""
        extractor = FeatureExtractor()

        stats = extractor.get_feature_statistics()

        assert isinstance(stats, dict)
        assert "normalization_method" in stats
        assert "image_size" in stats
        assert "feature_stats" in stats
        assert "feature_weights" in stats

    def test_async_lifecycle(self):
        """Test async lifecycle methods"""
        import asyncio

        async def test_async():
            extractor = FeatureExtractor()

            await extractor._initialize()
            await extractor._start_internal()
            await extractor._stop_internal()
            await extractor._cleanup()

            # Should not raise exceptions
            assert True

        asyncio.run(test_async())

    def test_error_handling(self):
        """Test error handling in feature extractor"""
        extractor = FeatureExtractor()

        # Test with invalid event data
        invalid_event = {"invalid": "data"}
        features = extractor.extract_features(invalid_event)
        assert features is not None  # Should return default features

        # Test normalization with invalid data
        invalid_features = NetworkFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="",  # Invalid IP
            destination_port=22,
            protocol="SSH",
        )

        normalized = extractor.normalize_features(invalid_features)
        assert isinstance(normalized, np.ndarray)

    def test_feature_weights(self):
        """Test feature importance weights"""
        extractor = FeatureExtractor()

        weights = extractor.feature_weights

        assert isinstance(weights, dict)
        assert "event_type" in weights
        assert "username_attempts" in weights
        assert "password_attempts" in weights

        # Check that weights are reasonable
        for weight in weights.values():
            assert isinstance(weight, float)
            assert 0.0 <= weight <= 1.0

    def test_custom_image_size(self):
        """Test feature extractor with custom image size"""
        extractor = FeatureExtractor(image_size=(64, 64))

        features = np.random.rand(17).astype(np.float32)
        image_tensor = extractor.features_to_image(features)

        assert image_tensor.shape[2] == 64  # height
        assert image_tensor.shape[3] == 64  # width


if __name__ == "__main__":
    pytest.main([__file__])
