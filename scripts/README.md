# NetSentinel Scripts

This directory contains utility scripts for managing and testing NetSentinel deployments.

## Quick Start Testing Workflow

### Option 1: Run All Tests (Recommended)
```bash
# Run complete test suite in optimal order
pwsh -File scripts/run_all_tests.ps1

# Skip component-specific tests (faster)
pwsh -File scripts/run_all_tests.ps1 -SkipComponentTests

# Quick infrastructure + core functionality only
pwsh -File scripts/run_all_tests.ps1 -Quick
```

### Option 2: Manual Testing Steps
```bash
# 1. Test Docker infrastructure and core APIs
pwsh -File scripts/test-netsentinel-docker.ps1

# 2. Test all functionality and components
pwsh -File scripts/test_functionality.ps1

# 3. Test specific components (as needed)
python scripts/test_enterprise_database.py
python scripts/test_firewall.py
python scripts/test_alerting.py
python scripts/test_sdn_integration.py
python scripts/test_complete_data_flow.py
```

## Available Scripts

### Core Testing Scripts

#### `run_all_tests.ps1`
**Purpose:** Orchestrate all test scripts in optimal sequence
- Runs infrastructure, functionality, component, and integration tests
- Provides comprehensive test results and timing
- Supports different testing modes (full, skip components, quick)
- Clear pass/fail reporting with detailed statistics

**Usage:**
```powershell
# Run complete test suite
pwsh -File scripts/run_all_tests.ps1

# Skip component-specific tests (faster execution)
pwsh -File scripts/run_all_tests.ps1 -SkipComponentTests

# Quick mode: infrastructure + core functionality only
pwsh -File scripts/run_all_tests.ps1 -Quick
```

#### `test-netsentinel-docker.ps1`
**Purpose:** Comprehensive infrastructure and basic API testing
- Tests all 11 Docker services health status
- Validates core API endpoints (health, auth, threats)
- Checks web interface accessibility (Grafana, Kafka UI, Redis Commander)
- Verifies honeypot services (FTP, SSH, HTTP, HTTPS ports)
- Tests data persistence (Redis, Elasticsearch)
- Provides production readiness assessment

**Usage:**
```powershell
# Basic test
pwsh -File scripts/test-netsentinel-docker.ps1

# Quiet mode (exit code only)
pwsh -File scripts/test-netsentinel-docker.ps1 -Quiet

# Export to JSON
pwsh -File scripts/test-netsentinel-docker.ps1 -Json
```

#### `test_functionality.ps1`
**Purpose:** Comprehensive functionality testing
- Tests Kafka, Redis, and Elasticsearch functionality
- Validates all 37 API endpoints across all services
- Tests threat intelligence operations
- Tests SIEM integration operations
- Tests event processing pipeline
- Verifies web interface accessibility

**Usage:**
```powershell
pwsh -File scripts/test_functionality.ps1
```

### Component-Specific Test Scripts

#### `test_enterprise_database.py`
**Purpose:** Test Elasticsearch and InfluxDB integration
- Tests database manager initialization
- Validates API endpoints for database operations
- Tests search functionality and data persistence
- Verifies metrics collection and retrieval

**Usage:**
```bash
python scripts/test_enterprise_database.py
```

#### `test_firewall.py`
**Purpose:** Test firewall management and IP blocking
- Tests firewall manager functionality
- Validates firewall API endpoints
- Tests automated IP blocking based on threat scores
- Verifies firewall status and blocked IP management

**Usage:**
```bash
python scripts/test_firewall.py
```

#### `test_alerting.py`
**Purpose:** Test alert generation and management
- Tests alert manager initialization (when available)
- Validates alert API endpoints
- Tests alert filtering and escalation (when supported)
- Verifies security alert generation

**Usage:**
```bash
python scripts/test_alerting.py
```

#### `test_sdn_integration.py`
**Purpose:** Test SDN controller integration
- Tests SDN manager and controller management
- Validates SDN controller types (OpenDaylight, ONOS, Ryu)
- Tests SDN connectivity and flow management

**Usage:**
```bash
python scripts/test_sdn_integration.py
```

#### `test_complete_data_flow.py`
**Purpose:** Test end-to-end data processing pipeline
- Tests complete event processing workflow
- Validates API connectivity and responsiveness
- Tests event simulation and processing verification
- Confirms data flow from ingestion to storage

**Usage:**
```bash
python scripts/test_complete_data_flow.py
```

### Utility and Management Scripts

#### `start_event_processor.py`
**Purpose:** Start the NetSentinel event processor service

**Usage:**
```bash
python scripts/start_event_processor.py
```

#### `simulate_netsentinel_event.py`
**Purpose:** Simulate security events for testing

**Usage:**
```bash
# Send single SSH event
python scripts/simulate_netsentinel_event.py --ip 192.168.1.100 --type ssh --count 1

# Send multiple events
python scripts/simulate_netsentinel_event.py --ip 192.168.1.100 --type ssh --count 10
```

#### `train_ml_models.py`
**Purpose:** Train ML models for anomaly detection

**Usage:**
```bash
# Train with default settings
python scripts/train_ml_models.py --dataset-size 1000 --epochs 10
```

## Testing Strategy

### Recommended Testing Order

1. **Infrastructure First**: `test-netsentinel-docker.ps1`
   - Ensures all services are running before detailed testing

2. **Comprehensive Functionality**: `test_functionality.ps1`
   - Tests all APIs and core functionality end-to-end

