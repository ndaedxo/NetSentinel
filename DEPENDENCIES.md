# NetSentinel Dependencies Guide

This document provides a comprehensive overview of all dependencies required for NetSentinel, organized by functionality and importance.

## Dependency Categories

### 1. Core Dependencies (Required)
These are essential for basic NetSentinel functionality:

```
Twisted>=24.11.0          # Core networking framework
zope.interface>=7.2       # Interface definitions
requests>=2.31.0          # HTTP client library
urllib3>=2.0.7            # HTTP utilities
simplejson>=3.16.0        # JSON processing
cryptography>=41.0.0      # Cryptographic functions
pyasn1>=0.4.5            # ASN.1 encoding/decoding
pyOpenSSL>=22.1.0         # SSL/TLS support
service-identity>=21.1.0  # SSL certificate validation
bcrypt>=4.0.0             # Password hashing
passlib>=1.7.1            # Password hashing utilities
Jinja2>=3.0.1             # Template engine
PyPDF2>=1.26.0            # PDF processing
fpdf>=1.7.2               # PDF generation
ntlmlib>=0.72             # NTLM authentication
hpfeeds>=3.0.0            # Honeypot feeds
flask>=2.3.0              # Web framework
kafka-python>=2.0.2       # Kafka client
redis>=4.6.0              # Redis client
scapy>=2.5.0              # Packet analysis
pcapy-ng>=1.0.0           # Packet capture
```

### 2. API Server Dependencies (Optional)
Required for REST API functionality:

```
fastapi>=0.100.0          # Modern web framework
uvicorn[standard]>=0.23.0  # ASGI server
pydantic>=2.0.0           # Data validation
```

### 3. Machine Learning Dependencies (Optional)
Required for ML-based anomaly detection:

```
torch>=2.0.0              # PyTorch framework
torchvision>=0.15.0       # Computer vision
torchaudio>=2.0.0         # Audio processing
lightning>=2.0.0          # PyTorch Lightning
anomalib>=1.1.0           # Anomaly detection library
numpy>=1.21.0             # Numerical computing
opencv-python>=4.5.0      # Computer vision
pillow>=10.0.0            # Image processing
scikit-learn>=1.0.0       # Machine learning
```

### 4. Enterprise Database Dependencies (Optional)
Required for enterprise database integration:

```
elasticsearch>=8.0.0      # Elasticsearch client
influxdb-client>=1.36.0   # InfluxDB client
```

### 5. Monitoring Dependencies (Optional)
Required for monitoring and observability:

```
prometheus-client>=0.17.0 # Prometheus metrics
psutil>=5.9.0             # System monitoring
```

### 6. Enhanced Networking Dependencies (Optional)
Required for advanced networking features:

```
aiohttp>=3.8.0            # Async HTTP client
asyncio-mqtt>=0.13.0      # MQTT client
```

### 7. Development Dependencies (Optional)
Required for development, testing, and CI/CD:

```
pytest>=7.4.0            # Testing framework
pytest-cov>=3.0.0         # Coverage testing
pytest-xdist>=2.5.0       # Parallel testing
pytest-mock>=3.11.0       # Mocking utilities
pytest-asyncio>=0.21.0    # Async testing
pytest-html>=3.1.0        # HTML test reports
pytest-playwright>=0.3.0  # Playwright testing
playwright>=1.30.0         # Browser automation
faker>=13.0.0             # Test data generation
factory-boy>=3.2.0        # Test factories
black>=22.0.0             # Code formatting
flake8>=4.0.0             # Linting
flake8-typing-imports>=1.12.0 # Type checking
isort>=5.10.0             # Import sorting
mypy>=0.950               # Static type checking
pylint>=2.12.0            # Code analysis
bandit>=1.7.0             # Security analysis
safety>=2.2.0             # Vulnerability scanning
coverage>=6.3.0           # Code coverage
coverage-badge>=1.1.0     # Coverage badges
sphinx>=4.5.0             # Documentation
sphinx-rtd-theme>=1.0.0   # Documentation theme
myst-parser>=0.17.0       # Markdown parser
pre-commit>=2.17.0        # Git hooks
tox>=3.24.0               # Testing environments
pip-tools>=6.6.0          # Dependency management
locust>=2.15.0,<2.30.0    # Load testing
docker>=5.0.0             # Docker client
docker-compose>=1.29.0    # Docker Compose
kubernetes>=21.7.0        # Kubernetes client
requests-mock>=1.9.0      # HTTP mocking
responses>=0.20.0          # HTTP mocking
httpx>=0.23.0             # HTTP client
testcontainers>=3.7.0     # Test containers
sqlmap>=1.6.0             # SQL injection testing
flask-testing>=0.8.1      # Flask testing
python-dotenv>=0.19.0     # Environment variables
typing-extensions>=4.0.0   # Type hints
structlog>=21.5.0         # Structured logging
freezegun>=1.1.0          # Time mocking
drf-spectacular>=0.24.0   # API documentation
openapi-spec-validator>=0.4.0 # OpenAPI validation
```

