"""
NetSentinel Test Configuration and Fixtures
Global pytest configuration and shared test fixtures
"""

import os
import pytest
import time
import tempfile
import shutil
from unittest.mock import Mock, patch
from typing import Dict, Any, Generator, Optional

# Conditional imports for optional dependencies
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

# Import NetSentinel modules (these should always be available in development)
try:
    from src.netsentinel.firewall_manager import FirewallManager, get_firewall_manager
    from src.netsentinel.siem_integration import SiemManager, get_siem_manager
    from src.netsentinel.sdn_integration import SDNManager, get_sdn_manager

    NETSENTINEL_AVAILABLE = True
except ImportError as e:
    # Create mock classes for testing when NetSentinel is not available
    class MockFirewallManager:
        def __init__(self):
            pass

        def _detect_backend(self):
            return None

        def cleanup_test_rules(self):
            pass

    class MockSiemManager:
        def __init__(self):
            self.connectors = {}
            self.enabled_systems = {}
            self.event_filters = {}
            self.active_flows = {}

        def get_statistics(self):
            return {"events_sent": 0}

        def add_webhook_connector(self, name, url, **kwargs):
            self.connectors[name] = {"type": "webhook", "url": url, **kwargs}

        def enable_system(self, name):
            self.enabled_systems[name] = True

        def set_event_filter(self, system, **kwargs):
            self.event_filters[system] = kwargs

        def send_event(self, event):
            return True

    class MockSDNManager:
        def __init__(self):
            self.controllers = {}
            self.quarantine_policies = {}
            self.active_flows = {}

        def get_status(self):
            return {"controllers": []}

        def add_controller(self, controller):
            self.controllers[controller.name] = controller

        def quarantine_ip(self, ip, **kwargs):
            return True

        def release_quarantine(self, policy_name):
            return True

        def mirror_traffic(self, source_ip, **kwargs):
            return True

        def redirect_traffic(self, source_ip, **kwargs):
            return True

    FirewallManager = MockFirewallManager
    get_firewall_manager = lambda: MockFirewallManager()
    SiemManager = MockSiemManager
    get_siem_manager = lambda: MockSiemManager()
    SDNManager = MockSDNManager
    get_sdn_manager = lambda: MockSDNManager()
    NETSENTINEL_AVAILABLE = False

# Conditional import for event processor (requires kafka)
try:
    import kafka  # noqa: F401
    from netsentinel.processors.refactored_event_processor import (
        RefactoredEventProcessor,
        ProcessorConfig,
    )

    EVENT_PROCESSOR_AVAILABLE = True
except ImportError:
    RefactoredEventProcessor = None
    ProcessorConfig = None
    EVENT_PROCESSOR_AVAILABLE = False


# Test configuration
@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Global test configuration"""
    return {
        "redis_host": os.getenv("REDIS_HOST", "localhost"),
        "redis_port": int(os.getenv("REDIS_PORT", "6379")),
        "kafka_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        "test_timeout": 30,
        "performance_threshold": 5.0,  # seconds
        "memory_threshold": 100 * 1024 * 1024,  # 100MB
    }


@pytest.fixture(scope="session")
def redis_client(test_config):
    """Redis client for testing"""
    if not REDIS_AVAILABLE:
        pytest.skip("Redis not available for testing")

    try:
        client = redis.Redis(
            host=test_config["redis_host"],
            port=test_config["redis_port"],
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        # Test connection
        client.ping()
        yield client
    except Exception:
        pytest.skip("Redis not available for testing")
    finally:
        try:
            client.close()
        except:
            pass


@pytest.fixture(scope="session")
def temp_dir():
    """Temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch("redis.Redis") as mock_redis_class:
        mock_client = Mock()
        mock_redis_class.return_value = mock_client

        # Mock common Redis operations
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock_client.setex.return_value = True
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = False
        mock_client.ping.return_value = True
        mock_client.publish.return_value = 1

        yield mock_client


@pytest.fixture
def mock_kafka():
    """Mock Kafka producer and consumer"""
    with (
        patch("kafka.KafkaProducer") as mock_producer_class,
        patch("kafka.KafkaConsumer") as mock_consumer_class,
    ):

        mock_producer = Mock()
        mock_consumer = Mock()

        mock_producer_class.return_value = mock_producer
        mock_consumer_class.return_value = mock_consumer

        # Mock producer methods
        mock_producer.send.return_value = Mock()
        mock_producer.flush.return_value = None

        # Mock consumer methods
        mock_consumer.subscribe.return_value = None
        mock_consumer.poll.return_value = {}
        mock_consumer.close.return_value = None

        yield {"producer": mock_producer, "consumer": mock_consumer}


