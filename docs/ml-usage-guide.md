# NetSentinel ML Usage Guide

## 🧠 **Machine Learning Anomaly Detection Usage**

This guide provides practical examples and use cases for NetSentinel's ML-powered anomaly detection.

## 🚀 **Quick Examples**

### **Basic Anomaly Detection**
```python
from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector

# Initialize detector
detector = NetworkEventAnomalyDetector(model_type="fastflow")

# Train on normal traffic
normal_events = [
    {"logtype": 4002, "src_host": "192.168.1.10", "dst_port": 22, "logdata": {"USERNAME": "user1"}},
    {"logtype": 3000, "src_host": "192.168.1.11", "dst_port": 80, "logdata": {"PATH": "/index.html"}}
]

detector.train_on_normal_events(normal_events)

# Detect anomalies
suspicious_event = {
    "logtype": 4002,
    "src_host": "192.168.1.100",
    "dst_port": 22,
    "logdata": {"USERNAME": "admin", "PASSWORD": "password123"}
}

score, analysis = detector.detect_anomaly(suspicious_event)
print(f"Anomaly Score: {score:.3f}")
```

### **Real-time Monitoring**
```python
import time
from netsentinel.processors.event_analyzer import EventAnalyzer

# Configure ML-enabled analyzer
config = {
    "ml_enabled": True,
    "ml_model_type": "fastflow",
    "ml_config": {"threshold": 0.5}
}

analyzer = EventAnalyzer(config=config)

# Monitor events in real-time
def monitor_events():
    while True:
        event = get_next_event()  # Your event source
        
        # Analyze with ML
        ml_score, ml_analysis = analyzer._ml_analysis(event)
        
        if ml_score > 0.6:
            print(f"🚨 Anomaly detected: {ml_score:.3f}")
            trigger_alert(event, ml_score, ml_analysis)
        
        time.sleep(0.1)  # 10Hz monitoring
```

## 📊 **Use Cases**

### **1. SSH Brute Force Detection**
```python
def detect_ssh_brute_force():
    detector = NetworkEventAnomalyDetector()
    
    # Train on normal SSH traffic
    normal_ssh_events = [
        {"logtype": 4002, "src_host": "192.168.1.10", "dst_port": 22, "logdata": {"USERNAME": "user1"}},
        {"logtype": 4002, "src_host": "192.168.1.11", "dst_port": 22, "logdata": {"USERNAME": "user2"}}
    ]
    
    detector.train_on_normal_events(normal_ssh_events)
    
    # Detect brute force attempts
    brute_force_events = [
        {"logtype": 4002, "src_host": "192.168.1.100", "dst_port": 22, "logdata": {"USERNAME": "admin"}},
        {"logtype": 4002, "src_host": "192.168.1.100", "dst_port": 22, "logdata": {"USERNAME": "root"}},
        {"logtype": 4002, "src_host": "192.168.1.100", "dst_port": 22, "logdata": {"USERNAME": "administrator"}}
    ]
    
    for event in brute_force_events:
        score, analysis = detector.detect_anomaly(event)
        if score > 0.7:
            print(f"🚨 SSH Brute Force detected: {score:.3f}")
            block_ip(event["src_host"])
```

### **2. HTTP Anomaly Detection**
```python
def detect_http_anomalies():
    detector = NetworkEventAnomalyDetector(model_type="efficient_ad")
    
    # Train on normal HTTP traffic
    normal_http_events = [
        {"logtype": 3000, "src_host": "192.168.1.10", "dst_port": 80, "logdata": {"PATH": "/index.html"}},
        {"logtype": 3000, "src_host": "192.168.1.11", "dst_port": 80, "logdata": {"PATH": "/about.html"}}
    ]
    
    detector.train_on_normal_events(normal_http_events)
    
    # Detect suspicious HTTP requests
    suspicious_events = [
        {"logtype": 3000, "src_host": "192.168.1.100", "dst_port": 80, "logdata": {"PATH": "/admin.php"}},
        {"logtype": 3000, "src_host": "192.168.1.101", "dst_port": 80, "logdata": {"PATH": "/wp-admin/"}}
    ]
    
    for event in suspicious_events:
        score, analysis = detector.detect_anomaly(event)
        if score > 0.6:
            print(f"🚨 Suspicious HTTP request: {score:.3f}")
            log_suspicious_activity(event, score)
```

