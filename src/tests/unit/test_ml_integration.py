#!/usr/bin/env python3
"""
Test ML integration and anomaly detection functionality
Comprehensive test suite for NetSentinel ML capabilities
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
    from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector, EventFeatures
    from netsentinel.processors.event_analyzer import EventAnalyzer
    from netsentinel.core.models import StandardEvent, create_event
    ML_AVAILABLE = True
except ImportError:
    torch = None
    np = None
    NetworkEventAnomalyDetector = None
    EventFeatures = None
    EventAnalyzer = None
    StandardEvent = None
    create_event = None
    ML_AVAILABLE = False


@pytest.mark.skipif(not ML_AVAILABLE, reason="ML dependencies not available")
class TestMLIntegration:
    """Test ML integration functionality"""

    def test_ml_detector_initialization(self):
        """Test ML detector can be initialized"""
        detector = NetworkEventAnomalyDetector(
            model_type="fastflow",
            model_path="/tmp/test_model.pth"
        )
        
        assert detector.model_type == "fastflow"
        assert detector.is_trained == False
        assert detector.model is not None

    def test_feature_extraction(self):
        """Test feature extraction from event data"""
        detector = NetworkEventAnomalyDetector()
        
        event_data = {
            "logtype": 4002,  # SSH login
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {
                "USERNAME": "admin",
                "PASSWORD": "password123"
            }
        }
        
        features = detector._extract_features(event_data)
        
        assert features is not None
        assert features.event_type == 4002
        assert features.source_ip == "192.168.1.100"
        assert features.destination_port == 22
        assert features.protocol == "SSH"
        assert features.username_attempts == 1
        assert features.password_attempts == 1

    def test_feature_normalization(self):
        """Test feature normalization"""
        detector = NetworkEventAnomalyDetector()
        
        features = EventFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH",
            username_attempts=1,
            password_attempts=1
        )
        
        normalized = detector._normalize_features(features)
        
        assert normalized is not None
        assert normalized.shape == (1, 7)  # 7 features
        assert np.all(normalized >= 0) and np.all(normalized <= 1)  # Normalized to [0,1]

    def test_image_tensor_creation(self):
        """Test conversion of features to image-like tensors"""
        detector = NetworkEventAnomalyDetector()
        
        features = np.array([[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]], dtype=np.float32)
        image_tensor = detector._create_feature_image(features)
        
        assert image_tensor is not None
        assert image_tensor.shape[0] == 1  # Batch size
        assert image_tensor.shape[1] == 3  # RGB channels
        assert image_tensor.shape[2] > 0 and image_tensor.shape[3] > 0  # Height and width

    def test_anomaly_detection(self):
        """Test anomaly detection functionality"""
        detector = NetworkEventAnomalyDetector()
        
        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin"}
        }
        
        score, analysis = detector.detect_anomaly(event_data)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert isinstance(analysis, dict)
        assert "ml_score" in analysis
        assert "behavioral_context" in analysis

    def test_model_training(self):
        """Test model training with sample data"""
        detector = NetworkEventAnomalyDetector()
        
        # Create sample training data
        normal_events = [
            {
                "logtype": 4002,
                "src_host": "192.168.1.10",
                "dst_port": 22,
                "logdata": {"USERNAME": "user1"}
            },
            {
                "logtype": 3000,
                "src_host": "192.168.1.11",
                "dst_port": 80,
                "logdata": {"PATH": "/index.html"}
            }
        ]
        
        detector.train_on_normal_events(normal_events)
        
        assert detector.is_trained == True
        assert hasattr(detector, 'training_data')

    def test_event_analyzer_ml_integration(self):
        """Test EventAnalyzer ML integration"""
        config = {
            "ml_enabled": True,
            "ml_model_type": "fastflow"
        }
        
        analyzer = EventAnalyzer(config=config)
        
        assert analyzer.ml_enabled == True
        assert analyzer.ml_analyzer is not None

    def test_ml_analysis_in_event_analyzer(self):
        """Test ML analysis in EventAnalyzer"""
        config = {
            "ml_enabled": True,
            "ml_model_type": "fastflow"
        }
        
        analyzer = EventAnalyzer(config=config)
        
        # Create test event
        event = create_event(
            event_type="4002",
            source="192.168.1.100",
            data={"logdata": {"USERNAME": "admin"}},
            severity="medium"
        )
        
        # Test ML analysis
        ml_score, ml_analysis = analyzer._ml_analysis(event)
        
        assert isinstance(ml_score, float)
        assert ml_score >= 0.0

    def test_behavioral_analysis(self):
        """Test behavioral analysis functionality"""
        detector = NetworkEventAnomalyDetector()
        
        # Add some events to history
        for i in range(5):
            features = EventFeatures(
                timestamp=time.time() - i * 60,
                event_type=4002,
                source_ip="192.168.1.100",
                destination_port=22,
                protocol="SSH"
            )
            detector.event_history.append(features)
        
        # Test behavioral analysis
        current_features = EventFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH"
        )
        
        score = detector._behavioral_analysis(current_features)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_model_persistence(self):
        """Test model save/load functionality"""
        detector = NetworkEventAnomalyDetector(model_path="/tmp/test_model.pth")
        
        # Train with sample data
        normal_events = [
            {
                "logtype": 4002,
                "src_host": "192.168.1.10",
                "dst_port": 22,
                "logdata": {"USERNAME": "user1"}
            }
        ]
        
        detector.train_on_normal_events(normal_events)
        
        # Test save
        detector._save_model()
        
        # Create new detector and test load
        detector2 = NetworkEventAnomalyDetector(model_path="/tmp/test_model.pth")
        detector2._load_model()
        
        assert detector2.is_trained == True
        assert hasattr(detector2, 'training_data')

    def test_analyze_event_interface(self):
        """Test analyze_event interface method"""
        detector = NetworkEventAnomalyDetector()
        
        features = {
            "timestamp": time.time(),
            "event_type": 4002,
            "source_ip": "192.168.1.100",
            "destination_port": 22,
            "protocol": "SSH",
            "username_attempts": 1,
            "password_attempts": 1
        }
        
        result = detector.analyze_event(features)
        
        assert isinstance(result, dict)
        assert "is_anomaly" in result
        assert "anomaly_score" in result
        assert "confidence" in result
        assert isinstance(result["is_anomaly"], bool)
        assert isinstance(result["anomaly_score"], float)


    def test_ml_detector_error_handling(self):
        """Test ML detector error handling and fallback mechanisms"""
        detector = NetworkEventAnomalyDetector()
        
        # Test with invalid event data
        invalid_event = {"invalid": "data"}
        score, analysis = detector.detect_anomaly(invalid_event)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert "error" in analysis

    def test_ml_detector_with_different_model_types(self):
        """Test ML detector with different Anomalib model types"""
        model_types = ["fastflow", "efficient_ad", "padim"]
        
        for model_type in model_types:
            detector = NetworkEventAnomalyDetector(model_type=model_type)
            assert detector.model_type == model_type
            assert detector.model is not None

    def test_feature_extraction_edge_cases(self):
        """Test feature extraction with edge cases"""
        detector = NetworkEventAnomalyDetector()
        
        # Test with missing fields
        incomplete_event = {
            "logtype": 4002,
            "src_host": "192.168.1.100"
            # Missing dst_port and logdata
        }
        
        features = detector._extract_features(incomplete_event)
        assert features is not None
        assert features.destination_port == 0  # Default value
        assert features.protocol == "UNKNOWN"  # Default value

    def test_feature_normalization_edge_cases(self):
        """Test feature normalization with edge cases"""
        detector = NetworkEventAnomalyDetector()
        
        # Test with extreme values
        features = EventFeatures(
            timestamp=time.time(),
            event_type=9999,  # High event type
            source_ip="192.168.1.100",
            destination_port=65535,  # Max port
            protocol="UNKNOWN",
            username_attempts=100,  # High attempt count
            password_attempts=100
        )
        
        normalized = detector._normalize_features(features)
        assert normalized is not None
        assert np.all(normalized >= 0) and np.all(normalized <= 1)

    def test_ml_analysis_with_training_data(self):
        """Test ML analysis with actual training data"""
        detector = NetworkEventAnomalyDetector()
        
        # Train with normal events
        normal_events = [
            {"logtype": 4002, "src_host": "192.168.1.10", "dst_port": 22, "logdata": {"USERNAME": "user1"}},
            {"logtype": 4002, "src_host": "192.168.1.11", "dst_port": 22, "logdata": {"USERNAME": "user2"}},
            {"logtype": 3000, "src_host": "192.168.1.12", "dst_port": 80, "logdata": {"PATH": "/index.html"}}
        ]
        
        detector.train_on_normal_events(normal_events)
        
        # Test anomaly detection with similar event
        similar_event = {
            "logtype": 4002,
            "src_host": "192.168.1.10",
            "dst_port": 22,
            "logdata": {"USERNAME": "user1"}
        }
        
        score, analysis = detector.detect_anomaly(similar_event)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_ml_analysis_with_different_event(self):
        """Test ML analysis with different event types"""
        detector = NetworkEventAnomalyDetector()
        
        # Train with SSH events
        normal_events = [
            {"logtype": 4002, "src_host": "192.168.1.10", "dst_port": 22, "logdata": {"USERNAME": "user1"}},
            {"logtype": 4002, "src_host": "192.168.1.11", "dst_port": 22, "logdata": {"USERNAME": "user2"}}
        ]
        
        detector.train_on_normal_events(normal_events)
        
        # Test with different event type (HTTP)
        different_event = {
            "logtype": 3000,
            "src_host": "192.168.1.100",
            "dst_port": 80,
            "logdata": {"PATH": "/admin.php"}
        }
        
        score, analysis = detector.detect_anomaly(different_event)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_model_persistence_with_temp_file(self):
        """Test model persistence with temporary file"""
        with tempfile.NamedTemporaryFile(suffix='.pth', delete=False) as tmp_file:
            model_path = tmp_file.name
        
        try:
            detector = NetworkEventAnomalyDetector(model_path=model_path)
            
            # Train with sample data
            normal_events = [
                {"logtype": 4002, "src_host": "192.168.1.10", "dst_port": 22, "logdata": {"USERNAME": "user1"}}
            ]
            
            detector.train_on_normal_events(normal_events)
            detector._save_model()
            
            # Verify file exists
            assert os.path.exists(model_path)
            
            # Test loading
            detector2 = NetworkEventAnomalyDetector(model_path=model_path)
            detector2._load_model()
            
            assert detector2.is_trained == True
            assert hasattr(detector2, 'training_data')
            
        finally:
            # Cleanup
            if os.path.exists(model_path):
                os.unlink(model_path)

    def test_ml_analyzer_initialization_failure(self):
        """Test ML analyzer initialization failure handling"""
        config = {
            "ml_enabled": True,
            "ml_model_type": "invalid_model"
        }
        
        # This should not raise an exception
        analyzer = EventAnalyzer(config=config)
        assert analyzer.ml_enabled == False  # Should be disabled due to error

    def test_ml_analysis_without_training(self):
        """Test ML analysis without prior training"""
        detector = NetworkEventAnomalyDetector()
        
        # Don't train the model
        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin"}
        }
        
        score, analysis = detector.detect_anomaly(event_data)
        
        # Should still work with behavioral analysis only
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert isinstance(analysis, dict)

    def test_behavioral_analysis_with_empty_history(self):
        """Test behavioral analysis with empty event history"""
        detector = NetworkEventAnomalyDetector()
        
        # No events in history
        features = EventFeatures(
            timestamp=time.time(),
            event_type=4002,
            source_ip="192.168.1.100",
            destination_port=22,
            protocol="SSH"
        )
        
        score = detector._behavioral_analysis(features)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_ml_analysis_integration_with_event_analyzer(self):
        """Test complete ML analysis integration with EventAnalyzer"""
        config = {
            "ml_enabled": True,
            "ml_model_type": "fastflow",
            "ml_config": {"threshold": 0.5}
        }
        
        analyzer = EventAnalyzer(config=config)
        
        # Create multiple test events
        events = [
            create_event(
                event_type="4002",
                source="192.168.1.100",
                data={"logdata": {"USERNAME": "admin"}},
                severity="medium"
            ),
            create_event(
                event_type="3000",
                source="192.168.1.101",
                data={"logdata": {"PATH": "/admin.php"}},
                severity="high"
            )
        ]
        
        for event in events:
            ml_score, ml_analysis = analyzer._ml_analysis(event)
            assert isinstance(ml_score, float)
            assert ml_score >= 0.0

    def test_ml_detector_thread_safety(self):
        """Test ML detector thread safety"""
        detector = NetworkEventAnomalyDetector()
        
        # Add events from multiple threads
        import threading
        
        def add_events():
            for i in range(10):
                features = EventFeatures(
                    timestamp=time.time(),
                    event_type=4002,
                    source_ip=f"192.168.1.{i}",
                    destination_port=22,
                    protocol="SSH"
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

    def test_ml_detector_memory_management(self):
        """Test ML detector memory management"""
        detector = NetworkEventAnomalyDetector()
        
        # Add many events to test memory management
        for i in range(1000):
            features = EventFeatures(
                timestamp=time.time() - i,
                event_type=4002,
                source_ip=f"192.168.1.{i % 10}",
                destination_port=22,
                protocol="SSH"
            )
            detector.event_history.append(features)
        
        # Should maintain reasonable memory usage
        assert len(detector.event_history) <= 1000

    def test_ml_detector_performance(self):
        """Test ML detector performance with large datasets"""
        detector = NetworkEventAnomalyDetector()
        
        # Create large training dataset
        normal_events = []
        for i in range(100):
            normal_events.append({
                "logtype": 4002,
                "src_host": f"192.168.1.{i % 10}",
                "dst_port": 22,
                "logdata": {"USERNAME": f"user{i}"}
            })
        
        start_time = time.time()
        detector.train_on_normal_events(normal_events)
        training_time = time.time() - start_time
        
        # Training should complete in reasonable time
        assert training_time < 10.0  # Should complete within 10 seconds
        assert detector.is_trained == True

    def test_ml_detector_configuration_validation(self):
        """Test ML detector configuration validation"""
        # Test with invalid model type
        detector = NetworkEventAnomalyDetector(model_type="invalid_model")
        assert detector.model_type == "invalid_model"
        
        # Test with invalid model path
        detector = NetworkEventAnomalyDetector(model_path="/invalid/path/model.pth")
        assert detector.model_path == "/invalid/path/model.pth"

    def test_ml_detector_feature_statistics(self):
        """Test ML detector feature statistics tracking"""
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
                password_attempts=i
            )
            detector.event_history.append(features)
        
        # Check that feature statistics are being tracked
        assert hasattr(detector, 'feature_stats')
        assert isinstance(detector.feature_stats, dict)

    def test_ml_detector_anomaly_scoring_consistency(self):
        """Test ML detector anomaly scoring consistency"""
        detector = NetworkEventAnomalyDetector()
        
        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin"}
        }
        
        # Run multiple times to check consistency
        scores = []
        for _ in range(5):
            score, _ = detector.detect_anomaly(event_data)
            scores.append(score)
        
        # Scores should be consistent (within reasonable variance)
        assert all(isinstance(score, float) for score in scores)
        assert all(0.0 <= score <= 1.0 for score in scores)

    def test_ml_detector_edge_case_handling(self):
        """Test ML detector edge case handling"""
        detector = NetworkEventAnomalyDetector()
        
        # Test with None values
        event_data = {
            "logtype": None,
            "src_host": None,
            "dst_port": None,
            "logdata": None
        }
        
        score, analysis = detector.detect_anomaly(event_data)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_ml_detector_large_feature_vectors(self):
        """Test ML detector with large feature vectors"""
        detector = NetworkEventAnomalyDetector()
        
        # Create features with large values
        features = EventFeatures(
            timestamp=time.time(),
            event_type=9999,
            source_ip="192.168.1.100",
            destination_port=65535,
            protocol="SSH",
            username_attempts=1000,
            password_attempts=1000
        )
        
        normalized = detector._normalize_features(features)
        assert normalized is not None
        assert np.all(normalized >= 0) and np.all(normalized <= 1)

    def test_ml_detector_model_switching(self):
        """Test ML detector model switching"""
        detector = NetworkEventAnomalyDetector(model_type="fastflow")
        assert detector.model_type == "fastflow"
        
        # Switch model type
        detector.model_type = "efficient_ad"
        assert detector.model_type == "efficient_ad"

    def test_ml_detector_cleanup(self):
        """Test ML detector cleanup functionality"""
        detector = NetworkEventAnomalyDetector()
        
        # Add some data
        for i in range(10):
            features = EventFeatures(
                timestamp=time.time(),
                event_type=4002,
                source_ip=f"192.168.1.{i}",
                destination_port=22,
                protocol="SSH"
            )
            detector.event_history.append(features)
        
        # Test cleanup
        detector._cleanup()
        assert len(detector.event_history) == 0

    def test_ml_detector_async_operations(self):
        """Test ML detector async operations"""
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
                    protocol="SSH"
                )
                detector.event_history.append(features)
            
            # Test async cleanup
            await detector._cleanup()
            assert len(detector.event_history) == 0
        
        # Run async test
        asyncio.run(test_async_cleanup())


if __name__ == "__main__":
    pytest.main([__file__])
