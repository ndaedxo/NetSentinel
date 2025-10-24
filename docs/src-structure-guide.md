# NetSentinel Source Structure Guide

## 📁 **What's in `src/` Directory**

The `src/` directory follows **Python packaging best practices** and contains the **source code** of the NetSentinel package.

## 🏗️ **Current `src/` Structure**

```
src/
├── __init__.py                    # Package initialization
└── netsentinel/                   # Main NetSentinel package
    ├── __init__.py               # Package version and metadata
    ├── core/                     # Core functionality
    │   ├── base.py              # Base classes and interfaces
    │   ├── models.py            # Data models and schemas
    │   ├── event_bus.py         # Event bus implementation
    │   ├── container.py         # Dependency injection
    │   └── ...                  # Other core components
    ├── processors/              # Event processing
    │   ├── event_analyzer.py   # ML-powered event analysis
    │   ├── event_consumer.py   # Kafka event consumption
    │   ├── api_server.py       # REST API server
    │   └── ...                 # Other processors
    ├── gateway/                 # API Gateway
    │   ├── api_gateway.py      # Main gateway
    │   ├── routing.py          # Request routing
    │   └── middleware.py       # Gateway middleware
    ├── modules/                 # Honeypot modules
    │   ├── ssh.py             # SSH honeypot
    │   ├── http.py            # HTTP honeypot
    │   ├── ftp.py             # FTP honeypot
    │   └── ...                 # Other honeypot services
    ├── ml_anomaly_detector.py  # ML anomaly detection
    ├── firewall_manager.py     # Firewall automation
    ├── threat_intelligence.py  # Threat intelligence
    ├── siem_integration.py     # SIEM integration
    ├── sdn_integration.py      # SDN integration
    └── tests/                  # Package tests
        ├── unit/              # Unit tests
        └── integration/       # Integration tests
```

## 🎯 **Benefits of `src/` Layout**

### **1. Clean Separation**
- **Source Code**: All in `src/`
- **Tests**: Separate `tests/` directory
- **Documentation**: `docs/` directory
- **Scripts**: `scripts/` directory
- **Configuration**: Root level files

### **2. Import Safety**
- Prevents accidental imports from development directory
- Ensures tests import from installed package
- Reduces import path confusion

### **3. Packaging Best Practices**
- Follows PEP 517/518 standards
- Compatible with modern Python packaging tools
- Works with `pip install -e .` (editable installs)

## 📦 **What Should Be in `src/`**

### **✅ Move to `src/`**
```
src/netsentinel/                 # Main package (ALREADY MOVED)
├── All Python modules          # Core functionality
├── Configuration files         # Package config
├── Data files                  # Static data
└── Package tests              # Unit tests
```

### **❌ Keep in Root (Don't Move)**
```
# External dependencies
anomalib/                       # External ML library
bin/                           # Executable scripts
build_scripts/                 # Build automation
docs/                          # Documentation
scripts/                       # Utility scripts
tests/                         # Integration tests
k8s/                          # Kubernetes manifests
helm/                         # Helm charts
```

## 🔧 **Configuration Updates**

### **1. pyproject.toml (Already Correct)**
```toml
[tool.setuptools.packages.find]
where = ["src"]  # ✅ Points to src/ directory
```

### **2. Import Path Updates**
```python
# Before (root level)
from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector

# After (src/ layout) - Same import works!
from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector
```

### **3. Test Configuration**
```python
# pytest.ini - Update if needed
[tool:pytest]
testpaths = tests src/netsentinel/tests
pythonpath = src
```

## 🚀 **Development Workflow**

### **1. Editable Installation**
```bash
# Install in development mode
pip install -e .

# This makes src/netsentinel available as 'netsentinel' package
```

### **2. Running Tests**
```bash
# Run all tests
pytest

# Run package tests only
pytest src/netsentinel/tests/

# Run integration tests
pytest tests/
```

### **3. Development Commands**
```bash
# Install with ML dependencies
pip install -e .[ml]

# Install with monitoring dependencies
pip install -e .[monitoring]

# Install development dependencies
pip install -e .[dev]
```

## 📊 **Package Structure Benefits**

### **1. Clear Organization**
- **`src/netsentinel/`**: Main package code
- **`tests/`**: Integration and end-to-end tests
- **`docs/`**: Documentation and guides
- **`scripts/`**: Utility and training scripts
- **`k8s/`**: Kubernetes deployment manifests

### **2. Import Clarity**
```python
# Package imports (from src/)
from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector
from netsentinel.processors.event_analyzer import EventAnalyzer
from netsentinel.core.models import StandardEvent

# External imports (from root)
from anomalib.models import Fastflow
import kafka
import redis
```

### **3. Testing Strategy**
- **Unit Tests**: `src/netsentinel/tests/unit/`
- **Integration Tests**: `tests/integration/`
- **End-to-End Tests**: `tests/`
- **ML Tests**: `src/netsentinel/tests/unit/test_ml_*.py`

## 🎯 **Migration Checklist**

### **✅ Completed**
- [x] Created `src/` directory structure
- [x] Moved `netsentinel/` package to `src/netsentinel/`
- [x] Updated `pyproject.toml` for src layout
- [x] Created `src/__init__.py`
- [x] Maintained import compatibility

### **🔄 Next Steps**
- [ ] Update CI/CD pipelines for src layout
- [ ] Update documentation references
- [ ] Test editable installation
- [ ] Verify all imports work correctly

## 📚 **Best Practices**

### **1. Package Development**
```bash
# Always use editable installs for development
pip install -e .

# Test imports work correctly
python -c "from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector"
```

### **2. Testing Strategy**
```bash
# Run package unit tests
pytest src/netsentinel/tests/unit/

# Run integration tests
pytest tests/

# Run all tests
pytest
```

### **3. Documentation**
- Keep package documentation in `docs/`
- Keep API documentation in `src/netsentinel/` docstrings
- Update README.md with new structure

## 🔍 **Verification**

### **1. Check Structure**
```bash
# Verify src layout
ls -la src/
ls -la src/netsentinel/

# Check imports work
python -c "import netsentinel; print(netsentinel.__version__)"
```

### **2. Test Installation**
```bash
# Test editable install
pip install -e .
python -c "from netsentinel.ml_anomaly_detector import NetworkEventAnomalyDetector"

# Test package scripts
netsentinel --help
netsentinel-train --help
```

### **3. Run Tests**
```bash
# Test package functionality
pytest src/netsentinel/tests/unit/test_ml_integration.py -v

# Test integration
pytest tests/integration/ -v
```

## 🎉 **Summary**

The `src/` layout provides:

- ✅ **Clean separation** of source code and tests
- ✅ **Import safety** and clarity
- ✅ **Packaging best practices** compliance
- ✅ **Development workflow** improvements
- ✅ **Maintainability** and organization

NetSentinel now follows **modern Python packaging standards** with a clean, organized structure that separates concerns and improves maintainability! 🚀

---

*Last Updated: December 19, 2024*
