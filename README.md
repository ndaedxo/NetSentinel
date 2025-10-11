# NetSentinel Hybrid Detection & Mitigation System

A modern honeypot system with real-time threat detection and mitigation capabilities using Kafka, Valkey, Prometheus, and Grafana.

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### 2. Start the Hybrid System

```bash
# Clone and navigate to the project
cd netsentinel

# Start all services (NetSentinel, Kafka, Valkey, Prometheus, Grafana, etc.)
docker-compose up -d

# View logs
docker-compose logs -f netsentinel-honeypot
```

### 3. Access Your System

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana Dashboards** | http://localhost:3000 | Real-time monitoring & alerts |
| **Kafka UI** | http://localhost:8080 | Kafka topic management |
| **Redis Commander** | http://localhost:8081 | Valkey data management |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **NetSentinel API** | http://localhost:8082 | Threat analysis API |

**Grafana Credentials:** `admin` / `hybrid-admin-2024`

## 🏗️ Architecture

### Core Components

```
NetSentinel → Kafka → Enhanced Event Processor → Valkey
                    ↓           ↓
              Prometheus ← Grafana ← ML Models (Anomalib)
```

- **NetSentinel** - Multi-protocol honeypot (FTP, SSH, Telnet, HTTP, HTTPS, MySQL)
- **Kafka** - Real-time event streaming platform
- **Enhanced Event Processor** - Hybrid threat detection (rule-based + ML)
- **Anomalib ML Models** - FastFlow, EfficientAD, PaDiM for behavioral analysis
- **Valkey** - High-performance caching and data storage
- **Prometheus** - Metrics collection and alerting
- **Grafana** - Real-time dashboards and visualization

### Data Flow

1. **Detection**: NetSentinel captures suspicious network activity
2. **Packet Analysis**: Real-time network traffic monitoring and anomaly detection
3. **Streaming**: Events sent to Kafka in real-time (honeypot + packet anomalies)
4. **Hybrid Processing**:
   - Rule-based scoring (traditional threat detection)
   - ML-based anomaly detection (behavioral analysis)
   - Packet-level anomaly detection (network scanning, unusual traffic)
   - Threat intelligence enrichment (external feed correlation)
   - Combined hybrid threat scoring
5. **Automated Response**: High-threat IPs automatically blocked via firewall
6. **Enterprise Storage**: Events and metrics stored in Elasticsearch and InfluxDB for analytics
7. **Cache Layer**: Valkey provides high-speed caching for real-time operations
8. **Monitoring**: Metrics collected by Prometheus, visualized in Grafana

## 🔧 Development & Local Testing

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run OpenCanary Locally

```bash
# Run in development mode
./bin/opencanaryd --dev

# Or use Docker for isolated testing
docker-compose up -d opencanary
```

### Test Integration

