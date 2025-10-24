# NetSentinel Setup Guide

This guide covers the setup and installation of NetSentinel after the code cleanup and improvements.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git (for cloning the repository)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd NetSentinel
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies

#### Core Dependencies (Required)
```bash
pip install -r requirements.txt
```

#### Optional Dependencies (for specific features)

**For API Server (FastAPI):**
```bash
pip install fastapi uvicorn pydantic
```

**For Packet Analysis (Scapy):**
```bash
pip install scapy pcapy-ng
```

**For Machine Learning:**
```bash
pip install torch torchvision anomalib scikit-learn
```

**For Enterprise Features:**
```bash
pip install elasticsearch influxdb-client
```

**For Monitoring:**
```bash
pip install prometheus-client psutil
```

### 4. Configuration Setup

#### Create Configuration File

Copy the sample configuration:
```bash
cp src/netsentinel/data/settings.json netsentinel.conf
```

Or create your own configuration file. The system will look for configuration files in this order:
1. `/etc/netsentinel/netsentinel.conf`
2. `~/.netsentinel.conf`
3. `netsentinel.conf` (current directory)

#### Configuration Options

The configuration file supports the following main sections:

- **Device**: Basic device information
- **Services**: Honeypot services (SSH, HTTP, FTP, etc.)
- **Logging**: Logging configuration
- **Alerts**: Alert notification settings
- **Database**: Database configuration
- **Monitoring**: Metrics and health check settings
- **ML**: Machine learning settings
- **SDN**: Software-defined networking integration
- **SIEM**: Security information and event management
- **Threat Intelligence**: Threat feed configuration
- **Firewall**: Firewall integration
- **API**: REST API settings

### 5. Database Setup

#### SQLite (Default)
No additional setup required. The system will create the database automatically.

#### PostgreSQL (Optional)
```bash
pip install psycopg2-binary
```

#### MySQL (Optional)
```bash
pip install mysql-connector-python
```

### 6. Service Setup

#### Systemd Service (Linux)

Create a systemd service file:

```bash
sudo cp netsentinel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable netsentinel
sudo systemctl start netsentinel
```

#### Windows Service

Use the provided Windows service installer or run as a service using NSSM.

#### Docker (Recommended)

```bash
# Build the image
docker build -t netsentinel .

# Run with docker-compose
docker-compose up -d
```

## Testing

### Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_core_components.py -v
python -m pytest tests/test_cleanup_validation.py -v

# Run with coverage
python -m pytest tests/ --cov=netsentinel --cov-report=html
```

### Validate Installation

```bash
# Test core components
python -c "from netsentinel.core.base import BaseComponent; print('✅ Core components working')"

# Test configuration
python -c "from netsentinel.config import get_config; print('✅ Configuration working')"

# Test models
python -c "from netsentinel.core.models import create_event; print('✅ Models working')"
```

## Usage

### Basic Usage

```python
from netsentinel.core.base import BaseComponent
from netsentinel.core.models import create_event, create_alert
from netsentinel.config import get_config

# Get configuration
config = get_config()

# Create an event
event = create_event(
    event_type="ssh_login",
    source="192.168.1.100",
    data={"username": "admin", "password": "password123"},
    severity="medium"
)

# Create an alert
alert = create_alert(
    title="Suspicious SSH Login",
    description="Multiple failed login attempts detected",
    severity="high",
    source="netsentinel",
    event_data=event.data
)
```

### Advanced Usage

```python
from netsentinel.core.container import ServiceContainer
from netsentinel.core.error_handler import NetSentinelErrorHandler

# Create service container
container = ServiceContainer()

# Register services
container.register_singleton("error_handler", NetSentinelErrorHandler())

# Start all services
await container.start_all()

# Use services
error_handler = container.get("error_handler")
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Configuration Errors**: Check configuration file syntax
3. **Permission Errors**: Ensure proper file permissions
4. **Port Conflicts**: Check if required ports are available

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

```bash
# Check system health
curl http://localhost:8081/health

# Check metrics
curl http://localhost:9090/metrics
```

## Performance Tuning

### Memory Optimization

- Adjust `max_connections` in configuration
- Set appropriate `queue_size` for processors
- Configure `max_flows` for packet analysis

### CPU Optimization

- Set `max_workers` for parallel processing
- Configure `retry_attempts` for error handling
- Adjust `timeout` values

### Storage Optimization

- Configure database cleanup intervals
- Set appropriate log rotation
- Configure cache TTL values

## Security Considerations

1. **Network Security**: Use firewalls and VPNs
2. **Authentication**: Enable strong authentication
3. **Encryption**: Use TLS/SSL for communications
4. **Access Control**: Implement proper access controls
5. **Monitoring**: Enable comprehensive monitoring

## Support

For issues and questions:

1. Check the logs: `/var/log/netsentinel.log`
2. Review configuration: `netsentinel.conf`
3. Run diagnostics: `python -m netsentinel.diagnostics`
4. Check system resources: `python -m netsentinel.monitoring.health_checker`

## Changelog

### After Cleanup (Latest)
- ✅ Fixed 540+ code quality issues
- ✅ Improved error handling
- ✅ Enhanced logging
- ✅ Better type safety
- ✅ Cleaner imports
- ✅ Comprehensive testing
- ✅ Better documentation

### Key Improvements
- Lazy configuration loading
- Centralized error handling
- Improved component lifecycle
- Better resource management
- Enhanced monitoring
- Comprehensive testing suite
