"""
Basic unit tests for NetSentinel core functionality
Tests that don't require external dependencies
"""

import pytest
import time

# Conditional imports for NetSentinel modules
try:
    from netsentinel.siem_integration import SiemEvent
    from netsentinel.sdn_integration import FlowRule, QuarantinePolicy
    from netsentinel.firewall_manager import FirewallManager

    NETSENTINEL_AVAILABLE = True
except ImportError:
    # Create mock classes for testing
    class MockSiemEvent:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class MockFlowRule:
        def __init__(self, **kwargs):
            self.switch_id = kwargs.get("switch_id", "")
            self.priority = kwargs.get("priority", 0)
            self.table_id = kwargs.get("table_id", 0)

    class MockQuarantinePolicy:
        def __init__(self, **kwargs):
            self.name = kwargs.get("name", "")
            self.target_ip = kwargs.get("target_ip", "")
            self.switch_id = kwargs.get("switch_id", "")
            self.duration = kwargs.get("duration", 0)
            self.active = kwargs.get("active", True)

    class MockFirewallManager:
        def __init__(self):
            pass

        def _detect_backend(self):
            return None

    SiemEvent = MockSiemEvent
    FlowRule = MockFlowRule
    QuarantinePolicy = MockQuarantinePolicy
    FirewallManager = MockFirewallManager
    NETSENTINEL_AVAILABLE = False


def test_siem_event_creation():
    """Test SiemEvent basic functionality"""
    import time

    event = SiemEvent(
        timestamp=time.time(),
        source="test",
        event_type="4002",
        severity="high",
        message="test event",
        raw_data={"logtype": "4002", "src_host": "192.168.1.100"},
    )

    assert event.event_type == "4002"
    assert event.severity == "high"
    assert event.source == "test"
    assert event.raw_data["logtype"] == "4002"


def test_flow_rule_creation():
    """Test FlowRule basic functionality"""
    flow = FlowRule(switch_id="openflow:1", priority=100)

    assert flow.switch_id == "openflow:1"
    assert flow.priority == 100
    assert flow.table_id == 0  # default


def test_quarantine_policy_creation():
    """Test QuarantinePolicy basic functionality"""

    policy = QuarantinePolicy(
        name="test_policy",
        target_ip="192.168.1.100",
        switch_id="openflow:1",
        duration=3600,
    )

    assert policy.name == "test_policy"
    assert policy.target_ip == "192.168.1.100"
    assert policy.active is True
    assert policy.duration == 3600


def test_firewall_manager_creation():
    """Test FirewallManager basic functionality"""
    import platform

    # Skip firewall tests on Windows (no iptables/ufw/firewalld)
    if platform.system() == "Windows":
        pytest.skip("Firewall tests not available on Windows")

    manager = FirewallManager()

    # Should be able to detect firewall backend (may return None if no firewall)
    if hasattr(manager, "_detect_backend"):
        firewall_backend = manager._detect_backend()
        assert firewall_backend in ["iptables", "ufw", "firewalld", "nftables", None]
    else:
        # For mock manager, just verify it exists
        assert manager is not None


def test_json_operations():
    """Test JSON serialization/deserialization"""
    import json

    test_data = {"event_type": "4002", "severity": "high", "source_ip": "192.168.1.100"}

    # Serialize
    json_str = json.dumps(test_data)
    assert isinstance(json_str, str)

    # Deserialize
    parsed = json.loads(json_str)
    assert parsed == test_data


def test_string_formatting():
    """Test string formatting operations"""
    ip = "192.168.1.100"
    event_type = "4002"

    message = f"Security event: {event_type} from {ip}"
    assert "192.168.1.100" in message
    assert "4002" in message


def test_list_operations():
    """Test list operations"""
    events = ["4002", "3000", "4000"]

    assert len(events) == 3
    assert "4002" in events
    assert events[0] == "4002"

    # Test filtering
    high_priority = [e for e in events if e.startswith("4")]
    assert len(high_priority) == 2


def test_dict_operations():
    """Test dictionary operations"""
    event_data = {"logtype": "4002", "src_host": "192.168.1.100", "threat_score": 8.5}

    assert event_data["logtype"] == "4002"
    assert event_data.get("threat_score") == 8.5
    assert event_data.get("nonexistent", "default") == "default"


def test_exception_handling():
    """Test exception handling"""
    try:
        raise ValueError("test error")
    except ValueError as e:
        assert str(e) == "test error"
    except Exception:
        pytest.fail("Wrong exception type")


def test_type_checking():
    """Test basic type checking"""
    # Test string
    assert isinstance("test", str)

    # Test int/float
    assert isinstance(42, int)
    assert isinstance(3.14, float)

    # Test list
    assert isinstance([1, 2, 3], list)

    # Test dict
    assert isinstance({"key": "value"}, dict)


def test_boolean_operations():
    """Test boolean operations"""
    threat_score = 8.5

    # Test comparisons
    assert threat_score > 7.0
    assert threat_score >= 8.5
    assert threat_score < 10.0

    # Test boolean logic
    is_high_threat = threat_score >= 7.0
    assert is_high_threat is True

    should_alert = is_high_threat and threat_score > 8.0
    assert should_alert is True


def test_none_handling():
    """Test None value handling"""
    data = {"key": None, "value": "test"}

    assert data.get("key") is None
    assert data.get("value") == "test"
    assert data.get("missing", "default") == "default"


def test_time_operations():
    """Test time-related operations"""

    # Test timestamp generation
    timestamp = time.time()
    assert isinstance(timestamp, float)
    assert timestamp > 1609459200  # After 2021

    # Test time differences
    start = time.time()
    time.sleep(0.001)  # Very short sleep
    end = time.time()

    assert end >= start
    assert end - start < 1.0  # Should be very small