## Installation Commands

### Minimal Installation (Core Only)
```bash
pip install twisted zope.interface requests urllib3 simplejson cryptography pyasn1 pyOpenSSL service-identity bcrypt passlib Jinja2 PyPDF2 fpdf ntlmlib hpfeeds flask kafka-python redis scapy pcapy-ng
```

### Standard Installation (Core + API)
```bash
pip install -r requirements.txt
```

### Full Installation (All Features)
```bash
pip install -r requirements.txt
pip install torch torchvision anomalib scikit-learn elasticsearch influxdb-client prometheus-client psutil aiohttp asyncio-mqtt
```

### Development Installation
```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-xdist pytest-mock pytest-asyncio black flake8 isort mypy pylint bandit safety coverage sphinx pre-commit tox
```

## Platform-Specific Dependencies

### Windows
```bash
# Additional Windows dependencies
pip install pywin32 wmi
```

### Linux
```bash
# Additional Linux dependencies
pip install python-systemd
```

### macOS
```bash
# Additional macOS dependencies
pip install pyobjc
```

## Docker Dependencies

### Base Image
```dockerfile
FROM python:3.11-slim
```

### System Dependencies
```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcap-dev \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
```

## Version Compatibility

### Python Version Support
- **Python 3.8**: Full support
- **Python 3.9**: Full support
- **Python 3.10**: Full support
- **Python 3.11**: Full support (recommended)
- **Python 3.12**: Full support

### Operating System Support
- **Linux**: Full support (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- **Windows**: Full support (Windows 10+, Windows Server 2019+)
- **macOS**: Full support (macOS 10.15+)

## Dependency Conflicts

### Common Conflicts
1. **Twisted vs asyncio**: Use asyncio-compatible Twisted versions
2. **Scapy vs pcapy-ng**: Use pcapy-ng for better performance
3. **PyTorch vs TensorFlow**: Choose one ML framework
4. **Elasticsearch versions**: Use compatible client versions

### Resolution Strategies
1. **Pin versions**: Use exact version numbers
2. **Use virtual environments**: Isolate dependencies
3. **Update gradually**: Test compatibility
4. **Use dependency resolvers**: pip-tools, poetry

## Security Considerations

### Vulnerable Dependencies
Regularly check for vulnerabilities:
```bash
pip install safety
safety check
```

### Secure Installation
```bash
# Use trusted sources
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

# Verify checksums
pip install --require-hashes -r requirements.txt
```

## Troubleshooting

### Common Issues
1. **Import errors**: Check Python path and virtual environment
2. **Version conflicts**: Use dependency resolution tools
3. **Compilation errors**: Install build dependencies
4. **Permission errors**: Use virtual environments

### Debug Commands
```bash
# Check installed packages
pip list

# Check for conflicts
pip check

# Show dependency tree
pip show --verbose package-name

# Check for updates
pip list --outdated
```

## Maintenance

### Regular Updates
```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Update specific packages
pip install --upgrade package-name

# Check for security updates
safety check --json
```

### Dependency Pinning
```bash
# Generate requirements with exact versions
pip freeze > requirements-exact.txt

# Generate requirements with hashes
pip hash -r requirements.txt
```

This comprehensive dependency guide ensures that NetSentinel can be installed and configured correctly across different environments and use cases.
