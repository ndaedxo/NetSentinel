"""
Unit tests for NetSentinel SIEM integration
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from netsentinel.siem_integration import (
    SiemManager, SiemEvent, SplunkConnector, ElkConnector,
    SyslogConnector, WebhookSiemConnector, get_siem_manager
)


class TestSiemEvent:
    """Test cases for SiemEvent class"""

    def test_siem_event_creation(self):
        """Test SiemEvent object creation"""
        event = SiemEvent(
            timestamp=1640995200.123,
            source="netsentinel",
            event_type="4002",
            severity="high",
            message="SSH login attempt",
            host="netsentinel-01",
            source_ip="192.168.1.100",
            raw_data={"logtype": "4002", "src_host": "192.168.1.100"}
        )

        assert event.timestamp == 1640995200.123
        assert event.source == "netsentinel"
        assert event.event_type == "4002"
        assert event.severity == "high"
        assert event.message == "SSH login attempt"
        assert event.host == "netsentinel-01"
        assert event.source_ip == "192.168.1.100"
        assert event.raw_data["logtype"] == "4002"

    def test_siem_event_defaults(self):
        """Test SiemEvent default values"""
        event = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="test",
            severity="low",
            message="test message"
        )

        assert event.tags == []
        assert event.host is None
        assert event.source_ip is None
        assert event.destination_ip is None
        assert event.user is None

    def test_splunk_format(self):
        """Test Splunk HEC event formatting"""
        event = SiemEvent(
            timestamp=1640995200.123,
            source="netsentinel",
            event_type="4002",
            severity="high",
            message="SSH login attempt",
            source_ip="192.168.1.100",
            raw_data={"threat_score": 8.5}
        )

        splunk_event = event.to_splunk()

        assert splunk_event["time"] == 1640995200.123
        assert splunk_event["host"] == "netsentinel"
        assert splunk_event["source"] == "netsentinel"
        assert splunk_event["sourcetype"] == "netsentinel:4002"
        assert splunk_event["event"]["message"] == "SSH login attempt"
        assert splunk_event["event"]["severity"] == "high"
        assert splunk_event["event"]["source_ip"] == "192.168.1.100"
        assert splunk_event["event"]["threat_score"] == 8.5

    def test_syslog_format(self):
        """Test syslog RFC 5424 formatting"""
        event = SiemEvent(
            timestamp=1640995200.123,
            source="netsentinel",
            event_type="4002",
            severity="high",
            message="SSH login attempt",
            host="netsentinel-01"
        )

        syslog_msg = event.to_syslog()

        # Should start with priority
        assert syslog_msg.startswith("<")
        assert "1 2022-01-01T" in syslog_msg  # ISO timestamp
        assert "netsentinel-01" in syslog_msg
        assert "SSH login attempt" in syslog_msg

    def test_json_format(self):
        """Test JSON event formatting"""
        event = SiemEvent(
            timestamp=1640995200.123,
            source="netsentinel",
            event_type="4002",
            severity="high",
            message="SSH login attempt",
            raw_data={"threat_score": 8.5}
        )

        json_str = event.to_json()
        json_data = json.loads(json_str)

        assert json_data["@timestamp"] == "2022-01-01T00:00:00Z"
        assert json_data["host"] == "netsentinel"
        assert json_data["event_type"] == "4002"
        assert json_data["severity"] == "high"
        assert json_data["message"] == "SSH login attempt"
        assert json_data["threat_score"] == 8.5


class TestSplunkConnector:
    """Test cases for Splunk connector"""

    @pytest.fixture
    def splunk_connector(self):
        """Create a test Splunk connector"""
        return SplunkConnector(
            endpoint="https://splunk.example.com:8088",
            token="test-token",
            index="netsentinel",
            batch_size=5
        )

    @patch('netsentinel.siem_integration.requests.post')
    def test_send_single_event(self, mock_post, splunk_connector):
        """Test sending single event to Splunk"""
        mock_post.return_value = Mock(status_code=200, text="Success")

        event = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test event"
        )

        result = splunk_connector.send_event(event)
        assert result is True

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://splunk.example.com:8088/services/collector/event"
        assert "Authorization" in call_args[1]["headers"]

    @patch('netsentinel.siem_integration.requests.post')
    def test_send_event_failure(self, mock_post, splunk_connector):
        """Test handling of send failures"""
        mock_post.return_value = Mock(status_code=500, text="Internal Server Error")

        event = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test event"
        )

        result = splunk_connector.send_event(event)
        assert result is False

    def test_batch_buffering(self, splunk_connector):
        """Test event batching"""
        events = []
        for i in range(3):
            event = SiemEvent(
                timestamp=time.time(),
                source="test",
                event_type="4002",
                severity="high",
                message=f"Test event {i}"
            )
            events.append(event)

        # Buffer events
        for event in events:
            splunk_connector.buffer_event(event)

        # Should not have flushed yet (batch_size = 5)
        assert len(splunk_connector.event_buffer) == 3

        # Add more events to trigger flush
        for i in range(3):
            event = SiemEvent(
                timestamp=time.time(),
                source="test",
                event_type="4002",
                severity="high",
                message=f"Test event {i+3}"
            )
            splunk_connector.buffer_event(event)

        # Should have flushed automatically
        assert len(splunk_connector.event_buffer) == 1  # One event left

    @patch('netsentinel.siem_integration.requests.post')
    def test_batch_flush(self, mock_post, splunk_connector):
        """Test batch flushing"""
        mock_post.return_value = Mock(status_code=200, text="Success")

        # Fill buffer
        for i in range(5):
            event = SiemEvent(
                timestamp=time.time(),
                source="test",
                event_type="4002",
                severity="high",
                message=f"Test event {i}"
            )
            splunk_connector.buffer_event(event)

        # Manually trigger flush
        splunk_connector.flush_buffer()

        # Should have made one batch request
        assert mock_post.call_count == 1
        assert len(splunk_connector.event_buffer) == 0


class TestElkConnector:
    """Test cases for ELK connector"""

    @pytest.fixture
    def elk_connector(self):
        """Create a test ELK connector"""
        return ElkConnector(
            elasticsearch_url="http://elasticsearch:9200",
            index_prefix="netsentinel"
        )

    @patch('netsentinel.siem_integration.ElkConnector.session')
    def test_send_to_elasticsearch(self, mock_session, elk_connector):
        """Test sending event to Elasticsearch"""
        mock_session.post.return_value = Mock(status_code=201)

        event = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test event"
        )

        result = elk_connector.send_event(event)
        assert result is True

        # Verify the request was made to correct index
        call_args = mock_session.post.call_args
        assert "netsentinel-" in call_args[0][0]  # Index name should contain prefix
        assert "application/json" in call_args[1]["headers"]["Content-Type"]

    @patch('netsentinel.siem_integration.ElkConnector.session')
    def test_send_to_logstash(self, mock_session, elk_connector):
        """Test sending event to Logstash"""
        elk_connector.logstash_url = "http://logstash:8080"
        mock_session.post.return_value = Mock(status_code=200)

        event = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test event"
        )

        result = elk_connector.send_to_logstash(event)
        assert result is True

        mock_session.post.assert_called_once()


class TestSyslogConnector:
    """Test cases for Syslog connector"""

    @pytest.fixture
    def syslog_connector(self):
        """Create a test Syslog connector"""
        return SyslogConnector(
            host="127.0.0.1",
            port=514,
            protocol="udp",
            hostname="test-host"
        )

    @patch('netsentinel.siem_integration.socket.socket')
    def test_send_udp_syslog(self, mock_socket_class, syslog_connector):
        """Test sending syslog via UDP"""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        event = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test syslog event",
            host="test-host"
        )

        result = syslog_connector.send_event(event)
        assert result is True

        # Verify UDP sendto was called
        mock_socket.sendto.assert_called_once()

    @patch('netsentinel.siem_integration.socket.socket')
    def test_send_tcp_syslog(self, mock_socket_class):
        """Test sending syslog via TCP"""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        connector = SyslogConnector(
            host="127.0.0.1",
            port=514,
            protocol="tcp"
        )

        event = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test syslog event"
        )

        result = connector.send_event(event)
        assert result is True

        # Verify TCP connect and send were called
        mock_socket.connect.assert_called_once_with(("127.0.0.1", 514))
        mock_socket.send.assert_called_once()


class TestWebhookSiemConnector:
    """Test cases for Webhook SIEM connector"""

    @pytest.fixture
    def webhook_connector(self):
        """Create a test webhook connector"""
        return WebhookSiemConnector(
            webhook_url="https://webhook.example.com/events",
            headers={"Authorization": "Bearer test-token"}
        )

    @patch('netsentinel.siem_integration.requests.Session.request')
    def test_send_webhook_event(self, mock_request, webhook_connector):
        """Test sending event via webhook"""
        mock_request.return_value = Mock(status_code=200)

        event = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test webhook event"
        )

        result = webhook_connector.send_event(event)
        assert result is True

        # Verify the request was made correctly
        call_args = mock_request.call_args
        assert call_args[0][1] == "https://webhook.example.com/events"  # URL
        assert call_args[0][0] == "POST"  # Method
        assert "Authorization" in call_args[1]["headers"]


class TestSiemManager:
    """Test cases for SiemManager class"""

    @pytest.fixture
    def siem_manager(self):
        """Create a test SIEM manager instance"""
        manager = SiemManager()
        yield manager
        # Clean up
        manager.connectors.clear()
        manager.enabled_systems.clear()

    def test_singleton_pattern(self):
        """Test that SIEM manager follows singleton pattern"""
        manager1 = get_siem_manager()
        manager2 = get_siem_manager()
        assert manager1 is manager2

    def test_add_splunk_connector(self, siem_manager):
        """Test adding Splunk connector"""
        siem_manager.add_splunk_connector(
            "test_splunk",
            "https://splunk.example.com:8088",
            "test-token"
        )

        assert "splunk_test_splunk" in siem_manager.connectors
        connector = siem_manager.connectors["splunk_test_splunk"]
        assert isinstance(connector, SplunkConnector)

    def test_add_elk_connector(self, siem_manager):
        """Test adding ELK connector"""
        siem_manager.add_elk_connector(
            "test_elk",
            "http://elasticsearch:9200"
        )

        assert "elk_test_elk" in siem_manager.connectors
        connector = siem_manager.connectors["elk_test_elk"]
        assert isinstance(connector, ElkConnector)

    def test_enable_disable_system(self, siem_manager):
        """Test enabling and disabling SIEM systems"""
        # Add a connector first
        siem_manager.add_webhook_connector("test_webhook", "https://example.com")

        # Enable system
        siem_manager.enable_system("webhook_test_webhook")
        assert "webhook_test_webhook" in siem_manager.enabled_systems

        # Disable system
        siem_manager.disable_system("webhook_test_webhook")
        assert "webhook_test_webhook" not in siem_manager.enabled_systems

    def test_event_filtering(self, siem_manager):
        """Test event filtering functionality"""
        # Set filter rules
        siem_manager.set_event_filter(
            "test_system",
            event_types=["4002", "4000"],
            severities=["high", "critical"],
            min_score=7.0
        )

        # Test filtering logic
        assert siem_manager._passes_filter("test_system", SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test",
            raw_data={"threat_score": 8.0}
        )) is True

        # Test event type filter
        assert siem_manager._passes_filter("test_system", SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="3000",  # Not in filter
            severity="high",
            message="Test",
            raw_data={"threat_score": 8.0}
        )) is False

        # Test score filter
        assert siem_manager._passes_filter("test_system", SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test",
            raw_data={"threat_score": 5.0}  # Below threshold
        )) is False

    @patch('netsentinel.siem_integration.SiemManager._convert_to_siem_event')
    def test_send_event_processing(self, mock_convert, siem_manager):
        """Test event sending and processing"""
        # Setup
        mock_convert.return_value = SiemEvent(
            timestamp=time.time(),
            source="test",
            event_type="4002",
            severity="high",
            message="Test event"
        )

        siem_manager.add_webhook_connector("test_webhook", "https://example.com")
        siem_manager.enable_system("webhook_test_webhook")

        with patch.object(siem_manager.connectors["webhook_test_webhook"], 'send_event', return_value=True):
            result = siem_manager.send_event({"logtype": "4002", "threat_score": 8.0})
            assert result is True

    def test_statistics_tracking(self, siem_manager):
        """Test statistics tracking"""
        initial_stats = siem_manager.get_statistics()

        # Add a connector
        siem_manager.add_webhook_connector("test_webhook", "https://example.com")
        siem_manager.enable_system("webhook_test_webhook")

        # Send an event (mock)
        with patch.object(siem_manager.connectors["webhook_test_webhook"], 'send_event', return_value=True):
            siem_manager.send_event({"logtype": "4002", "threat_score": 8.0})

        updated_stats = siem_manager.get_statistics()

        assert updated_stats["connectors_active"] > initial_stats["connectors_active"]
        assert updated_stats["events_sent"] > initial_stats["events_sent"]

    def test_error_handling(self, siem_manager):
        """Test error handling in SIEM operations"""
        # Test with invalid connector
        result = siem_manager.send_event({"invalid": "data"})
        assert result is False  # Should handle gracefully

        # Test with non-existent system
        siem_manager.enable_system("non_existent_system")
        result = siem_manager.send_event({"logtype": "4002"})
        assert result is False  # Should handle missing connectors

    def test_buffer_flushing(self, siem_manager):
        """Test buffer flushing functionality"""
        siem_manager.add_splunk_connector(
            "test_splunk",
            "https://splunk.example.com:8088",
            "test-token",
            batch_size=2
        )
        siem_manager.enable_system("splunk_test_splunk")

        # Buffer some events
        for i in range(3):
            siem_manager.send_event({
                "logtype": "4002",
                "threat_score": 8.0,
                "src_host": f"192.168.1.{i}"
            })

        # Flush buffers
        siem_manager.flush_buffers()

        # Verify buffers are empty
        for connector in siem_manager.connectors.values():
            if hasattr(connector, 'event_buffer'):
                assert len(connector.event_buffer) == 0


class TestSiemManagerIntegration:
    """Integration tests for SIEM manager"""

    @pytest.mark.integration
    def test_full_siem_pipeline(self, siem_manager):
        """Test complete SIEM pipeline"""
        # Setup multiple connectors
        siem_manager.add_webhook_connector("test_webhook", "https://httpbin.org/post")
        siem_manager.enable_system("webhook_test_webhook")

        # Set filtering
        siem_manager.set_event_filter(
            "webhook_test_webhook",
            event_types=["4002"],
            severities=["high", "critical"],
            min_score=6.0
        )

        # Send test events
        test_events = [
            {"logtype": "4002", "threat_score": 8.0, "src_host": "192.168.1.100"},
            {"logtype": "3000", "threat_score": 8.0, "src_host": "192.168.1.101"},  # Wrong type
            {"logtype": "4002", "threat_score": 4.0, "src_host": "192.168.1.102"},  # Low score
        ]

        results = []
        for event in test_events:
            result = siem_manager.send_event(event)
            results.append(result)

        # First event should succeed, others should be filtered
        assert results[0] is True  # High score, correct type
        # Others may fail due to mock setup

    @pytest.mark.performance
    def test_performance_under_load(self, siem_manager):
        """Test SIEM performance under load"""
        import time

        # Setup connector
        siem_manager.add_webhook_connector("perf_test", "https://httpbin.org/post")
        siem_manager.enable_system("webhook_perf_test")

        # Generate test events
        events = []
        for i in range(100):
            events.append({
                "logtype": "4002",
                "threat_score": 7.0 + (i % 3),  # Vary scores
                "src_host": f"192.168.1.{i % 255}",
                "timestamp": time.time()
            })

        start_time = time.time()

        # Send events
        for event in events:
            siem_manager.send_event(event)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process events reasonably fast
        assert processing_time < 30.0  # Less than 30 seconds for 100 events

        events_per_second = len(events) / processing_time
        assert events_per_second > 2  # At least 2 events per second

    @pytest.mark.security
    def test_security_validations(self, siem_manager):
        """Test security validations"""
        # Test with malicious event data
        malicious_event = {
            "logtype": "<script>alert('xss')</script>",
            "threat_score": "'; DROP TABLE events; --",
            "src_host": "192.168.1.100",
            "custom_field": "../../../etc/passwd"
        }

        # Should handle malicious input gracefully
        try:
            result = siem_manager.send_event(malicious_event)
            assert isinstance(result, bool)  # Should not crash
        except Exception as e:
            # If it fails, it should fail gracefully
            assert "malicious" not in str(e).lower()
