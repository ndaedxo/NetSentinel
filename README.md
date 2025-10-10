# OpenCanary Hybrid Detection & Mitigation System

A modern honeypot system with real-time threat detection and mitigation capabilities using Kafka, Valkey, Prometheus, and Grafana.

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### 2. Start the Hybrid System

```bash
# Clone and navigate to the project
cd opencanary

# Start all services (OpenCanary, Kafka, Valkey, Prometheus, Grafana, etc.)
docker-compose up -d

# View logs
docker-compose logs -f opencanary-honeypot
```

### 3. Access Your System

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana Dashboards** | http://localhost:3000 | Real-time monitoring & alerts |
| **Kafka UI** | http://localhost:8080 | Kafka topic management |
| **Redis Commander** | http://localhost:8081 | Valkey data management |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **Event Processor API** | http://localhost:8082 | Threat analysis API |

**Grafana Credentials:** `admin` / `hybrid-admin-2024`

## 🏗️ Architecture

### Core Components

```
OpenCanary → Kafka → Event Processor → Valkey
                    ↓
              Prometheus ← Grafana
```

- **OpenCanary** - Multi-protocol honeypot (FTP, SSH, Telnet, HTTP, HTTPS, MySQL)
- **Kafka** - Real-time event streaming platform
- **Event Processor** - Threat correlation and scoring engine
- **Valkey** - High-performance caching and data storage
- **Prometheus** - Metrics collection and alerting
- **Grafana** - Real-time dashboards and visualization

### Data Flow

1. **Detection**: OpenCanary captures suspicious network activity
2. **Streaming**: Events sent to Kafka in real-time
3. **Processing**: Event processor analyzes and scores threats
4. **Storage**: Threat data cached in Valkey for quick access
5. **Monitoring**: Metrics collected by Prometheus, visualized in Grafana

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
docker exec opencanary-kafka kafka-topics --list --bootstrap-server localhost:9092

# View events in Kafka
docker exec opencanary-kafka kafka-console-consumer --topic opencanary-events --bootstrap-server localhost:9092 --from-beginning --max-messages 5

# Check Valkey data
docker exec opencanary-valkey valkey-cli -a hybrid-detection-2024 keys "opencanary:*"

# Test threat analysis API
curl http://localhost:8082/threats
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

### Log Integration
Events are automatically sent to:
- **Kafka**: `opencanary-events` topic
- **Valkey**: `opencanary:event:*` keys
- **File**: `/var/log/opencanary/opencanary.log`

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
- Port scanning detection
- Service fingerprinting

### Real-Time Analysis
- Threat scoring algorithm
- Event correlation
- IP-based threat tracking
- Automated alert generation

### Data Protection
- Secure Valkey authentication
- Encrypted Kafka communication
- Container isolation
- Configurable access controls

## 📁 Project Structure

```
opencanary/
├── opencanary/                 # Core OpenCanary code
│   ├── logger.py               # Enhanced logging with Kafka/Valkey handlers
│   ├── event_processor.py      # Real-time threat analysis
│   └── modules/                # Honeypot service modules
├── hybrid-data/                # Configuration and data
│   └── opencanary/config/      # OpenCanary configuration
├── bin/                        # Executable scripts
├── Dockerfile                  # OpenCanary container
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

**OpenCanary not starting:**
```bash
# Check logs
docker-compose logs opencanary-honeypot

# Restart container
docker-compose restart opencanary
```

**No events in Kafka:**
```bash
# Verify Kafka is healthy
docker-compose ps kafka

# Check topic creation
docker exec opencanary-kafka kafka-topics --describe --topic opencanary-events --bootstrap-server localhost:9092
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