3. **Component-Specific Testing**: Individual component tests
   - Use when debugging specific components or after changes

4. **Integration Testing**: `test_complete_data_flow.py`
   - Final verification of complete event processing pipeline

### Test Coverage

| Component | Test Script | Coverage |
|-----------|-------------|----------|
| **Infrastructure** | `test-netsentinel-docker.ps1` | Docker services, ports, basic APIs |
| **Core APIs** | `test_functionality.ps1` | All 37 API endpoints, event processing |
| **Database** | `test_enterprise_database.py` | Elasticsearch, InfluxDB operations |
| **Firewall** | `test_firewall.py` | IP blocking, firewall management |
| **Alerting** | `test_alerting.py` | Alert generation, notification system |
| **SDN** | `test_sdn_integration.py` | SDN controllers, network policies |
| **Data Flow** | `test_complete_data_flow.py` | End-to-end event processing |
| **Threat Intel** | `test_functionality.ps1` | IP checking, feed management |
| **SIEM** | `test_functionality.ps1` | Event forwarding, connectors |

## Development Guidelines

### Adding New Test Scripts

1. **Naming Convention**: Use `test_<component>.py` for Python, `test_<component>.ps1` for PowerShell
2. **Error Handling**: Include comprehensive try-catch blocks and meaningful error messages
3. **Documentation**: Add docstrings and inline comments explaining test logic
4. **Logging**: Use consistent logging format and provide clear pass/fail indicators
5. **Environment**: Support both Docker and non-Docker environments where possible
6. **Configuration**: Use environment variables for configurable settings

### Script Template (Python)

```python
#!/usr/bin/env python3
"""
Test script for <component> functionality
Tests <specific functionality>
"""

import requests
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EVENT_PROCESSOR_URL = "http://localhost:8082"

def test_<component>_functionality():
    """Test <component> functionality"""
    print("🔍 Testing <Component> Functionality...")

    try:
        # Test implementation here
        return True
    except Exception as e:
        print(f"❌ <Component> test failed: {e}")
        return False

def main():
    """Run all <component> tests"""
    print("<Component> Test Suite")
    print("=" * 40)

    tests = [
        test_<component>_functionality,
        # Add more test functions
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All <component> tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### Script Template (PowerShell)

```powershell
#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test NetSentinel <component> functionality

.DESCRIPTION
    Comprehensive testing of <component> features and API endpoints

.PARAMETER Quiet
    Suppress output, return exit code only

.EXAMPLE
    .\test_<component>.ps1
    .\test_<component>.ps1 -Quiet
#>

param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

# Configuration
$ApiBase = "http://localhost:8082"

function Write-ColoredOutput {
    param([string]$Message, [string]$Color = "White")
    if (-not $Quiet) {
        Write-Host $Message -ForegroundColor $Color
    }
}

function Test-<Component>Functionality {
    Write-ColoredOutput "🔍 Testing <Component> Functionality..." "Cyan"

    try {
        # Test implementation here
        return $true
    }
    catch {
        Write-ColoredOutput "❌ <Component> test failed: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Main execution
Write-ColoredOutput "<Component> Test Suite" "Yellow"
Write-ColoredOutput ("=" * 40) "Yellow"

$tests = @(
    ${function:Test-<Component>Functionality}
    # Add more test functions
)

$passed = 0
$total = $tests.Count

foreach ($test in $tests) {
    if (& $test) {
        $passed++
    }
}

Write-ColoredOutput "`n📊 Test Results: $passed/$total tests passed" "Cyan"

if ($passed -eq $total) {
    Write-ColoredOutput "🎉 All <component> tests passed!" "Green"
    exit 0
} else {
    Write-ColoredOutput "❌ Some tests failed." "Red"
    exit 1
}
```

## Troubleshooting

### Common Issues

**PowerShell Script Issues:**
- Ensure you're using PowerShell Core (`pwsh`) not Windows PowerShell
- Check that `curl` is available in PATH
- Verify Docker services are running: `docker-compose ps`

**Python Script Issues:**
- Ensure Python 3.8+ is installed
- Install required packages: `pip install requests`
- Set PYTHONPATH if needed: `$env:PYTHONPATH = "$PWD/src;$PWD"`

**Docker Environment Issues:**
- Ensure all services are healthy: `docker-compose ps`
- Check service logs: `docker-compose logs <service_name>`
- Restart services if needed: `docker-compose restart`

**API Testing Issues:**
- Verify API server is responding: `curl http://localhost:8082/health`
- Check for import errors in event processor logs
- Ensure all required environment variables are set

**Permission Issues:**
- PowerShell: Scripts may need execution policy: `Set-ExecutionPolicy RemoteSigned`
- Docker: Run with appropriate privileges for system operations
- File permissions: Ensure scripts have execute permissions

### Environment Variables

Common environment variables used by test scripts:

- `NETSENTINEL_API_BASE`: API server URL (default: `http://localhost:8082`)
- `NETSENTINEL_KAFKA_SERVERS`: Kafka bootstrap servers
- `NETSENTINEL_REDIS_HOST`: Redis hostname
- `NETSENTINEL_REDIS_PORT`: Redis port

### Getting Help

For issues not covered here:
1. Check the specific test script's error messages
2. Review Docker container logs: `docker-compose logs event-processor`
3. Verify network connectivity between services
4. Check firewall/antivirus blocking connections