### **3. Network Scanning Detection**
```python
def detect_network_scanning():
    detector = NetworkEventAnomalyDetector()
    
    # Train on normal network behavior
    normal_events = [
        {"logtype": 4002, "src_host": "192.168.1.10", "dst_port": 22, "logdata": {"USERNAME": "user1"}},
        {"logtype": 3000, "src_host": "192.168.1.11", "dst_port": 80, "logdata": {"PATH": "/index.html"}}
    ]
    
    detector.train_on_normal_events(normal_events)
    
    # Detect scanning patterns
    scanning_events = [
        {"logtype": 4002, "src_host": "192.168.1.100", "dst_port": 22, "logdata": {"USERNAME": "admin"}},
        {"logtype": 4002, "src_host": "192.168.1.100", "dst_port": 23, "logdata": {"USERNAME": "admin"}},
        {"logtype": 4002, "src_host": "192.168.1.100", "dst_port": 21, "logdata": {"USERNAME": "admin"}}
    ]
    
    for event in scanning_events:
        score, analysis = detector.detect_anomaly(event)
        if score > 0.8:
            print(f"🚨 Network scanning detected: {score:.3f}")
            alert_security_team(event, score)
```

## 🔧 **Advanced Usage**

### **Custom Feature Engineering**
```python
def custom_feature_extraction(event_data):
    """Extract custom features for ML analysis"""
    features = {
        "timestamp": event_data.get("timestamp", time.time()),
        "event_type": event_data.get("logtype", 0),
        "source_ip": event_data.get("src_host", "unknown"),
        "destination_port": event_data.get("dst_port", 0),
        "protocol": determine_protocol(event_data.get("dst_port", 0)),
        "username_attempts": count_username_attempts(event_data),
        "password_attempts": count_password_attempts(event_data),
        "connection_duration": calculate_duration(event_data),
        "bytes_transferred": event_data.get("bytes", 0),
        "error_count": count_errors(event_data)
    }
    return features

def determine_protocol(port):
    """Determine protocol from port number"""
    if port == 22:
        return "SSH"
    elif port == 80 or port == 443:
        return "HTTP"
    elif port == 21:
        return "FTP"
    else:
        return "UNKNOWN"
```

### **Model Ensemble**
```python
def ensemble_anomaly_detection(event_data):
    """Use multiple models for better accuracy"""
    models = [
        NetworkEventAnomalyDetector(model_type="fastflow"),
        NetworkEventAnomalyDetector(model_type="efficient_ad"),
        NetworkEventAnomalyDetector(model_type="padim")
    ]
    
    # Train all models
    for model in models:
        model.train_on_normal_events(normal_events)
    
    # Get predictions from all models
    scores = []
    for model in models:
        score, _ = model.detect_anomaly(event_data)
        scores.append(score)
    
    # Ensemble prediction (average)
    ensemble_score = sum(scores) / len(scores)
    
    # Weighted ensemble (give more weight to better models)
    weights = [0.4, 0.4, 0.2]  # fastflow, efficient_ad, padim
    weighted_score = sum(s * w for s, w in zip(scores, weights))
    
    return weighted_score, {"individual_scores": scores}
```

### **Real-time Streaming**
```python
import asyncio
from kafka import KafkaConsumer

async def stream_anomaly_detection():
    """Real-time anomaly detection from Kafka stream"""
    detector = NetworkEventAnomalyDetector()
    
    # Train on historical data
    historical_events = load_historical_data(days=7)
    detector.train_on_normal_events(historical_events)
    
    # Set up Kafka consumer
    consumer = KafkaConsumer(
        'network_events',
        bootstrap_servers=['localhost:9092'],
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    # Process events in real-time
    for message in consumer:
        event_data = message.value
        
        # Detect anomalies
        score, analysis = detector.detect_anomaly(event_data)
        
        if score > 0.6:
            # Send to alert system
            await send_alert(event_data, score, analysis)
            
            # Update firewall rules
            if score > 0.8:
                await block_ip(event_data["src_host"])
        
        # Update model with new data
        if score < 0.3:  # Normal event
            detector.event_history.append(extract_features(event_data))
```