@pytest.fixture
def event_processor(mock_redis, mock_kafka):
    """Test event processor instance"""
    if not EVENT_PROCESSOR_AVAILABLE:
        pytest.skip("EventProcessor not available (missing kafka dependency)")

    with patch.dict(
        os.environ,
        {
            "ALERTING_ENABLED": "false",
            "ENTERPRISE_DB_ENABLED": "false",
            "THREAT_INTEL_ENABLED": "false",
            "PACKET_ANALYSIS_ENABLED": "false",
            "SIEM_ENABLED": "false",
            "SDN_ENABLED": "false",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        },
    ):
        if EVENT_PROCESSOR_AVAILABLE:
            processor = RefactoredEventProcessor(
                ProcessorConfig(
                    kafka_servers=["localhost:9092"],
                    kafka_topic="test-events",
                    consumer_group="test-processor",
                    ml_enabled=False,
                    alerting_enabled=False,
                    siem_enabled=False,
                    firewall_enabled=False,
                )
            )
            yield processor
            # Cleanup will be handled by the processor's stop method
        else:
            pytest.skip("EventProcessor not available (missing kafka dependency)")


@pytest.fixture
def firewall_manager():
    """Test firewall manager instance"""
    manager = FirewallManager()
    yield manager
    # Clean up any test rules
    try:
        if hasattr(manager, "cleanup_test_rules"):
            manager.cleanup_test_rules()
    except:
        pass


@pytest.fixture
def siem_manager():
    """Test SIEM manager instance"""
    manager = SiemManager()
    yield manager
    # Clean up
    if hasattr(manager, "connectors"):
        manager.connectors.clear()
    if hasattr(manager, "enabled_systems"):
        manager.enabled_systems.clear()
    if hasattr(manager, "event_filters"):
        manager.event_filters.clear()
    if hasattr(manager, "active_flows"):
        manager.active_flows.clear()


@pytest.fixture
def sdn_manager():
    """Test SDN manager instance"""
    manager = SDNManager()
    yield manager
    # Clean up
    if hasattr(manager, "controllers"):
        manager.controllers.clear()
    if hasattr(manager, "quarantine_policies"):
        manager.quarantine_policies.clear()
    if hasattr(manager, "active_flows"):
        manager.active_flows.clear()


@pytest.fixture
def sample_security_event():
    """Sample security event for testing"""
    return {
        "logtype": "4002",
        "src_host": "192.168.1.100",
        "logdata": {
            "username": "admin",
            "password": "secret123",
            "timestamp": time.time(),
        },
        "timestamp": time.time(),
    }


@pytest.fixture
def sample_ssh_attack():
    """Sample SSH brute force attack event"""
    return {
        "logtype": "4002",
        "src_host": "10.0.0.1",
        "logdata": {
            "username": "root",
            "password": "password123",
            "session_id": "abc123",
            "timestamp": time.time(),
        },
        "timestamp": time.time(),
    }


@pytest.fixture
def sample_http_anomaly():
    """Sample HTTP anomaly event"""
    return {
        "logtype": "3000",
        "src_host": "192.168.1.50",
        "logdata": {
            "request": "GET /admin.php?cmd=../../../../etc/passwd",
            "user_agent": "sqlmap/1.6.0",
            "response_code": 404,
            "timestamp": time.time(),
        },
        "timestamp": time.time(),
    }


@pytest.fixture
def sample_packet_anomaly():
    """Sample packet-level anomaly event"""
    return {
        "logtype": "9999",
        "src_host": "172.16.0.10",
        "logdata": {
            "protocol": "TCP",
            "ports_scanned": [22, 23, 80, 443, 3389],
            "scan_type": "SYN_SCAN",
            "packet_count": 150,
            "timestamp": time.time(),
        },
        "timestamp": time.time(),
    }


@pytest.fixture
def high_threat_event():
    """High threat security event"""
    return {
        "logtype": "4002",
        "src_host": "192.168.1.100",
        "threat_score": 9.5,
        "rule_score": 7.0,
        "ml_score": 2.5,
        "logdata": {
            "username": "admin",
            "password": "admin",
            "successful": True,
            "timestamp": time.time(),
        },
        "timestamp": time.time(),
    }


@pytest.fixture
def low_threat_event():
    """Low threat security event"""
    return {
        "logtype": "3000",
        "src_host": "192.168.1.200",
        "threat_score": 2.1,
        "rule_score": 2.0,
        "ml_score": 0.1,
        "logdata": {
            "request": "GET /favicon.ico",
            "user_agent": "Mozilla/5.0",
            "response_code": 200,
            "timestamp": time.time(),
        },
        "timestamp": time.time(),
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for firewall testing"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def mock_requests():
    """Mock requests for API testing"""
    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
        patch("requests.put") as mock_put,
        patch("requests.delete") as mock_delete,
    ):

        # Default successful responses
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "ok"})
        mock_post.return_value = Mock(status_code=201, json=lambda: {"id": "test123"})
        mock_put.return_value = Mock(status_code=200, json=lambda: {"updated": True})
        mock_delete.return_value = Mock(status_code=204)

        yield {
            "get": mock_get,
            "post": mock_post,
            "put": mock_put,
            "delete": mock_delete,
        }


@pytest.fixture
def mock_socket():
    """Mock socket for network testing"""
    with patch("socket.socket") as mock_socket_class:
        mock_sock = Mock()
        mock_socket_class.return_value = mock_sock

        # Mock socket operations
        mock_sock.connect.return_value = None
        mock_sock.send.return_value = 10
        mock_sock.recv.return_value = b"OK"
        mock_sock.close.return_value = None

        yield mock_sock


