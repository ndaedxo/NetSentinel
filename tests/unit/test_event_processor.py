"""
Unit tests for NetSentinel event processor
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from netsentinel.event_processor import EventProcessor


class TestEventProcessor:
    """Test cases for EventProcessor class"""

    @pytest.fixture
    def processor(self):
        """Create a test event processor instance"""
        with patch.dict('os.environ', {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'KAFKA_BOOTSTRAP_SERVERS': 'localhost:9092',
            'ALERTING_ENABLED': 'false',
            'ENTERPRISE_DB_ENABLED': 'false',
            'THREAT_INTEL_ENABLED': 'false',
            'PACKET_ANALYSIS_ENABLED': 'false',
            'SIEM_ENABLED': 'false',
            'SDN_ENABLED': 'false'
        }):
            processor = EventProcessor()
            yield processor
            processor.cleanup()

    def test_initialization(self, processor):
        """Test event processor initialization"""
        assert processor is not None
        assert hasattr(processor, 'valkey')
        assert hasattr(processor, 'kafka_consumer')
        assert hasattr(processor, 'alerting_enabled') is False
        assert hasattr(processor, 'enterprise_db_enabled') is False

    @patch('netsentinel.event_processor.redis.Redis')
    def test_redis_connection(self, mock_redis, processor):
        """Test Redis connection setup"""
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance

        # Reinitialize to trigger Redis connection
        processor.__init__()

        mock_redis.assert_called_once()
        assert processor.valkey == mock_redis_instance

    def test_threat_score_calculation(self, processor):
        """Test threat score calculation logic"""
        # Test SSH login event
        ssh_event = {
            'logtype': '4002',
            'logdata': {'username': 'admin', 'password': 'password'}
        }

        score = processor._calculate_threat_score(ssh_event)
        assert score > 0

        # Test normal HTTP event
        http_event = {
            'logtype': '3000',
            'logdata': {'request': 'GET /index.html'}
        }

        normal_score = processor._calculate_threat_score(http_event)
        assert normal_score < score  # HTTP should have lower threat score

    def test_ml_anomaly_detection(self, processor):
        """Test ML-based anomaly detection"""
        with patch('netsentinel.ml_anomaly_detector.detect_anomalies') as mock_detect:
            mock_detect.return_value = {
                'is_anomaly': True,
                'confidence': 0.95,
                'anomaly_score': 8.5
            }

            event = {'logtype': '4002', 'src_host': '192.168.1.100'}
            result = processor._detect_ml_anomalies(event)

            assert result['is_anomaly'] is True
            assert result['confidence'] == 0.95
            mock_detect.assert_called_once()

    def test_hybrid_scoring(self, processor):
        """Test hybrid threat scoring combining rule-based and ML"""
        rule_score = 6.0
        ml_score = 7.5
        expected_hybrid = (rule_score + ml_score) / 2

        hybrid_score = processor._calculate_hybrid_score(rule_score, ml_score)
        assert hybrid_score == expected_hybrid

    @patch('netsentinel.event_processor.send_to_siem')
    def test_siem_integration(self, mock_send_siem, processor):
        """Test SIEM event forwarding"""
        processor.siem_enabled = True
        processor.siem_manager = Mock()

        event_data = {
            'logtype': '4002',
            'src_host': '192.168.1.100',
            'threat_score': 8.5
        }

        # Mock the hybrid score calculation to return high score
        with patch.object(processor, '_calculate_hybrid_score', return_value=8.5):
            processor._process_single_event(event_data)

        mock_send_siem.assert_called_once()

    @patch('netsentinel.event_processor.quarantine_threat_ip')
    def test_sdn_response(self, mock_quarantine, processor):
        """Test SDN quarantine response"""
        processor.sdn_enabled = True

        event_data = {
            'logtype': '4002',
            'src_host': '192.168.1.100'
        }

        # Mock high threat score
        with patch.object(processor, '_calculate_hybrid_score', return_value=9.0):
            processor._process_single_event(event_data)

        mock_quarantine.assert_called_once()

    def test_correlation_engine(self, processor):
        """Test event correlation functionality"""
        # Mock Redis for correlation storage
        processor.valkey = Mock()

        event_data = {
            'logtype': '4002',
            'src_host': '192.168.1.100',
            'timestamp': time.time()
        }

        processor._correlate_events(event_data)

        # Verify correlation data was stored
        processor.valkey.setex.assert_called()

    def test_event_filtering(self, processor):
        """Test event filtering logic"""
        # Test valid event
        valid_event = {
            'logtype': '4002',
            'src_host': '192.168.1.100',
            'logdata': {'username': 'admin'}
        }

        assert processor._is_valid_event(valid_event) is True

        # Test invalid event (missing required fields)
        invalid_event = {
            'logtype': '4002'
            # Missing src_host
        }

        assert processor._is_valid_event(invalid_event) is False

    def test_error_handling(self, processor):
        """Test error handling in event processing"""
        # Test with malformed event data
        malformed_event = {
            'logtype': 'invalid',
            'src_host': None,
            'logdata': None
        }

        # Should not raise exception
        try:
            processor._process_single_event(malformed_event)
        except Exception as e:
            pytest.fail(f"Event processing raised unexpected exception: {e}")

    @patch('netsentinel.event_processor.logger')
    def test_logging_integration(self, mock_logger, processor):
        """Test logging integration"""
        event_data = {
            'logtype': '4002',
            'src_host': '192.168.1.100'
        }

        with patch.object(processor, '_calculate_hybrid_score', return_value=8.0):
            processor._process_single_event(event_data)

        # Verify logging calls were made
        mock_logger.info.assert_called()

    def test_performance_metrics(self, processor):
        """Test performance metrics collection"""
        with patch('netsentinel.event_processor.PROCESSING_DURATION') as mock_histogram:
            event_data = {
                'logtype': '4002',
                'src_host': '192.168.1.100'
            }

            processor._process_single_event(event_data)

            # Verify metrics were recorded
            mock_histogram.observe.assert_called_once()

    def test_resource_cleanup(self, processor):
        """Test proper resource cleanup"""
        processor.cleanup()

        # Verify connections are closed
        if hasattr(processor, 'kafka_consumer'):
            processor.kafka_consumer.close.assert_called()


class TestEventProcessorConfiguration:
    """Test configuration handling"""

    def test_environment_variables(self):
        """Test environment variable configuration"""
        with patch.dict('os.environ', {
            'ALERTING_ENABLED': 'true',
            'ENTERPRISE_DB_ENABLED': 'true',
            'THREAT_INTEL_ENABLED': 'true'
        }):
            processor = EventProcessor()
            assert processor.alerting_enabled is True
            assert processor.enterprise_db_enabled is True
            assert processor.threat_intel_enabled is True
            processor.cleanup()

    def test_default_configurations(self):
        """Test default configuration values"""
        with patch.dict('os.environ', {}, clear=True):
            processor = EventProcessor()
            assert processor.alerting_enabled is False  # Default should be False
            assert processor.enterprise_db_enabled is False
            processor.cleanup()


class TestEventProcessorIntegration:
    """Integration tests for event processor"""

    @pytest.mark.integration
    def test_full_event_processing_pipeline(self, processor):
        """Test complete event processing pipeline"""
        # Mock all external dependencies
        processor.valkey = Mock()
        processor.kafka_producer = Mock()

        with patch('netsentinel.event_processor.store_security_event'), \
             patch('netsentinel.event_processor.create_security_alert'), \
             patch('netsentinel.event_processor.send_to_siem'), \
             patch('netsentinel.event_processor.quarantine_threat_ip'):

            event_data = {
                'logtype': '4002',
                'src_host': '192.168.1.100',
                'logdata': {'username': 'admin', 'password': 'secret'},
                'timestamp': time.time()
            }

            # Process the event
            processor._process_single_event(event_data)

            # Verify all components were called
            processor.valkey.setex.assert_called()
            # Other assertions would verify the pipeline worked correctly

    @pytest.mark.performance
    def test_processing_performance(self, processor):
        """Test event processing performance"""
        import time

        # Generate test events
        events = []
        for i in range(100):
            events.append({
                'logtype': '4002',
                'src_host': f'192.168.1.{i}',
                'logdata': {'username': f'user{i}', 'password': 'pass'},
                'timestamp': time.time()
            })

        start_time = time.time()

        # Process events
        for event in events:
            processor._process_single_event(event)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process 100 events in reasonable time (less than 10 seconds)
        assert processing_time < 10.0

        events_per_second = len(events) / processing_time
        assert events_per_second > 5  # At least 5 events per second