```bash
# Check Kafka topics
docker exec netsentinel-kafka kafka-topics --list --bootstrap-server localhost:9092

# View events in Kafka
docker exec netsentinel-kafka kafka-console-consumer --topic netsentinel-events --bootstrap-server localhost:9092 --from-beginning --max-messages 5

# Check Valkey data
docker exec netsentinel-valkey valkey-cli -a hybrid-detection-2024 keys "netsentinel:*"

# Test threat analysis API
curl http://localhost:8082/threats

# Test ML model information
curl http://localhost:8082/ml/model-info

# Train ML model on recent events
curl -X POST http://localhost:8082/ml/train

# Test firewall integration
curl http://localhost:8082/firewall/status

# Manually block an IP
curl -X POST http://localhost:8082/firewall/block/192.168.1.100 \
  -H "Content-Type: application/json" \
  -d '{"reason": "manual_test"}'

# Check if IP is blocked
curl http://localhost:8082/firewall/check/192.168.1.100

# List all blocked IPs
curl http://localhost:8082/firewall/blocked

# Run firewall integration tests
python scripts/test_firewall.py

# Test packet analysis status
curl http://localhost:8082/packet/status

# Get packet-level anomalies
curl http://localhost:8082/packet/anomalies

# View active network flows
curl http://localhost:8082/packet/flows

# Start packet capture
curl -X POST http://localhost:8082/packet/start \
  -H "Content-Type: application/json" \
  -d '{"interface": "eth0"}'

# Stop packet capture
curl -X POST http://localhost:8082/packet/stop

# Run packet analysis integration tests
python scripts/test_packet_analysis.py

# Test threat intelligence status
curl http://localhost:8082/threat-intel/status

# Check if an IP is a known threat
curl http://localhost:8082/threat-intel/check/8.8.8.8

# Get threat indicators
curl "http://localhost:8082/threat-intel/indicators?type=ip&limit=10"

# View threat feeds status
curl http://localhost:8082/threat-intel/feeds

# Manually update threat feeds
curl -X POST http://localhost:8082/threat-intel/update

# Run threat intelligence integration tests
python scripts/test_threat_intelligence.py

# Test enterprise database status
curl http://localhost:8082/db/status

# Search security events
curl "http://localhost:8082/db/search/events?src_ip=192.168.1.100&size=10"

# Get recent events (last 24 hours)
curl http://localhost:8082/db/events/recent

# Get time-series metrics
curl "http://localhost:8082/db/metrics/opencanary_events?hours=24"

# Run enterprise database integration tests
python scripts/test_enterprise_database.py

# Test alerting system status
curl http://localhost:8082/alerts/status

# Get active alerts
curl "http://localhost:8082/alerts?limit=10&acknowledged=false"

# Get alerts by severity
curl "http://localhost:8082/alerts?severity=high"

# Generate a test alert
curl -X POST http://localhost:8082/alerts/test \
  -H "Content-Type: application/json" \
  -d '{"severity": "medium", "message": "Test alert from API"}'

# Acknowledge an alert
curl -X POST http://localhost:8082/alerts/1234567890_1234/acknowledge

# View alert rules
curl http://localhost:8082/alerts/rules

# Run alerting system integration tests
python scripts/test_alerting.py
```

## ⚙️ Configuration

### OpenCanary Services
Edit `hybrid-data/opencanary/config/opencanary.conf` to enable/disable services:

```json
{
  "ftp.enabled": true,
  "ssh.enabled": true,
  "http.enabled": true,
  "mysql.enabled": true,
  // ... other services
}
```

### Environment Variables
Key configuration via environment variables:

- `KAFKA_BOOTSTRAP_SERVERS` - Kafka connection
- `VALKEY_HOST`, `VALKEY_PORT`, `VALKEY_PASSWORD` - Valkey connection
- `PROMETHEUS_MULTIPROC_DIR` - Metrics directory

## 📊 Monitoring & Alerts

### Real-Time Dashboards
- **Grafana**: http://localhost:3000
  - Threat overview dashboard
  - Service status monitoring
  - Event correlation views

### Metrics & APIs
- **Prometheus**: http://localhost:9090
- **Event Processor API**:
  - `GET /health` - System health
  - `GET /metrics` - Prometheus metrics
  - `GET /threats` - Current threats
  - `GET /threats/{ip}` - Specific IP analysis
- `GET /firewall/status` - Firewall status and blocked IPs
- `POST /firewall/block/{ip}` - Manually block an IP
- `POST /firewall/unblock/{ip}` - Manually unblock an IP
- `GET /firewall/blocked` - List all blocked IPs
- `GET /firewall/check/{ip}` - Check if IP is blocked
- `GET /packet/status` - Packet analysis status and statistics
- `GET /packet/anomalies` - Recent packet-level anomalies
- `GET /packet/flows` - Active network flows
- `POST /packet/start` - Start packet capture
- `POST /packet/stop` - Stop packet capture
- `GET /threat-intel/status` - Threat intelligence status and statistics
- `GET /threat-intel/check/<indicator>` - Check if indicator is a threat
- `GET /threat-intel/indicators` - Get threat indicators with filtering
- `GET /threat-intel/feeds` - Get threat feed status
- `POST /threat-intel/feeds/<feed>/enable` - Enable/disable threat feeds
- `POST /threat-intel/update` - Manually update threat feeds
- `GET /db/status` - Enterprise database status and statistics
- `GET /db/search/events` - Search security events in Elasticsearch
- `GET /db/metrics/<measurement>` - Get time-series metrics from InfluxDB
- `GET /db/events/recent` - Get recent security events (24h)
- `GET /db/anomalies/recent` - Get recent anomaly detections (24h)
- `GET /alerts/status` - Alert system status and statistics
- `GET /alerts` - Get alerts with filtering options
- `POST /alerts/<id>/acknowledge` - Acknowledge an alert
- `POST /alerts/<id>/resolve` - Resolve an alert
- `GET /alerts/rules` - Get alert rules configuration
- `GET /alerts/templates` - Get alert templates
- `POST /alerts/test` - Generate a test alert

