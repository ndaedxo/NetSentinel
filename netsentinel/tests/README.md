# NetSentinel Testing Guide

Comprehensive testing infrastructure for NetSentinel - Advanced Network Anomaly Detection & Mitigation System.

## 🧪 Testing Overview

NetSentinel uses a multi-layered testing approach to ensure code quality, functionality, and reliability:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Full system workflow testing
- **Performance Tests**: Load and performance validation
- **Security Tests**: Security vulnerability testing
- **Smoke Tests**: Quick CI/CD validation

## 🚀 Quick Start

### Run All Tests
```bash
# Run complete test suite
make test

# Run with coverage
make test-unit

# Run specific test categories
make test-integration
make test-e2e
```

### Run Smoke Tests (CI/CD)
```bash
# Quick validation for CI/CD pipelines
make smoke-tests

# Individual smoke test
pytest tests/unit/test_smoke.py -v
```

## 📁 Test Structure

```
tests/
├── conftest.py              # Global pytest configuration and fixtures
├── unit/                    # Unit tests (individual components)
│   ├── test_event_processor.py
│   ├── test_firewall_manager.py
│   ├── test_siem_integration.py
│   ├── test_sdn_integration.py
│   └── test_smoke.py
├── integration/             # Integration tests (component interaction)
│   └── test_netsentinel_integration.py
├── e2e/                     # End-to-end tests (full workflows)
└── helpers/                 # Test utilities and fixtures
    ├── conftest.py
    └── data.py
```

## 🛠️ Test Categories

### Unit Tests (`tests/unit/`)
Test individual components in isolation:

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific component tests
pytest tests/unit/test_event_processor.py -v
pytest tests/unit/test_firewall_manager.py -v
pytest tests/unit/test_siem_integration.py -v
pytest tests/unit/test_sdn_integration.py -v
```

### Integration Tests (`tests/integration/`)
Test component interactions:

```bash
# Run integration tests
pytest tests/integration/ -v

# Test full system integration
pytest tests/integration/test_netsentinel_integration.py -v
```

### End-to-End Tests (`tests/e2e/`)
Test complete user workflows:

```bash
# Run E2E tests (requires full environment)
pytest tests/e2e/ -v
```

### Performance Tests
Test system performance under load:

```bash
# Performance tests
pytest tests/unit/ -k "performance" -v

# Memory usage tests
pytest tests/unit/ -k "memory" -v
```

### Security Tests
Test security-related functionality:

```bash
# Security tests
pytest tests/unit/ -k "security" -v

# Run security linting
make security-scan
```

## 🎯 Test Fixtures

### Global Fixtures (`conftest.py`)

#### Core Components
```python
@pytest.fixture
def event_processor():
    """NetSentinel event processor instance"""

@pytest.fixture
def firewall_manager():
    """Firewall manager instance"""

@pytest.fixture
def siem_manager():
    """SIEM integration manager instance"""

@pytest.fixture
def sdn_manager():
    """SDN integration manager instance"""
```

#### Test Data
```python
@pytest.fixture
def sample_security_event():
    """Sample SSH login event"""

@pytest.fixture
def high_threat_event():
    """High-threat security event"""

@pytest.fixture
def low_threat_event():
    """Low-threat security event"""
```

#### Mock Services
```python
@pytest.fixture
def mock_redis():
    """Mock Redis client"""

@pytest.fixture
def mock_kafka():
    """Mock Kafka producer/consumer"""

@pytest.fixture
def mock_requests():
    """Mock HTTP requests"""
```

## 🏃 Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_event_processor.py

# Run specific test function
pytest tests/unit/test_event_processor.py::TestEventProcessor::test_initialization

# Run tests matching pattern
pytest -k "threat" -v

# Run tests with markers
pytest -m "unit" -v
pytest -m "integration" -v
pytest -m "performance" -v
```

### Advanced Options

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Generate HTML report
pytest --html=report.html

