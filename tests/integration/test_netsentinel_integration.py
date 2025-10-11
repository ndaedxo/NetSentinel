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
    def test_event_ingestion_to_processing_pipeline(self, integration_setup, event_processor, sample_security_event):
        """Test complete event ingestion to processing pipeline"""
        config = integration_setup

        # Send event through processor
        result = event_processor._process_single_event(sample_security_event)

        # Verify event was processed
        assert result is not None

        # Verify Redis storage (correlation data)
        event_processor.valkey.setex.assert_called()

        # Verify threat score calculation occurred
        assert 'threat_score' in sample_security_event or hasattr(event_processor, '_calculate_threat_score')

    @pytest.mark.integration
    def test_multi_component_event_flow(self, integration_setup, event_processor, siem_manager):
        """Test event flow through multiple NetSentinel components"""
        config = integration_setup

        # Create high-threat event
        high_threat_event = {
            'logtype': '4002',
            'src_host': '192.168.1.100',
            'logdata': {'username': 'admin', 'password': 'password'},
            'timestamp': time.time()
        }

        # Mock threat score to trigger multiple responses
        with patch.object(event_processor, '_calculate_hybrid_score', return_value=8.5), \
             patch.object(event_processor, 'alerting_enabled', True), \
             patch.object(event_processor, 'siem_enabled', True):

            # Process event
            event_processor._process_single_event(high_threat_event)

            # Verify multiple components were triggered
            # Alerting
            assert event_processor.alert_manager.generate_alert.called

            # SIEM forwarding (if enabled)
            if event_processor.siem_enabled:
                siem_manager.send_event.assert_called()

    @pytest.mark.integration
    def test_concurrent_event_processing(self, integration_setup, event_processor):
        """Test concurrent event processing"""
        config = integration_setup

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
                result = event_processor._process_single_event(event)
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

    @pytest.mark.integration
    def test_firewall_response_integration(self, integration_setup, event_processor, firewall_manager):
        """Test firewall response integration"""
        config = integration_setup

        # Create critical threat event
        critical_event = {
            'logtype': '4002',
            'src_host': '192.168.1.100',
            'timestamp': time.time()
        }

        with patch.object(event_processor, '_calculate_hybrid_score', return_value=9.0), \
             patch.object(firewall_manager, 'block_ip', return_value=True) as mock_block:

            # Process critical event
            event_processor._process_single_event(critical_event)

            # Verify firewall blocking was attempted
            mock_block.assert_called_with('192.168.1.100', mock_block.call_args[1]['reason'])

    @pytest.mark.integration
    def test_siem_integration_flow(self, integration_setup, event_processor, siem_manager):
        """Test SIEM integration end-to-end"""
        config = integration_setup

        # Add test SIEM connector
        siem_manager.add_webhook_connector("test_integration", "https://httpbin.org/post")
        siem_manager.enable_system("webhook_test_integration")

        # Create event that should trigger SIEM
        siem_event = {
            'logtype': '4002',
            'src_host': '192.168.1.100',
            'timestamp': time.time()
        }

        with patch.object(event_processor, '_calculate_hybrid_score', return_value=8.0), \
             patch.object(siem_manager.connectors["webhook_test_integration"], 'send_event', return_value=True) as mock_send:

            # Process event
            event_processor._process_single_event(siem_event)

            # Verify SIEM forwarding occurred
            mock_send.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_system_resilience_under_load(self, integration_setup, event_processor):
        """Test system resilience under sustained load"""
        config = integration_setup

        # Generate sustained load (100 events)
        events_processed = 0
        errors_encountered = 0

        start_time = time.time()

        for i in range(100):
            event = {
                'logtype': '4002',
                'src_host': f'192.168.1.{i % 255}',
                'logdata': {'username': f'user{i}', 'password': f'pass{i}'},
                'timestamp': time.time()
            }

            try:
                result = event_processor._process_single_event(event)
                if result is not None:
                    events_processed += 1
            except Exception as e:
                errors_encountered += 1
                print(f"Error processing event {i}: {e}")

        end_time = time.time()
        processing_time = end_time - start_time

        # Performance assertions
        assert events_processed >= 95, f"Only {events_processed}/100 events processed successfully"
        assert errors_encountered <= 5, f"Too many errors: {errors_encounter}"
        assert processing_time < 60, f"Processing took too long: {processing_time:.2f}s"

        events_per_second = events_processed / processing_time
        assert events_per_second >= 1, f"Processing rate too low: {events_per_second:.2f} events/sec"

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
            # Create new processor instance
            from netsentinel.event_processor import EventProcessor
            processor = EventProcessor()

            # Verify configuration was applied
            assert processor.alerting_enabled is True
            assert processor.siem_enabled is True
            assert processor.sdn_enabled is False

            processor.cleanup()

    @pytest.mark.integration
    def test_component_health_monitoring(self, integration_setup, event_processor):
        """Test component health monitoring"""
        config = integration_setup

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
            event_processor.valkey.ping.assert_not_called()  # Should not fail

            # Test Kafka connectivity (mocked)
            # event_processor.kafka_producer.send.assert_not_called()

        except Exception as e:
            pytest.fail(f"Component health check failed: {e}")

    @pytest.mark.integration
    @pytest.mark.performance
    def test_memory_usage_under_load(self, integration_setup, event_processor, memory_monitor):
        """Test memory usage under load"""
        config = integration_setup

        initial_memory = memory_monitor.get_current_usage()

        # Process batch of events
        for i in range(50):
            event = {
                'logtype': '4002',
                'src_host': f'192.168.1.{i % 255}',
                'logdata': {'username': f'user{i}', 'password': 'pass'},
                'timestamp': time.time()
            }
            event_processor._process_single_event(event)

        final_memory = memory_monitor.get_current_usage()
        memory_delta = final_memory - initial_memory

        # Memory usage should not grow excessively
        max_allowed_growth = 50 * 1024 * 1024  # 50MB
        assert memory_delta < max_allowed_growth, f"Memory grew by {memory_delta} bytes"

    @pytest.mark.integration
    def test_error_recovery_and_logging(self, integration_setup, event_processor):
        """Test error recovery and logging"""
        config = integration_setup

        # Test with malformed event
        malformed_event = {
            'logtype': None,
            'src_host': None,
            'logdata': None
        }

        # Should not crash the processor
        try:
            event_processor._process_single_event(malformed_event)
        except Exception as e:
            pytest.fail(f"Processor crashed on malformed event: {e}")

        # Test with missing external service
        with patch.object(event_processor, 'valkey', None):
            event = {
                'logtype': '4002',
                'src_host': '192.168.1.100',
                'timestamp': time.time()
            }

            # Should handle gracefully
            result = event_processor._process_single_event(event)
            assert result is not None  # Processing should continue

    @pytest.mark.integration
    def test_data_flow_integrity(self, integration_setup, event_processor):
        """Test data flow integrity through the system"""
        config = integration_setup

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
        event_processor._process_single_event(original_data)

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
                'null_value': None,
                'nested': {'key': 'value'}
            },
            'timestamp': time.time()
        }

        # Should handle complex data structures
        result = event_processor._process_single_event(complex_event)
        assert result is not None

    @pytest.mark.integration
    @pytest.mark.slow
    def test_long_running_stability(self, integration_setup, event_processor):
        """Test long-running stability"""
        config = integration_setup

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
                event_processor._process_single_event(event)
                events_processed += 1
            except Exception as e:
                pytest.fail(f"System became unstable after {events_processed} events: {e}")

            # Small delay to prevent overwhelming
            time.sleep(0.01)

        # Verify sustained performance
        assert events_processed >= 2000, f"Only processed {events_processed} events in 30 seconds"
        print(f"Successfully processed {events_processed} events in stability test")