### Log Integration
Events are automatically sent to:
- **Kafka**: `netsentinel-events` topic
- **Valkey**: `threat:*` and `correlation:*` keys
- **File**: `/var/log/netsentinel/netsentinel.log`

## 🛠️ Management Commands

```bash
# System control
docker-compose up -d          # Start all services
docker-compose down           # Stop all services
docker-compose logs -f        # View logs
docker-compose restart        # Restart services

# Development
docker-compose build          # Rebuild containers
docker-compose up -d --build  # Build and start
docker-compose down -v        # Stop and remove volumes
```

## 🔐 Security Features

### Active Detection
- Multi-protocol honeypot simulation
- Credential harvesting
- Port scanning detection (honeypot + network-level)
- Service fingerprinting

### Real-Time Analysis
- Threat scoring algorithm
- Event correlation (honeypot + packet-level events)
- IP-based threat tracking
- Automated alert generation

### Packet-Level Monitoring
- **Real-time Network Traffic Analysis**: Capture and analyze all network packets
- **Flow Tracking**: Monitor network flows and connection patterns
- **Anomaly Detection**: Identify port scanning, unusual traffic patterns
- **Protocol Analysis**: Deep packet inspection for TCP, UDP, ICMP

### Threat Intelligence Integration
- **External Feed Processing**: Automatic updates from multiple threat intelligence sources
- **Indicator Enrichment**: IPs, domains, URLs checked against known threat databases
- **Confidence Scoring**: Threat scores adjusted based on intelligence confidence levels
- **Feed Management**: Enable/disable individual threat feeds and monitor feed health

### Enterprise Database Storage
- **Elasticsearch Integration**: Full-text search and analytics for security events
- **InfluxDB Time-Series**: High-performance metrics storage and querying
- **Long-term Retention**: Historical data storage beyond cache limits
- **Advanced Analytics**: Complex queries and aggregations for threat hunting
- **Scalable Architecture**: Distributed storage ready for high-volume deployments

### Comprehensive Alerting System
- **Multi-Channel Notifications**: Email, Slack, Teams, and webhook support
- **Intelligent Alert Routing**: Severity-based routing and escalation
- **Alert Deduplication**: Prevents alert fatigue with throttling
- **Interactive Management**: Acknowledge, resolve, and track alerts via API
- **Customizable Templates**: Flexible alert formatting and content

### Automated Response
- **Automatic IP Blocking**: High-threat IPs blocked via iptables/ufw/firewalld
- **Firewall Integration**: Native support for Linux firewalls
- **Threat Score Threshold**: Configurable blocking threshold (default: 7.0/10)
- **Manual Firewall Management**: API endpoints for manual block/unblock operations

### Data Protection
- Secure Valkey authentication
- Encrypted Kafka communication
- Container isolation
- Configurable access controls

## 📁 Project Structure

```
netsentinel/
├── opencanary/                 # Core NetSentinel code
│   ├── logger.py               # Enhanced logging with Kafka/Valkey handlers
│   ├── event_processor.py      # Real-time threat analysis
│   └── modules/                # Honeypot service modules
├── hybrid-data/                # Configuration and data
│   └── opencanary/config/      # NetSentinel configuration
├── bin/                        # Executable scripts
├── Dockerfile                  # NetSentinel container
├── Dockerfile.event-processor  # Event processor container
├── docker-compose.yml          # Hybrid system orchestration
└── requirements.txt            # Python dependencies
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test your changes with the Docker setup
4. Submit a pull request

## 📄 License

BSD License - see LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**NetSentinel not starting:**
```bash
# Check logs
docker-compose logs netsentinel-honeypot

# Restart container
docker-compose restart netsentinel
```

**No events in Kafka:**
```bash
# Verify Kafka is healthy
docker-compose ps kafka

# Check topic creation
docker exec netsentinel-kafka kafka-topics --describe --topic netsentinel-events --bootstrap-server localhost:9092
```

**Grafana not accessible:**
- Ensure port 3000 is available
- Check Grafana logs: `docker-compose logs grafana`

### Support

- **Documentation**: Check the `docs/` directory
- **Issues**: Open a GitHub issue
- **Community**: Join our discussions

---
**⚠️ Security Notice**: This is a research and detection tool. Use responsibly and only on networks you own or have permission to monitor.