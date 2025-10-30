# NetSentinel Developer Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Contributing](#contributing)
6. [Code Standards](#code-standards)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

**System Requirements**:
- Python 3.11+ (backend)
- Node.js 18+ (frontend)
- Docker & Docker Compose
- Git

**Development Tools**:
- VS Code (recommended) or your preferred IDE
- Python Virtual Environment
- npm/yarn for frontend dependencies

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/your-org/netsentinel.git
cd netsentinel

# Setup backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup frontend
cd netsentinel-ui
npm install

# Start development environment
cd ..
docker-compose up -d
```

---

## Development Environment

### Backend Development

#### Environment Variables

Create a `.env` file in the root directory:

```bash
# Kafka Configuration
NETSENTINEL_KAFKA_SERVERS=localhost:9092
NETSENTINEL_KAFKA_TOPIC=netsentinel-events

# Redis Configuration
NETSENTINEL_REDIS_HOST=localhost
NETSENTINEL_REDIS_PORT=6379
NETSENTINEL_REDIS_PASSWORD=hybrid-detection-2024

# ML Configuration
NETSENTINEL_ML_ENABLED=true
NETSENTINEL_ML_MODEL_TYPE=fastflow

# API Configuration
NETSENTINEL_API_HOST=0.0.0.0
NETSENTINEL_API_PORT=8082

# Logging
NETSENTINEL_LOG_LEVEL=DEBUG
```

#### Running the Backend

```bash
# Activate virtual environment
source venv/bin/activate

# Run event processor
python -m netsentinel.processors.refactored_event_processor

# Run API server
python -m netsentinel.processors.api_server

# Run with debug logging
NETSENTINEL_LOG_LEVEL=DEBUG python -m netsentinel.processors.refactored_event_processor
```

#### Hot Reload

```bash
# Use watchfiles for auto-reload
pip install watchfiles
watchfiles --python netsentinel.processors.refactored_event_processor
```

### Frontend Development

#### Development Server

```bash
cd netsentinel-ui

# Start development server
npm run dev

# Server will start on http://localhost:5173
```

#### Environment Configuration

Create `netsentinel-ui/.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:8082
VITE_WS_URL=ws://localhost:8082
VITE_OAUTH_CLIENT_ID=your-client-id
VITE_OAUTH_CLIENT_SECRET=your-client-secret
```

#### Hot Reload

The Vite dev server automatically reloads on file changes.

---

## Project Structure

### Backend Structure

```
src/netsentinel/
├── __init__.py
├── config.py                          # Configuration management
├── core/                              # Core architecture
│   ├── base.py                        # BaseComponent, BaseProcessor
│   ├── models.py                      # Data models
│   ├── error_handler.py               # Error handling
│   ├── event_sourcing.py              # Event sourcing patterns
│   └── ...
├── processors/                        # Event processing
│   ├── event_analyzer.py              # Threat analysis
│   ├── event_consumer.py              # Kafka consumer
│   ├── refactored_event_processor.py  # Main processor
│   └── api_server.py                  # REST API
├── modules/                           # Honeypot services
│   ├── ssh.py
│   ├── ftp.py
│   ├── http.py
│   └── ...
├── ml_anomaly_detector.py            # ML-based detection
├── packet_analyzer.py                # Packet-level analysis
├── firewall_manager.py               # Firewall integration
├── threat_intelligence.py            # Threat intel feeds
├── siem_integration.py               # SIEM connectors
├── sdn_integration.py                # SDN integration
├── alerts/                           # Alerting system
├── monitoring/                       # Monitoring & metrics
└── utils/                            # Utilities
```

### Frontend Structure

```
netsentinel-ui/
├── src/
│   ├── components/            # Reusable UI components
│   │   ├── Header.tsx
│   │   ├── SidebarNav.tsx
│   │   ├── StatCard.tsx
│   │   ├── ThreatTable.tsx
│   │   └── ...
│   ├── pages/                 # Page components
│   │   ├── Dashboard.tsx
│   │   ├── Login.tsx
│   │   ├── ThreatIntelligence.tsx
│   │   └── ...
│   ├── services/              # API services
│   │   ├── auth-service.ts
│   │   ├── threats-service.ts
│   │   └── ...
│   ├── hooks/                 # Custom React hooks
│   │   ├── useApi-hook.ts
│   │   ├── useToast.tsx
│   │   └── ...
│   ├── mock/                  # Mock data
│   ├── types/                 # TypeScript types
│   ├── utils/                 # Utility functions
│   ├── App.tsx                # Main app component
│   └── main.tsx               # Entry point
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

### Key Files

**Backend**:
- `pyproject.toml` - Python project configuration
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Docker orchestration
- `.env` - Environment variables

**Frontend**:
- `package.json` - Node.js dependencies
- `vite.config.ts` - Vite configuration
- `.env.local` - Frontend environment variables
- `tsconfig.json` - TypeScript configuration

---

## Development Workflow

### Git Workflow

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
git add .
git commit -m "feat: Add feature description"

# Push to remote
git push origin feature/your-feature-name

# Create pull request on GitHub
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: Add new feature
fix: Bug fix
docs: Documentation changes
style: Code style changes
refactor: Code refactoring
test: Add or update tests
chore: Build process or auxiliary tool changes
```

### Code Review Process

1. Create feature branch
2. Make changes with tests
3. Ensure all tests pass
4. Update documentation if needed
5. Create pull request
6. Address review feedback
7. Merge to main

---

## Contributing

### Setting Up for Contribution

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR-USERNAME/netsentinel.git
cd netsentinel

# Add upstream remote
git remote add upstream https://github.com/original-org/netsentinel.git

# Keep your fork updated
git fetch upstream
git merge upstream/main
```

### Contribution Guidelines

1. **Code Quality**: Follow code standards and style guides
2. **Tests**: Add tests for new features and bug fixes
3. **Documentation**: Update docs for new features
4. **Pull Requests**: Provide clear description and rationale
5. **Backward Compatibility**: Ensure changes don't break existing functionality

### Areas Needing Contribution

#### High Priority
- **ML Integration**: Complete Anomalib model integration
- **Backend-Frontend Integration**: Connect UI to real APIs
- **WebSocket Support**: Real-time updates implementation
- **Authentication**: OAuth/JWT implementation

#### Medium Priority
- **Additional SIEM Connectors**: New SIEM integrations
- **SDN Controllers**: Support for additional controllers
- **Performance Optimization**: Caching and optimization
- **Security Audits**: Security improvements

#### Low Priority
- **UI Enhancements**: Additional UI features
- **Documentation**: Tutorials and guides
- **Examples**: Code examples and demos
- **Internationalization**: Multi-language support

---

## Code Standards

### Python Code Style

**Style Guide**: PEP 8

**Tools**:
```bash
# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .

# Type checking
mypy .
```

**Configuration**: See `pyproject.toml` for detailed configuration.

### TypeScript Code Style

**Style Guide**: Standard TypeScript conventions

**Tools**:
```bash
# Format code
npm run lint

# Type checking
npm run check

# Auto-fix
npm run lint -- --fix
```

### Code Review Checklist

- [ ] Code follows style guide
- [ ] All tests pass
- [ ] No linter errors
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] Backward compatibility maintained
- [ ] Security considerations addressed
- [ ] Performance impact evaluated