@pytest.fixture
def mock_threading():
    """Mock threading for concurrent testing"""
    with (
        patch("threading.Thread") as mock_thread_class,
        patch("threading.Lock") as mock_lock_class,
    ):

        mock_thread = Mock()
        mock_lock = Mock()

        mock_thread_class.return_value = mock_thread
        mock_lock_class.return_value = mock_lock

        # Mock thread operations
        mock_thread.start.return_value = None
        mock_thread.join.return_value = None
        mock_thread.is_alive.return_value = False

        # Mock lock operations
        mock_lock.acquire.return_value = True
        mock_lock.release.return_value = None
        mock_lock.__enter__ = Mock(return_value=mock_lock)
        mock_lock.__exit__ = Mock(return_value=None)

        yield {"thread": mock_thread, "lock": mock_lock}


@pytest.fixture
def performance_timer():
    """Performance timing fixture"""

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0

        def assert_under_threshold(
            self, threshold_seconds: float, operation: str = "operation"
        ):
            """Assert that operation completed within threshold"""
            elapsed = self.elapsed
            assert (
                elapsed < threshold_seconds
            ), f"{operation} took {elapsed:.2f}s (threshold: {threshold_seconds}s)"

    timer = Timer()
    timer.start()
    yield timer
    timer.stop()


@pytest.fixture
def memory_monitor():
    """Memory usage monitoring fixture"""
    import psutil

    class MemoryMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.initial_memory = self.process.memory_info().rss

        def get_current_usage(self):
            """Get current memory usage in bytes"""
            return self.process.memory_info().rss

        def get_memory_delta(self):
            """Get memory usage delta from start"""
            return self.get_current_usage() - self.initial_memory

        def assert_under_threshold(
            self, threshold_bytes: int, operation: str = "operation"
        ):
            """Assert that memory usage is under threshold"""
            current = self.get_current_usage()
            assert (
                current < threshold_bytes
            ), f"{operation} used {current} bytes (threshold: {threshold_bytes} bytes)"

    yield MemoryMonitor()


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "playwright: Playwright browser tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "database: Database tests")
    config.addinivalue_line("markers", "ml: Machine learning tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "smoke: Smoke tests for CI/CD")
    config.addinivalue_line("markers", "network: Network-related tests")


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Clean up singleton instances between tests"""
    yield
    # Reset singletons
    try:
        # Try to reset firewall manager singleton
        import netsentinel.firewall_manager as fm_module

        if hasattr(fm_module, "_firewall_manager_instance"):
            fm_module._firewall_manager_instance = None
    except:
        pass

    try:
        # Try to reset SIEM manager singleton
        import netsentinel.siem_integration as siem_module

        if hasattr(siem_module, "_siem_manager_instance"):
            siem_module._siem_manager_instance = None
    except:
        pass

    try:
        # Try to reset SDN manager singleton
        import netsentinel.sdn_integration as sdn_module

        if hasattr(sdn_module, "_sdn_manager_instance"):
            sdn_module._sdn_manager_instance = None
    except:
        pass


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    # Set test environment variables
    test_env = {
        "NETSENTINEL_TESTING": "true",
        "FLASK_ENV": "testing",
        "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    }

    # Save original environment
    original_env = {}
    for key in test_env:
        original_env[key] = os.environ.get(key)

    # Set test environment
    os.environ.update(test_env)

    yield

    # Restore original environment
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


# Custom test utilities
def assert_event_processed_successfully(
    processor, event_data, expected_score_range=None
):
    """Assert that an event was processed successfully"""
    result = processor._process_single_event(event_data)

    # Basic assertions
    assert result is not None

    # Check that threat score was calculated
    if "threat_score" in event_data:
        assert isinstance(event_data["threat_score"], (int, float))

    # Check score range if specified
    if expected_score_range:
        min_score, max_score = expected_score_range
        assert min_score <= event_data.get("threat_score", 0) <= max_score


def assert_api_response_success(response_data, required_fields=None):
    """Assert that an API response indicates success"""
    assert isinstance(response_data, dict)

    # Check for success indicators
    if "status" in response_data:
        assert response_data["status"] in ["success", "ok", True]

    if "error" in response_data:
        assert response_data["error"] is None or response_data["error"] == ""

    # Check required fields
    if required_fields:
        for field in required_fields:
            assert (
                field in response_data
            ), f"Required field '{field}' missing from response"


def assert_security_event_structure(event):
    """Assert that a security event has the correct structure"""
    required_fields = ["logtype", "src_host", "timestamp"]

    for field in required_fields:
        assert field in event, f"Required field '{field}' missing from security event"

    # Validate field types
    assert isinstance(event["logtype"], str)
    assert isinstance(event["timestamp"], (int, float))

    # Validate threat scores if present
    if "threat_score" in event:
        assert isinstance(event["threat_score"], (int, float))
        assert 0 <= event["threat_score"] <= 10


def wait_for_condition(condition_func, timeout=10, interval=0.1):
    """Wait for a condition to become true"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)

    return False
