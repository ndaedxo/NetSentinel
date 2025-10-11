# SIEM Integration Guide

NetSentinel provides comprehensive SIEM (Security Information and Event Management) integration to forward security events to enterprise security platforms. This enables centralized security monitoring and correlation across your entire security infrastructure.

## 🎯 Supported SIEM Systems

NetSentinel supports integration with the following SIEM systems:

### Splunk
- **Method**: HTTP Event Collector (HEC)
- **Protocol**: REST API with authentication tokens
- **Features**: Batch processing, custom indexes, real-time ingestion

### ELK Stack
- **Method**: Elasticsearch API / Logstash HTTP Input
- **Protocol**: REST API with optional authentication
- **Features**: Direct indexing, full-text search, Kibana visualization

### Syslog
- **Method**: RFC 5424 compliant syslog
- **Protocol**: TCP/UDP transport
- **Features**: Standard security logging format, wide compatibility

### Generic Webhook
- **Method**: HTTP POST to custom endpoints
- **Protocol**: REST API with custom headers
- **Features**: Flexible integration with any webhook-compatible system

## 🔧 Configuration

### Environment Variables

Configure SIEM integration through environment variables:

```bash
# Enable SIEM integration
SIEM_ENABLED=true

# Splunk Configuration
SPLUNK_HEC_URL=https://splunk-server:8088/services/collector/event
SPLUNK_HEC_TOKEN=your-splunk-hec-token
SPLUNK_INDEX=netsentinel

# ELK Configuration
ELASTICSEARCH_URL=https://elasticsearch:9200
ELASTICSEARCH_API_KEY=your-api-key
# OR
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your-password

# Syslog Configuration
SYSLOG_HOST=192.168.1.10
SYSLOG_PORT=514
SYSLOG_PROTOCOL=udp

# Generic Webhook Configuration
SIEM_WEBHOOK_URL=https://siem-webhook.example.com/events
SIEM_WEBHOOK_TOKEN=your-webhook-token
```

### Docker Compose Configuration

Add the environment variables to your `docker-compose.yml`:

```yaml
event-processor:
  environment:
    - SIEM_ENABLED=true
    - SPLUNK_HEC_URL=${SPLUNK_HEC_URL}
    - SPLUNK_HEC_TOKEN=${SPLUNK_HEC_TOKEN}
    - ELASTICSEARCH_URL=http://elasticsearch:9200
    - SYSLOG_HOST=${SYSLOG_HOST}
    - SIEM_WEBHOOK_URL=${SIEM_WEBHOOK_URL}
```

## 📊 Event Forwarding

### Automatic Forwarding

NetSentinel automatically forwards high-threat events (threat score ≥ 6.0) to configured SIEM systems. Events include:

- **Security Events**: SSH brute force, port scans, suspicious login attempts
- **Network Anomalies**: Unusual traffic patterns, protocol violations
- **Threat Intelligence**: Correlated malicious indicators
- **System Alerts**: Configuration changes, system health issues

### Event Format

Events are formatted according to each SIEM system's requirements:

#### Splunk HEC Format
```json
{
  "time": 1640995200.123,
  "host": "netsentinel-cluster",
  "source": "netsentinel",
  "sourcetype": "netsentinel:4002",
  "event": {
    "message": "SSH login attempt from 192.168.1.100",
    "severity": "high",
    "event_type": "4002",
    "source_ip": "192.168.1.100",
    "threat_score": 8.5,
    "tags": ["honeypot", "ssh"]
  }
}
```

#### Syslog Format (RFC 5424)
```
<165>1 2024-01-01T12:00:00.123Z netsentinel netsentinel 4002 - [netsentinel@12345 event_type="4002" severity="high"] SSH login attempt from 192.168.1.100
```

#### ELK Format
```json
{
  "@timestamp": "2024-01-01T12:00:00.123Z",
  "host": "netsentinel-cluster",
  "source": "netsentinel",
  "event_type": "4002",
  "severity": "high",
  "message": "SSH login attempt from 192.168.1.100",
  "source_ip": "192.168.1.100",
  "threat_score": 8.5,
  "tags": ["honeypot", "ssh"]
}
```

## 🔍 Event Filtering

Control which events are forwarded using filtering rules:

### Default Filters

NetSentinel applies default filters to prevent SIEM flooding:

- **Event Types**: SSH (4002), FTP (4000), HTTP anomalies
- **Severities**: High and Critical only
- **Threat Score**: Minimum 6.0

### Custom Filters

Configure custom filtering via API:

```bash
# Set filtering rules for Splunk
curl -X POST http://localhost:8082/siem/filters/splunk_default \
  -H "Content-Type: application/json" \
  -d '{
    "event_types": ["4002", "4000", "9999"],
    "severities": ["critical"],
    "min_score": 8.0
  }'
```

### Filter Parameters

- **event_types**: Array of logtype codes to include
- **severities**: Array of severity levels (low, medium, high, critical)
- **min_score**: Minimum threat score threshold

