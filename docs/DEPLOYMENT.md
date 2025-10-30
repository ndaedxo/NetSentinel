# NetSentinel Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Deployment Options](#deployment-options)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Production Configuration](#production-configuration)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum Requirements**:
- CPU: 2 cores
- RAM: 4GB
- Storage: 50GB
- OS: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)

**Recommended for Production**:
- CPU: 4+ cores
- RAM: 16GB+
- Storage: 100GB+ SSD
- OS: Ubuntu 22.04 LTS or RHEL 9

### Required Software

**For Docker Deployment**:
- Docker Engine 20.10+
- Docker Compose 2.0+

**For Kubernetes Deployment**:
- Kubernetes 1.24+
- kubectl 1.24+
- Helm 3.0+

### Network Requirements

- **Ports to Open**:
  - 21 (FTP honeypot)
  - 22 (SSH honeypot)
  - 23 (Telnet honeypot)
  - 80 (HTTP honeypot)
  - 443 (HTTPS honeypot)
  - 3306/3307 (MySQL honeypot)
  - 8080 (Kafka UI)
  - 8081 (Redis Commander)
  - 8082 (API Server)
  - 3000 (Grafana)
  - 9090 (Prometheus)
  - 9200 (Elasticsearch)
  - 8086 (InfluxDB)

- **Firewall Access**:
  - Root/privileged access for iptables management
  - NET_ADMIN and NET_RAW capabilities for packet capture

---

## Deployment Options

### 1. Docker Compose (Recommended for Testing/Development)

Best for:
- Development environments
- Single-server deployments
- Quick deployments
- Testing and evaluation

### 2. Kubernetes (Recommended for Production)

Best for:
- Production environments
- High availability
- Scalability
- Multi-server deployments

### 3. Hybrid Deployment

Combine Docker Compose with Kubernetes for staged deployments.

---

## Docker Deployment

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/netsentinel.git
cd netsentinel

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f netsentinel

# Stop all services
docker-compose down
```

### Production Configuration

#### 1. Update Environment Variables

Create a `.env` file:

```bash
# Security
NETSENTINEL_API_KEY=your-secure-api-key-here
REDIS_PASSWORD=your-secure-redis-password

# SIEM Integration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SPLUNK_HEC_URL=https://your-splunk-instance:8088/services/collector
SPLUNK_HEC_TOKEN=your-splunk-hec-token
ELASTICSEARCH_URL=https://your-elasticsearch:9200

# SDN Integration
SDN_ENABLED=true
SDN_CONTROLLER_NAME=opendaylight
OPENDLIGHT_HOST=your-opendaylight-host
OPENDLIGHT_PORT=8181
OPENDLIGHT_USERNAME=admin
OPENDLIGHT_PASSWORD=admin

# Email Configuration
NETSENTINEL_SMTP_SERVER=smtp.gmail.com
NETSENTINEL_SMTP_PORT=587
NETSENTINEL_ALERT_FROM_EMAIL=alerts@yourcompany.com
```

#### 2. Configure Resource Limits

Update `docker-compose.yml`:

```yaml
services:
  netsentinel:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

#### 3. Enable Persistent Storage

Ensure volumes are configured:

```yaml
volumes:
  kafka-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/netsentinel/kafka-data
  redis-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/netsentinel/redis-data
  grafana-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/netsentinel/grafana-data
```

#### 4. Setup Auto-restart

```yaml
services:
  netsentinel:
    restart: unless-stopped
    restart_policy:
      condition: on-failure
      delay: 5s
      max_attempts: 3
      window: 120s
```

### Health Checks

```bash
# Check API health
curl http://localhost:8082/health

# Check event processor
curl http://localhost:8082/status

# Check metrics
curl http://localhost:8082/metrics
```

### Backup and Recovery