---

## Testing

### Backend Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_event_analyzer.py

# Run with coverage
pytest --cov=netsentinel --cov-report=html

# Run specific test
pytest tests/test_event_analyzer.py::test_threat_detection

# Run integration tests
pytest -m integration

# Run with verbose output
pytest -v

# Run in watch mode
pip install pytest-watch
ptw
```

### Frontend Testing

```bash
cd netsentinel-ui

# Run unit tests
npm test

# Run with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Run in watch mode
npm run test:watch

# Run accessibility tests
npm run test:a11y
```

### Writing Tests

#### Backend Test Example

```python
import pytest
from netsentinel.processors.event_analyzer import EventAnalyzer

@pytest.mark.asyncio
async def test_threat_detection():
    analyzer = EventAnalyzer()
    await analyzer.start()
    
    event = create_test_event()
    result = await analyzer.analyze_event(event)
    
    assert result.threat_score > 0
    assert result.threat_level in ThreatLevel
    
    await analyzer.stop()
```

#### Frontend Test Example

```typescript
import { render, screen } from '@testing-library/react';
import { StatCard } from '@/components/StatCard';

describe('StatCard', () => {
  it('renders stat card correctly', () => {
    render(<StatCard title="Total Events" value={1000} />);
    expect(screen.getByText('Total Events')).toBeInTheDocument();
    expect(screen.getByText('1000')).toBeInTheDocument();
  });
});
```

### Test Coverage Goals

- **Backend**: 80%+ coverage
- **Frontend**: 80%+ coverage
- **Critical Paths**: 100% coverage
- **Utility Functions**: 90%+ coverage

---

## Troubleshooting

### Common Development Issues

#### Import Errors

```bash
# Backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python -m netsentinel.processors.refactored_event_processor

# Frontend
npm install
```

#### Port Conflicts

```bash
# Check what's using the port
lsof -i :8082  # macOS/Linux
netstat -ano | findstr :8082  # Windows

# Change port in configuration
# Backend: Change NETSENTINEL_API_PORT in .env
# Frontend: Change port in vite.config.ts
```

#### Docker Issues

```bash
# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check logs
docker-compose logs -f netsentinel

# Clean up
docker-compose down -v
docker system prune -a
```

#### Frontend Build Issues

```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite

# Rebuild
npm run build
```

#### Backend Module Not Found

```bash
# Install dependencies
pip install -r requirements.txt

# Check Python path
echo $PYTHONPATH

# Run from project root
cd /path/to/netsentinel
python -m netsentinel.processors.refactored_event_processor
```

### Debugging

#### Enable Debug Logging

```bash
# Backend
NETSENTINEL_LOG_LEVEL=DEBUG python -m netsentinel.processors.refactored_event_processor

# Frontend: Open browser DevTools Console
```

#### Python Debugger

```python
import pdb

# Add breakpoint
pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()
```

#### VS Code Debugging

**Backend** (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ]
}
```

**Frontend** (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Launch Chrome",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173"
    }
  ]
}
```

---

## Additional Resources

### Documentation

- [API Documentation](API.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Architecture Overview](project-overview.md)
- [ML Setup Guide](ml-setup-guide.md)

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/)
- [Docker Documentation](https://docs.docker.com/)

### Community

- GitHub Issues: [Report bugs or request features](https://github.com/your-org/netsentinel/issues)
- Discussions: [Join discussions](https://github.com/your-org/netsentinel/discussions)
- Discord: [Join the community](https://discord.gg/netsentinel)

---

**Happy Coding! 🚀**

**Last Updated**: January 2024  
**Version**: 1.0.0