### **Batch Processing**
```python
def batch_anomaly_detection(events_batch):
    """Process multiple events in batch for efficiency"""
    detector = NetworkEventAnomalyDetector()
    
    # Train on normal data
    detector.train_on_normal_events(normal_events)
    
    # Process batch
    results = []
    for event in events_batch:
        score, analysis = detector.detect_anomaly(event)
        results.append({
            "event": event,
            "anomaly_score": score,
            "analysis": analysis,
            "timestamp": time.time()
        })
    
    # Filter anomalies
    anomalies = [r for r in results if r["anomaly_score"] > 0.5]
    
    # Generate report
    generate_anomaly_report(anomalies)
    
    return results
```

## 📈 **Performance Optimization**

### **Caching and Optimization**
```python
from functools import lru_cache
import pickle

class OptimizedMLDetector:
    def __init__(self, model_path):
        self.detector = NetworkEventAnomalyDetector(model_path=model_path)
        self.detector._load_model()
        
        # Cache for frequently accessed data
        self._cache = {}
    
    @lru_cache(maxsize=1000)
    def _cached_analysis(self, event_hash):
        """Cache analysis results for identical events"""
        return self.detector.detect_anomaly(self._cache[event_hash])
    
    def detect_anomaly_optimized(self, event_data):
        """Optimized anomaly detection with caching"""
        event_hash = hash(str(event_data))
        
        if event_hash not in self._cache:
            self._cache[event_hash] = event_data
        
        return self._cached_analysis(event_hash)
```

### **Parallel Processing**
```python
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

def parallel_anomaly_detection(events_list):
    """Process events in parallel for better performance"""
    detector = NetworkEventAnomalyDetector()
    detector.train_on_normal_events(normal_events)
    
    # Process in parallel
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(detector.detect_anomaly, event) for event in events_list]
        results = [future.result() for future in futures]
    
    return results
```

## 🔍 **Monitoring and Alerting**

### **Alert System Integration**
```python
def alert_system_integration():
    """Integrate with alert systems"""
    detector = NetworkEventAnomalyDetector()
    
    def on_anomaly_detected(event_data, score, analysis):
        """Handle anomaly detection"""
        if score > 0.8:
            # Critical alert
            send_slack_alert(f"🚨 CRITICAL: Anomaly detected - Score: {score:.3f}")
            send_email_alert("Critical anomaly detected", event_data)
            
        elif score > 0.6:
            # High risk alert
            send_slack_alert(f"⚠️ HIGH RISK: Anomaly detected - Score: {score:.3f}")
            
        elif score > 0.4:
            # Suspicious activity
            log_suspicious_activity(event_data, score)
    
    # Monitor events
    for event in event_stream:
        score, analysis = detector.detect_anomaly(event)
        if score > 0.4:
            on_anomaly_detected(event, score, analysis)
```

### **Metrics and Dashboard**
```python
def ml_metrics_dashboard():
    """Create ML metrics dashboard"""
    metrics = {
        "total_events_processed": 0,
        "anomalies_detected": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "average_inference_time": 0.0,
        "model_accuracy": 0.0
    }
    
    def update_metrics(event, score, analysis, inference_time):
        """Update metrics"""
        metrics["total_events_processed"] += 1
        metrics["average_inference_time"] = (
            (metrics["average_inference_time"] * (metrics["total_events_processed"] - 1) + inference_time) /
            metrics["total_events_processed"]
        )
        
        if score > 0.5:
            metrics["anomalies_detected"] += 1
    
    return metrics
```

## 🧪 **Testing and Validation**

### **Unit Testing**
```python
import pytest

def test_ml_detector_basic():
    """Test basic ML detector functionality"""
    detector = NetworkEventAnomalyDetector()
    
    # Test initialization
    assert detector.model_type == "fastflow"
    assert detector.is_trained == False
    
    # Test training
    normal_events = [
        {"logtype": 4002, "src_host": "192.168.1.10", "dst_port": 22, "logdata": {"USERNAME": "user1"}}
    ]
    
    detector.train_on_normal_events(normal_events)
    assert detector.is_trained == True
    
    # Test detection
    event_data = {
        "logtype": 4002,
        "src_host": "192.168.1.100",
        "dst_port": 22,
        "logdata": {"USERNAME": "admin"}
    }
    
    score, analysis = detector.detect_anomaly(event_data)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
```