#### Backup Configuration
```bash
# Create backup script
cat > /opt/netsentinel/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/netsentinel/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup data volumes
docker run --rm -v netsentinel-kafka-data:/data -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/kafka-data-$DATE.tar.gz -C /data .

docker run --rm -v netsentinel-redis-data:/data -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/redis-data-$DATE.tar.gz -C /data .

docker run --rm -v netsentinel-grafana-data:/data -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/grafana-data-$DATE.tar.gz -C /data .

echo "Backup completed: $DATE"
EOF

chmod +x /opt/netsentinel/backup.sh
```

#### Restore from Backup
```bash
# Restore procedure
docker-compose down
docker volume rm netsentinel-kafka-data
docker run --rm -v $BACKUP_DIR:/backup -v netsentinel-kafka-data:/data \
  alpine tar xzf /backup/kafka-data-20240101_120000.tar.gz -C /data
docker-compose up -d
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Verify Kubernetes cluster
kubectl cluster-info

# Check available nodes
kubectl get nodes

# Verify Helm is installed
helm version
```

### Using Helm Charts

#### 1. Add Helm Repository
```bash
# Add NetSentinel Helm repository (if configured)
helm repo add netsentinel https://charts.netsentinel.io
helm repo update
```

#### 2. Create Namespace
```bash
kubectl create namespace netsentinel
```

#### 3. Install NetSentinel
```bash
# Install with default values
helm install netsentinel ./helm/netsentinel -n netsentinel

# Install with custom values
helm install netsentinel ./helm/netsentinel -n netsentinel \
  -f my-values.yaml
```

#### 4. Verify Installation
```bash
# Check pods
kubectl get pods -n netsentinel

# Check services
kubectl get svc -n netsentinel

# Check ingress
kubectl get ingress -n netsentinel
```

### Helm Values Configuration

Create `my-values.yaml`:

```yaml
# Replica counts
replicaCount: 3

# Resource limits
resources:
  limits:
    cpu: "2"
    memory: "4Gi"
  requests:
    cpu: "1"
    memory: "2Gi"

# Service configuration
service:
  type: LoadBalancer
  port: 8082

# Ingress configuration
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: netsentinel.yourcompany.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: netsentinel-tls
      hosts:
        - netsentinel.yourcompany.com

# Security
security:
  apiKey: "your-secure-api-key"

# SIEM Integration
siem:
  enabled: true
  slackWebhook: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  splunkHecUrl: "https://your-splunk-instance:8088/services/collector"
  splunkHecToken: "your-splunk-hec-token"

# SDN Integration
sdn:
  enabled: true
  controller: "opendaylight"

# Monitoring
monitoring:
  prometheus:
    enabled: true
    scrapeInterval: 30s
  grafana:
    enabled: true
```

### Persistent Storage

#### Create Storage Class
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: netsentinel-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  volumeBindingMode: WaitForFirstConsumer
```

#### Update Persistent Volumes
```yaml
# In values.yaml or ConfigMap
persistence:
  enabled: true
  storageClass: netsentinel-storage
  size: 100Gi
```

### High Availability

#### Pod Disruption Budget
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: netsentinel-pdb
  namespace: netsentinel
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: netsentinel
```

#### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: netsentinel-hpa
  namespace: netsentinel
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: netsentinel
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Production Configuration

### Security Settings

#### 1. Enable TLS/SSL

```yaml
# In docker-compose.yml or Kubernetes config
services:
  netsentinel-api:
    environment:
      - SSL_ENABLED=true
      - SSL_CERT_PATH=/etc/ssl/certs/netsentinel.crt
      - SSL_KEY_PATH=/etc/ssl/private/netsentinel.key
    volumes:
      - ./certs:/etc/ssl/certs:ro
      - ./private:/etc/ssl/private:ro
```

#### 2. Configure Authentication

```python
# config/security.py
SECURITY_CONFIG = {
    "jwt_secret": "your-secret-key",
    "jwt_algorithm": "HS256",
    "token_expiry": 3600,
    "api_keys_enabled": True,
    "rate_limiting": {
        "enabled": True,
        "requests_per_minute": 100
    }
}
```

#### 3. Network Segmentation

```bash
# Create isolated Docker network
docker network create --driver bridge --subnet=10.0.0.0/24 netsentinel-internal

# Update docker-compose.yml
networks:
  internal:
    external: true
    name: netsentinel-internal
```

