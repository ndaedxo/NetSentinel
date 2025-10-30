# NetSentinel Documentation Index

Welcome to the NetSentinel documentation! This guide helps you find the right documentation for your needs.

**Last Updated**: January 2024  
**Version**: 1.0.0

---

## 📚 Documentation Quick Start

### For End Users
- Start with: [Project Overview](project-overview.md)
- Then read: [Quick Start](#quick-start) in main README

### For Developers
- Start with: [Developer Guide](DEVELOPER_GUIDE.md)
- Then read: [API Documentation](API.md)

### For DevOps/Deployment
- Start with: [Deployment Guide](DEPLOYMENT.md)
- Then read: [Troubleshooting Guide](TROUBLESHOOTING.md)

---

## 📖 Core Documentation

### Getting Started
- **[README.md](../README.md)** - Project overview, quick start, and architecture
- **[SETUP_GUIDE.md](../SETUP_GUIDE.md)** - Installation and setup instructions
- **[project-overview.md](project-overview.md)** - Comprehensive project overview and design

### API & Integration
- **[API.md](API.md)** - Complete REST API reference with examples
- **[siem-integration.md](siem-integration.md)** - SIEM system integration guide
- **[sdn-integration.md](sdn-integration.md)** - SDN controller integration guide

### Deployment
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
  - Docker deployment
  - Kubernetes deployment
  - Production configuration
  - Security hardening

### Development
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Developer setup and workflows
- **[src-structure-guide.md](src-structure-guide.md)** - Source code structure
- **[directory-reorganization.md](directory-reorganization.md)** - Directory organization

### Machine Learning
- **[ml-setup-guide.md](ml-setup-guide.md)** - ML setup and configuration
- **[ml-usage-guide.md](ml-usage-guide.md)** - ML usage and best practices
- **[ai-features-overview.md](ai-features-overview.md)** - AI features overview

### Operations
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[implementation-status.md](implementation-status.md)** - Current implementation status
- **[migration-complete.md](migration-complete.md)** - Migration status

---

## 🎯 Documentation by Use Case

### I Want To...

#### ...Install NetSentinel
1. Read: [SETUP_GUIDE.md](../SETUP_GUIDE.md)
2. Follow: Quick Start in [README.md](../README.md)
3. Configure: Environment variables

#### ...Deploy to Production
1. Read: [DEPLOYMENT.md](DEPLOYMENT.md)
2. Choose: Docker or Kubernetes deployment
3. Configure: Security settings
4. Monitor: Using Grafana

#### ...Develop Features
1. Read: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
2. Setup: Development environment
3. Read: [API.md](API.md) for API details
4. Test: Using provided test suites

#### ...Integrate with SIEM
1. Read: [siem-integration.md](siem-integration.md)
2. Configure: SIEM connectors
3. Test: Integration endpoints
4. Monitor: Forwarded events

#### ...Configure SDN Integration
1. Read: [sdn-integration.md](sdn-integration.md)
2. Setup: SDN controller connection
3. Configure: Quarantine policies
4. Test: Traffic isolation

#### ...Use Machine Learning
1. Read: [ml-setup-guide.md](ml-setup-guide.md)
2. Configure: ML models
3. Train: Models on your data
4. Monitor: ML performance

#### ...Troubleshoot Issues
1. Read: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Run: Health check scripts
3. Check: Service logs
4. Review: Common solutions

---

## 🏗️ Architecture Documentation

### System Architecture
- [Project Overview](project-overview.md) - High-level architecture
- [README.md](../README.md) - Architecture section
- [src-structure-guide.md](src-structure-guide.md) - Code structure

### Component Documentation
- **Core Components**: See `src/netsentinel/core/` README
- **Event Processing**: See `src/netsentinel/processors/` README
- **Honeypot Services**: See `src/netsentinel/modules/` README

### Frontend Documentation
- [Frontend Implementation Status](../netsentinel-ui/IMPLEMENTATION_STATUS.md)
- [Frontend Design](../netsentinel-ui/design.md)

---

## 📊 API Documentation

### REST API
- **Base URL**: `http://localhost:8082`
- **Documentation**: [API.md](API.md)
- **Interactive Docs**: http://localhost:8082/docs (Swagger UI)
- **ReDoc**: http://localhost:8082/redoc

### API Endpoints Overview

#### Health & Status
- `GET /health` - Health check
- `GET /status` - System status
- `GET /metrics` - Prometheus metrics

#### Threat Intelligence
- `GET /threats` - Get all threats
- `GET /threats/{ip}` - Get threat by IP
- `GET /correlations/{ip}` - Get correlations

#### Firewall Management
- `GET /firewall/status` - Firewall status
- `POST /firewall/block/{ip}` - Block IP
- `POST /firewall/unblock/{ip}` - Unblock IP
- `GET /firewall/blocked` - List blocked IPs

#### Machine Learning
- `GET /ml/model-info` - ML model information
- `POST /ml/train` - Train models

#### Packet Analysis
- `GET /packet/status` - Packet analysis status
- `GET /packet/anomalies` - Get anomalies
- `GET /packet/flows` - Get active flows

#### Threat Intelligence Feeds
- `GET /threat-intel/status` - TI status
- `GET /threat-intel/check/{indicator}` - Check indicator
- `GET /threat-intel/indicators` - Get indicators

#### Enterprise Databases
- `GET /db/status` - Database status
- `GET /db/search/events` - Search events
- `GET /db/metrics/{measurement}` - Get metrics

#### Alerts
- `GET /alerts` - Get alerts
- `POST /alerts/{id}/acknowledge` - Acknowledge alert

#### SIEM Integration
- `GET /siem/status` - SIEM status
- `GET /siem/connectors` - Get connectors

#### SDN Integration
- `GET /sdn/status` - SDN status
- `POST /sdn/quarantine` - Quarantine IP
- `GET /sdn/flows` - Get flows

---

## 🔧 Configuration Documentation

### Configuration Files
- **Backend**: `src/data/settings.json`, environment variables
- **Frontend**: `netsentinel-ui/.env.local`
- **Docker**: `docker-compose.yml`

### Environment Variables
See [SETUP_GUIDE.md](../SETUP_GUIDE.md) and [DEPLOYMENT.md](DEPLOYMENT.md) for complete lists.

### Key Configuration Areas
- Authentication & Security
- Honeypot Services
- ML Models
- SIEM Connectors
- SDN Controllers
- Database Settings
- Monitoring & Alerting

---

## 🧪 Testing Documentation

### Backend Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=netsentinel --cov-report=html

# Run specific tests
pytest tests/test_event_analyzer.py
```

### Frontend Testing
```bash
cd netsentinel-ui

# Unit tests
npm test

# E2E tests
npm run test:e2e

# Coverage
npm run test:coverage
```

### Integration Testing
- See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for integration test setup
- Test scripts in `scripts/` directory

---

## 🚀 Deployment Documentation

### Deployment Options
- **Docker Compose**: See [DEPLOYMENT.md](DEPLOYMENT.md#docker-deployment)
- **Kubernetes**: See [DEPLOYMENT.md](DEPLOYMENT.md#kubernetes-deployment)
- **Helm Charts**: See `helm/netsentinel/` directory

### Production Hardening
- Security configuration
- Performance tuning
- Monitoring setup
- Backup & recovery

---

## 🐛 Troubleshooting

### Quick Links
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Complete troubleshooting guide
- [Common Issues](#common-issues) below

### Common Issues
1. Services won't start
2. No events being processed
3. High memory usage
4. API not responding
5. Kafka/Redis connection issues

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions.

---

## 📈 Additional Resources

### Service-Specific Documentation
- **Services**: `docs/services/` directory
  - `webserver.rst` - Web server honeypot
  - `mysql.rst` - MySQL honeypot
  - `mssql.rst` - MSSQL honeypot
  - `windows.rst` - Windows services

### Alert Configuration
- **Alerts**: `docs/alerts/` directory
  - `email.rst` - Email alerts
  - `hpfeeds.rst` - HPFeeds integration
  - `webhook.md` - Webhook notifications

### Starting Guides
- **Starting**: `docs/starting/` directory
  - `netsentinel.rst` - Starting NetSentinel
  - `configuration.rst` - Configuration guide
  - `correlator.rst` - Event correlation

---

## 🔍 Finding Information

### By Topic

**Architecture & Design**
- Project Overview
- Source Structure Guide
- Directory Reorganization

**Setup & Installation**
- Setup Guide
- Quick Start
- Configuration Guide

**Development**
- Developer Guide
- API Documentation
- Code Structure

**Operations**
- Deployment Guide
- Troubleshooting
- Monitoring

**Integration**
- SIEM Integration
- SDN Integration
- API Documentation

**Advanced Features**
- ML Setup Guide
- ML Usage Guide
- AI Features Overview

---

## 📝 Documentation Maintenance

### Contributing to Documentation

1. **Follow Standards**:
   - Use Markdown format (.md) for new docs
   - Maintain consistent structure
   - Include code examples
   - Keep it up-to-date

2. **Documentation Types**:
   - **Guides**: Step-by-step instructions
   - **References**: API specs, configurations
   - **Explanations**: Architecture, design decisions
   - **Troubleshooting**: Problem-solving guides

3. **Update Process**:
   - Update docs with code changes
   - Review periodically
   - Get feedback from users
   - Keep examples working

### Documentation Quality

✅ **Good Documentation**:
- Clear and concise
- Well-organized
- Includes examples
- Up-to-date
- User-tested

❌ **Poor Documentation**:
- Vague or unclear
- Disorganized
- Missing examples
- Outdated
- Untested examples

---

## 📞 Getting Help

### Documentation Resources
1. This index
2. Search in documentation
3. API interactive docs
4. Code comments

### Support Channels
1. **GitHub Issues**: Bug reports and feature requests
2. **GitHub Discussions**: Questions and discussions
3. **Documentation**: Search existing docs
4. **Community**: Join discussions

### When Asking for Help
- Describe your use case
- Include error messages
- Show configuration (sanitized)
- Provide logs
- Mention documentation you've read

---

## 📅 Documentation Updates

### Recent Updates
- January 2024: Major documentation overhaul
  - Created comprehensive API documentation
  - Added deployment guide
  - Created developer guide
  - Added troubleshooting guide
  - Separated implementation status

### Planned Updates
- Additional integration guides
- More code examples
- Video tutorials
- Architecture diagrams
- Best practices guide

---

## 🎓 Learning Path

### Beginner
1. Read [README.md](../README.md)
2. Complete [SETUP_GUIDE.md](../SETUP_GUIDE.md)
3. Explore [project-overview.md](project-overview.md)

### Intermediate
1. Read [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
2. Study [API.md](API.md)
3. Review [DEPLOYMENT.md](DEPLOYMENT.md)

### Advanced
1. Deep dive into [architecture documentation](#architecture-documentation)
2. Explore [integration guides](#integration)
3. Contribute to documentation

---

**Happy Reading! 📚**

For questions, suggestions, or improvements, please open an issue or discussion on GitHub.

**Last Updated**: January 2024  
**Version**: 1.0.0

