#!/usr/bin/env python3
"""
Model Manager for NetSentinel ML Components

Handles model loading, versioning, persistence, and lifecycle management
for anomaly detection models.
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
from datetime import datetime

# Anomalib imports
from anomalib.deploy.inferencers import TorchInferencer

# Import new core components
try:
    from ..core.base import BaseComponent
    from ..utils.centralized import create_logger
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from utils.centralized import create_logger

logger = create_logger("model_manager", level="INFO")


class ModelVersion:
    """Represents a model version with metadata"""

    def __init__(
        self,
        version_id: str,
        model_type: str,
        model_path: str,
        metadata_path: str,
        created_at: float,
        training_metrics: Optional[Dict[str, Any]] = None,
        checksum: Optional[str] = None,
    ):
        self.version_id = version_id
        self.model_type = model_type
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.created_at = created_at
        self.training_metrics = training_metrics or {}
        self.checksum = checksum

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "version_id": self.version_id,
            "model_type": self.model_type,
            "model_path": self.model_path,
            "metadata_path": self.metadata_path,
            "created_at": self.created_at,
            "training_metrics": self.training_metrics,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelVersion':
        """Create from dictionary"""
        return cls(
            version_id=data["version_id"],
            model_type=data["model_type"],
            model_path=data["model_path"],
            metadata_path=data["metadata_path"],
            created_at=data["created_at"],
            training_metrics=data.get("training_metrics", {}),
            checksum=data.get("checksum"),
        )


class ModelManager(BaseComponent):
    """
    Manages ML model lifecycle, versioning, and persistence

    Provides centralized model management including:
    - Model loading and unloading
    - Version management and rollback
    - Model validation and health checks
    - Automatic cleanup of old versions
    """

    def __init__(
        self,
        name: str = "model_manager",
        models_dir: str = "models",
        max_versions: int = 5,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize model manager

        Args:
            name: Component name
            models_dir: Directory to store models
            max_versions: Maximum number of versions to keep per model type
            config: Additional configuration
        """
        super().__init__(name, config, logger)

        self.models_dir = Path(models_dir)
        self.max_versions = max_versions

        # Model registry: model_type -> list of ModelVersion
        self.model_registry: Dict[str, List[ModelVersion]] = {}

        # Loaded models: model_type -> TorchInferencer
        self.loaded_models: Dict[str, TorchInferencer] = {}

        # Model health tracking
        self.model_health: Dict[str, Dict[str, Any]] = {}

        # Create models directory
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Registry file
        self.registry_file = self.models_dir / "model_registry.json"

        # Load existing registry
        self._load_registry()

    def _load_registry(self):
        """Load model registry from disk"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    registry_data = json.load(f)

                for model_type, versions_data in registry_data.items():
                    versions = [
                        ModelVersion.from_dict(v) for v in versions_data
                    ]
                    # Sort by creation time (newest first)
                    versions.sort(key=lambda v: v.created_at, reverse=True)
                    self.model_registry[model_type] = versions

                logger.info(f"Loaded registry with {len(self.model_registry)} model types")

        except Exception as e:
            logger.error(f"Failed to load model registry: {e}")
            # Start with empty registry
            self.model_registry = {}

    def _save_registry(self):
        """Save model registry to disk"""
        try:
            registry_data = {}
            for model_type, versions in self.model_registry.items():
                registry_data[model_type] = [v.to_dict() for v in versions]

            with open(self.registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save model registry: {e}")

    def register_model(
        self,
        model_type: str,
        model_path: str,
        metadata_path: Optional[str] = None,
        training_metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Register a new model version

        Args:
            model_type: Type of model (e.g., 'fastflow', 'efficientad')
            model_path: Path to the model files
            metadata_path: Path to metadata file
            training_metrics: Training performance metrics

        Returns:
            str: Version ID of the registered model
        """
        try:
            # Generate version ID
            timestamp = time.time()
            content_hash = self._calculate_model_hash(model_path)
            version_id = f"{model_type}_{int(timestamp)}_{content_hash[:8]}"

            # Create metadata path if not provided
            if not metadata_path:
                metadata_path = str(Path(model_path) / "metadata.json")

            # Create ModelVersion
            version = ModelVersion(
                version_id=version_id,
                model_type=model_type,
                model_path=model_path,
                metadata_path=metadata_path,
                created_at=timestamp,
                training_metrics=training_metrics,
                checksum=content_hash,
            )

            # Add to registry
            if model_type not in self.model_registry:
                self.model_registry[model_type] = []

            self.model_registry[model_type].insert(0, version)  # Newest first

            # Cleanup old versions
            self._cleanup_old_versions(model_type)

            # Save registry
            self._save_registry()

            logger.info(f"Registered new model version: {version_id}")
            return version_id

        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            raise

    def _calculate_model_hash(self, model_path: str) -> str:
        """Calculate hash of model files for versioning"""
        try:
            path = Path(model_path)
            if path.is_file():
                # Single file
                with open(path, 'rb') as f:
                    content = f.read()
            else:
                # Directory - hash all files
                content = b""
                for file_path in sorted(path.rglob("*")):
                    if file_path.is_file():
                        with open(file_path, 'rb') as f:
                            content += f.read()

            return hashlib.sha256(content).hexdigest()

        except Exception as e:
            logger.warning(f"Failed to calculate model hash: {e}")
            return f"fallback_{int(time.time())}"

    def _cleanup_old_versions(self, model_type: str):
        """Clean up old versions of a model type"""
        if model_type not in self.model_registry:
            return

        versions = self.model_registry[model_type]
        if len(versions) <= self.max_versions:
            return

        # Keep only the newest versions
        versions_to_remove = versions[self.max_versions:]

        for version in versions_to_remove:
            try:
                # Remove model files
                model_path = Path(version.model_path)
                if model_path.exists():
                    if model_path.is_file():
                        model_path.unlink()
                    else:
                        import shutil
                        shutil.rmtree(model_path)

                # Remove metadata file
                metadata_path = Path(version.metadata_path)
                if metadata_path.exists():
                    metadata_path.unlink()

                logger.debug(f"Removed old model version: {version.version_id}")

            except Exception as e:
                logger.warning(f"Failed to remove old version {version.version_id}: {e}")

        # Update registry
        self.model_registry[model_type] = versions[:self.max_versions]

    def load_model(self, model_type: str, version_id: Optional[str] = None) -> Optional[TorchInferencer]:
        """
        Load a model for inference

        Args:
            model_type: Type of model to load
            version_id: Specific version to load (latest if None)

        Returns:
            TorchInferencer: Loaded model or None if not found
        """
        try:
            if model_type not in self.model_registry:
                logger.warning(f"No models registered for type: {model_type}")
                return None

            versions = self.model_registry[model_type]
            if not versions:
                logger.warning(f"No versions available for model type: {model_type}")
                return None

            # Select version
            if version_id:
                version = next((v for v in versions if v.version_id == version_id), None)
                if not version:
                    logger.warning(f"Version {version_id} not found for {model_type}")
                    return None
            else:
                version = versions[0]  # Latest version

            # Check if already loaded
            if model_type in self.loaded_models:
                current_version = getattr(self.loaded_models[model_type], '_version_id', None)
                if current_version == version.version_id:
                    logger.debug(f"Model {model_type} already loaded (version {version.version_id})")
                    return self.loaded_models[model_type]

            # Load model
            model_path = Path(version.model_path)
            if not model_path.exists():
                logger.error(f"Model path does not exist: {model_path}")
                return None

            # Load TorchInferencer
            inferencer = TorchInferencer(
                model_path=str(model_path),
                device="auto",
            )

            # Store version info
            inferencer._version_id = version.version_id
            inferencer._model_type = model_type
            inferencer._loaded_at = time.time()

            # Update loaded models
            self.loaded_models[model_type] = inferencer

            # Update health tracking
            self._update_model_health(model_type, version)

            logger.info(f"Loaded model {model_type} version {version.version_id}")
            return inferencer

        except Exception as e:
            logger.error(f"Failed to load model {model_type}: {e}")
            return None

    def _update_model_health(self, model_type: str, version: ModelVersion):
        """Update health tracking for a model"""
        self.model_health[model_type] = {
            "version_id": version.version_id,
            "loaded_at": time.time(),
            "last_health_check": time.time(),
            "inference_count": 0,
            "error_count": 0,
            "avg_inference_time": 0.0,
        }

    def unload_model(self, model_type: str) -> bool:
        """
        Unload a model from memory

        Args:
            model_type: Type of model to unload

        Returns:
            bool: True if unloaded successfully
        """
        try:
            if model_type in self.loaded_models:
                del self.loaded_models[model_type]
                if model_type in self.model_health:
                    del self.model_health[model_type]
                logger.info(f"Unloaded model: {model_type}")
                return True
            else:
                logger.warning(f"Model {model_type} not loaded")
                return False

        except Exception as e:
            logger.error(f"Failed to unload model {model_type}: {e}")
            return False

    def get_model_info(self, model_type: str) -> Optional[Dict[str, Any]]:
        """Get information about a model type"""
        try:
            if model_type not in self.model_registry:
                return None

            versions = self.model_registry[model_type]
            latest_version = versions[0] if versions else None

            info = {
                "model_type": model_type,
                "version_count": len(versions),
                "latest_version": latest_version.to_dict() if latest_version else None,
                "is_loaded": model_type in self.loaded_models,
                "all_versions": [v.to_dict() for v in versions],
            }

            # Add health info if loaded
            if model_type in self.model_health:
                info["health"] = self.model_health[model_type]

            return info

        except Exception as e:
            logger.error(f"Failed to get model info for {model_type}: {e}")
            return None

    def get_available_models(self) -> List[str]:
        """Get list of available model types"""
        return list(self.model_registry.keys())

    def get_model_health(self, model_type: str) -> Optional[Dict[str, Any]]:
        """Get health information for a model"""
        return self.model_health.get(model_type)

    def check_model_health(self, model_type: str) -> Dict[str, Any]:
        """
        Perform health check on a loaded model

        Returns:
            Dict with health status and metrics
        """
        try:
            if model_type not in self.loaded_models:
                return {"status": "not_loaded", "model_type": model_type}

            inferencer = self.loaded_models[model_type]
            health_info = self.model_health.get(model_type, {})

            # Perform basic health check (this is simplified)
            status = "healthy"

            # Check if model has been used recently
            time_since_load = time.time() - health_info.get("loaded_at", 0)
            if time_since_load > 86400:  # 24 hours
                status = "stale"

            # Check error rate
            inference_count = health_info.get("inference_count", 0)
            error_count = health_info.get("error_count", 0)
            if inference_count > 0:
                error_rate = error_count / inference_count
                if error_rate > 0.1:  # 10% error rate
                    status = "unhealthy"

            health_result = {
                "status": status,
                "model_type": model_type,
                "version_id": health_info.get("version_id"),
                "loaded_at": health_info.get("loaded_at"),
                "inference_count": inference_count,
                "error_count": error_count,
                "error_rate": error_count / max(inference_count, 1),
                "avg_inference_time": health_info.get("avg_inference_time", 0),
                "last_check": time.time(),
            }

            # Update health info
            self.model_health[model_type]["last_health_check"] = time.time()
            self.model_health[model_type]["status"] = status

            return health_result

        except Exception as e:
            logger.error(f"Health check failed for {model_type}: {e}")
            return {
                "status": "error",
                "model_type": model_type,
                "error": str(e),
                "last_check": time.time(),
            }

    def cleanup(self):
        """Clean up all loaded models and resources"""
        try:
            # Unload all models
            for model_type in list(self.loaded_models.keys()):
                self.unload_model(model_type)

            # Save registry
            self._save_registry()

            logger.info("Model manager cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize model manager resources"""
        # Registry is already loaded in __init__
        logger.info("Model manager initialized")

    async def _start_internal(self):
        """Start model manager internal operations"""
        # No background operations needed
        pass

    async def _stop_internal(self):
        """Stop model manager internal operations"""
        # Perform cleanup
        self.cleanup()

    async def _cleanup(self):
        """Cleanup model manager resources"""
        self.cleanup()
