#!/usr/bin/env python3
"""
NetSentinel ML Model Training Script
Trains anomaly detection models on network event data
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import pandas as pd

# Add NetSentinel to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector
from netsentinel.processors.event_analyzer import EventAnalyzer
from netsentinel.core.models import create_event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MLModelTrainer:
    """ML model trainer for NetSentinel anomaly detection"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.detector = NetworkEventAnomalyDetector(
            model_type=config.get("model_type", "fastflow"),
            model_path=config.get("model_path"),
            config=config.get("ml_config", {})
        )
        
    def load_training_data(self, data_path: str) -> List[Dict]:
        """Load training data from file"""
        logger.info(f"Loading training data from {data_path}")
        
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Training data file not found: {data_path}")
        
        # Load data based on file extension
        if data_path.endswith('.json'):
            with open(data_path, 'r') as f:
                data = json.load(f)
        elif data_path.endswith('.csv'):
            df = pd.read_csv(data_path)
            data = df.to_dict('records')
        else:
            raise ValueError(f"Unsupported file format: {data_path}")
        
        logger.info(f"Loaded {len(data)} training samples")
        return data
    
    def generate_synthetic_data(self, num_samples: int = 1000) -> List[Dict]:
        """Generate synthetic training data for testing"""
        logger.info(f"Generating {num_samples} synthetic training samples")
        
        synthetic_data = []
        protocols = ["SSH", "HTTP", "FTP", "SMTP"]
        ports = [22, 80, 21, 25]
        
        for i in range(num_samples):
            protocol = np.random.choice(protocols)
            port = ports[protocols.index(protocol)]
            
            event = {
                "logtype": 4002 if protocol == "SSH" else 3000,
                "src_host": f"192.168.1.{np.random.randint(1, 255)}",
                "dst_port": port,
                "logdata": {
                    "USERNAME": f"user{np.random.randint(1, 100)}",
                    "PASSWORD": f"pass{np.random.randint(1, 1000)}" if protocol == "SSH" else None,
                    "PATH": f"/page{np.random.randint(1, 100)}.html" if protocol == "HTTP" else None
                }
            }
            synthetic_data.append(event)
        
        return synthetic_data
    
    def preprocess_data(self, data: List[Dict]) -> List[Dict]:
        """Preprocess training data"""
        logger.info("Preprocessing training data")
        
        processed_data = []
        for event in data:
            # Clean and validate data
            if self._is_valid_event(event):
                processed_data.append(event)
        
        logger.info(f"Preprocessed {len(processed_data)} valid events")
        return processed_data
    
    def _is_valid_event(self, event: Dict) -> bool:
        """Validate event data"""
        required_fields = ["logtype", "src_host"]
        return all(field in event for field in required_fields)
    
    def train_model(self, training_data: List[Dict]) -> Dict[str, Any]:
        """Train the ML model"""
        logger.info(f"Training model on {len(training_data)} samples")
        
        start_time = time.time()
        
        # Train the model
        self.detector.train_on_normal_events(training_data)
        
        training_time = time.time() - start_time
        
        # Get training metrics
        metrics = {
            "training_time": training_time,
            "samples_processed": len(training_data),
            "is_trained": self.detector.is_trained,
            "model_type": self.detector.model_type,
            "feature_stats": self.detector.feature_stats
        }
        
        logger.info(f"Training completed in {training_time:.2f} seconds")
        return metrics
    
    def validate_model(self, test_data: List[Dict]) -> Dict[str, Any]:
        """Validate the trained model"""
        logger.info(f"Validating model on {len(test_data)} test samples")
        
        predictions = []
        inference_times = []
        
        for event in test_data:
            start_time = time.time()
            score, analysis = self.detector.detect_anomaly(event)
            inference_time = time.time() - start_time
            
            predictions.append({
                "event": event,
                "anomaly_score": score,
                "analysis": analysis,
                "inference_time": inference_time
            })
            
            inference_times.append(inference_time)
        
        # Calculate validation metrics
        avg_inference_time = np.mean(inference_times)
        anomaly_count = sum(1 for p in predictions if p["anomaly_score"] > 0.5)
        
        validation_metrics = {
            "total_predictions": len(predictions),
            "anomalies_detected": anomaly_count,
            "anomaly_rate": anomaly_count / len(predictions),
            "avg_inference_time": avg_inference_time,
            "predictions": predictions
        }
        
        logger.info(f"Validation completed - Anomaly rate: {validation_metrics['anomaly_rate']:.3f}")
        return validation_metrics
    
    def save_model(self, model_path: str) -> bool:
        """Save the trained model"""
        try:
            self.detector.model_path = model_path
            self.detector._save_model()
            logger.info(f"Model saved to {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def load_model(self, model_path: str) -> bool:
        """Load a trained model"""
        try:
            self.detector.model_path = model_path
            self.detector._load_model()
            logger.info(f"Model loaded from {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


def main():
    """Main training function"""
    parser = argparse.ArgumentParser(description="Train NetSentinel ML models")
    parser.add_argument("--data-path", type=str, help="Path to training data file")
    parser.add_argument("--model-type", type=str, default="fastflow", 
                       choices=["fastflow", "efficient_ad", "padim"],
                       help="ML model type")
    parser.add_argument("--model-path", type=str, help="Path to save/load model")
    parser.add_argument("--synthetic", action="store_true", 
                       help="Generate synthetic training data")
    parser.add_argument("--num-samples", type=int, default=1000,
                       help="Number of synthetic samples to generate")
    parser.add_argument("--test-data", type=str, help="Path to test data file")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--output-dir", type=str, default="./models",
                       help="Output directory for models and reports")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load configuration
    config = {
        "model_type": args.model_type,
        "model_path": args.model_path or os.path.join(args.output_dir, f"{args.model_type}_model.pth"),
        "ml_config": {
            "threshold": 0.5,
            "confidence_threshold": 0.7,
            "batch_size": 32,
            "epochs": 10
        }
    }
    
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config.update(json.load(f))
    
    # Initialize trainer
    trainer = MLModelTrainer(config)
    
    try:
        # Load or generate training data
        if args.synthetic:
            training_data = trainer.generate_synthetic_data(args.num_samples)
        elif args.data_path:
            training_data = trainer.load_training_data(args.data_path)
        else:
            logger.error("No training data provided. Use --data-path or --synthetic")
            return 1
        
        # Preprocess data
        training_data = trainer.preprocess_data(training_data)
        
        if not training_data:
            logger.error("No valid training data after preprocessing")
            return 1
        
        # Train model
        training_metrics = trainer.train_model(training_data)
        
        # Validate model if test data provided
        validation_metrics = None
        if args.test_data:
            test_data = trainer.load_training_data(args.test_data)
            test_data = trainer.preprocess_data(test_data)
            validation_metrics = trainer.validate_model(test_data)
        
        # Save model
        if trainer.save_model(config["model_path"]):
            logger.info("Model training completed successfully")
        else:
            logger.error("Failed to save model")
            return 1
        
        # Save training report
        report = {
            "training_metrics": training_metrics,
            "validation_metrics": validation_metrics,
            "config": config,
            "timestamp": time.time()
        }
        
        report_path = os.path.join(args.output_dir, f"{args.model_type}_training_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Training report saved to {report_path}")
        
        # Print summary
        print("\n" + "="*50)
        print("TRAINING SUMMARY")
        print("="*50)
        print(f"Model Type: {args.model_type}")
        print(f"Training Samples: {training_metrics['samples_processed']}")
        print(f"Training Time: {training_metrics['training_time']:.2f}s")
        print(f"Model Saved: {config['model_path']}")
        
        if validation_metrics:
            print(f"Test Samples: {validation_metrics['total_predictions']}")
            print(f"Anomaly Rate: {validation_metrics['anomaly_rate']:.3f}")
            print(f"Avg Inference Time: {validation_metrics['avg_inference_time']:.4f}s")
        
        print("="*50)
        
        return 0
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return 1


def test_model_inference():
    """Test model inference with sample data"""
    logger.info("Testing model inference")
    
    # Create test detector
    detector = NetworkEventAnomalyDetector(model_type="fastflow")
    
    # Generate test events
    test_events = [
        {
            "logtype": 4002,
            "src_host": "192.168.1.100",
            "dst_port": 22,
            "logdata": {"USERNAME": "admin"}
        },
        {
            "logtype": 3000,
            "src_host": "192.168.1.101",
            "dst_port": 80,
            "logdata": {"PATH": "/admin.php"}
        }
    ]
    
    # Test inference
    for i, event in enumerate(test_events):
        start_time = time.time()
        score, analysis = detector.detect_anomaly(event)
        inference_time = time.time() - start_time
        
        print(f"Event {i+1}:")
        print(f"  Anomaly Score: {score:.3f}")
        print(f"  Inference Time: {inference_time:.4f}s")
        print(f"  Analysis: {analysis}")
        print()


if __name__ == "__main__":
    # Run main training if called directly
    if len(sys.argv) > 1:
        exit_code = main()
        sys.exit(exit_code)
    else:
        # Run test inference
        test_model_inference()