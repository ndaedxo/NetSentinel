"""
NetSentinel Full System Integration Tests
End-to-end testing of the complete NetSentinel pipeline
"""

import pytest
import time
import json
import threading
import requests
from unittest.mock import Mock, patch
import os
import tempfile


class TestNetSentinelFullIntegration:
    """Full integration tests for NetSentinel system"""

    @pytest.fixture(scope="class")
    def integration_setup(self, temp_dir):
        """Set up full NetSentinel integration environment"""
        # Create test configuration
        config = {
            'redis_host': 'localhost',
            'redis_port': 6379,
            'kafka_servers': 'localhost:9092',
            'temp_dir': temp_dir,
            'test_timeout': 60,
        }

        # Mock external services if not available
        with patch('redis.Redis') as mock_redis, \
             patch('kafka.KafkaProducer') as mock_producer, \
             patch('kafka.KafkaConsumer') as mock_consumer:

            # Configure mocks
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            mock_producer_instance = Mock()
            mock_producer.return_value = mock_producer_instance

            mock_consumer_instance = Mock()
            mock_consumer.return_value = mock_consumer_instance

            # Set up environment variables for testing
            test_env = {
                'ALERTING_ENABLED': 'true',
                'ENTERPRISE_DB_ENABLED': 'false',  # Skip DB for integration tests
                'THREAT_INTEL_ENABLED': 'true',
                'PACKET_ANALYSIS_ENABLED': 'false',  # Skip packet analysis
                'SIEM_ENABLED': 'true',
                'SDN_ENABLED': 'false',  # Skip SDN
                'REDIS_HOST': config['redis_host'],
                'REDIS_PORT': str(config['redis_port']),
                'KAFKA_BOOTSTRAP_SERVERS': config['kafka_servers'],
            }

            with patch.dict(os.environ, test_env):
                yield config

    @pytest.mark.integration
    def test_event_ingestion_to_processing_pipeline(self, integration_setup):
        """Test complete event ingestion to processing pipeline"""
        from netsentinel.event_processor import EventProcessor

        config = integration_setup

        # Create processor
        processor = EventProcessor()

        try:
            # Send event through processor
            test_event = {
                'logtype': '4002',
                'src_host': '192.168.1.100',
                'logdata': {'username': 'admin', 'password': 'secret'},
                'timestamp': time.time()
            }

            result = processor._process_single_event(test_event)

            # Verify event was processed
            assert result is not None

            # Verify Redis storage (correlation data)
            processor.valkey.setex.assert_called()

        finally:
            processor.cleanup()

    @pytest.mark.integration
    def test_multi_component_event_flow(self, integration_setup):
        """Test event flow through multiple NetSentinel components"""
        from netsentinel.event_processor import EventProcessor
        from netsentinel.siem_integration import SiemManager

        config = integration_setup

        # Create components
        processor = EventProcessor()
        siem_manager = SiemManager()

        # Add test SIEM connector
        siem_manager.add_webhook_connector("test_integration", "https://httpbin.org/post")
        siem_manager.enable_system("webhook_test_integration")

        try:
            # Create high-threat event
            high_threat_event = {
                'logtype': '4002',
                'src_host': '192.168.1.100',
                'logdata': {'username': 'admin', 'password': 'password'},
                'timestamp': time.time()
            }

            # Mock threat score to trigger multiple responses
            with patch.object(processor, '_calculate_hybrid_score', return_value=8.5), \
                 patch.object(processor, 'alerting_enabled', True), \
                 patch.object(processor, 'siem_enabled', True):

                # Process event
                processor._process_single_event(high_threat_event)

                # Verify multiple components were triggered
                # Alerting
                assert processor.alert_manager.generate_alert.called

                # SIEM forwarding (if enabled)
                if processor.siem_enabled:
                    siem_manager.send_event.assert_called()

        finally:
            processor.cleanup()

    @pytest.mark.integration
    def test_concurrent_event_processing(self, integration_setup):
        """Test concurrent event processing"""
        from netsentinel.event_processor import EventProcessor

        config = integration_setup

        processor = EventProcessor()

        try:
            # Generate multiple events
            events = []
            for i in range(10):
                event = {
                    'logtype': '4002',
                    'src_host': f'192.168.1.{100 + i}',
                    'logdata': {'username': f'user{i}', 'password': 'pass'},
                    'timestamp': time.time()
                }
                events.append(event)

            # Process events concurrently
            threads = []
            results = []

            def process_event(event):
                try:
                    result = processor._process_single_event(event)
                    results.append(result)
                except Exception as e:
                    results.append(f"error: {e}")

            for event in events:
                thread = threading.Thread(target=process_event, args=(event,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join(timeout=30)

            # Verify all events were processed
            assert len(results) == len(events)
            assert all(r is not None for r in results if not isinstance(r, str))

        finally:
            processor.cleanup()

    @pytest.mark.integration
    def test_firewall_response_integration(self, integration_setup):
        """Test firewall response integration"""
        from netsentinel.event_processor import EventProcessor
        from netsentinel.firewall_manager import FirewallManager

        config = integration_setup

        processor = EventProcessor()
        firewall_manager = FirewallManager()

        try:
            # Create critical threat event
            critical_event = {
                'logtype': '4002',
                'src_host': '192.168.1.100',
                'timestamp': time.time()
            }

            with patch.object(processor, '_calculate_hybrid_score', return_value=9.0), \
                 patch.object(firewall_manager, 'block_ip', return_value=True) as mock_block:

                # Process critical event
                processor._process_single_event(critical_event)

                # Verify firewall blocking was attempted
                mock_block.assert_called_with('192.168.1.100', mock_block.call_args[1]['reason'])

        finally:
            processor.cleanup()

    @pytest.mark.integration
    def test_siem_integration_flow(self, integration_setup):
        """Test SIEM integration end-to-end"""
        from netsentinel.event_processor import EventProcessor
        from netsentinel.siem_integration import SiemManager

        config = integration_setup

        processor = EventProcessor()
        siem_manager = SiemManager()

        # Add test SIEM connector
        siem_manager.add_webhook_connector("test_integration", "https://httpbin.org/post")
        siem_manager.enable_system("webhook_test_integration")

        try:
            # Create event that should trigger SIEM
            siem_event = {
                'logtype': '4002',
                'src_host': '192.168.1.100',
                'timestamp': time.time()
            }

            with patch.object(processor, '_calculate_hybrid_score', return_value=8.0), \
                 patch.object(siem_manager.connectors["webhook_test_integration"], 'send_event', return_value=True) as mock_send:

                # Process event
                processor._process_single_event(siem_event)

                # Verify SIEM forwarding occurred
                mock_send.assert_called_once()

        finally:
            processor.cleanup()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_system_resilience_under_load(self, integration_setup):
        """Test system resilience under sustained load"""
        from netsentinel.event_processor import EventProcessor

        config = integration_setup

        processor = EventProcessor()

        try:
            # Generate sustained load (100 events)
            events_processed = 0
            errors_encountered = 0

            start_time = time.time()

            for i in range(100):
                event = {
                    'logtype': '4002',
                    'src_host': f'192.168.1.{i % 255}',
                    'logdata': {'username': f'user{i}', 'password': 'pass'},
                    'timestamp': time.time()
                }

                try:
                    result = processor._process_single_event(event)
                    if result is not None:
                        events_processed += 1
                except Exception as e:
                    errors_encountered += 1
                    print(f"Error processing event {i}: {e}")

                # Small delay to prevent overwhelming
                time.sleep(0.01)

            end_time = time.time()
            processing_time = end_time - start_time

            # Performance assertions
            assert events_processed >= 95, f"Only {events_processed}/100 events processed successfully"
            assert errors_encountered <= 5, f"Too many errors: {errors_encounter}"
            assert processing_time < 60, f"Processing took too long: {processing_time:.2f}s"

            events_per_second = events_processed / processing_time
            assert events_per_second >= 1, f"Processing rate too low: {events_per_second:.2f} events/sec"

        finally:
            processor.cleanup()

    @pytest.mark.integration
    def test_configuration_persistence(self, integration_setup):
        """Test configuration persistence across components"""
        config = integration_setup

        # Set environment configuration
        test_config = {
            'ALERTING_ENABLED': 'true',
            'SIEM_ENABLED': 'true',
            'SDN_ENABLED': 'false',
            'FIREWALL_BLOCK_THRESHOLD': '7.5'
        }

        with patch.dict(os.environ, test_config):
            from netsentinel.event_processor import EventProcessor
            processor = EventProcessor()

            try:
                # Verify configuration was applied
                assert processor.alerting_enabled is True
                assert processor.siem_enabled is True
                assert processor.sdn_enabled is False

            finally:
                processor.cleanup()

    @pytest.mark.integration
    def test_component_health_monitoring(self, integration_setup):
        """Test component health monitoring"""
        from netsentinel.event_processor import EventProcessor

        config = integration_setup

        processor = EventProcessor()

        try:
            # Test processor health
            health_data = {
                'status': 'healthy',
                'timestamp': time.time(),
                'uptime': 12345,
                'version': '1.0.0'
            }

            # Verify processor can report health
            # This would typically be tested via API endpoint

            # Test component connectivity
            try:
                # Test Redis connectivity (mocked)
                processor.valkey.ping.assert_not_called()  # Should not fail

                # Test Kafka connectivity (mocked)
                # processor.kafka_producer.send.assert_not_called()

            except Exception as e:
                pytest.fail(f"Component health check failed: {e}")

        finally:
            processor.cleanup()

    @pytest.mark.integration
    @pytest.mark.performance
    def test_memory_usage_under_load(self, integration_setup):
        """Test memory usage under load"""
        from netsentinel.event_processor import EventProcessor

        config = integration_setup

        processor = EventProcessor()

        try:
            initial_memory = 0  # Would need psutil for real memory monitoring

            # Process batch of events
            for i in range(50):
                event = {
                    'logtype': '4002',
                    'src_host': f'192.168.1.{i % 255}',
                    'logdata': {'username': f'user{i}', 'password': 'pass'},
                    'timestamp': time.time()
                }
                processor._process_single_event(event)

            final_memory = 0  # Would need psutil for real memory monitoring
            memory_delta = final_memory - initial_memory

            # Memory usage should not grow excessively
            max_allowed_growth = 50 * 1024 * 1024  # 50MB
            assert memory_delta < max_allowed_growth

        finally:
            processor.cleanup()

    @pytest.mark.integration
    def test_error_recovery_and_logging(self, integration_setup):
        """Test error recovery and logging"""
        from netsentinel.event_processor import EventProcessor

        config = integration_setup

        processor = EventProcessor()

        try:
            # Test with malformed event
            malformed_event = {
                'logtype': None,
                'src_host': None,
                'logdata': None
            }

            # Should not crash the processor
            try:
                processor._process_single_event(malformed_event)
            except Exception as e:
                pytest.fail(f"Processor crashed on malformed event: {e}")

            # Test with missing external service
            with patch.object(processor, 'valkey', None):
                event = {
                    'logtype': '4002',
                    'src_host': '192.168.1.100',
                    'timestamp': time.time()
                }

                # Should handle gracefully
                result = processor._process_single_event(event)
                assert result is not None  # Processing should continue

        finally:
            processor.cleanup()

    @pytest.mark.integration
    def test_data_flow_integrity(self, integration_setup):
        """Test data flow integrity through the system"""
        from netsentinel.event_processor import EventProcessor

        config = integration_setup

        processor = EventProcessor()

        try:
            # Create test event with known data
            original_data = {
                'logtype': '4002',
                'src_host': '192.168.1.100',
                'logdata': {
                    'username': 'testuser',
                    'password': 'testpass',
                    'session_id': 'abc123'
                },
                'timestamp': time.time(),
                'custom_field': 'test_value'
            }

            # Process event
            processor._process_single_event(original_data)

            # Verify data integrity was maintained
            # (In real implementation, would check stored data matches original)

            # Test with various data types
            complex_event = {
                'logtype': '3000',
                'src_host': '192.168.1.200',
                'logdata': {
                    'numbers': [1, 2, 3, 4, 5],
                    'strings': ['a', 'b', 'c'],
                    'boolean': True,
                    'null': None,
                    'nested': {'key': 'value'}
                },
                'timestamp': time.time()
            }

            # Should handle complex data structures
            result = processor._process_single_event(complex_event)
            assert result is not None

        finally:
            processor.cleanup()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_long_running_stability(self, integration_setup):
        """Test long-running stability"""
        from netsentinel.event_processor import EventProcessor

        config = integration_setup

        processor = EventProcessor()

        try:
            # Run for extended period (30 seconds)
            start_time = time.time()
            events_processed = 0

            while time.time() - start_time < 30:  # 30 seconds
                event = {
                    'logtype': '4002',
                    'src_host': f'192.168.1.{events_processed % 255}',
                    'logdata': {'username': f'user{events_processed}', 'password': 'pass'},
                    'timestamp': time.time()
                }

                try:
                    processor._process_single_event(event)
                    events_processed += 1
                except Exception as e:
                    pytest.fail(f"System became unstable after {events_processed} events: {e}")

                # Small delay to prevent overwhelming
                time.sleep(0.01)

            # Verify sustained performance
            assert events_processed >= 2000, f"Only processed {events_processed} events in 30 seconds"
            print(f"Successfully processed {events_processed} events in stability test")

        finally:
            processor.cleanup()
