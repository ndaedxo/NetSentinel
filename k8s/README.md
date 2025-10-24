# NetSentinel Kubernetes Deployment

This directory contains Kubernetes manifests for deploying NetSentinel in a production Kubernetes cluster.

## 🏗️ Architecture

The NetSentinel system consists of the following Kubernetes resources:

- **Namespace**: `netsentinel` - Isolated environment for all components
- **ConfigMaps**: Configuration for services
- **PersistentVolumeClaims**: Data persistence for databases and caches
- **Deployments**: Application deployments with health checks
- **Services**: Internal networking between components
- **Ingress**: External access to web interfaces
- **RBAC**: Permissions for Prometheus monitoring

## 📦 Components

### Core Services
- **ZooKeeper**: Kafka coordination service
- **Kafka**: Event streaming platform
- **NetSentinel Honeypot**: Multi-protocol honeypot sensors
- **Event Processor**: Real-time threat analysis engine

### Databases
- **Valkey**: High-performance caching layer
- **Elasticsearch**: Document storage and search
- **InfluxDB**: Time-series metrics storage

### Monitoring & Management
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Dashboards and visualization
- **Kafka UI**: Kafka topic management interface

## 🚀 Deployment Instructions

### Prerequisites

1. **Kubernetes Cluster**: Version 1.19+ with kubectl access
2. **Helm**: For potential future enhancements (optional)
3. **Storage**: Persistent volume support (recommended)
4. **Network**: Ingress controller (nginx, traefik, etc.)

### Step 1: Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### Step 2: Deploy Infrastructure

```bash
# ZooKeeper and Kafka
kubectl apply -f k8s/zookeeper.yaml
kubectl apply -f k8s/kafka.yaml

# Wait for Kafka to be ready
kubectl wait --for=condition=ready pod -l app=kafka -n netsentinel --timeout=300s
```

### Step 3: Deploy Databases

```bash
# Redis cache
kubectl apply -f k8s/redis.yaml

# Elasticsearch
kubectl apply -f k8s/elasticsearch.yaml

# InfluxDB
kubectl apply -f k8s/influxdb.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l component=database -n netsentinel --timeout=600s
```

### Step 4: Deploy NetSentinel Core

```bash
# Honeypot sensors
kubectl apply -f k8s/netsentinel.yaml

# Event processing engine
kubectl apply -f k8s/event-processor.yaml

# Wait for core services
kubectl wait --for=condition=ready pod -l component=honeypot -n netsentinel --timeout=300s
kubectl wait --for=condition=ready pod -l component=analytics -n netsentinel --timeout=300s
```

### Step 5: Deploy Monitoring

```bash
# Prometheus
kubectl apply -f k8s/prometheus.yaml

# Grafana
kubectl apply -f k8s/grafana.yaml

# Kafka UI
kubectl apply -f k8s/ingress.yaml
```

### Step 6: Deploy Ingress (Optional)

```bash
# Configure ingress for external access
kubectl apply -f k8s/ingress.yaml
```

## 🔍 Verification

### Check Pod Status

```bash
kubectl get pods -n netsentinel
kubectl get pvc -n netsentinel
kubectl get services -n netsentinel
```

### Check Service Health

```bash
# NetSentinel API
kubectl port-forward -n netsentinel svc/netsentinel-event-processor 8082:8082
curl http://localhost:8082/health

# Grafana
kubectl port-forward -n netsentinel svc/grafana 3000:3000
# Access at http://localhost:3000 (admin/hybrid-admin-2024)

# Prometheus
kubectl port-forward -n netsentinel svc/prometheus 9090:9090
# Access at http://localhost:9090
```

### Check Logs

```bash
# View NetSentinel logs
kubectl logs -n netsentinel -l app=netsentinel-honeypot -f

# View event processor logs
kubectl logs -n netsentinel -l app=netsentinel-event-processor -f
```

## ⚙️ Configuration

### Environment Variables

Key configuration options can be modified through environment variables in the deployment manifests:

- `FIREWALL_BLOCK_THRESHOLD`: Threat score threshold for IP blocking (default: 7.0)
- `ALERTING_ENABLED`: Enable/disable alerting system (default: true)
- `ENTERPRISE_DB_ENABLED`: Enable Elasticsearch/InfluxDB storage (default: true)
- `PACKET_ANALYSIS_ENABLED`: Enable network packet analysis (default: true)
- `THREAT_INTEL_ENABLED`: Enable threat intelligence feeds (default: true)

### Scaling

Adjust replica counts in deployment manifests:

```bash
# Scale event processor
kubectl scale deployment netsentinel-event-processor -n netsentinel --replicas=3

# Scale honeypot sensors
kubectl scale deployment netsentinel-honeypot -n netsentinel --replicas=5
```

### Resource Management

Modify resource requests/limits in deployment manifests:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

## 🔧 Maintenance

### Updates

```bash
# Update all components
kubectl apply -f k8s/

# Rolling restart
kubectl rollout restart deployment -n netsentinel
```

### Backup

```bash
# Backup persistent data
kubectl cp netsentinel/elasticsearch-XXXX:/usr/share/elasticsearch/data ./backup/elasticsearch
kubectl cp netsentinel/influxdb-XXXX:/var/lib/influxdb2 ./backup/influxdb
```

### Troubleshooting

```bash
# Check events
kubectl get events -n netsentinel --sort-by='.lastTimestamp'

# Debug pods
kubectl describe pod <pod-name> -n netsentinel

# Check resource usage
kubectl top pods -n netsentinel
```

## 🌐 External Access

### Ingress Configuration

Update `k8s/ingress.yaml` with your domain:

```yaml
spec:
  rules:
  - host: your-domain.com  # Change this
    http:
      paths:
      - path: /grafana
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3000
```

### Port Forwarding (Development)

```bash
# Grafana
kubectl port-forward -n netsentinel svc/grafana 3000:3000

# NetSentinel API
kubectl port-forward -n netsentinel svc/netsentinel-event-processor 8082:8082

# Prometheus
kubectl port-forward -n netsentinel svc/prometheus 9090:9090

# Kafka UI
kubectl port-forward -n netsentinel svc/kafka-ui 8080:8080
```

## 📊 Monitoring

### Health Checks

All deployments include readiness probes. Check health:

```bash
kubectl get pods -n netsentinel
# All pods should show 'Running' and 'Ready'
```

### Metrics

Access Prometheus metrics:
- **Prometheus**: http://your-domain.com/prometheus
- **Grafana**: http://your-domain.com/grafana
- **NetSentinel API**: http://your-domain.com/api

### Logging

Centralized logging can be implemented with:
- **Fluentd**: Log collection
- **Elasticsearch**: Log storage
- **Kibana**: Log visualization

## 🔒 Security Considerations

### Network Policies

Implement network policies for security:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: netsentinel-policy
  namespace: netsentinel
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### Secrets Management

Use Kubernetes secrets for sensitive data:

```bash
kubectl create secret generic netsentinel-secrets \
  --from-literal=redis-password=your-password \
  --from-literal=influxdb-token=your-token \
  -n netsentinel
```

### RBAC

The Prometheus service account has cluster-level permissions for monitoring. Restrict as needed for your environment.

## 🚀 Production Deployment

For production deployment:

1. **Use external databases** instead of in-cluster for scalability
2. **Implement backup strategies** for persistent data
3. **Configure TLS certificates** for ingress
4. **Set up monitoring alerts** for critical services
5. **Implement log aggregation** and analysis
6. **Configure resource limits** based on load testing

## 📞 Support

For deployment issues:
1. Check pod logs: `kubectl logs -n netsentinel <pod-name>`
2. Verify service networking: `kubectl get endpoints -n netsentinel`
3. Check resource usage: `kubectl describe nodes`

---

**Status**: ✅ **Kubernetes manifests ready for deployment**