# Show slowest tests
pytest --durations=10

# Run failed tests first
pytest --lf

# Run tests and stop on first failure
pytest -x

# Debug mode
pytest --pdb
```

## 📊 Code Coverage

### Generate Coverage Reports

```bash
# Run tests with coverage
pytest --cov=netsentinel --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html

# Coverage for specific modules
pytest --cov=netsentinel.event_processor --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=netsentinel --cov-fail-under=80
```

### Coverage Configuration

Coverage settings in `pyproject.toml`:
```toml
[tool.coverage.run]
source = ["netsentinel"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "docs/*",
    "scripts/*",
    "anomalib/*",
    "opencanary/modules/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "raise AssertionError",
]
```

## 🔧 Development Workflow

### Pre-commit Hooks
```bash
# Install pre-commit hooks
make hooks-install

# Run pre-commit on all files
make lint

# Run pre-commit on changed files
pre-commit run
```

### Code Formatting
```bash
# Format code
make format

# Check formatting without modifying
make format-check
```

### Type Checking
```bash
# Run mypy type checking
mypy netsentinel/

# Run with additional options
mypy netsentinel/ --ignore-missing-imports
```

## 🐳 Docker Testing

### Test in Docker Environment
```bash
# Build and run tests in Docker
make docker-test

# Run smoke tests in Docker
make docker-smoke

# Test specific components
docker-compose exec event-processor pytest tests/unit/test_event_processor.py -v
```

### Docker Compose Testing
```bash
# Start test environment
docker-compose up -d

# Run tests against running services
pytest tests/integration/ --docker-compose

# Stop test environment
docker-compose down
```

## 🚀 CI/CD Integration

### GitHub Actions Workflow
The CI/CD pipeline includes:

1. **Pre-commit checks**: Code formatting and linting
2. **Unit tests**: Component testing with coverage
3. **Integration tests**: Component interaction testing
4. **API tests**: REST API validation
5. **Docker tests**: Container build and runtime testing
6. **Security tests**: Vulnerability scanning
7. **Performance tests**: Load testing
8. **Smoke tests**: Quick validation

### Local CI Simulation
```bash
# Run full CI pipeline locally
make ci

# Quick CI checks
make ci-quick
```

## 🐛 Debugging Tests

### Debug Failed Tests
```bash
# Run failed tests with detailed output
pytest --lf -v --tb=long

# Debug specific test
pytest tests/unit/test_event_processor.py::TestEventProcessor::test_initialization --pdb

# Show captured output
pytest -s --capture=no
```

### Test Isolation Issues
```bash
# Run tests in random order to detect dependencies
pytest --random-order

# Run single test in isolation
pytest tests/unit/test_event_processor.py::TestEventProcessor::test_initialization --runxfail
```

### Performance Debugging
```bash
# Profile test execution
pytest --durations=10

# Memory profiling
pytest --memray

# CPU profiling
pytest --profile
```

## 📈 Performance Testing

### Load Testing
```bash
# Test event processing under load
pytest tests/unit/test_event_processor.py::TestEventProcessor::test_performance_under_load -v

# Test concurrent operations
pytest tests/unit/ -k "concurrent" -v

# Memory usage testing
pytest tests/unit/ -k "memory" -v
```

### Benchmarking
```bash
# Compare performance across versions
pytest-benchmark tests/unit/test_event_processor.py

# Save benchmark results
pytest-benchmark --benchmark-save=benchmark.json tests/unit/test_event_processor.py
```

## 🔒 Security Testing

### Static Security Analysis
```bash
# Run bandit security linting
bandit -r netsentinel/

# Run safety dependency checking
safety check

# Comprehensive security scan
make security-scan
```

### Runtime Security Tests
```bash
# Test input validation
pytest tests/unit/ -k "security" -v

# Test authentication/authorization
pytest tests/integration/ -k "auth" -v

