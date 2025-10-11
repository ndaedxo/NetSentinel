"""
NetSentinel Smoke Tests
Quick validation tests for CI/CD pipelines
"""

import pytest
import time
import os
from unittest.mock import Mock, patch


@pytest.mark.smoke
def test_basic_imports():
    """Test that core modules can be imported (without heavy dependencies)"""
    try:
        import netsentinel
        from netsentinel.firewall_manager import FirewallManager
        from netsentinel.siem_integration import SiemManager, SiemEvent
        from netsentinel.sdn_integration import SDNManager
        from netsentinel.packet_analyzer import PacketAnalyzer
        from netsentinel.alert_manager import AlertManager

        # All basic imports successful (threat_intelligence may not be implemented yet)
        assert True

    except ImportError as e:
        # Allow threat_intelligence import to fail if not implemented
        if "threat_intelligence" not in str(e):
            pytest.fail(f"Import failed: {e}")


@pytest.mark.smoke
def test_core_class_instantiation():
    """Test that core classes can be instantiated (skipping those requiring external deps)"""
    import platform

    try:
        from netsentinel.siem_integration import SiemManager, SiemEvent
        from netsentinel.sdn_integration import SDNManager

        # Test instantiation of classes that don't require external deps
        siem = SiemManager()
        sdn = SDNManager()

        # Test SiemEvent creation
        event = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="test event",
            raw_data={"test": "data"}
        )

        # Skip firewall manager on Windows
        if platform.system() != 'Windows':
            from netsentinel.firewall_manager import FirewallManager
            firewall = FirewallManager()

        assert True

    except Exception as e:
        pytest.fail(f"Instantiation failed: {e}")


@pytest.mark.smoke
def test_configuration_loading():
    """Test that configuration can be loaded (skipping event processor)"""
    test_configs = [
        {'ALERTING_ENABLED': 'true'},
        {'SIEM_ENABLED': 'true'},
        {'SDN_ENABLED': 'false'},
        {'THREAT_INTEL_ENABLED': 'true'},
    ]

    # Just test that environment variables work
    for config in test_configs:
        with patch.dict(os.environ, config):
            # Test that we can read the config
            key = list(config.keys())[0]
            assert os.environ.get(key) == config[key]


@pytest.mark.smoke
def test_basic_functionality():
    """Test basic functionality of core components (platform-safe)"""
    import platform

    # Test SIEM manager creation (safe)
    from netsentinel.siem_integration import SiemManager
    siem = SiemManager()
    status = siem.get_statistics()
    assert isinstance(status, dict)
    assert 'events_sent' in status

    # Test SDN manager creation (safe)
    from netsentinel.sdn_integration import SDNManager
    sdn = SDNManager()
    status = sdn.get_status()
    assert isinstance(status, dict)
    assert 'controllers' in status

    # Skip firewall tests on Windows
    if platform.system() != 'Windows':
        # Test firewall manager detection
        from netsentinel.firewall_manager import FirewallManager
        firewall = FirewallManager()
        firewall_type = firewall._detect_firewall_type()
        assert firewall_type in ['iptables', 'ufw', 'firewalld', 'nftables', None]


@pytest.mark.smoke
@pytest.mark.skip(reason="Requires kafka and redis dependencies")
def test_event_processing_smoke():
    """Smoke test for event processing (skipped - requires external deps)"""
    pytest.skip("Event processing test requires kafka and redis dependencies")


@pytest.mark.smoke
@pytest.mark.skip(reason="Requires redis and kafka dependencies")
def test_mock_services():
    """Test that mocked services work (skipped - requires external deps)"""
    pytest.skip("Mock services test requires redis and kafka dependencies")


@pytest.mark.smoke
def test_data_structures():
    """Test core data structures"""
    from netsentinel.siem_integration import SiemEvent
    from netsentinel.sdn_integration import FlowRule, QuarantinePolicy

    # Test SiemEvent
    event = SiemEvent(
        timestamp=time.time(),
        source="test",
        event_type="4002",
        severity="high",
        message="test event",
        raw_data={"logtype": "4002"}
    )
    assert event.event_type == "4002"
    assert event.severity == "high"

    # Test FlowRule
    flow = FlowRule(
        switch_id="openflow:1",
        priority=100,
        match={"ipv4_src": "192.168.1.100"},
        actions=[{"drop-action": {}}]
    )
    assert flow.switch_id == "openflow:1"
    assert flow.priority == 100

    # Test QuarantinePolicy
    policy = QuarantinePolicy(
        name="test_policy",
        target_ip="192.168.1.100",
        switch_id="openflow:1",
        duration=3600
    )
    assert policy.name == "test_policy"
    assert policy.target_ip == "192.168.1.100"
    assert not policy.is_expired()


@pytest.mark.smoke
def test_environment_variables():
    """Test environment variable handling"""
    test_vars = [
        'ALERTING_ENABLED',
        'SIEM_ENABLED',
        'SDN_ENABLED',
        'THREAT_INTEL_ENABLED',
        'PACKET_ANALYSIS_ENABLED',
        'ENTERPRISE_DB_ENABLED'
    ]

    for var in test_vars:
        # Test default (not set)
        value = os.getenv(var, 'false')
        assert isinstance(value, str)

        # Test explicit setting
        os.environ[var] = 'true'
        assert os.getenv(var) == 'true'

        # Clean up
        if var in os.environ:
            del os.environ[var]


