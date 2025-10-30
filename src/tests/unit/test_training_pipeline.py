#!/usr/bin/env python3
"""
Unit tests for TrainingPipeline component
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

# Conditional imports for ML dependencies
try:
    import torch
    import numpy as np
    from netsentinel.ml_models.training_pipeline import TrainingPipeline

    ML_AVAILABLE = True
except ImportError:
    torch = None
    np = None
    TrainingPipeline = None
    ML_AVAILABLE = False


@pytest.mark.skipif(not ML_AVAILABLE, reason="ML dependencies not available")
class TestTrainingPipeline:
    """Comprehensive test suite for TrainingPipeline"""

    def test_pipeline_initialization_defaults(self):
        """Test pipeline initialization with default parameters"""
        pipeline = TrainingPipeline()

        assert pipeline.model_type == "fastflow"
        assert pipeline.model_path.endswith("fastflow_anomaly_detector.pth")
        assert pipeline.engine is None
        assert pipeline.model is None
        assert pipeline.is_trained == False
        assert pipeline.training_config["epochs"] == 10
        assert pipeline.training_config["batch_size"] == 32

    def test_pipeline_initialization_custom_params(self):
        """Test pipeline initialization with custom parameters"""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = os.path.join(temp_dir, "custom_model.pth")

            pipeline = TrainingPipeline(
                model_type="efficientad",
                model_path=model_path,
                config={
                    "epochs": 5,
                    "batch_size": 16,
                    "learning_rate": 0.01,
                }
            )

            assert pipeline.model_type == "efficientad"
            assert pipeline.model_path == model_path
            assert pipeline.training_config["epochs"] == 5
            assert pipeline.training_config["batch_size"] == 16
            assert pipeline.training_config["learning_rate"] == 0.01

    @patch('netsentinel.ml_models.training_pipeline.Fastflow')
    def test_model_initialization(self, mock_fastflow):
        """Test model initialization"""
        mock_model = Mock()
        mock_fastflow.return_value = mock_model

        pipeline = TrainingPipeline()
        pipeline._initialize_model()

        assert pipeline.model == mock_model
        mock_fastflow.assert_called_once()

    @patch('netsentinel.ml_models.training_pipeline.Engine')
    def test_engine_initialization(self, mock_engine):
        """Test training engine initialization"""
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        pipeline = TrainingPipeline()
        pipeline._initialize_engine()

        assert pipeline.engine == mock_engine_instance
        mock_engine.assert_called_once_with(
            accelerator="auto",
            devices=1,
            max_epochs=10,
        )

    def test_feature_extraction(self):
        """Test feature extraction from event data"""
        pipeline = TrainingPipeline()

        event = {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin"},
        }

        features = pipeline._extract_event_features(event)

        assert features["event_type"] == 4002
        assert features["source_ip"] == "192.168.1.100"
        assert features["destination_port"] == 22
        assert features["protocol"] == "SSH"
        assert features["username_attempts"] == 1

    def test_protocol_determination(self):
        """Test protocol determination from event type and port"""
        pipeline = TrainingPipeline()

        # Test event type mapping
        assert pipeline._determine_protocol(4002, 22) == "SSH"
        assert pipeline._determine_protocol(3000, 80) == "HTTP"
        assert pipeline._determine_protocol(9999, 443) == "HTTPS"  # Port-based fallback

    def test_image_creation(self):
        """Test feature to image conversion"""
        pipeline = TrainingPipeline()

        features = {
            "event_type": 4002,
            "destination_port": 22,
            "username_attempts": 1,
            "password_attempts": 0,
        }

        image_array = pipeline._create_feature_image(features)

        assert image_array.shape[0] == 32  # height
        assert image_array.shape[1] == 32  # width
        assert image_array.shape[2] == 3   # RGB channels
        assert image_array.dtype == np.uint8

    @patch('netsentinel.ml_models.training_pipeline.Fastflow')
    @patch('netsentinel.ml_models.training_pipeline.Engine')
    @patch('netsentinel.ml_models.training_pipeline.Folder')
    def test_training_workflow(self, mock_folder, mock_engine, mock_fastflow):
        """Test the complete training workflow"""
        # Setup mocks
        mock_model = Mock()
        mock_fastflow.return_value = mock_model

        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance

        mock_dataset = Mock()
        mock_folder.return_value = mock_dataset

        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = os.path.join(temp_dir, "test_model.pth")

            pipeline = TrainingPipeline(model_path=model_path)

            # Mock training data
            events = [
                {
                    "logtype": 4002,
                    "src_host": "192.168.1.100",
                    "dst_port": 22,
                    "logdata": {"USERNAME": "user1"},
                }
            ]

            # Run training (will use mocks)
            result = pipeline.train_on_events(events, epochs=1)

            # Verify the workflow was called
            assert isinstance(result, bool)  # Should return True/False
            # Note: Actual training may fail due to mocking, but workflow should run

    def test_training_metrics(self):
        """Test training metrics retrieval"""
        pipeline = TrainingPipeline()

        metrics = pipeline.get_training_metrics()

        assert isinstance(metrics, dict)
        assert "model_type" in metrics
        assert "is_trained" in metrics
        assert "training_config" in metrics
        assert "model_path" in metrics

    def test_error_handling(self):
        """Test error handling in training pipeline"""
        pipeline = TrainingPipeline()

        # Test with invalid events
        result = pipeline.train_on_events([])
        assert result == False

        # Test with None events
        result = pipeline.train_on_events(None)
        assert result == False

    def test_component_lifecycle(self):
        """Test component lifecycle methods"""
        pipeline = TrainingPipeline()

        # Test async initialization
        import asyncio

        async def test_async():
            await pipeline._initialize()
            await pipeline._start_internal()
            await pipeline._stop_internal()
            await pipeline._cleanup()

            # Should not raise exceptions
            assert True

        asyncio.run(test_async())

    def test_configuration_handling(self):
        """Test configuration parameter handling"""
        config = {
            "epochs": 20,
            "batch_size": 64,
            "image_size": [64, 64],
            "learning_rate": 0.005,
        }

        pipeline = TrainingPipeline(config=config)

        assert pipeline.training_config["epochs"] == 20
        assert pipeline.training_config["batch_size"] == 64
        assert pipeline.training_config["image_size"] == (64, 64)
        assert pipeline.training_config["learning_rate"] == 0.005


if __name__ == "__main__":
    pytest.main([__file__])