### Performance Tuning

#### 1. Adjust Kafka Settings

```yaml
environment:
  KAFKA_HEAP_OPTS: "-Xmx2G -Xms2G"
  KAFKA_LOG_RETENTION_HOURS: 168
  KAFKA_LOG_SEGMENT_BYTES: 1073741824
```

#### 2. Optimize Redis

```yaml
command: >
  redis-server
  --maxmemory 2gb
  --maxmemory-policy allkeys-lru
  --appendonly yes
```

#### 3. Database Tuning

```yaml
# Elasticsearch
environment:
  - "ES_JAVA_OPTS=-Xms4g -Xmx4g"

# InfluxDB
environment:
  - INFLUXDB_DATA_CACHE_SNAPSHOT_MEMORY_SIZE=26214400
```

---

## Security Hardening

### Container Security

#### 1. Use Non-Root User
```dockerfile
# In Dockerfile
RUN useradd -r -s /bin/false netsentinel
USER netsentinel
```

#### 2. Implement Resource Limits
```yaml
# In docker-compose.yml or Kubernetes
resources:
  limits:
    cpus: '2'
    memory: 4G
    pids: 100
  reservations:
    cpus: '1'
    memory: 2G
```

#### 3. Enable Security Context
```yaml
# Kubernetes
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
    add:
    - NET_ADMIN
    - NET_RAW
```

### Network Security

#### 1. Implement Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: netsentinel-netpol
  namespace: netsentinel
spec:
  podSelector:
    matchLabels:
      app: netsentinel
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: allowed-namespace
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: allowed-namespace
```

#### 2. Configure Firewall Rules
```bash
# Allow only necessary ports
ufw allow 8082/tcp  # API
ufw allow 3000/tcp  # Grafana
ufw enable
```

### Secret Management

#### Using Kubernetes Secrets
```bash
# Create secrets
kubectl create secret generic netsentinel-secrets \
  --from-literal=api-key=your-api-key \
  --from-literal=redis-password=your-redis-password \
  -n netsentinel
```

#### Using External Secret Managers
```yaml
# Example with HashiCorp Vault
vault:
  enabled: true
  address: "https://vault.yourcompany.com:8200"
  secretPath: "secret/netsentinel"
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Automated health check script
#!/bin/bash
while true; do
    if ! curl -f http://localhost:8082/health > /dev/null 2>&1; then
        echo "Health check failed. Restarting..."
        docker-compose restart netsentinel
    fi
    sleep 60
done
```

### Log Management

#### Configure Log Rotation
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

#### Centralized Logging
```yaml
# Send logs to ELK Stack
logging:
  driver: "gelf"
  options:
    gelf-address: "udp://your-logstash-host:12201"
```

### Updates and Upgrades

```bash
# Update NetSentinel
cd netsentinel
git pull origin main
docker-compose build --no-cache
docker-compose up -d

# Rollback if needed
docker-compose down
docker-compose up -d --scale netsentinel=0
# Restore from backup and restart
```

---

## Troubleshooting

### Common Issues

#### 1. Container Won't Start
```bash
# Check logs
docker-compose logs netsentinel

# Check resources
docker stats

# Check ports
netstat -tulpn | grep 8082
```

#### 2. Kafka Connection Issues
```bash
# Test Kafka connection
docker exec netsentinel-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check Kafka logs
docker-compose logs kafka
```

#### 3. High Memory Usage
```bash
# Check memory usage
docker stats netsentinel

# Limit memory
# Update docker-compose.yml resources section
```

#### 4. API Not Responding
```bash
# Test API
curl http://localhost:8082/health

# Check if container is running
docker ps | grep netsentinel

# Restart API container
docker-compose restart netsentinel
```

### Getting Help

- **Documentation**: See `docs/` directory
- **Issues**: Open a GitHub issue
- **Logs**: Check `/var/log/netsentinel/`
- **Metrics**: View Grafana dashboards at http://localhost:3000

---

**Last Updated**: January 2024
**Version**: 1.0.0

