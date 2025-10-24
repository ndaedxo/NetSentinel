# NetSentinel ML Integration Setup Guide

## 🧠 **Machine Learning Anomaly Detection Setup**

This guide provides comprehensive instructions for setting up and using NetSentinel's AI-powered anomaly detection capabilities.

## 📋 **Prerequisites**

### **System Requirements**
- Python 3.8+
- PyTorch 1.9+
- CUDA 11.0+ (for GPU acceleration)
- 8GB+ RAM (16GB+ recommended)
- 10GB+ free disk space

### **Dependencies**
```bash
# Core ML dependencies
pip install torch torchvision torchaudio
pip install anomalib==2.3.0
pip install numpy scikit-learn
pip install pandas matplotlib seaborn

# NetSentinel ML dependencies
pip install -r requirements.txt
```

## 🚀 **Quick Start**

### **1. Basic ML Setup**
```python
from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector

# Initialize ML detector
detector = NetworkEventAnomalyDetector(
    model_type="fastflow",  # or "efficient_ad", "padim"
    model_path="/path/to/model.pth"
)

# Train on normal network events
normal_events = [
    {
        "logtype": 4002,
        "src_host": "192.168.1.10",
        "dst_port": 22,
        "logdata": {"USERNAME": "user1"}
    },
    # ... more normal events
]

detector.train_on_normal_events(normal_events)

# Detect anomalies
event_data = {
    "logtype": 4002,
    "src_host": "192.168.1.100",
    "dst_port": 22,
    "logdata": {"USERNAME": "admin"}
}

anomaly_score, analysis = detector.detect_anomaly(event_data)
print(f"Anomaly Score: {anomaly_score}")
print(f"Analysis: {analysis}")
```

### **2. Integration with EventAnalyzer**
```python
from netsentinel.processors.event_analyzer import EventAnalyzer

# Configure ML-enabled analyzer
config = {
    "ml_enabled": True,
    "ml_model_type": "fastflow",
    "ml_model_path": "/path/to/model.pth",
    "ml_config": {
        "threshold": 0.5,
        "confidence_threshold": 0.7
    }
}

analyzer = EventAnalyzer(config=config)

# Analyze events with ML
event = create_event(
    event_type="4002",
    source="192.168.1.100",
    data={"logdata": {"USERNAME": "admin"}},
    severity="medium"
)

ml_score, ml_analysis = analyzer._ml_analysis(event)
```

## 🔧 **Advanced Configuration**

### **Model Types**

#### **FastFlow (Recommended)**
- **Best for**: Real-time anomaly detection
- **Performance**: Fast inference, good accuracy
- **Memory**: Moderate usage
```python
detector = NetworkEventAnomalyDetector(model_type="fastflow")
```

#### **EfficientAD**
- **Best for**: High accuracy requirements
- **Performance**: Slower inference, higher accuracy
- **Memory**: Higher usage
```python
detector = NetworkEventAnomalyDetector(model_type="efficient_ad")
```

#### **PaDiM**
- **Best for**: Resource-constrained environments
- **Performance**: Fast inference, moderate accuracy
- **Memory**: Low usage
```python
detector = NetworkEventAnomalyDetector(model_type="padim")
```

### **Configuration Options**
```python
config = {
    "ml_enabled": True,
    "ml_model_type": "fastflow",
    "ml_model_path": "/models/anomaly_detector.pth",
    "ml_config": {
        "threshold": 0.5,              # Anomaly threshold (0-1)
        "confidence_threshold": 0.7,   # Confidence threshold
        "batch_size": 32,             # Batch size for training
        "epochs": 10,                 # Training epochs
        "learning_rate": 0.001,       # Learning rate
        "feature_dim": 7,             # Feature dimension
        "image_size": 64              # Image size for tensors
    }
}
```

## 📊 **Training Data Preparation**

### **Data Format**
```python
# Normal network events for training
normal_events = [
    {
        "logtype": 4002,           # Event type (SSH login)
        "src_host": "192.168.1.10", # Source IP
        "dst_port": 22,             # Destination port
        "logdata": {                # Event data
            "USERNAME": "user1",
            "PASSWORD": "password123"
        }
    },
    {
        "logtype": 3000,           # HTTP request
        "src_host": "192.168.1.11",
        "dst_port": 80,
        "logdata": {
            "PATH": "/index.html",
            "METHOD": "GET"
        }
    }
    # ... more normal events
]
```