# Test data sanitization
pytest tests/unit/ -k "sanitization" -v
```

## 📝 Writing Tests

### Test File Structure
```python
import pytest
from netsentinel.module import ClassToTest

class TestClassToTest:
    """Test cases for ClassToTest"""

    @pytest.fixture
    def instance(self):
        """Test instance fixture"""
        return ClassToTest()

    def test_initialization(self, instance):
        """Test object initialization"""
        assert instance is not None

    def test_method_functionality(self, instance):
        """Test method behavior"""
        result = instance.method()
        assert result == expected_value

    @pytest.mark.parametrize("input,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
    ])
    def test_parameterized_cases(self, input, expected):
        """Test multiple input/output combinations"""
        result = function_under_test(input)
        assert result == expected
```

### Test Best Practices

#### Naming Conventions
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Fixtures: Lowercase with underscores

#### Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Mock external dependencies
- Clean up resources after tests

#### Assertions
- Use descriptive assertion messages
- Test both positive and negative cases
- Test edge cases and error conditions
- Verify state changes, not just return values

## 🔧 Test Utilities

### Custom Assertions
```python
def assert_event_processed_successfully(processor, event_data):
    """Assert that an event was processed successfully"""
    result = processor._process_single_event(event_data)
    assert result is not None

def assert_api_response_success(response_data, required_fields=None):
    """Assert that an API response indicates success"""
    assert isinstance(response_data, dict)
    assert response_data.get('status') in ['success', 'ok', True]
    if required_fields:
        for field in required_fields:
            assert field in response_data
```

### Test Data Helpers
```python
def create_test_event(event_type="4002", threat_score=5.0):
    """Create a test security event"""
    return {
        'logtype': event_type,
        'src_host': '192.168.1.100',
        'threat_score': threat_score,
        'timestamp': time.time()
    }

def wait_for_condition(condition_func, timeout=10):
    """Wait for a condition to become true"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(0.1)
    return False
```

## 📊 Test Reporting

### Generate Reports
```bash
# HTML test report
pytest --html=test-report.html

# JUnit XML for CI systems
pytest --junitxml=test-results.xml

# Coverage reports
pytest --cov=netsentinel --cov-report=html --cov-report=xml
```

### Custom Reporting
```python
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Custom test reporting hook"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # Log additional information for failed tests
        print(f"Test {item.nodeid} failed: {report.longrepr}")
```

## 🚨 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Install in development mode
pip install -e .
```

#### Database Connection Issues
```bash
# Check Redis/Kafka connectivity
redis-cli ping
kafka-console-producer --broker-list localhost:9092 --topic test

# Use mock services for unit tests
pytest tests/unit/ --mock-db
```

#### Slow Tests
```bash
# Run with timing information
pytest --durations=10

# Skip slow tests
pytest -m "not slow"

# Run in parallel
pytest -n auto
```

#### Memory Issues
```bash
# Monitor memory usage
pytest --memray

# Run garbage collection between tests
pytest --gc-disable
```

## 📚 Resources

### Testing Frameworks
- [pytest](https://docs.pytest.org/) - Testing framework
- [pytest-cov](https://pytest-cov.readthedocs.io/) - Coverage reporting
- [pytest-mock](https://pytest-mock.readthedocs.io/) - Mocking utilities

### Code Quality
- [black](https://black.readthedocs.io/) - Code formatting
- [flake8](https://flake8.pycqa.org/) - Linting
- [mypy](https://mypy.readthedocs.io/) - Type checking
- [bandit](https://bandit.readthedocs.io/) - Security linting

### CI/CD
- [GitHub Actions](https://docs.github.com/en/actions) - CI/CD platform
- [tox](https://tox.readthedocs.io/) - Test automation
- [pre-commit](https://pre-commit.com/) - Git hooks

---

**Test Status**: ✅ **Comprehensive testing infrastructure implemented**

For additional testing help, check the specific test files or run `make help` for available commands.