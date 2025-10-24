# NetSentinel Helm Chart

A Helm chart for deploying NetSentinel Hybrid Detection & Mitigation System on Kubernetes.

## 🚀 Installation

### Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Persistent volume support (recommended)

### Add Repository (if applicable)

```bash
# Add NetSentinel Helm repository
helm repo add netsentinel https://charts.netsentinel.local
helm repo update
```

### Install Chart

```bash
# Install NetSentinel
helm install netsentinel ./helm/netsentinel

# Install with custom values
helm install netsentinel ./helm/netsentinel -f my-values.yaml

# Install in specific namespace
helm install netsentinel ./helm/netsentinel -n netsentinel --create-namespace
```

### Install with Custom Configuration

```bash
# Create custom values file
cat > my-values.yaml << EOF
netsentinel:
  config:
    ssh:
      port: 2222
    http:
      port: 8080

eventProcessor:
  env:
    firewallBlockThreshold: "8.0"

ingress:
  enabled: true
  hosts:
    - host: netsentinel.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
EOF

# Install with custom values
helm install netsentinel ./helm/netsentinel -f my-values.yaml
```

## 🔧 Configuration

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global Docker image registry | `""` |
| `global.imagePullSecrets` | Global Docker registry secret names | `[]` |

### NetSentinel Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `netsentinel.enabled` | Enable NetSentinel honeypot | `true` |
| `netsentinel.replicaCount` | Number of honeypot replicas | `1` |
| `netsentinel.config.*` | Honeypot configuration | See values.yaml |

### Event Processor Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `eventProcessor.enabled` | Enable event processor | `true` |
| `eventProcessor.replicaCount` | Number of event processor replicas | `1` |
| `eventProcessor.env.*` | Environment variables | See values.yaml |

### Database Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `elasticsearch.enabled` | Enable Elasticsearch | `true` |
| `influxdb.enabled` | Enable InfluxDB | `true` |
| `redis.enabled` | Enable Redis cache | `true` |

### Monitoring Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `prometheus.enabled` | Enable Prometheus | `true` |
| `grafana.enabled` | Enable Grafana | `true` |
| `grafana.adminPassword` | Grafana admin password | `"hybrid-admin-2024"` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `""` |
| `ingress.hosts` | Ingress hosts configuration | `[]` |

## 📊 Accessing NetSentinel

### Port Forwarding (Development)

```bash
# Grafana
kubectl port-forward -n netsentinel svc/netsentinel-grafana 3000:3000

# NetSentinel API
kubectl port-forward -n netsentinel svc/netsentinel-event-processor 8082:8082

# Prometheus
kubectl port-forward -n netsentinel svc/netsentinel-prometheus 9090:9090

# Kafka UI
kubectl port-forward -n netsentinel svc/netsentinel-kafka-ui 8080:8080
```

### With Ingress

If ingress is enabled, access NetSentinel at:
- **Grafana**: http://your-domain.com/grafana
- **NetSentinel API**: http://your-domain.com/api
- **Prometheus**: http://your-domain.com/prometheus

### Default Credentials

- **Grafana**: admin / hybrid-admin-2024
- **InfluxDB**: admin / netsentinel2024!
- **Valkey**: (no auth by default)

## 🔄 Upgrading

```bash
# Upgrade NetSentinel
helm upgrade netsentinel ./helm/netsentinel

# Upgrade with new values
helm upgrade netsentinel ./helm/netsentinel -f new-values.yaml
```

## 🗑️ Uninstalling

```bash
# Uninstall NetSentinel
helm uninstall netsentinel

# Clean up persistent volumes (CAUTION: This deletes data)
kubectl delete pvc -l app.kubernetes.io/instance=netsentinel
```

## 🔧 Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n netsentinel
kubectl get pvc -n netsentinel
```

### View Logs

```bash
# Honeypot logs
kubectl logs -n netsentinel -l app.kubernetes.io/name=netsentinel-honeypot -f

# Event processor logs
kubectl logs -n netsentinel -l app.kubernetes.io/name=netsentinel-event-processor -f
```

### Debug Issues

```bash
# Check events
kubectl get events -n netsentinel --sort-by='.lastTimestamp'

# Describe problematic pod
kubectl describe pod <pod-name> -n netsentinel
```

## 🏗️ Architecture

The Helm chart deploys:

### Core Components
- **NetSentinel Honeypot**: Multi-protocol sensors
- **Event Processor**: Real-time analysis engine
- **Kafka + ZooKeeper**: Event streaming
- **Valkey**: High-performance cache

### Databases
- **Elasticsearch**: Document storage and search
- **InfluxDB**: Time-series metrics

### Monitoring
- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and visualization
- **Kafka UI**: Management interface

### Security Features
- **Firewall Integration**: Automatic IP blocking
- **Packet Analysis**: Network traffic monitoring
- **Threat Intelligence**: External feed integration
- **Alerting System**: Multi-channel notifications

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale honeypot sensors
kubectl scale deployment netsentinel-netsentinel-honeypot -n netsentinel --replicas=3

# Scale event processors
kubectl scale deployment netsentinel-event-processor -n netsentinel --replicas=2
```

### Vertical Scaling

Update resource limits in values.yaml:

```yaml
netsentinel:
  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi
```

## 🔒 Security

### Network Policies

The chart includes basic network policies. For production:

```yaml
# Restrict pod-to-pod communication
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: netsentinel-restrict
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
  --from-literal=redis-password=your-secure-password \
  --from-literal=influxdb-token=your-secure-token \
  -n netsentinel
```

### TLS Configuration

Enable TLS for ingress:

```yaml
ingress:
  enabled: true
  tls:
    - secretName: netsentinel-tls
      hosts:
        - netsentinel.yourdomain.com
```

## 📋 Requirements

- **Kubernetes**: 1.19+
- **Helm**: 3.0+
- **Resources**: Minimum 4GB RAM, 2 CPU cores
- **Storage**: 50GB+ for databases and logs
- **Network**: Ingress controller for external access

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test with `helm template`
5. Submit a pull request

## 📄 License

This chart is licensed under the BSD License.

---

**Status**: ✅ **Helm chart ready for deployment**

For detailed documentation, visit: https://netsentinel.readthedocs.io/
