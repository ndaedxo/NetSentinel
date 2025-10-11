#!/usr/bin/env python3
"""
ML Model Training Script for OpenCanary Anomaly Detection
Trains Anomalib models on network event data
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from anomalib.models import Fastflow, EfficientAd, Padim
from anomalib.engine import Engine
from anomalib.data import Folder
from opencanary.ml_anomaly_detector import NetworkEventAnomalyDetector

def load_training_data(data_path: str):
    """Load training data from OpenCanary logs or Valkey"""
    training_events = []
    
    if os.path.exists(data_path):
        with open(data_path, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    training_events.append(event)
                except json.JSONDecodeError:
                    continue
    
    return training_events

def train_model(model_type: str, training_data: list, output_path: str):
    """Train the specified model on training data"""
    print(f"Training {model_type} model on {len(training_data)} events...")
    
    # Initialize detector
    detector = NetworkEventAnomalyDetector(model_type=model_type)
    
    # Train on normal events (assuming training data contains normal behavior)
    detector.train_on_normal_events(training_data, epochs=10)
    
    # Save model info
    model_info = detector.get_model_info()
    model_info['training_data_size'] = len(training_data)
    model_info['training_timestamp'] = time.time()
    
    with open(output_path, 'w') as f:
        json.dump(model_info, f, indent=2)
    
    print(f"Model training completed. Info saved to {output_path}")
    return detector

def main():
    parser = argparse.ArgumentParser(description='Train ML models for OpenCanary anomaly detection')
    parser.add_argument('--model', choices=['fastflow', 'efficient_ad', 'padim'], 
                       default='fastflow', help='Model type to train')
    parser.add_argument('--data', default='hybrid-data/opencanary/logs/opencanary.log',
                       help='Path to training data file')
    parser.add_argument('--output', default='models/',
                       help='Output directory for trained models')
    parser.add_argument('--events', type=int, default=1000,
                       help='Number of events to use for training')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Load training data
    print(f"Loading training data from {args.data}...")
    training_data = load_training_data(args.data)
    
    if not training_data:
        print("No training data found!")
        return 1
    
    # Limit training data
    if len(training_data) > args.events:
        training_data = training_data[:args.events]
    
    print(f"Loaded {len(training_data)} training events")
    
    # Train model
    output_path = os.path.join(args.output, f'{args.model}_model_info.json')
    detector = train_model(args.model, training_data, output_path)
    
    print("Training completed successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