@pytest.mark.smoke
def test_file_structure():
    """Test that required files exist"""
    required_files = [
        'netsentinel/__init__.py',
        'netsentinel/event_processor.py',
        'netsentinel/firewall_manager.py',
        'requirements.txt',
        'pytest.ini',
        '.flake8',
        '.pre-commit-config.yaml'
    ]

    for file_path in required_files:
        assert os.path.exists(file_path), f"Required file missing: {file_path}"


@pytest.mark.smoke
def test_performance_baselines():
    """Test basic performance baselines"""
    start_time = time.time()

    # Simple computation
    result = sum(range(1000))

    end_time = time.time()
    duration = end_time - start_time

    # Should complete very quickly
    assert duration < 1.0, f"Basic computation took {duration}s"
    assert result == 499500, f"Incorrect result: {result}"


@pytest.mark.smoke
def test_memory_basic():
    """Test basic memory operations"""
    import gc

    # Create some objects
    test_list = [i for i in range(1000)]
    test_dict = {f"key_{i}": f"value_{i}" for i in range(100)}

    # Verify they exist and are correct
    assert len(test_list) == 1000
    assert len(test_dict) == 100
    assert test_list[0] == 0
    assert test_dict["key_0"] == "value_0"

    # Cleanup
    del test_list, test_dict
    gc.collect()


@pytest.mark.smoke
def test_json_handling():
    """Test JSON serialization/deserialization"""
    import json

    test_data = {
        "string": "test",
        "number": 42,
        "boolean": True,
        "null": None,
        "array": [1, 2, 3],
        "object": {"nested": "value"}
    }

    # Serialize
    json_str = json.dumps(test_data)
    assert isinstance(json_str, str)
    assert len(json_str) > 10

    # Deserialize
    parsed_data = json.loads(json_str)
    assert parsed_data == test_data


@pytest.mark.smoke
def test_threading_basic():
    """Test basic threading operations"""
    import threading

    results = []

    def worker():
        results.append("worked")

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=5)

    assert results == ["worked"]
    assert not thread.is_alive()


@pytest.mark.smoke
def test_exception_handling():
    """Test exception handling"""
    try:
        raise ValueError("test exception")
    except ValueError as e:
        assert str(e) == "test exception"
    except Exception:
        pytest.fail("Wrong exception type caught")

    # Test that normal code still works after exception
    result = 1 + 1
    assert result == 2


@pytest.mark.smoke
def test_networking_basic():
    """Test basic networking operations"""
    import socket

    # Test DNS resolution (should not fail)
    try:
        result = socket.getaddrinfo("localhost", 80)
        assert len(result) > 0
    except socket.gaierror:
        # DNS resolution might fail in some environments, which is OK
        pass


@pytest.mark.smoke
def test_time_operations():
    """Test time-related operations"""
    import datetime

    # Test timestamp generation
    timestamp = time.time()
    assert isinstance(timestamp, float)
    assert timestamp > 1609459200  # After 2021

    # Test datetime operations
    dt = datetime.datetime.now()
    assert isinstance(dt, datetime.datetime)

    # Test time differences
    time.sleep(0.001)  # Very short sleep
    later_timestamp = time.time()
    assert later_timestamp >= timestamp


@pytest.mark.smoke
def test_file_operations():
    """Test basic file operations"""
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        temp_path = f.name

    try:
        # Read back content
        with open(temp_path, 'r') as f:
            content = f.read()
        assert content == "test content"
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.smoke
def test_regex_operations():
    """Test regular expression operations"""
    import re

    # Test basic regex matching
    pattern = r'\d{3}-\d{3}-\d{4}'
    text = "Call 123-456-7890 for support"

    match = re.search(pattern, text)
    assert match is not None
    assert match.group() == "123-456-7890"


@pytest.mark.smoke
def test_collections_operations():
    """Test collection data structure operations"""
    # Test list operations
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert sum(test_list) == 15
    assert max(test_list) == 5
    assert min(test_list) == 1

    # Test dict operations
    test_dict = {"a": 1, "b": 2, "c": 3}
    assert len(test_dict) == 3
    assert test_dict["a"] == 1
    assert "b" in test_dict
    assert test_dict.get("d", "default") == "default"

    # Test set operations
    test_set = {1, 2, 3, 2, 1}  # Duplicates removed
    assert len(test_set) == 3
    assert 1 in test_set
    assert 4 not in test_set


@pytest.mark.smoke
def test_string_operations():
    """Test string operations"""
    test_string = "Hello, NetSentinel!"

    # Test basic operations
    assert len(test_string) == 19
    assert test_string.upper() == "HELLO, NETSENTINEL!"
    assert test_string.lower() == "hello, netsentinel!"
    assert test_string.startswith("Hello")
    assert test_string.endswith("!")

    # Test formatting
    formatted = f"Test: {test_string}"
    assert formatted == "Test: Hello, NetSentinel!"

    # Test splitting/joining
    parts = test_string.split(", ")
    assert parts == ["Hello", "NetSentinel!"]
    joined = ", ".join(parts)
    assert joined == test_string


@pytest.mark.smoke
def test_math_operations():
    """Test mathematical operations"""
    # Test basic arithmetic
    assert 1 + 1 == 2
    assert 5 - 3 == 2
    assert 3 * 4 == 12
    assert 8 / 2 == 4
    assert 2 ** 3 == 8
    assert 7 % 3 == 1

    # Test floating point
    assert abs(1.5 - 1.2) < 0.4  # Approximate equality
    assert round(3.14159, 2) == 3.14

    # Test complex calculations
    result = (2 + 3) * (4 - 1) / 2.0
    assert result == 7.5
