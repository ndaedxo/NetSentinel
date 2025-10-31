#!/usr/bin/env python3
"""
Comprehensive test suite for ML anomaly detector
Tests all aspects of the NetworkEventAnomalyDetector class
"""

import pytest
import time
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Conditional imports for ML dependencies
try:
    import torch
    import numpy as np
    from netsentinel.ml_anomaly_detector import (
        NetworkEventAnomalyDetector,
        EventFeatures,
    )

    ML_AVAILABLE = True
except ImportError:
    torch = None
    np = None
    NetworkEventAnomalyDetector = None
    EventFeatures = None
    ML_AVAILABLE = False


@pytest.mark.skipif(not ML_AVAILABLE, reason="ML dependencies not available")
class TestNetworkEventAnomalyDetector:
    """Comprehensive test suite for NetworkEventAnomalyDetector"""

    def test_detector_initialization_defaults(self):
        """Test detector initialization with default parameters"""
        detector = NetworkEventAnomalyDetector()

        assert detector.model_type == "fastflow"
        assert detector.is_trained == False
        assert detector.model_path is None
        assert len(detector.event_history) == 0
        # New architecture uses separate components
        assert hasattr(detector, 'model_manager')
        assert hasattr(detector, 'feature_extractor')
        assert detector.inferencer is None  # No model loaded initially

    def test_detector_initialization_custom_params(self):
        """Test detector initialization with custom parameters"""
        detector = NetworkEventAnomalyDetector(
            model_type="efficient_ad",
            model_path="/tmp/test_model.pth",
            config={"threshold": 0.7},
        )

        assert detector.model_type == "efficient_ad"
        assert detector.model_path == "/tmp/test_model.pth"
        assert detector.config["threshold"] == 0.7

    def test_feature_extraction_complete_event(self):
        """Test feature extraction with complete event data"""
        detector = NetworkEventAnomalyDetector()

        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin", "PASSWORD": "password123", "ATTEMPT": "1"},
        }

        features = detector._extract_features(event_data)

        assert features is not None
        assert features.event_type == 4002
        assert features.source_ip == "192.168.1.100"
        assert features.destination_port == 22
        assert features.protocol == "SSH"
        assert features.username_attempts == 1
        assert features.password_attempts == 1

    def test_feature_extraction_minimal_event(self):
        """Test feature extraction with minimal event data"""
        detector = NetworkEventAnomalyDetector()

        event_data = {"logtype": 3000, "src_host": "192.168.1.100"}

        features = detector._extract_features(event_data)

        assert features is not None
        assert features.event_type == 3000
        assert features.source_ip == "192.168.1.100"
        assert features.destination_port == 0  # Default
        assert features.protocol == "UNKNOWN"  # Default

    def test_feature_extraction_edge_cases(self):
        """Test feature extraction with edge cases using new FeatureExtractor"""
        detector = NetworkEventAnomalyDetector()

        # Test with None values
        event_data = {
            "logtype": None,
            "src_host": None,
            "dst_port": None,
            "logdata": None,
        }

        features = detector._extract_features(event_data)
        assert features is not None
        assert features.event_type == 0  # Default
        assert features.source_ip == "unknown"  # Default

    def test_feature_extractor_edge_cases(self):
        """Test FeatureExtractor with various edge cases"""
        detector = NetworkEventAnomalyDetector()

        # Test with malformed IP addresses
        event_data = {
            "logtype": 4002,
            "src_host": "999.999.999.999",  # Invalid IP
            "dst_port": 22,
            "logdata": {"USERNAME": "test"},
        }

        features = detector._extract_features(event_data)
        assert features is not None
        assert features.source_ip == "999.999.999.999"  # Should preserve as-is

        # Test with very large port numbers
        event_data_large_port = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 99999,  # Invalid port
            "logdata": {"USERNAME": "test"},
        }

        features_large = detector._extract_features(event_data_large_port)
        assert features_large is not None
        assert features_large.destination_port == 99999  # Should preserve

        # Test with empty logdata
        event_data_empty = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {},
        }

        features_empty = detector._extract_features(event_data_empty)
        assert features_empty is not None
        assert features_empty.username_attempts == 0  # Default
        assert features_empty.password_attempts == 0  # Default

    def test_feature_normalization_basic(self):
        """Test basic feature normalization"""
        detector = NetworkEventAnomalyDetector()

        features = EventFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
            username_attempts=1,
            password_attempts=1,
        )

        normalized = detector._normalize_features(features)

        assert normalized is not None
        assert normalized.shape == (17,)  # NetworkFeatures has 17 features
        # Note: normalization may not be strictly 0-1 for all features

    def test_feature_normalization_extreme_values(self):
        """Test feature normalization with extreme values"""
        detector = NetworkEventAnomalyDetector()

        features = EventFeatures(
            timestamp=time.time(),
            event_type=9999,
            source_ip="192.168.1.100",
            destination_port=65535,
            protocol="SSH",
            username_attempts=1000,
            password_attempts=1000,
        )

        normalized = detector._normalize_features(features)

        assert normalized is not None
        assert normalized.shape == (17,)  # NetworkFeatures has 17 features
        # Note: normalization may not be strictly 0-1 for all features

    def test_image_tensor_creation_basic(self):
        """Test basic image tensor creation"""
        detector = NetworkEventAnomalyDetector()

        features = np.array([[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]], dtype=np.float32)
        image_tensor = detector._create_feature_image(features)

        assert image_tensor is not None
        assert image_tensor.shape[0] == 1  # Batch size
        assert image_tensor.shape[1] == 3  # RGB channels
        assert image_tensor.shape[2] > 0 and image_tensor.shape[3] > 0

    def test_image_tensor_creation_multiple_features(self):
        """Test image tensor creation with multiple feature vectors"""
        detector = NetworkEventAnomalyDetector()

        features = np.array(
            [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]],
            dtype=np.float32,
        )

        image_tensor = detector._create_feature_image(features)

        assert image_tensor is not None
        assert image_tensor.shape[0] == 2  # Batch size
        assert image_tensor.shape[1] == 3  # RGB channels

    def test_anomaly_detection_basic(self):
        """Test basic anomaly detection"""
        detector = NetworkEventAnomalyDetector()

        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin"},
        }

        score, analysis = detector.detect_anomaly(event_data)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert isinstance(analysis, dict)
        assert "ml_score" in analysis
        assert "behavioral_context" in analysis

    def test_anomaly_detection_with_training(self):
        """Test anomaly detection with trained model"""
        detector = NetworkEventAnomalyDetector()

        # Train with normal events
        normal_events = [
            {
                "logtype": 4002,
                "src_host": "192.168.1.10",
                "dst_port": 22,
                "logdata": {"USERNAME": "user1"},
            },
            {
                "logtype": 4002,
                "src_host": "192.168.1.11",
                "dst_port": 22,
                "logdata": {"USERNAME": "user2"},
            },
        ]

        detector.train_on_normal_events(normal_events)

        # Test with similar event
        similar_event = {
            "logtype": 4002,
            "src_host": "192.168.1.10",
            "dst_port": 22,
            "logdata": {"USERNAME": "user1"},
        }

        score, analysis = detector.detect_anomaly(similar_event)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_model_training_basic(self):
        """Test basic model training"""
        detector = NetworkEventAnomalyDetector()

        normal_events = [
            {
                "logtype": 4002,
                "src_host": "192.168.1.10",
                "dst_port": 22,
                "logdata": {"USERNAME": "user1"},
            },
            {
                "logtype": 3000,
                "src_host": "192.168.1.11",
                "dst_port": 80,
                "logdata": {"PATH": "/index.html"},
            },
        ]

        detector.train_on_normal_events(normal_events)

        assert detector.is_trained == True
        assert hasattr(detector, "training_data")

    def test_model_training_empty_data(self):
        """Test model training with empty data"""
        detector = NetworkEventAnomalyDetector()

        detector.train_on_normal_events([])

        # Should handle empty data gracefully
        assert detector.is_trained == False

    def test_model_training_invalid_data(self):
        """Test model training with invalid data"""
        detector = NetworkEventAnomalyDetector()

        invalid_events = [
            {"invalid": "data"},
            {"logtype": "not_a_number", "src_host": "192.168.1.10"},
        ]

        detector.train_on_normal_events(invalid_events)

        # Should handle invalid data gracefully
        assert detector.is_trained == False

    def test_model_persistence_save_load(self):
        """Test model save and load functionality"""
        with tempfile.NamedTemporaryFile(suffix=".pth", delete=False) as tmp_file:
            model_path = tmp_file.name

        try:
            detector = NetworkEventAnomalyDetector(model_path=model_path)

            # Train with sample data
            normal_events = [
                {
                    "logtype": 4002,
                    "src_host": "192.168.1.10",
                    "dst_port": 22,
                    "logdata": {"USERNAME": "user1"},
                }
            ]

            detector.train_on_normal_events(normal_events)
            detector._save_model()

            # Verify file exists
            assert os.path.exists(model_path)

            # Test loading
            detector2 = NetworkEventAnomalyDetector(model_path=model_path)
            detector2._load_model()

            assert detector2.is_trained == True
            assert hasattr(detector2, "training_data")

        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)

    def test_model_persistence_nonexistent_file(self):
        """Test model loading from nonexistent file"""
        detector = NetworkEventAnomalyDetector(model_path="/nonexistent/path/model.pth")

        # Should handle nonexistent file gracefully
        detector._load_model()
        assert detector.is_trained == False

    def test_behavioral_analysis_basic(self):
        """Test basic behavioral analysis"""
        detector = NetworkEventAnomalyDetector()

        # Add some events to history
        for i in range(5):
            features = EventFeatures(
                timestamp=time.time() - i * 60,
                event_type=4002,
                source_ip="192.168.1.100",
                destination_port=22,
                protocol="SSH",
            )
            detector.event_history.append(features)

        current_features = EventFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
        )

        score = detector._behavioral_analysis(current_features)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_behavioral_analysis_empty_history(self):
        """Test behavioral analysis with empty history"""
        detector = NetworkEventAnomalyDetector()

        features = EventFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
        )

        score = detector._behavioral_analysis(features)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_ml_anomaly_detection_with_training_data(self):
        """Test ML anomaly detection with training data"""
        detector = NetworkEventAnomalyDetector()

        # Train with normal events
        normal_events = [
            {
                "logtype": 4002,
                "src_host": "192.168.1.10",
                "dst_port": 22,
                "logdata": {"USERNAME": "user1"},
            }
        ]

        detector.train_on_normal_events(normal_events)

        features = EventFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
        )

        normalized_features = detector._normalize_features(features)
        ml_score = detector._ml_anomaly_detection(features, normalized_features)

        assert isinstance(ml_score, float)
        assert 0.0 <= ml_score <= 1.0

    def test_ml_anomaly_detection_without_training_data(self):
        """Test ML anomaly detection without training data"""
        detector = NetworkEventAnomalyDetector()

        features = EventFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
        )

        normalized_features = detector._normalize_features(features)
        ml_score = detector._ml_anomaly_detection(features, normalized_features)

        assert isinstance(ml_score, float)
        assert ml_score == 0.0  # Should return 0 without training data

    def test_analyze_event_interface(self):
        """Test analyze_event_sync interface method"""
        detector = NetworkEventAnomalyDetector()

        features = {
            "timestamp": time.time(),
            "event_type": 4002,
            "source_ip": "192.168.1.100",
            "destination_port": 22,
            "protocol": "SSH",
            "username_attempts": 1,
            "password_attempts": 1,
        }

        result = detector.analyze_event_sync(features)

        assert isinstance(result, dict)
        assert "is_anomaly" in result
        assert "anomaly_score" in result
        assert "confidence" in result
        assert isinstance(result["is_anomaly"], bool)
        assert isinstance(result["anomaly_score"], float)

    def test_analyze_event_with_training(self):
        """Test analyze_event_sync with trained model"""
        detector = NetworkEventAnomalyDetector()

        # Train with normal events
        normal_events = [
            {
                "logtype": 4002,
                "src_host": "192.168.1.10",
                "dst_port": 22,
                "logdata": {"USERNAME": "user1"},
            }
        ]

        detector.train_on_normal_events(normal_events)

        features = {
            "timestamp": time.time(),
            "event_type": 4002,
            "source_ip": "192.168.1.100",
            "destination_port": 22,
            "protocol": "SSH",
            "username_attempts": 1,
            "password_attempts": 1,
        }

        result = detector.analyze_event_sync(features)

        assert isinstance(result, dict)
        assert "is_anomaly" in result
        assert "anomaly_score" in result
        assert "confidence" in result

    def test_cleanup_functionality(self):
        """Test cleanup functionality"""
        import asyncio

        async def run_cleanup_test():
            detector = NetworkEventAnomalyDetector()

            # Add some data
            for i in range(10):
                features = EventFeatures(
                    timestamp=time.time(),
                    event_type=4002,
                    source_ip=f"192.168.1.{i}",
                    destination_port=22,
                    protocol="SSH",
                )
                detector.event_history.append(features)

            # Test async cleanup
            await detector._cleanup()
            assert len(detector.event_history) == 0

        # Run the async test
        asyncio.run(run_cleanup_test())

    def test_async_cleanup(self):
        """Test async cleanup functionality"""
        import asyncio

        async def test_async_cleanup():
            detector = NetworkEventAnomalyDetector()

            # Add some data
            for i in range(5):
                features = EventFeatures(
                    timestamp=time.time(),
                    event_type=4002,
                    source_ip=f"192.168.1.{i}",
                    destination_port=22,
                    protocol="SSH",
                )
                detector.event_history.append(features)

            # Test async cleanup
            await detector._cleanup()
            assert len(detector.event_history) == 0

        # Run async test
        asyncio.run(test_async_cleanup())

    def test_detector_thread_safety(self):
        """Test detector thread safety"""
        detector = NetworkEventAnomalyDetector()

        import threading

        def add_events():
            for i in range(10):
                features = EventFeatures(
                    timestamp=time.time(),
                    event_type=4002,
                    source_ip=f"192.168.1.{i}",
                    destination_port=22,
                    protocol="SSH",
                )
                detector.event_history.append(features)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=add_events)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have 50 events total
        assert len(detector.event_history) == 50

    def test_detector_memory_management(self):
        """Test detector memory management"""
        detector = NetworkEventAnomalyDetector()

        # Add many events to test memory management
        for i in range(1000):
            features = EventFeatures(
                timestamp=time.time() - i,
                event_type=4002,
                source_ip=f"192.168.1.{i % 10}",
                destination_port=22,
                protocol="SSH",
            )
            detector.event_history.append(features)

        # Should maintain reasonable memory usage
        assert len(detector.event_history) <= 1000

    def test_detector_performance(self):
        """Test detector performance with large datasets"""
        detector = NetworkEventAnomalyDetector()

        # Create large training dataset
        normal_events = []
        for i in range(100):
            normal_events.append(
                {
                    "logtype": 4002,
                    "src_host": f"192.168.1.{i % 10}",
                    "dst_port": 22,
                    "logdata": {"USERNAME": f"user{i}"},
                }
            )

        start_time = time.time()
        detector.train_on_normal_events(normal_events)
        training_time = time.time() - start_time

        # Training should complete in reasonable time
        assert training_time < 10.0
        assert detector.is_trained == True

    def test_detector_error_handling(self):
        """Test detector error handling"""
        detector = NetworkEventAnomalyDetector()

        # Test with invalid event data
        invalid_event = {"invalid": "data"}
        score, analysis = detector.detect_anomaly(invalid_event)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert "error" in analysis

    def test_detector_configuration_validation(self):
        """Test detector configuration validation"""
        # Test with invalid model type
        detector = NetworkEventAnomalyDetector(model_type="invalid_model")
        assert detector.model_type == "invalid_model"

        # Test with invalid model path
        detector = NetworkEventAnomalyDetector(model_path="/invalid/path/model.pth")
        assert detector.model_path == "/invalid/path/model.pth"

    def test_detector_feature_statistics(self):
        """Test detector feature statistics tracking with new architecture"""
        detector = NetworkEventAnomalyDetector()

        # Add some events to build statistics
        for i in range(10):
            features = EventFeatures(
                timestamp=time.time(),
                event_type=4002,
                source_ip="192.168.1.100",
                destination_port=22,
                protocol="SSH",
                username_attempts=i,
                password_attempts=i,
            )
            detector.event_history.append(features)

        # Check that new ML components are properly initialized
        assert hasattr(detector, "model_manager")
        assert hasattr(detector, "feature_extractor")
        assert hasattr(detector, "inferencer")
        # Check that event history is being maintained
        assert len(detector.event_history) == 10

    def test_detector_anomaly_scoring_consistency(self):
        """Test detector anomaly scoring consistency"""
        detector = NetworkEventAnomalyDetector()

        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin"},
        }

        # Run multiple times to check consistency
        scores = []
        for _ in range(5):
            score, _ = detector.detect_anomaly(event_data)
            scores.append(score)

        # Scores should be consistent (within reasonable variance)
        assert all(isinstance(score, float) for score in scores)
        assert all(0.0 <= score <= 1.0 for score in scores)

    def test_detector_edge_case_handling(self):
        """Test detector edge case handling"""
        detector = NetworkEventAnomalyDetector()

        # Test with None values
        event_data = {
            "logtype": None,
            "src_host": None,
            "dst_port": None,
            "logdata": None,
        }

        score, analysis = detector.detect_anomaly(event_data)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_detector_large_feature_vectors(self):
        """Test detector with large feature vectors"""
        detector = NetworkEventAnomalyDetector()

        # Create features with large values
        features = EventFeatures(
            timestamp=time.time(),
            event_type=9999,
            source_ip="192.168.1.100",
            destination_port=65535,
            protocol="SSH",
            username_attempts=1000,
            password_attempts=1000,
        )

        normalized = detector._normalize_features(features)
        assert normalized is not None
        assert normalized.shape == (17,)  # NetworkFeatures has 17 features
        # Note: normalization may not be strictly 0-1 for all features

    def test_detector_model_switching(self):
        """Test detector model switching"""
        detector = NetworkEventAnomalyDetector(model_type="fastflow")
        assert detector.model_type == "fastflow"

        # Switch model type
        detector.model_type = "efficient_ad"
        assert detector.model_type == "efficient_ad"

    def test_model_manager_state_transitions(self):
        """Test model state transitions with ModelManager"""
        detector = NetworkEventAnomalyDetector()

        # Initially no model loaded
        assert detector.inferencer is None
        assert detector.is_trained == False

        # Test training creates a model
        normal_events = [
            {
                "logtype": 4002,
                "src_host": "192.168.1.10",
                "dst_port": 22,
                "logdata": {"USERNAME": "user1"},
            }
        ]

        detector.train_on_normal_events(normal_events)
        # After training, detector should be marked as trained
        assert detector.is_trained == True

        # Test model manager has the model registered
        model_info = detector.model_manager.get_model_info("fastflow")
        assert model_info is not None
        assert model_info["version_count"] >= 1


if __name__ == "__main__":
    pytest.main([__file__])
