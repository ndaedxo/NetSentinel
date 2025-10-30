# NetSentinel API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Models](#models)
5. [Examples](#examples)
6. [Error Handling](#error-handling)

---

## Overview

The NetSentinel API provides RESTful endpoints for managing and monitoring the security platform. The API is built on FastAPI and follows OpenAPI 3.0 specifications.

### Base URL
```
http://localhost:8082
```

### API Version
```
v1.0.0
```

### Content Type
All requests and responses use `application/json` unless otherwise specified.

### Interactive Documentation
- **Swagger UI**: http://localhost:8082/docs
- **ReDoc**: http://localhost:8082/redoc

---

## Authentication

Currently, NetSentinel uses basic authentication with API keys (planned). Include the API key in the header:

```http
Authorization: Bearer YOUR_API_KEY
```

Note: In development/demo mode, authentication may be disabled. Check your deployment configuration.

---

## Endpoints

### Health & Status

#### Health Check
```http
GET /health
```

Returns the health status of the API server and event processor.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": 1703123456.789,
  "uptime": 3600.5,
  "version": "1.0.0"
}
```

**Error Response** (503 Service Unavailable):
```json
{
  "detail": "Service unhealthy"
}
```

#### Get Status
```http
GET /status
```

Returns detailed system status including component health.

**Response** (200 OK):
```json
{
  "api_server": {
    "status": "healthy",
    "uptime": 3600.5,
    "host": "0.0.0.0",
    "port": 8082
  },
  "event_processor": {
    "status": "healthy",
    "metrics": {
      "events_processed": 12345,
      "threats_detected": 42
    }
  },
  "components": {
    "ml_detector": {"status": "healthy"},
    "firewall_manager": {"status": "healthy"}
  }
}
```

#### Get Metrics
```http
GET /metrics
```

Returns Prometheus-compatible metrics.

**Response** (200 OK):
```
text/plain

# NetSentinel API Server Metrics
netsentinel_api_uptime_seconds{service="api_server"} 3600.5
netsentinel_api_requests_total{service="api_server",endpoint="health"} 150
...
```

---

### Threat Intelligence

#### Get All Threats
```http
GET /threats?min_score=0.0&limit=100
```

Get threat intelligence data with optional filtering.

**Query Parameters**:
- `min_score` (float, optional): Minimum threat score to include (default: 0.0)
- `limit` (int, optional): Maximum number of threats to return (default: 100)

**Response** (200 OK):
```json
{
  "total_threats": 42,
  "threats": {
    "192.168.1.100": {
      "source_ip": "192.168.1.100",
      "threat_score": 8.5,
      "threat_level": "high",
      "event_count": 15,
      "last_seen": 1703123456.789,
      "indicators": ["port_scan", "brute_force", "suspicious_credentials"]
    },
    "10.0.0.50": {
      "source_ip": "10.0.0.50",
      "threat_score": 6.2,
      "threat_level": "medium",
      "event_count": 8,
      "last_seen": 1703123400.123,
      "indicators": ["unusual_traffic_pattern"]
    }
  }
}
```

**Error Response** (503 Service Unavailable):
```json
{
  "detail": "Event processor not available"
}
```

#### Get Threat by IP
```http
GET /threats/{ip_address}
```

Get detailed threat information for a specific IP address.

**Path Parameters**:
- `ip_address` (string, required): IP address to query

**Response** (200 OK):
```json
{
  "source_ip": "192.168.1.100",
  "threat_score": 8.5,
  "threat_level": "high",
  "event_count": 15,
  "last_seen": 1703123456.789,
  "indicators": ["port_scan", "brute_force", "suspicious_credentials"]
}
```

**Error Responses**:
- `404 Not Found`: No threat data found for the IP address
- `500 Internal Server Error`: Server error processing the request

#### Get Correlations by IP
```http
GET /correlations/{ip_address}?limit=10
```

Get correlation data for a specific IP address.

**Path Parameters**:
- `ip_address` (string, required): IP address to query

**Query Parameters**:
- `limit` (int, optional): Maximum number of correlations to return (default: 10)

**Response** (200 OK):
```json
{
  "ip_address": "192.168.1.100",
  "correlations": [
    {
      "correlation_score": 0.85,
      "pattern_detected": "port_scanning",
      "created_at": 1703123456.789,
      "expires_at": 1703130456.789,
      "event_count": 5,
      "events": [
        {"event_id": "evt_001", "timestamp": 1703123456.789},
        {"event_id": "evt_002", "timestamp": 1703123457.123}
      ]
    }
  ]
}
```

---

### Machine Learning

#### Get ML Model Information
```http
GET /ml/model-info
```

Get information about active ML models.

**Response** (200 OK):
```json
{
  "models": [
    {
      "name": "fastflow",
      "type": "fastflow",
      "is_trained": true,
      "accuracy": 0.92,
      "status": "active",
      "last_trained": "2024-01-01T12:00:00Z"
    },
    {
      "name": "efficientad",
      "type": "efficient_ad",
      "is_trained": true,
      "accuracy": 0.88,
      "status": "active",
      "last_trained": "2024-01-01T11:00:00Z"
    }
  ]
}
```

#### Train ML Model
```http
POST /ml/train
```

Trigger manual ML model training.

**Response** (200 OK):
```json
{
  "status": "training_started",
  "message": "Training job initiated",
  "job_id": "train_123456789"
}
```

---

### Firewall Management

#### Get Firewall Status
```http
GET /firewall/status
```

Get current firewall status and statistics.

**Response** (200 OK):
```json
{
  "status": "active",
  "provider": "iptables",
  "blocked_ips": 25,
  "total_blocks": 150,
  "auto_blocks": 125,
  "manual_blocks": 25
}
```

#### Check IP Block Status
```http
GET /firewall/check/{ip_address}
```

Check if an IP address is currently blocked.

**Path Parameters**:
- `ip_address` (string, required): IP address to check

**Response** (200 OK):
```json
{
  "ip_address": "192.168.1.100",
  "is_blocked": true,
  "blocked_at": "2024-01-01T12:00:00Z",
  "reason": "high_threat_score",
  "block_duration": 3600
}
```

#### Block IP Address
```http
POST /firewall/block/{ip_address}
```

Manually block an IP address.

**Path Parameters**:
- `ip_address` (string, required): IP address to block

**Request Body**:
```json
{
  "reason": "manual_block",
  "duration": 3600
}
```

**Response** (200 OK):
```json
{
  "status": "blocked",
  "ip_address": "192.168.1.100",
  "message": "IP address blocked successfully"
}
```

#### Unblock IP Address
```http
POST /firewall/unblock/{ip_address}
```

Manually unblock an IP address.

**Path Parameters**:
- `ip_address` (string, required): IP address to unblock

**Response** (200 OK):
```json
{
  "status": "unblocked",
  "ip_address": "192.168.1.100",
  "message": "IP address unblocked successfully"
}
```

#### List Blocked IPs
```http
GET /firewall/blocked
```

Get list of all currently blocked IP addresses.

**Response** (200 OK):
```json
{
  "blocked_ips": [
    {
      "ip_address": "192.168.1.100",
      "blocked_at": "2024-01-01T12:00:00Z",
      "reason": "high_threat_score",
      "block_duration": 3600
    },
    {
      "ip_address": "10.0.0.50",
      "blocked_at": "2024-01-01T11:30:00Z",
      "reason": "manual_block",
      "block_duration": 7200
    }
  ]
}
```

---

### Packet Analysis

#### Get Packet Analysis Status
```http
GET /packet/status
```

Get packet analysis status and statistics.

**Response** (200 OK):
```json
{
  "status": "active",
  "capture_enabled": true,
  "interface": "eth0",
  "packets_captured": 12345,
  "anomalies_detected": 8,
  "flows_tracked": 150
}
```

#### Get Packet Anomalies
```http
GET /packet/anomalies?limit=10
```

Get recent packet-level anomalies.

**Query Parameters**:
- `limit` (int, optional): Maximum number of anomalies to return (default: 10)

**Response** (200 OK):
```json
{
  "anomalies": [
    {
      "id": "anom_001",
      "type": "port_scan",
      "source_ip": "192.168.1.100",
      "score": 0.85,
      "detected_at": "2024-01-01T12:00:00Z",
      "description": "Port scanning detected on multiple ports"
    }
  ]
}
```

#### Get Active Flows
```http
GET /packet/flows
```

Get active network flows.

**Response** (200 OK):
```json
{
  "flows": [
    {
      "id": "flow_001",
      "source_ip": "192.168.1.100",
      "destination_ip": "192.168.1.50",
      "protocol": "TCP",
      "status": "active",
      "bytes": 1024,
      "packets": 10,
      "start_time": "2024-01-01T12:00:00Z"
    }
  ]
}
```

#### Start Packet Capture
```http
POST /packet/start
```

Start packet capture on a specified interface.

**Request Body**:
```json
{
  "interface": "eth0"
}
```

**Response** (200 OK):
```json
{
  "status": "started",
  "interface": "eth0",
  "message": "Packet capture started successfully"
}
```

#### Stop Packet Capture
```http
POST /packet/stop
```

Stop active packet capture.

**Response** (200 OK):
```json
{
  "status": "stopped",
  "message": "Packet capture stopped successfully"
}
```

---

### Threat Intelligence

#### Get Threat Intelligence Status
```http
GET /threat-intel/status
```

Get threat intelligence system status and statistics.

**Response** (200 OK):
```json
{
  "status": "active",
  "total_indicators": 10000,
  "feeds_configured": 5,
  "feeds_active": 4,
  "last_update": "2024-01-01T12:00:00Z"
}
```

#### Check Threat Indicator
```http
GET /threat-intel/check/{indicator}
```

Check if an indicator (IP, domain, URL, hash) is a known threat.

**Path Parameters**:
- `indicator` (string, required): Indicator to check

**Response** (200 OK):
```json
{
  "indicator": "192.168.1.100",
  "is_threat": true,
  "confidence": 0.85,
  "source": "MISP",
  "last_seen": "2024-01-01T12:00:00Z",
  "threat_types": ["malware", "C2_server"]
}
```

#### Get Threat Indicators
```http
GET /threat-intel/indicators?type=ip&limit=10
```

Get threat indicators with filtering.

**Query Parameters**:
- `type` (string, optional): Filter by indicator type (ip, domain, url, hash)
- `limit` (int, optional): Maximum number of indicators to return (default: 10)

**Response** (200 OK):
```json
{
  "indicators": [
    {
      "value": "192.168.1.100",
      "type": "ip",
      "threat_types": ["malware", "C2_server"],
      "confidence": 0.85,
      "source": "MISP",
      "first_seen": "2024-01-01T10:00:00Z",
      "last_seen": "2024-01-01T12:00:00Z"
    }
  ]
}
```

#### Get Threat Feeds Status
```http
GET /threat-intel/feeds
```

Get status of configured threat intelligence feeds.

**Response** (200 OK):
```json
{
  "feeds": [
    {
      "name": "misp_default",
      "type": "MISP",
      "status": "active",
      "last_update": "2024-01-01T12:00:00Z",
      "indicators_count": 5000
    },
    {
      "name": "alienvault_otx",
      "type": "OTX",
      "status": "active",
      "last_update": "2024-01-01T11:00:00Z",
      "indicators_count": 3000
    }
  ]
}
```

#### Update Threat Feeds
```http
POST /threat-intel/update
```

Manually update threat intelligence feeds.

**Response** (200 OK):
```json
{
  "status": "updating",
  "message": "Threat feeds update initiated",
  "feeds": ["misp_default", "alienvault_otx"]
}
```

---

### Enterprise Database

#### Get Database Status
```http
GET /db/status
```

Get enterprise database status and statistics.

**Response** (200 OK):
```json
{
  "elasticsearch": {
    "status": "connected",
    "indices": 5,
    "documents": 100000
  },
  "influxdb": {
    "status": "connected",
    "buckets": 3,
    "measurements": 10
  }
}
```

#### Search Events
```http
GET /db/search/events?src_ip=192.168.1.100&size=10
```

Search security events in Elasticsearch.

**Query Parameters**:
- `src_ip` (string, optional): Filter by source IP
- `dst_ip` (string, optional): Filter by destination IP
- `event_type` (string, optional): Filter by event type
- `severity` (string, optional): Filter by severity
- `size` (int, optional): Number of results to return (default: 10)
- `from` (int, optional): Offset for pagination (default: 0)

**Response** (200 OK):
```json
{
  "total": 150,
  "events": [
    {
      "id": "evt_001",
      "timestamp": "2024-01-01T12:00:00Z",
      "source_ip": "192.168.1.100",
      "event_type": "ssh_login",
      "severity": "medium"
    }
  ]
}
```

#### Get Recent Events
```http
GET /db/events/recent
```

Get recent security events (last 24 hours).

**Response** (200 OK):
```json
{
  "total": 150,
  "events": [
    {
      "id": "evt_001",
      "timestamp": "2024-01-01T12:00:00Z",
      "source_ip": "192.168.1.100",
      "event_type": "ssh_login",
      "severity": "medium"
    }
  ]
}
```

#### Get Time-Series Metrics
```http
GET /db/metrics/{measurement}?hours=24
```

Get time-series metrics from InfluxDB.

**Path Parameters**:
- `measurement` (string, required): Measurement name (e.g., `opencanary_events`)

**Query Parameters**:
- `hours` (int, optional): Time range in hours (default: 24)

**Response** (200 OK):
```json
{
  "measurement": "opencanary_events",
  "points": [
    {"time": "2024-01-01T12:00:00Z", "value": 100},
    {"time": "2024-01-01T12:05:00Z", "value": 150}
  ]
}
```

---

### Alerts

#### Get Alerts
```http
GET /alerts?limit=10&acknowledged=false&severity=high
```

Get alerts with filtering options.

**Query Parameters**:
- `limit` (int, optional): Maximum number of alerts to return (default: 10)
- `acknowledged` (boolean, optional): Filter by acknowledged status
- `severity` (string, optional): Filter by severity (low, medium, high, critical)
- `status` (string, optional): Filter by status (new, acknowledged, resolved)

**Response** (200 OK):
```json
{
  "alerts": [
    {
      "id": "alert_001",
      "title": "High threat detected",
      "severity": "high",
      "status": "new",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

#### Acknowledge Alert
```http
POST /alerts/{alert_id}/acknowledge
```

Acknowledge an alert.

**Path Parameters**:
- `alert_id` (string, required): Alert ID

**Response** (200 OK):
```json
{
  "status": "acknowledged",
  "alert_id": "alert_001",
  "acknowledged_at": "2024-01-01T12:05:00Z"
}
```

---

## Models

### ThreatLevel Enum
```typescript
enum ThreatLevel {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  CRITICAL = "critical"
}
```

### Event
```json
{
  "id": "string",
  "timestamp": "number",
  "event_type": "string",
  "source_ip": "string",
  "destination_ip": "string",
  "destination_port": "number",
  "protocol": "string",
  "data": {}
}
```

### Alert
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "severity": "ThreatLevel",
  "status": "string",
  "created_at": "number",
  "acknowledged_at": "number",
  "resolved_at": "number"
}
```

---

## Examples

### cURL Examples

#### Get All Threats
```bash
curl http://localhost:8082/threats
```

#### Block an IP Address
```bash
curl -X POST http://localhost:8082/firewall/block/192.168.1.100 \
  -H "Content-Type: application/json" \
  -d '{"reason": "high_threat_score", "duration": 3600}'
```

#### Check Health
```bash
curl http://localhost:8082/health
```

### Python Examples

#### Get Threats
```python
import requests

response = requests.get('http://localhost:8082/threats')
threats = response.json()
print(f"Found {threats['total_threats']} threats")
```

#### Block IP
```python
import requests

ip = "192.168.1.100"
response = requests.post(
    f'http://localhost:8082/firewall/block/{ip}',
    json={"reason": "manual_block", "duration": 3600}
)
print(response.json())
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- `200 OK` - Request succeeded
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service unavailable

### Common Errors

#### Rate Limiting
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

#### Validation Error
```json
{
  "detail": "Invalid IP address format"
}
```

#### Service Unavailable
```json
{
  "detail": "Event processor not available"
}
```

---

**Last Updated**: January 2024
**Version**: 1.0.0