### **Data Collection Best Practices**
1. **Collect diverse normal traffic**: Include various protocols, ports, and patterns
2. **Time-based sampling**: Collect data over different time periods
3. **Volume**: Aim for 1000+ normal events for good training
4. **Quality**: Ensure all training data represents legitimate traffic

### **Training Process**
```python
# Step 1: Collect normal events
normal_events = collect_normal_events(days=7)

# Step 2: Train the model
detector = NetworkEventAnomalyDetector(model_type="fastflow")
detector.train_on_normal_events(normal_events)

# Step 3: Save the model
detector._save_model()

# Step 4: Load for production use
detector = NetworkEventAnomalyDetector(model_path="/path/to/model.pth")
detector._load_model()
```

## 🔍 **Feature Engineering**

### **Extracted Features**
The ML detector automatically extracts these features:

1. **Temporal Features**
   - Event timestamp
   - Time-based patterns
   - Frequency analysis

2. **Network Features**
   - Source IP address
   - Destination port
   - Protocol type
   - Connection duration

3. **Behavioral Features**
   - Username attempts
   - Password attempts
   - Error counts
   - Bytes transferred

4. **Contextual Features**
   - Event type
   - Source reputation
   - Destination service

### **Feature Normalization**
```python
# Features are automatically normalized to [0, 1] range
features = detector._extract_features(event_data)
normalized = detector._normalize_features(features)

# Create image-like tensors for Anomalib models
image_tensor = detector._create_feature_image(normalized)
```

## 🎯 **Anomaly Detection**

### **Scoring System**
- **0.0 - 0.3**: Normal behavior
- **0.3 - 0.6**: Suspicious activity
- **0.6 - 0.8**: High risk
- **0.8 - 1.0**: Critical threat

### **Detection Methods**
1. **ML-based Scoring**: Uses trained models for anomaly detection
2. **Behavioral Analysis**: Pattern recognition and frequency analysis
3. **Combined Scoring**: ML + Behavioral analysis (70% + 30%)

### **Example Usage**
```python
# Detect anomaly in real-time
event_data = {
    "logtype": 4002,
    "src_host": "192.168.1.100",
    "dst_port": 22,
    "logdata": {"USERNAME": "admin"}
}

score, analysis = detector.detect_anomaly(event_data)

if score > 0.6:
    print(f"🚨 HIGH RISK: Anomaly detected!")
    print(f"Score: {score:.3f}")
    print(f"Analysis: {analysis}")
    
    # Trigger alert
    trigger_alert(event_data, score, analysis)
```

## 📈 **Performance Optimization**

### **GPU Acceleration**
```python
# Enable CUDA if available
import torch
if torch.cuda.is_available():
    detector = NetworkEventAnomalyDetector(
        model_type="fastflow",
        config={"device": "cuda"}
    )
```

### **Memory Management**
```python
# Configure memory settings
config = {
    "ml_config": {
        "batch_size": 16,        # Reduce for low memory
        "max_history": 1000,     # Limit event history
        "cleanup_interval": 3600 # Cleanup every hour
    }
}
```

### **Performance Monitoring**
```python
# Monitor ML performance
import time

start_time = time.time()
score, analysis = detector.detect_anomaly(event_data)
inference_time = time.time() - start_time

print(f"Inference time: {inference_time:.3f}s")
print(f"Anomaly score: {score:.3f}")
```

## 🧪 **Testing and Validation**

### **Unit Testing**
```python
# Run ML integration tests
pytest netsentinel/tests/unit/test_ml_integration.py
pytest netsentinel/tests/unit/test_ml_anomaly_detector.py
```

### **Performance Testing**
```python
# Test with large datasets
def test_performance():
    detector = NetworkEventAnomalyDetector()
    
    # Create large training set
    normal_events = generate_test_events(1000)
    
    start_time = time.time()
    detector.train_on_normal_events(normal_events)
    training_time = time.time() - start_time
    
    assert training_time < 10.0  # Should complete within 10 seconds
    assert detector.is_trained == True
```

### **Accuracy Validation**
```python
# Validate model accuracy
def validate_accuracy():
    detector = NetworkEventAnomalyDetector()
    
    # Train on normal data
    normal_events = load_normal_events()
    detector.train_on_normal_events(normal_events)
    
    # Test on known anomalies
    anomaly_events = load_anomaly_events()
    correct_predictions = 0
    
    for event in anomaly_events:
        score, _ = detector.detect_anomaly(event)
        if score > 0.5:  # Threshold
            correct_predictions += 1
    
    accuracy = correct_predictions / len(anomaly_events)
    print(f"Accuracy: {accuracy:.3f}")
```