### **Integration Testing**
```python
def test_ml_integration():
    """Test ML integration with EventAnalyzer"""
    config = {
        "ml_enabled": True,
        "ml_model_type": "fastflow"
    }
    
    analyzer = EventAnalyzer(config=config)
    
    # Test ML analysis
    event = create_event(
        event_type="4002",
        source="192.168.1.100",
        data={"logdata": {"USERNAME": "admin"}},
        severity="medium"
    )
    
    ml_score, ml_analysis = analyzer._ml_analysis(event)
    assert isinstance(ml_score, float)
    assert ml_score >= 0.0
```

## 📚 **API Examples**

### **REST API Integration**
```python
from flask import Flask, request, jsonify

app = Flask(__name__)
detector = NetworkEventAnomalyDetector()

@app.route('/analyze', methods=['POST'])
def analyze_event():
    """REST API endpoint for anomaly detection"""
    event_data = request.json
    
    try:
        score, analysis = detector.detect_anomaly(event_data)
        
        return jsonify({
            "anomaly_score": score,
            "is_anomaly": score > 0.5,
            "analysis": analysis,
            "timestamp": time.time()
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/train', methods=['POST'])
def train_model():
    """REST API endpoint for model training"""
    normal_events = request.json.get("events", [])
    
    try:
        detector.train_on_normal_events(normal_events)
        
        return jsonify({
            "status": "success",
            "message": "Model trained successfully",
            "is_trained": detector.is_trained
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### **GraphQL Integration**
```python
import graphene
from graphene import ObjectType, String, Float, Boolean

class AnomalyAnalysis(ObjectType):
    anomaly_score = Float()
    is_anomaly = Boolean()
    analysis = String()

class Query(ObjectType):
    analyze_event = graphene.Field(AnomalyAnalysis, event_data=graphene.String())
    
    def resolve_analyze_event(self, info, event_data):
        """GraphQL resolver for anomaly detection"""
        import json
        event = json.loads(event_data)
        score, analysis = detector.detect_anomaly(event)
        
        return AnomalyAnalysis(
            anomaly_score=score,
            is_anomaly=score > 0.5,
            analysis=str(analysis)
        )
```

## 🚀 **Production Deployment**

### **Docker Compose**
```yaml
# docker-compose.ml.yml
version: '3.8'
services:
  netsentinel-ml:
    build: .
    environment:
      - ML_ENABLED=true
      - ML_MODEL_TYPE=fastflow
      - ML_MODEL_PATH=/models/anomaly_detector.pth
    volumes:
      - ./models:/models
      - ./data:/data
    ports:
      - "8080:8080"
    depends_on:
      - kafka
      - redis
```

### **Kubernetes Deployment**
```yaml
# k8s/ml-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netsentinel-ml
spec:
  replicas: 3
  selector:
    matchLabels:
      app: netsentinel-ml
  template:
    metadata:
      labels:
        app: netsentinel-ml
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
        volumeMounts:
        - name: model-storage
          mountPath: /models
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: model-pvc
```

## 📊 **Monitoring and Observability**

### **Prometheus Metrics**
```python
from prometheus_client import Counter, Histogram, Gauge

# ML metrics
anomaly_detections = Counter('netsentinel_anomalies_detected_total', 'Total anomalies detected')
inference_duration = Histogram('netsentinel_inference_duration_seconds', 'Inference duration')
model_accuracy = Gauge('netsentinel_model_accuracy', 'Model accuracy')

def track_ml_metrics(score, inference_time, accuracy):
    """Track ML metrics for Prometheus"""
    if score > 0.5:
        anomaly_detections.inc()
    
    inference_duration.observe(inference_time)
    model_accuracy.set(accuracy)
```

### **Grafana Dashboard**
```json
{
  "dashboard": {
    "title": "NetSentinel ML Metrics",
    "panels": [
      {
        "title": "Anomaly Detection Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(netsentinel_anomalies_detected_total[5m])"
          }
        ]
      },
      {
        "title": "Inference Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, netsentinel_inference_duration_seconds)"
          }
        ]
      }
    ]
  }
}
```

## 🎯 **Best Practices**

1. **Model Management**
   - Regular retraining with new data
   - Version control for models
   - A/B testing for model updates

2. **Performance Optimization**
   - Batch processing for efficiency
   - Caching for repeated analysis
   - GPU acceleration when available

3. **Security**
   - Secure model storage
   - Access control for ML endpoints
   - Audit logging for ML decisions

4. **Monitoring**
   - Real-time performance metrics
   - Alert on model degradation
   - Regular accuracy validation

---

*Last Updated: December 19, 2024*