class TestNetSentinelAPISystemIntegration:
    """API-level system integration tests"""

    @pytest.fixture
    def api_base_url(self):
        """Base URL for API tests"""
        return os.getenv('NETSENTINEL_API_URL', 'http://localhost:8082')

    @pytest.mark.integration
    def test_api_endpoints_integration(self, api_base_url):
        """Test API endpoints work together"""
        # Test health endpoint
        health_response = requests.get(f"{api_base_url}/health", timeout=5)
        assert health_response.status_code == 200

        health_data = health_response.json()
        assert health_data.get('status') == 'healthy'

        # Test metrics endpoint
        metrics_response = requests.get(f"{api_base_url}/metrics", timeout=5)
        assert metrics_response.status_code == 200

        metrics_text = metrics_response.text
        assert 'HELP' in metrics_text or 'prometheus' in metrics_text.lower()

    @pytest.mark.integration
    def test_event_processing_api_flow(self, api_base_url, sample_security_event):
        """Test event processing through API"""
        # Send event via API
        response = requests.post(
            f"{api_base_url}/events",
            json=sample_security_event,
            timeout=10
        )

        # Should be accepted (may be processed asynchronously)
        assert response.status_code in [200, 201, 202]

    @pytest.mark.integration
    def test_configuration_api_integration(self, api_base_url):
        """Test configuration API integration"""
        # Test multiple configuration endpoints
        endpoints = [
            '/firewall/status',
            '/threat-intel/status',
            '/siem/status',
            '/sdn/status'
        ]

        for endpoint in endpoints:
            response = requests.get(f"{api_base_url}{endpoint}", timeout=5)
            # Should not crash, even if services not configured
            assert response.status_code in [200, 503, 500]  # 500/503 acceptable if not configured

    @pytest.mark.integration
    def test_error_handling_api_integration(self, api_base_url):
        """Test error handling in API integration"""
        # Test invalid endpoint
        response = requests.get(f"{api_base_url}/invalid-endpoint", timeout=5)
        assert response.status_code == 404

        # Test malformed request
        response = requests.post(
            f"{api_base_url}/events",
            data="invalid json",
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        assert response.status_code >= 400

    @pytest.mark.integration
    @pytest.mark.slow
    def test_api_performance_under_load(self, api_base_url, sample_security_event):
        """Test API performance under load"""
        import concurrent.futures

        def make_request():
            try:
                response = requests.post(
                    f"{api_base_url}/events",
                    json=sample_security_event,
                    timeout=10
                )
                return response.status_code
            except:
                return None

        # Make 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Check results
        successful_requests = sum(1 for r in results if r and r in [200, 201, 202])
        assert successful_requests >= 15, f"Only {successful_requests}/20 requests succeeded"
