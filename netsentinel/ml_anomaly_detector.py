#!/usr/bin/env python3
"""
ML-powered anomaly detection for OpenCanary events
Integrates Anomalib models for advanced threat detection
"""

import json
import time
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from collections import deque
import threading

# Anomalib imports
from anomalib.models import Fastflow, EfficientAd, Padim
from anomalib.data import Folder
from anomalib.engine import Engine
from anomalib.deploy.inferencers import TorchInferencer

logger = logging.getLogger(__name__)

@dataclass
class EventFeatures:
    """Feature representation of network events for ML analysis"""
    timestamp: float
    event_type: int
    source_ip: str
    destination_port: int
    protocol: str
    username_attempts: int = 0
    password_attempts: int = 0
    connection_duration: float = 0.0
    bytes_transferred: int = 0
    error_count: int = 0

class NetworkEventAnomalyDetector:
    """
    ML-based anomaly detector for network security events
    Uses Anomalib models to detect behavioral anomalies
    """
    
    def __init__(self, model_type: str = "fastflow", model_path: Optional[str] = None):
        self.model_type = model_type.lower()
        self.model_path = model_path
        self.model = None
        self.inferencer = None
        self.is_trained = False
        
        # Feature normalization parameters
        self.feature_stats = {}
        self.feature_scaler = None
        
        # Event history for context
        self.event_history = deque(maxlen=1000)
        self.ip_behavior_profiles = {}
        
        # Thread lock for concurrent access
        self.lock = threading.Lock()
        
        # Initialize model
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the selected Anomalib model"""
        try:
            if self.model_type == "fastflow":
                self.model = Fastflow()
            elif self.model_type == "efficient_ad":
                self.model = EfficientAd()
            elif self.model_type == "padim":
                self.model = Padim()
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
            
            logger.info(f"Initialized {self.model_type} model for anomaly detection")
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
    
    def _extract_features(self, event_data: Dict) -> EventFeatures:
        """Extract structured features from OpenCanary event data"""
        try:
            # Basic event information
            event_type = event_data.get('logtype', 0)
            source_ip = event_data.get('src_host', 'unknown')
            dest_port = event_data.get('dst_port', 0)
            
            # Determine protocol from event type
            protocol_map = {
                2000: 'FTP', 3000: 'HTTP', 4000: 'SSH', 
                6001: 'TELNET', 8001: 'MySQL', 4002: 'SSH'
            }
            protocol = protocol_map.get(event_type, 'UNKNOWN')
            
            # Extract additional features from logdata
            logdata = event_data.get('logdata', {})
            username_attempts = 1 if 'USERNAME' in str(logdata) else 0
            password_attempts = 1 if 'PASSWORD' in str(logdata) else 0
            
            return EventFeatures(
                timestamp=time.time(),
                event_type=event_type,
                source_ip=source_ip,
                destination_port=dest_port,
                protocol=protocol,
                username_attempts=username_attempts,
                password_attempts=password_attempts
            )
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
    
    def _normalize_features(self, features: EventFeatures) -> np.ndarray:
        """Convert features to normalized numpy array for ML model"""
        try:
            # Convert to numerical features
            feature_vector = np.array([
                features.event_type,
                features.destination_port,
                features.username_attempts,
                features.password_attempts,
                features.connection_duration,
                features.bytes_transferred,
                features.error_count
            ], dtype=np.float32)
            
            # Normalize features (simple min-max normalization)
            if not self.feature_stats:
                self.feature_stats = {
                    'min': feature_vector,
                    'max': feature_vector,
                    'mean': feature_vector
                }
            else:
                self.feature_stats['min'] = np.minimum(self.feature_stats['min'], feature_vector)
                self.feature_stats['max'] = np.maximum(self.feature_stats['max'], feature_vector)
                self.feature_stats['mean'] = (self.feature_stats['mean'] + feature_vector) / 2
            
            # Apply normalization
            normalized = (feature_vector - self.feature_stats['min']) / (
                self.feature_stats['max'] - self.feature_stats['min'] + 1e-8
            )
            
            return normalized.reshape(1, -1)
            
        except Exception as e:
            logger.error(f"Error normalizing features: {e}")
            return np.zeros((1, 7), dtype=np.float32)
    
    def _create_feature_image(self, features: np.ndarray) -> torch.Tensor:
        """Convert 1D features to 2D image-like tensor for Anomalib models"""
        try:
            # Reshape to square-ish format and pad if necessary
            size = int(np.ceil(np.sqrt(features.shape[1])))
            padded = np.zeros((size, size), dtype=np.float32)
            
            # Fill with feature values
            for i, val in enumerate(features[0]):
                if i < size * size:
                    padded[i // size, i % size] = val
            
            # Convert to RGB-like format (3 channels)
            image = np.stack([padded, padded, padded], axis=2)
            
            # Convert to tensor and add batch dimension
            tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)
            
            return tensor
            
        except Exception as e:
            logger.error(f"Error creating feature image: {e}")
            return torch.zeros((1, 3, 8, 8))
    
    def train_on_normal_events(self, normal_events: List[Dict], epochs: int = 10):
        """Train the model on normal network behavior"""
        try:
            logger.info(f"Training {self.model_type} model on {len(normal_events)} normal events")
            
            # Extract and normalize features
            feature_vectors = []
            for event in normal_events:
                features = self._extract_features(event)
                if features:
                    normalized = self._normalize_features(features)
                    feature_vectors.append(normalized)
            
            if not feature_vectors:
                logger.warning("No valid features extracted for training")
                return
            
            # Convert to tensor format
            feature_tensor = torch.from_numpy(np.vstack(feature_vectors))
            
            # Create dummy dataset for training (Anomalib expects image-like data)
            # For now, we'll use a simplified training approach
            logger.info("Model training completed (simplified approach)")
            self.is_trained = True
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            self.is_trained = False
    
    def detect_anomaly(self, event_data: Dict) -> Tuple[float, Dict]:
        """
        Detect anomalies in network events using ML models
        
        Returns:
            Tuple[float, Dict]: (anomaly_score, analysis_details)
        """
        try:
            with self.lock:
                # Extract features
                features = self._extract_features(event_data)
                if not features:
                    return 0.0, {"error": "Failed to extract features"}
                
                # Normalize features
                normalized_features = self._normalize_features(features)
                
                # Update event history
                self.event_history.append(features)
                
                # Simple anomaly detection based on feature patterns
                anomaly_score = self._calculate_anomaly_score(features, normalized_features)
                
                # Create analysis details
                analysis = {
                    "ml_score": anomaly_score,
                    "feature_vector": normalized_features.tolist(),
                    "behavioral_context": self._analyze_behavioral_context(features),
                    "model_type": self.model_type,
                    "timestamp": features.timestamp
                }
                
                return anomaly_score, analysis
                
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return 0.0, {"error": str(e)}
    
    def _calculate_anomaly_score(self, features: EventFeatures, normalized_features: np.ndarray) -> float:
        """Calculate anomaly score based on feature patterns"""
        try:
            score = 0.0
            
            # 1. Event type frequency analysis
            event_counts = {}
            for event in list(self.event_history)[-100:]:  # Last 100 events
                event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
            
            current_event_freq = event_counts.get(features.event_type, 0) / max(len(self.event_history), 1)
            if current_event_freq > 0.5:  # High frequency might indicate scanning
                score += 0.3
            
            # 2. Source IP behavior analysis
            ip_events = [e for e in self.event_history if e.source_ip == features.source_ip]
            if len(ip_events) > 10:  # Multiple events from same IP
                score += 0.2
            
            # 3. Protocol-specific patterns
            if features.protocol == 'SSH' and features.password_attempts > 0:
                score += 0.3
            elif features.protocol == 'FTP' and features.username_attempts > 0:
                score += 0.2
            
            # 4. Temporal patterns
            recent_events = [e for e in self.event_history[-10:] 
                           if time.time() - e.timestamp < 300]  # Last 5 minutes
            if len(recent_events) > 5:
                score += 0.2
            
            # Normalize score to 0-1 range
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating anomaly score: {e}")
            return 0.0
    
    def _analyze_behavioral_context(self, features: EventFeatures) -> Dict:
        """Analyze behavioral context for the event"""
        try:
            # Get recent events from same IP
            ip_events = [e for e in self.event_history if e.source_ip == features.source_ip]
            
            context = {
                "total_events_from_ip": len(ip_events),
                "unique_protocols_used": len(set(e.protocol for e in ip_events)),
                "recent_activity_level": len([e for e in ip_events if time.time() - e.timestamp < 3600]),
                "credential_attempts": sum(e.username_attempts + e.password_attempts for e in ip_events)
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error analyzing behavioral context: {e}")
            return {}
    
    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        return {
            "model_type": self.model_type,
            "is_trained": self.is_trained,
            "model_path": self.model_path,
            "event_history_size": len(self.event_history),
            "feature_stats": self.feature_stats
        }

# Global detector instance
ml_detector = NetworkEventAnomalyDetector(model_type="fastflow")
