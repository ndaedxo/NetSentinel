# NetSentinel Source Code

This directory contains the **source code** for the NetSentinel package following Python packaging best practices.

## 📁 **Structure**

```
src/
├── __init__.py                    # Package initialization
└── netsentinel/                   # Main NetSentinel package
    ├── __init__.py               # Package metadata
    ├── core/                     # Core functionality
    ├── processors/               # Event processing
    ├── gateway/                  # API Gateway
    ├── modules/                  # Honeypot modules
    ├── ml_anomaly_detector.py    # ML anomaly detection
    ├── firewall_manager.py       # Firewall automation
    ├── threat_intelligence.py    # Threat intelligence
    ├── siem_integration.py       # SIEM integration
    ├── sdn_integration.py        # SDN integration
    └── tests/                    # Package unit tests
```

## 🎯 **What's in `src/`**

### **✅ Source Code**
- **Core Package**: All NetSentinel Python modules
- **ML Components**: Machine learning anomaly detection
- **Processors**: Event processing and analysis
- **Gateway**: API Gateway and routing
- **Modules**: Honeypot service implementations
- **Tests**: Unit tests for package components

### **❌ What's NOT in `src/`**
- **External Dependencies**: `anomalib/` (external ML library)
- **Build Scripts**: `build_scripts/` (build automation)
- **Documentation**: `docs/` (documentation files)
- **Utility Scripts**: `scripts/` (training and utility scripts)
- **Integration Tests**: `tests/` (end-to-end tests)
- **Deployment**: `k8s/`, `helm/` (deployment manifests)

## 🚀 **Development**

### **Installation**
```bash
# Install in development mode
pip install -e .

# Install with ML dependencies
pip install -e .[ml]

# Install with monitoring dependencies
pip install -e .[monitoring]
```

### **Testing**
```bash
# Run package unit tests
pytest src/netsentinel/tests/unit/

# Run all tests
pytest
```

### **Import Usage**
```python
# Import from package
from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector
from netsentinel.processors.event_analyzer import EventAnalyzer
from netsentinel.core.models import StandardEvent
```

## 📦 **Package Benefits**

- **Clean Separation**: Source code isolated from tests and docs
- **Import Safety**: Prevents accidental imports from development directory
- **Packaging Best Practices**: Follows PEP 517/518 standards
- **Editable Installs**: Works with `pip install -e .`
- **Maintainability**: Clear organization and structure

---

*This directory contains the core NetSentinel package source code.*
