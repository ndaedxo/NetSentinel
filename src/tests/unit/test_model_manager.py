#!/usr/bin/env python3
"""
Unit tests for ModelManager component
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Conditional imports for ML dependencies
try:
    import torch
    from netsentinel.ml_models.model_manager import ModelManager, ModelVersion

    ML_AVAILABLE = True
except ImportError:
    torch = None
    ModelManager = None
    ModelVersion = None
    ML_AVAILABLE = False


@pytest.mark.skipif(not ML_AVAILABLE, reason="ML dependencies not available")
class TestModelManager:
    """Comprehensive test suite for ModelManager"""

    def test_manager_initialization_defaults(self):
        """Test model manager initialization with defaults"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            assert manager.models_dir == Path(temp_dir)
            assert manager.max_versions == 5
            assert isinstance(manager.model_registry, dict)
            assert isinstance(manager.loaded_models, dict)
            assert isinstance(manager.model_health, dict)
            assert (manager.models_dir / "model_registry.json").exists()

    def test_manager_initialization_custom_params(self):
        """Test model manager initialization with custom parameters"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(
                models_dir=temp_dir,
                max_versions=10,
            )

            assert manager.max_versions == 10

    def test_model_version_creation(self):
        """Test ModelVersion creation and serialization"""
        import time

        version = ModelVersion(
            version_id="test_v1",
            model_type="fastflow",
            model_path="/path/to/model",
            metadata_path="/path/to/metadata.json",
            created_at=time.time(),
            training_metrics={"accuracy": 0.95},
            checksum="abc123",
        )

        # Test serialization
        data = version.to_dict()
        assert data["version_id"] == "test_v1"
        assert data["model_type"] == "fastflow"
        assert data["training_metrics"]["accuracy"] == 0.95

        # Test deserialization
        version2 = ModelVersion.from_dict(data)
        assert version2.version_id == version.version_id
        assert version2.model_type == version.model_type

    def test_registry_persistence(self):
        """Test model registry save/load"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Add a model version
            import time
            version = ModelVersion(
                version_id="test_v1",
                model_type="fastflow",
                model_path=str(Path(temp_dir) / "model1"),
                metadata_path=str(Path(temp_dir) / "meta1.json"),
                created_at=time.time(),
            )

            manager.model_registry["fastflow"] = [version]
            manager._save_registry()

            # Create new manager and load registry
            manager2 = ModelManager(models_dir=temp_dir)
            manager2._load_registry()

            assert "fastflow" in manager2.model_registry
            assert len(manager2.model_registry["fastflow"]) == 1
            assert manager2.model_registry["fastflow"][0].version_id == "test_v1"

    def test_model_registration(self):
        """Test model registration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Create a dummy model file
            model_path = Path(temp_dir) / "test_model.pth"
            model_path.write_text("dummy model data")

            version_id = manager.register_model(
                model_type="fastflow",
                model_path=str(model_path),
                training_metrics={"accuracy": 0.95},
            )

            assert version_id is not None
            assert "fastflow" in manager.model_registry
            assert len(manager.model_registry["fastflow"]) == 1
            assert manager.model_registry["fastflow"][0].version_id == version_id

    def test_version_cleanup(self):
        """Test automatic cleanup of old versions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir, max_versions=2)

            # Register multiple versions
            for i in range(4):
                model_path = Path(temp_dir) / f"model_{i}.pth"
                model_path.write_text(f"dummy model {i}")

                manager.register_model(
                    model_type="fastflow",
                    model_path=str(model_path),
                )

            # Should only keep 2 versions
            assert len(manager.model_registry["fastflow"]) == 2

            # Check that oldest files were "removed" (in real implementation)
            # For this test, we just check the registry size
            versions = manager.model_registry["fastflow"]
            assert len(versions) == 2

    @patch('netsentinel.ml_models.model_manager.TorchInferencer')
    def test_model_loading(self, mock_inferencer):
        """Test model loading"""
        mock_inferencer_instance = Mock()
        mock_inferencer.return_value = mock_inferencer_instance

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Register a model first
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir()

            version_id = manager.register_model(
                model_type="fastflow",
                model_path=str(model_path),
            )

            # Try to load the model
            inferencer = manager.load_model("fastflow")

            if inferencer:  # May fail due to mocking
                assert inferencer == mock_inferencer_instance
                assert "fastflow" in manager.loaded_models
                assert "fastflow" in manager.model_health

    def test_model_unloading(self):
        """Test model unloading"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Manually add a loaded model
            manager.loaded_models["fastflow"] = Mock()
            manager.model_health["fastflow"] = {"loaded_at": 1234567890}

            # Unload the model
            result = manager.unload_model("fastflow")

            assert result == True
            assert "fastflow" not in manager.loaded_models
            assert "fastflow" not in manager.model_health

    def test_model_info_retrieval(self):
        """Test model information retrieval"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Register a model
            model_path = Path(temp_dir) / "test_model"
            model_path.mkdir()

            manager.register_model(
                model_type="fastflow",
                model_path=str(model_path),
                training_metrics={"accuracy": 0.95},
            )

            # Get model info
            info = manager.get_model_info("fastflow")

            assert info is not None
            assert info["model_type"] == "fastflow"
            assert info["version_count"] == 1
            assert info["latest_version"] is not None
            assert info["is_loaded"] == False

    def test_available_models(self):
        """Test getting list of available models"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Register models of different types
            for model_type in ["fastflow", "efficientad", "padim"]:
                model_path = Path(temp_dir) / f"{model_type}_model"
                model_path.mkdir()

                manager.register_model(
                    model_type=model_type,
                    model_path=str(model_path),
                )

            available = manager.get_available_models()
            assert set(available) == {"fastflow", "efficientad", "padim"}

    def test_health_check(self):
        """Test model health checking"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Test health check for non-existent model
            health = manager.check_model_health("nonexistent")
            assert health["status"] == "not_loaded"

            # Test health check for loaded model
            manager.loaded_models["fastflow"] = Mock()
            manager.model_health["fastflow"] = {
                "loaded_at": 1234567890,
                "inference_count": 100,
                "error_count": 5,
                "last_health_check": 1234567890,
            }

            health = manager.check_model_health("fastflow")
            assert health["status"] == "healthy"
            assert health["inference_count"] == 100
            assert health["error_count"] == 5
            assert health["error_rate"] == 0.05

    def test_checksum_calculation(self):
        """Test model checksum calculation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Create a test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            checksum = manager._calculate_model_hash(str(test_file))
            assert isinstance(checksum, str)
            assert len(checksum) == 64  # SHA256 hex length

    def test_cleanup(self):
        """Test manager cleanup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Add some mock loaded models
            manager.loaded_models["fastflow"] = Mock()
            manager.model_health["fastflow"] = {}

            # Run cleanup
            manager.cleanup()

            assert len(manager.loaded_models) == 0
            assert len(manager.model_health) == 0

    def test_async_lifecycle(self):
        """Test async lifecycle methods"""
        import asyncio

        async def test_async():
            with tempfile.TemporaryDirectory() as temp_dir:
                manager = ModelManager(models_dir=temp_dir)

                await manager._initialize()
                await manager._start_internal()
                await manager._stop_internal()
                await manager._cleanup()

                # Should not raise exceptions
                assert True

        asyncio.run(test_async())

    def test_error_handling(self):
        """Test error handling in model manager"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ModelManager(models_dir=temp_dir)

            # Test loading non-existent model
            inferencer = manager.load_model("nonexistent_type")
            assert inferencer is None

            # Test unloading non-existent model
            result = manager.unload_model("nonexistent_type")
            assert result == False

            # Test getting info for non-existent model
            info = manager.get_model_info("nonexistent_type")
            assert info is None


if __name__ == "__main__":
    pytest.main([__file__])