## 🔧 **Troubleshooting**

### **Common Issues**

#### **1. Model Training Fails**
```python
# Check data quality
if not normal_events:
    print("Error: No training data provided")
    
# Check feature extraction
features = detector._extract_features(normal_events[0])
if features is None:
    print("Error: Feature extraction failed")
```

#### **2. Low Accuracy**
```python
# Increase training data
normal_events = collect_more_data(days=14)

# Try different model type
detector = NetworkEventAnomalyDetector(model_type="efficient_ad")

# Adjust thresholds
config = {"ml_config": {"threshold": 0.3}}
```

#### **3. Performance Issues**
```python
# Reduce batch size
config = {"ml_config": {"batch_size": 8}}

# Use lighter model
detector = NetworkEventAnomalyDetector(model_type="padim")

# Enable cleanup
detector._cleanup()
```

### **Debug Mode**
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

detector = NetworkEventAnomalyDetector()
detector.train_on_normal_events(normal_events)
```

## 📚 **API Reference**

### **NetworkEventAnomalyDetector**

#### **Constructor**
```python
NetworkEventAnomalyDetector(
    model_type: str = "fastflow",
    model_path: Optional[str] = None,
    config: Dict[str, Any] = {}
)
```

#### **Methods**
```python
# Training
detector.train_on_normal_events(events: List[Dict]) -> None

# Detection
detector.detect_anomaly(event_data: Dict) -> Tuple[float, Dict]

# Analysis
detector.analyze_event(features: Dict) -> Dict

# Persistence
detector._save_model() -> None
detector._load_model() -> None

# Cleanup
detector._cleanup() -> None
```

### **EventAnalyzer Integration**
```python
# ML-enabled analysis
analyzer = EventAnalyzer(config={"ml_enabled": True})
ml_score, ml_analysis = analyzer._ml_analysis(event)
```

## 🚀 **Production Deployment**

### **Docker Configuration**
```dockerfile
# Dockerfile for ML-enabled NetSentinel
FROM python:3.9-slim

# Install ML dependencies
RUN pip install torch anomalib numpy scikit-learn

# Copy NetSentinel
COPY . /app
WORKDIR /app

# Run with ML enabled
ENV ML_ENABLED=true
ENV ML_MODEL_TYPE=fastflow
ENV ML_MODEL_PATH=/models/anomaly_detector.pth

CMD ["python", "-m", "netsentinel.core.engine"]
```

### **Kubernetes Configuration**
```yaml
# kubernetes/ml-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netsentinel-ml
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: netsentinel
        image: netsentinel:ml-latest
        env:
        - name: ML_ENABLED
          value: "true"
        - name: ML_MODEL_TYPE
          value: "fastflow"
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "1000m"
```

## 📊 **Monitoring and Metrics**

### **ML Metrics**
```python
# Track ML performance
ml_metrics = {
    "inference_time": inference_time,
    "anomaly_score": score,
    "confidence": analysis.get("confidence", 0.0),
    "model_accuracy": accuracy,
    "false_positive_rate": fpr,
    "false_negative_rate": fnr
}
```

### **Alerting**
```python
# ML-based alerting
if score > 0.8:
    send_critical_alert(event_data, score, analysis)
elif score > 0.6:
    send_high_risk_alert(event_data, score, analysis)
elif score > 0.4:
    send_suspicious_alert(event_data, score, analysis)
```

## 🎯 **Best Practices**

1. **Regular Model Retraining**: Retrain models weekly with new normal data
2. **Threshold Tuning**: Adjust thresholds based on false positive rates
3. **Feature Engineering**: Continuously improve feature extraction
4. **Performance Monitoring**: Monitor inference times and accuracy
5. **Data Quality**: Ensure training data represents current network behavior

## 📞 **Support**

For ML integration support:
- **Documentation**: See `docs/ml-setup-guide.md`
- **Tests**: Run `pytest netsentinel/tests/unit/test_ml_*.py`
- **Examples**: Check `scripts/train_ml_models.py`
- **Issues**: Report on GitHub issues

---

*Last Updated: December 19, 2024*
