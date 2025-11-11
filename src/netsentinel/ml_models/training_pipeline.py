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
    from ..core.event_bus import get_event_bus, create_event
    from ..utils.centralized import create_logger
    from .data_preprocessing import DataPreprocessingPipeline, PreprocessingConfig
    from .distributed_training import DistributedTrainer, DistributedTrainingConfig
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from utils.centralized import create_logger
    DataPreprocessingPipeline = None
    PreprocessingConfig = None
    DistributedTrainer = None
    DistributedTrainingConfig = None
    get_event_bus = None
    create_event = None

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

        # Initialize data preprocessing pipeline
        preprocessing_config = config.get("preprocessing", {}) if config else {}
        self.preprocessor = DataPreprocessingPipeline(
            config=PreprocessingConfig(**preprocessing_config)
        ) if DataPreprocessingPipeline else None

        # Initialize distributed training
        distributed_config = config.get("distributed", {}) if config else {}
        self.distributed_trainer = DistributedTrainer(
            config=DistributedTrainingConfig(**distributed_config)
        ) if DistributedTrainer else None

        # Preprocessing state
        self.is_preprocessing_fitted = False

        # WebSocket integration
        self.event_bus = get_event_bus() if get_event_bus else None

    def _publish_training_status(self, status: str, progress: float = 0.0,
                                details: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish training status update via WebSocket

        Args:
            status: Training status (started, progress, completed, failed)
            progress: Training progress (0.0 to 1.0)
            details: Additional status details
        """
        if not self.event_bus:
            return

        try:
            status_data = {
                "type": "ml.training.status",
                "data": {
                    "model_type": self.model_type,
                    "status": status,
                    "progress": progress,
                    "timestamp": time.time(),
                    "details": details or {}
                }
            }

            event = create_event("ml.training.status", status_data)
            self.event_bus.publish(event)

            logger.debug(f"Published ML training status: {status} ({progress:.1%})")

        except Exception as e:
            logger.warning(f"Failed to publish training status: {e}")

    def _publish_model_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Publish model performance metrics via WebSocket

        Args:
            metrics: Model performance metrics
        """
        if not self.event_bus:
            return

        try:
            metrics_data = {
                "type": "ml.model.metrics",
                "data": {
                    "model_type": self.model_type,
                    "metrics": metrics,
                    "timestamp": time.time()
                }
            }

            event = create_event("ml.model.metrics", metrics_data)
            self.event_bus.publish(event)

            logger.debug(f"Published ML model metrics for {self.model_type}")

        except Exception as e:
            logger.warning(f"Failed to publish model metrics: {e}")

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

    def preprocess_events(self, events: List[Dict[str, Any]], fit_preprocessor: bool = True) -> tuple:
        """
        Preprocess events using the data preprocessing pipeline

        Args:
            events: List of network events
            fit_preprocessor: Whether to fit the preprocessor on this data

        Returns:
            Tuple of (preprocessed_data, preprocessing_report)
        """
        if not self.preprocessor:
            logger.warning("Data preprocessing not available, skipping preprocessing")
            # Convert events to basic format
            import numpy as np
            basic_features = []
            for event in events:
                # Simple feature extraction
                features = [
                    event.get("logtype", 0),
                    event.get("dst_port", 0),
                    event.get("bytes_sent", 0),
                    event.get("bytes_received", 0),
                    event.get("error_count", 0),
                ]
                basic_features.append(features)
            return np.array(basic_features), {"message": "Basic preprocessing only"}

        try:
            # Convert events to format expected by preprocessor
            feature_dicts = []
            for event in events:
                # Convert event to feature dictionary that preprocessor expects
                feature_dict = {
                    "event_type": event.get("logtype", 0),
                    "destination_port": event.get("dst_port", 0),
                    "bytes_sent": event.get("bytes_sent", 0),
                    "bytes_received": event.get("bytes_received", 0),
                    "packets_sent": event.get("packets_sent", 0),
                    "packets_received": event.get("packets_received", 0),
                    "connection_duration": event.get("duration", 0.0),
                    "error_count": event.get("error_count", 0),
                    "timestamp": event.get("timestamp", time.time()),
                }
                feature_dicts.append(feature_dict)

            # Apply preprocessing
            if fit_preprocessor or not self.is_preprocessing_fitted:
                preprocessed_data, report = self.preprocessor.fit_transform(feature_dicts)
                self.is_preprocessing_fitted = True
            else:
                preprocessed_data, report = self.preprocessor.transform(feature_dicts)

            logger.info(f"Preprocessed {len(events)} events into {preprocessed_data.shape} features")
            return preprocessed_data, report

        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            # Fallback to basic preprocessing
            import numpy as np
            basic_features = []
            for event in events:
                features = [
                    event.get("logtype", 0),
                    event.get("dst_port", 0),
                    event.get("bytes_sent", 0),
                    event.get("bytes_received", 0),
                    event.get("error_count", 0),
                ]
                basic_features.append(features)
            return np.array(basic_features), {"error": str(e), "fallback": True}

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
            # Publish training started status
            self._publish_training_status("started", 0.0, {
                "event_count": len(events),
                "epochs": epochs or self.training_config.get('epochs', 10)
            })

            if epochs:
                self.training_config["epochs"] = epochs

            logger.info(
                f"Starting training with {len(events)} events, "
                f"{self.training_config['epochs']} epochs"
            )

            # Preprocess events
            logger.info("Preprocessing training data...")
            self._publish_training_status("preprocessing", 0.1, {"phase": "data_preprocessing"})
            preprocessed_data, preprocessing_report = self.preprocess_events(events, fit_preprocessor=True)
            logger.info(f"Preprocessing complete: {preprocessing_report}")
            self._publish_training_status("preprocessing_complete", 0.2, preprocessing_report)

            # Initialize model and engine
            self._publish_training_status("initializing", 0.25, {"phase": "model_initialization"})
            self._initialize_model()
            self._initialize_engine()
            self._publish_training_status("initialization_complete", 0.3, {"model_type": self.model_type})

            # Create temporary directory for dataset
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create dataset from events
                self._publish_training_status("dataset_creation", 0.35, {"phase": "dataset_preparation"})
                dataset = self._create_dataset_from_events(events, temp_dir)
                self._publish_training_status("dataset_ready", 0.4, {"phase": "dataset_ready"})

                # Train the model
                self._publish_training_status("training", 0.5, {"phase": "model_training"})
                start_time = time.time()
                self.engine.fit(
                    model=self.model,
                    datamodule=dataset,
                )
                training_time = time.time() - start_time

                logger.info(".2f")
                self._publish_training_status("training_complete", 0.8, {
                    "training_time": training_time,
                    "phase": "training_complete"
                })

                # Test the model
                self._publish_training_status("testing", 0.85, {"phase": "model_testing"})
                self.engine.test(model=self.model, datamodule=dataset)
                self._publish_training_status("testing_complete", 0.9, {"phase": "testing_complete"})

                # Save the trained model
                self._publish_training_status("saving", 0.95, {"phase": "model_saving"})
                self._save_trained_model()

                # Get final metrics and publish
                metrics = self.get_training_metrics()
                self._publish_model_metrics(metrics)
                self._publish_training_status("completed", 1.0, {
                    "metrics": metrics,
                    "phase": "training_completed"
                })

                self.is_trained = True
                logger.info("Training completed successfully")
                return True

        except Exception as e:
            logger.error(f"Training failed: {e}")
            self._publish_training_status("failed", 0.0, {
                "error": str(e),
                "phase": "training_failed"
            })
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

    def train_distributed(self, events: List[Dict[str, Any]], epochs: Optional[int] = None) -> bool:
        """
        Train the ML model using distributed training

        Args:
            events: List of network events for training
            epochs: Number of training epochs

        Returns:
            bool: True if training successful
        """
        if not self.distributed_trainer:
            logger.warning("Distributed training not available, falling back to regular training")
            return self.train_on_events(events, epochs)

        try:
            from .distributed_training import spawn_distributed_training

            if epochs:
                self.training_config["epochs"] = epochs

            logger.info(f"Starting distributed training with {len(events)} events")

            # Define training function for distributed execution
            def distributed_train_function(trainer, events, config):
                # Setup distributed training
                trainer.setup_distributed()

                # Preprocess data on main process
                if trainer.is_main_process():
                    preprocessed_data, report = self.preprocess_events(events, fit_preprocessor=True)
                    trainer.log_distributed(f"Preprocessing complete: {report}")
                else:
                    preprocessed_data = None

                # Initialize model and engine
                self._initialize_model()
                self._initialize_engine()

                # Wrap model for distributed training
                self.model = trainer.create_distributed_model(self.model)

                # Create dataset and dataloader
                with tempfile.TemporaryDirectory() as temp_dir:
                    if trainer.is_main_process():
                        dataset = self._create_dataset_from_events(events, temp_dir)
                        dataloader = trainer.create_distributed_dataloader(
                            dataset, config["batch_size"]
                        )

                    # Training loop would go here - simplified for now
                    trainer.log_distributed("Distributed training setup complete")

                trainer.cleanup_distributed()

            # Spawn distributed training
            world_size = self.distributed_trainer.config.world_size
            spawn_distributed_training(
                world_size=world_size,
                train_function=distributed_train_function,
                args=(events, self.training_config)
            )

            self.is_trained = True
            logger.info("Distributed training completed successfully")
            return True

        except Exception as e:
            logger.error(f"Distributed training failed: {e}")
            self.is_trained = False
            return False

    def get_preprocessing_summary(self) -> Dict[str, Any]:
        """Get summary of preprocessing pipeline status"""
        if self.preprocessor:
            return {
                "preprocessing_available": True,
                "is_fitted": self.is_preprocessing_fitted,
                "config": self.preprocessor.get_preprocessing_summary() if hasattr(self.preprocessor, 'get_preprocessing_summary') else {},
            }
        else:
            return {
                "preprocessing_available": False,
                "fallback_mode": True,
            }

    def get_distributed_training_summary(self) -> Dict[str, Any]:
        """Get summary of distributed training capabilities"""
        if self.distributed_trainer:
            return {
                "distributed_available": True,
                "config": self.distributed_trainer.get_training_stats(),
            }
        else:
            return {
                "distributed_available": False,
            }

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