## 🚀 API Endpoints

### Status and Monitoring

```bash
# Get SIEM integration status
GET /siem/status

# Get available connectors
GET /siem/connectors
```

### Connector Management

```bash
# Enable/disable connectors
POST /siem/connectors/{connector_name}/enable
{
  "enable": true
}

# Set filtering rules
POST /siem/filters/{connector_name}
{
  "event_types": ["4002", "4000"],
  "severities": ["high", "critical"],
  "min_score": 7.0
}
```

### Testing

```bash
# Send test event
POST /siem/test
{
  "severity": "high",
  "threat_score": 8.5
}
```

## 📈 Monitoring and Statistics

Monitor SIEM integration health:

```bash
curl http://localhost:8082/siem/status
```

Response:
```json
{
  "siem_enabled": true,
  "statistics": {
    "events_sent": 1250,
    "events_failed": 5,
    "connectors_active": 2,
    "last_event_time": 1640995200.123
  }
}
```

## 🛠️ Troubleshooting

### Common Issues

#### Splunk Connection Issues

```bash
# Check Splunk HEC endpoint
curl -k https://your-splunk:8088/services/collector/health

# Verify token permissions
curl -H "Authorization: Splunk YOUR_TOKEN" \
     https://your-splunk:8088/services/collector/event \
     -d '{"event": "test"}'
```

#### Elasticsearch Authentication

```bash
# Test Elasticsearch connection
curl -u elastic:password https://elasticsearch:9200/_cluster/health

# Verify API key
curl -H "Authorization: ApiKey YOUR_API_KEY" \
     https://elasticsearch:9200/_cluster/health
```

#### Syslog Connectivity

```bash
# Test syslog connection
echo "<165>1 $(date +%Y-%m-%dT%H:%M:%S) test-host test-app 123 - - Test message" | nc -u syslog-server 514

# Check firewall rules
sudo iptables -L | grep 514
```

### Log Analysis

Check NetSentinel logs for SIEM-related messages:

```bash
# View event processor logs
docker-compose logs -f event-processor | grep -i siem

# Check for forwarding errors
docker-compose logs event-processor | grep "Failed to forward"
```

## 🔒 Security Considerations

### Authentication
- Use HTTPS for all SIEM communications
- Implement proper authentication (tokens, API keys)
- Rotate credentials regularly

### Network Security
- Restrict SIEM traffic to authorized networks
- Use VPNs or private networks for sensitive environments
- Implement TLS certificate validation

### Event Filtering
- Configure appropriate filtering to prevent log flooding
- Monitor event volumes and adjust thresholds as needed
- Implement rate limiting for webhook endpoints

## 📊 Performance Optimization

### Batch Processing
- Splunk HEC supports batch event submission
- Configure batch sizes based on your throughput requirements
- Monitor queue depths and adjust flush intervals

### Connection Pooling
- Reuse HTTP connections for better performance
- Implement connection timeouts and retries
- Monitor connection health and implement failover

### Resource Management
- Allocate sufficient CPU/memory for event processing
- Monitor queue sizes and implement backpressure
- Scale event processor pods based on load

## 🔄 Integration Examples

### Splunk Setup

1. **Configure HEC**:
   ```
   Settings > Data Inputs > HTTP Event Collector
   Name: NetSentinel
   Token: (generate new token)
   Index: netsentinel
   ```

2. **Environment Variables**:
   ```bash
   SPLUNK_HEC_URL=https://splunk.company.com:8088/services/collector/event
   SPLUNK_HEC_TOKEN=your-token-here
   ```

### ELK Stack Setup

1. **Configure Elasticsearch Index**:
   ```bash
   curl -X PUT "elasticsearch:9200/netsentinel" \
        -H 'Content-Type: application/json' \
        -d'{"mappings":{"properties":{"@timestamp":{"type":"date"}}}}'
   ```

2. **Environment Variables**:
   ```bash
   ELASTICSEARCH_URL=https://elasticsearch.company.com:9200
   ELASTICSEARCH_USERNAME=elastic
   ELASTICSEARCH_PASSWORD=your-password
   ```

### Syslog Setup

1. **Configure rsyslog**:
   ```
   # Add to /etc/rsyslog.conf
   $ModLoad imtcp
   $InputTCPServerRun 514
   ```

2. **Environment Variables**:
   ```bash
   SYSLOG_HOST=192.168.1.10
   SYSLOG_PORT=514
   SYSLOG_PROTOCOL=tcp
   ```

## 📈 Best Practices

### Event Correlation
- Use consistent event naming conventions
- Include contextual information in events
- Implement proper timestamp handling

### Monitoring
- Monitor SIEM pipeline health
- Set up alerts for integration failures
- Track event delivery success rates

### Maintenance
- Regularly review and update filtering rules
- Monitor SIEM system capacity and performance
- Keep integration configurations documented

---

**Integration Status**: ✅ **SIEM integration fully implemented**

For additional support, check the NetSentinel logs or contact your security operations team.
