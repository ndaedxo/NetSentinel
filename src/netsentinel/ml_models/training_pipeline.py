#!/usr/bin/env python3
"""
ML Training Pipeline for NetSentinel

Provides comprehensive model training capabilities using Anomalib Engine
for anomaly detection in network security events.
"""

import os
import time
import tempfile
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging

# Anomalib imports
from anomalib.data import Folder
from anomalib.engine import Engine
from anomalib.models import Fastflow, EfficientAd, Padim
from anomalib.deploy.inferencers import TorchInferencer

# Import new core components
try:
    from ..core.base import BaseComponent
    from ..utils.centralized import create_logger
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from utils.centralized import create_logger

logger = create_logger("training_pipeline", level="INFO")


class TrainingPipeline(BaseComponent):
    """
    ML training pipeline for anomaly detection models

    Handles the complete training workflow including:
    - Data preparation and preprocessing
    - Model training with Anomalib Engine
    - Model validation and evaluation
    - Model persistence and versioning
    """

    def __init__(
        self,
        name: str = "training_pipeline",
        model_type: str = "fastflow",
        model_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize training pipeline

        Args:
            name: Component name
            model_type: Type of ML model ('fastflow', 'efficientad', 'padim')
            model_path: Path to save trained model
            config: Additional configuration
        """
        super().__init__(name, config, logger)

        self.model_type = model_type.lower()
        self.model_path = model_path or self._get_default_model_path()
        self.engine = None
        self.model = None
        self.is_trained = False

        # Training configuration
        self.training_config = {
            "epochs": 10,
            "batch_size": 32,
            "learning_rate": 0.001,
            "image_size": (256, 256),
            "accelerator": "auto",
            "devices": 1,
        }

        # Update config if provided
        if config:
            self.training_config.update(config)

        # Create model directory if it doesn't exist
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

    def _get_default_model_path(self) -> str:
        """Get default model path"""
        return f"models/{self.model_type}_anomaly_detector.pth"

    def _initialize_model(self):
        """Initialize the Anomalib model"""
        try:
            if self.model_type == "fastflow":
                self.model = Fastflow()
            elif self.model_type == "efficientad":
                self.model = EfficientAd()
            elif self.model_type == "padim":
                self.model = Padim()
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")

            logger.info(f"Initialized {self.model_type} model for training")

        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise

    def _initialize_engine(self):
        """Initialize Anomalib training engine"""
        try:
            self.engine = Engine(
                accelerator=self.training_config["accelerator"],
                devices=self.training_config["devices"],
                max_epochs=self.training_config["epochs"],
            )
            logger.info("Initialized Anomalib training engine")

        except Exception as e:
            logger.error(f"Failed to initialize training engine: {e}")
            raise

    def _create_dataset_from_events(
        self, events: List[Dict[str, Any]], temp_dir: str
    ) -> Folder:
        """
        Create Anomalib dataset from network events

        Converts network events to image-like data for anomaly detection training.
        """
        try:
            # Create temporary directories for normal/abnormal data
            normal_dir = os.path.join(temp_dir, "normal")
            os.makedirs(normal_dir, exist_ok=True)

            # For anomaly detection training, we assume all training data is "normal"
            # In production, you'd have separate normal/abnormal datasets
            for i, event in enumerate(events):
                # Convert event to feature representation
                features = self._extract_event_features(event)

                # Create a simple image representation
                # In a real implementation, this would be more sophisticated
                image_data = self._create_feature_image(features)

                # Save as temporary image file
                image_path = os.path.join(normal_dir, f"event_{i:06d}.png")
                self._save_image_array(image_data, image_path)

            # Create Anomalib Folder dataset
            dataset = Folder(
                root=temp_dir,
                normal_dir="normal",
                abnormal_dir=None,  # Only normal data for training
                image_size=self.training_config["image_size"],
                train_batch_size=self.training_config["batch_size"],
                eval_batch_size=self.training_config["batch_size"],
            )

            logger.info(f"Created dataset with {len(events)} training samples")
            return dataset

        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            raise

    def _extract_event_features(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from network event"""
        # Basic event information
        features = {
            "event_type": event.get("logtype", 0),
            "source_ip": event.get("src_host", "unknown"),
            "destination_port": event.get("dst_port", 0),
            "protocol": self._determine_protocol(event),
            "username_attempts": 1 if "USERNAME" in str(event.get("logdata", {})) else 0,
            "password_attempts": 1 if "PASSWORD" in str(event.get("logdata", {})) else 0,
            "timestamp": event.get("timestamp", time.time()),
        }

        return features

    def _determine_protocol(self, event: Dict[str, Any]) -> str:
        """Determine protocol from event type"""
        event_type = event.get("logtype", 0)
        protocol_map = {
            2000: "FTP",
            3000: "HTTP",
            4000: "SSH",
            6001: "TELNET",
            8001: "MySQL",
            4002: "SSH",
        }
        return protocol_map.get(event_type, "UNKNOWN")

    def _create_feature_image(self, features: Dict[str, Any]) -> np.ndarray:
        """Create image representation from features"""

        # Create a simple 32x32 RGB image from features
        # This is a simplified approach - real implementation would be more sophisticated
        image_size = 32
        image = np.zeros((image_size, image_size, 3), dtype=np.uint8)

        # Map features to image pixels
        # Event type -> red channel
        event_type_normalized = min(features["event_type"] / 10000, 1.0)
        image[:, :, 0] = int(event_type_normalized * 255)

        # Port -> green channel
        port_normalized = min(features["destination_port"] / 65535, 1.0)
        image[:, :, 1] = int(port_normalized * 255)

        # Attempts -> blue channel
        attempts = features["username_attempts"] + features["password_attempts"]
        attempts_normalized = min(attempts / 10, 1.0)
        image[:, :, 2] = int(attempts_normalized * 255)

        return image

    def _save_image_array(self, image_array: np.ndarray, path: str):
        """Save numpy array as image file"""
        from PIL import Image

        # Convert to PIL Image and save
        image = Image.fromarray(image_array.astype(np.uint8))
        image.save(path)

    def train_on_events(
        self, events: List[Dict[str, Any]], epochs: Optional[int] = None
    ) -> bool:
        """
        Train the ML model on network events

        Args:
            events: List of network events for training
            epochs: Number of training epochs (overrides config)

        Returns:
            bool: True if training successful
        """
        try:
            if epochs:
                self.training_config["epochs"] = epochs

            logger.info(
                f"Starting training with {len(events)} events, "
                f"{self.training_config['epochs']} epochs"
            )

            # Initialize model and engine
            self._initialize_model()
            self._initialize_engine()

            # Create temporary directory for dataset
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create dataset from events
                dataset = self._create_dataset_from_events(events, temp_dir)

                # Train the model
                start_time = time.time()
                self.engine.fit(
                    model=self.model,
                    datamodule=dataset,
                )
                training_time = time.time() - start_time

                logger.info(".2f")

                # Test the model
                self.engine.test(model=self.model, datamodule=dataset)

                # Save the trained model
                self._save_trained_model()

                self.is_trained = True
                logger.info("Training completed successfully")
                return True

        except Exception as e:
            logger.error(f"Training failed: {e}")
            self.is_trained = False
            return False

    def _save_trained_model(self):
        """Save the trained model for inference"""
        try:
            if not self.model_path:
                logger.warning("No model path specified, skipping save")
                return

            # Create model directory
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

            # Save model using Anomalib's export functionality
            # This creates a TorchInferencer-compatible model
            inferencer_path = self.model_path.replace('.pth', '_inferencer')
            os.makedirs(inferencer_path, exist_ok=True)

            # Export model for inference
            self.engine.export(
                model=self.model,
                export_mode="torch",
                export_root=inferencer_path,
            )

            # Save training metadata
            metadata = {
                "model_type": self.model_type,
                "training_config": self.training_config,
                "training_timestamp": time.time(),
                "inferencer_path": inferencer_path,
            }

            metadata_path = self.model_path.replace('.pth', '_metadata.json')
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Model saved to {inferencer_path}")

        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            raise

    def get_training_metrics(self) -> Dict[str, Any]:
        """Get training performance metrics"""
        if not self.engine:
            return {"error": "No training engine available"}

        try:
            # Get metrics from the engine
            metrics = {}

            # Add training configuration
            metrics.update({
                "model_type": self.model_type,
                "is_trained": self.is_trained,
                "training_config": self.training_config,
                "model_path": self.model_path,
            })

            # Add engine metrics if available
            if hasattr(self.engine, 'trainer') and self.engine.trainer:
                if hasattr(self.engine.trainer, 'logged_metrics'):
                    metrics["logged_metrics"] = dict(self.engine.trainer.logged_metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to get training metrics: {e}")
            return {"error": str(e)}

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize training pipeline resources"""
        # Initialize model and engine
        try:
            self._initialize_model()
            self._initialize_engine()
        except Exception as e:
            logger.error(f"Failed to initialize training pipeline: {e}")

    async def _start_internal(self):
        """Start training pipeline internal operations"""
        # Training pipeline is ready to use after initialization
        pass

    async def _stop_internal(self):
        """Stop training pipeline internal operations"""
        # No background operations to stop
        pass

    async def _cleanup(self):
        """Cleanup training pipeline resources"""
        # Clear model and engine references
        if hasattr(self, "model"):
            self.model = None
        if hasattr(self, "engine"):
            self.engine = None
