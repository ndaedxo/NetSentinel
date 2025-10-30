#!/usr/bin/env python3
"""
Integration tests for complete ML pipeline

Tests end-to-end ML functionality including:
- Model training with TrainingPipeline
- Model management with ModelManager
- Feature extraction and inference
- Integration with EventAnalyzer
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Conditional imports for ML dependencies
try:
    import torch
    import numpy as np
    from netsentinel.ml_models import TrainingPipeline, ModelManager, FeatureExtractor
    from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector
    from netsentinel.processors.event_analyzer import EventAnalyzer
    from netsentinel.core.models import StandardEvent

    ML_AVAILABLE = True
except ImportError:
    torch = None
    np = None
    TrainingPipeline = None
    ModelManager = None
    FeatureExtractor = None
    NetworkEventAnomalyDetector = None
    EventAnalyzer = None
    StandardEvent = None
    ML_AVAILABLE = False


@pytest.mark.skipif(not ML_AVAILABLE, reason="ML dependencies not available")
class TestMLPipelineIntegration:
    """Integration tests for complete ML pipeline"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def create_sample_events(self, count=10):
        """Create sample training events"""
        events = []
        base_time = 1609459200.0  # 2021-01-01 00:00:00 UTC

        for i in range(count):
            event = {
                "logtype": 4002 if i % 2 == 0 else 3000,  # Alternate SSH/HTTP
                "src_host": f"192.168.1.{i % 10 + 1}",
                "dst_port": 22 if i % 2 == 0 else 80,
                "logdata": {
                    "USERNAME": f"user{i}" if i % 3 == 0 else "",
                    "PASSWORD": f"pass{i}" if i % 4 == 0 else "",
                },
                "timestamp": base_time + i * 60,  # One minute apart
            }
            events.append(event)

        return events

    def create_standard_event(self, event_type=4002, source_ip="192.168.1.100"):
        """Create a StandardEvent for testing"""
        return StandardEvent(
            id=f"test_event_{event_type}",
            timestamp=1609459200.0,
            event_type=str(event_type),
            source=source_ip,
            severity=1,
            data={
                "logtype": event_type,
                "src_host": source_ip,
                "dst_port": 22 if event_type == 4002 else 80,
                "logdata": {"USERNAME": "testuser"} if event_type == 4002 else {},
            }
        )

    @patch('netsentinel.ml_models.training_pipeline.Fastflow')
    @patch('netsentinel.ml_models.training_pipeline.Engine')
    @patch('netsentinel.ml_models.training_pipeline.Folder')
    def test_training_pipeline_integration(self, mock_folder, mock_engine, mock_fastflow, temp_dir):
        """Test TrainingPipeline integration with mocked components"""
        # Setup mocks
        mock_model = Mock()
        mock_fastflow.return_value = mock_model

        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        mock_dataset = Mock()
        mock_folder.return_value = mock_dataset

        # Create training pipeline
        model_path = os.path.join(temp_dir, "test_model")
        pipeline = TrainingPipeline(
            model_type="fastflow",
            model_path=model_path,
        )

        # Create sample events
        events = self.create_sample_events(5)

        # Run training
        result = pipeline.train_on_events(events, epochs=1)

        # Verify the pipeline executed (may fail due to mocking, but should not crash)
        assert isinstance(result, bool)

    def test_model_manager_integration(self, temp_dir):
        """Test ModelManager integration"""
        manager = ModelManager(models_dir=temp_dir)

        # Register a model
        model_path = os.path.join(temp_dir, "test_model")
        os.makedirs(model_path, exist_ok=True)

        version_id = manager.register_model(
            model_type="fastflow",
            model_path=model_path,
            training_metrics={"accuracy": 0.95, "loss": 0.05}
        )

        assert version_id is not None

        # Get model info
        info = manager.get_model_info("fastflow")
        assert info is not None
        assert info["version_count"] == 1
        assert info["latest_version"]["training_metrics"]["accuracy"] == 0.95

        # Test health check
        health = manager.check_model_health("fastflow")
        assert health["status"] == "not_loaded"  # No actual model loaded

    def test_feature_extractor_integration(self):
        """Test FeatureExtractor integration"""
        extractor = FeatureExtractor()

        # Test feature extraction
        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin", "PASSWORD": "secret"},
            "timestamp": 1609459200.0,
        }

        features = extractor.extract_features(event_data)
        assert features is not None
        assert features.event_type == 4002
        assert features.protocol == "SSH"

        # Test normalization
        normalized = extractor.normalize_features(features)
        assert isinstance(normalized, np.ndarray)
        assert normalized.shape[0] == 17  # NetworkFeatures has 17 features

        # Test image conversion
        image_tensor = extractor.features_to_image(normalized)
        assert image_tensor.shape[0] == 1  # batch
        assert image_tensor.shape[1] == 3  # RGB channels

    @patch('netsentinel.ml_anomaly_detector.TorchInferencer')
    def test_ml_anomaly_detector_integration(self, mock_inferencer, temp_dir):
        """Test NetworkEventAnomalyDetector integration"""
        mock_inferencer_instance = Mock()
        mock_inferencer_instance.predict.return_value = Mock(
            pred_score=torch.tensor([0.1])
        )
        mock_inferencer.return_value = mock_inferencer_instance

        # Create detector
        detector = NetworkEventAnomalyDetector(
            model_type="fastflow",
            model_path=os.path.join(temp_dir, "test_model"),
            config={"models_dir": temp_dir}
        )

        # Test feature extraction
        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin"},
        }

        features = detector._extract_features(event_data)
        assert features is not None

        # Test anomaly detection
        score, analysis = detector.detect_anomaly(event_data)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert isinstance(analysis, dict)

    @patch('netsentinel.processors.event_analyzer.NetworkEventAnomalyDetector')
    @pytest.mark.asyncio
    async def test_event_analyzer_ml_integration(self, mock_detector_class):
        """Test EventAnalyzer ML integration"""
        # Setup mock detector
        mock_detector = Mock()
        mock_detector.analyze_event = AsyncMock(return_value={
            "is_anomaly": True,
            "anomaly_score": 0.8,
            "confidence": 0.9,
            "ml_analysis": {"test": "data"}
        })
        mock_detector_class.return_value = mock_detector

        # Create event analyzer with ML enabled
        analyzer = EventAnalyzer(config={"ml_enabled": True})

        # Create test event
        event = self.create_standard_event()

        # Test ML analysis
        score, ml_result = await analyzer._ml_analysis(event)

        # Verify ML integration
        assert isinstance(score, float)
        assert score == 8.0  # 0.8 * 10 (scaled)
        assert ml_result is not None
        assert ml_result["is_anomaly"] == True

    @pytest.mark.asyncio
    async def test_complete_ml_pipeline(self, temp_dir):
        """Test complete ML pipeline from training to inference"""
        # This is a high-level integration test that may need mocking
        # due to the complexity of actual ML training

        # Create components
        manager = ModelManager(models_dir=temp_dir)
        extractor = FeatureExtractor()

        # Create detector
        detector = NetworkEventAnomalyDetector(
            config={"models_dir": temp_dir}
        )

        # Test component interactions
        assert manager.models_dir == Path(temp_dir)
        assert extractor.normalization_method == "standard"
        assert detector.model_type == "fastflow"

        # Test feature extraction workflow
        event_data = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "test"},
        }

        # Extract features
        features = detector._extract_features(event_data)
        assert features is not None

        # Normalize features
        normalized = detector._normalize_features(features)
        assert isinstance(normalized, np.ndarray)

        # Convert to image
        image_tensor = detector._create_feature_image(normalized)
        assert isinstance(image_tensor, torch.Tensor)

        # Test behavioral analysis (should work without ML model)
        behavioral_score = detector._behavioral_analysis(features)
        assert isinstance(behavioral_score, float)
        assert 0.0 <= behavioral_score <= 1.0

    def test_error_handling_integration(self, temp_dir):
        """Test error handling across components"""
        # Create components
        manager = ModelManager(models_dir=temp_dir)
        detector = NetworkEventAnomalyDetector(config={"models_dir": temp_dir})

        # Test with invalid data
        invalid_event = {"invalid": "data"}
        score, analysis = detector.detect_anomaly(invalid_event)

        # Should handle gracefully
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

        # Test model manager with invalid paths
        info = manager.get_model_info("nonexistent")
        assert info is None

    @pytest.mark.asyncio
    async def test_async_component_lifecycle(self, temp_dir):
        """Test async lifecycle of all components"""
        # Create components
        manager = ModelManager(models_dir=temp_dir)
        extractor = FeatureExtractor()
        detector = NetworkEventAnomalyDetector(config={"models_dir": temp_dir})

        # Test async initialization
        await manager._initialize()
        await extractor._initialize()
        await detector._initialize()

        # Test async startup
        await manager._start_internal()
        await extractor._start_internal()
        await detector._start_internal()

        # Test async shutdown
        await manager._stop_internal()
        await extractor._stop_internal()
        await detector._stop_internal()

        # Test async cleanup
        await manager._cleanup()
        await extractor._cleanup()
        await detector._cleanup()

        # Should not raise exceptions
        assert True

    def test_memory_management_integration(self):
        """Test memory management across components"""
        # Create components
        extractor = FeatureExtractor()
        detector = NetworkEventAnomalyDetector()

        # Add many events to test memory limits
        for i in range(1500):  # More than default limit of 1000
            features = detector._extract_features({
                "logtype": 4002,
                "src_host": f"192.168.1.{i % 100}",
                "dst_port": 22,
            })
            if features:
                detector.event_history.append(features)

        # History should be limited
        assert len(detector.event_history) <= 1000

        # Test cleanup
        detector._cleanup()
        assert len(detector.event_history) == 0

    def test_configuration_integration(self):
        """Test configuration handling across components"""
        config = {
            "models_dir": "/custom/models",
            "max_model_versions": 10,
            "normalization_method": "minmax",
            "image_size": [64, 64],
            "ml_enabled": True,
            "ml_model_type": "efficientad",
        }

        # Test components with config
        manager = ModelManager(config=config)
        extractor = FeatureExtractor(config=config)
        detector = NetworkEventAnomalyDetector(config=config)

        # Verify configurations were applied
        assert manager.max_versions == 10
        assert extractor.normalization_method == "minmax"
        assert extractor.image_size == (64, 64)
        assert detector.model_type == "efficientad"


if __name__ == "__main__":
    pytest.main([__file__])
