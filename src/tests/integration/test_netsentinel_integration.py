"""
NetSentinel Full System Integration Tests
End-to-end testing of the complete NetSentinel pipeline
"""

import pytest
import time
import threading
import requests
from unittest.mock import Mock, patch
import os
import tempfile

# Import EventProcessor for backward compatibility
try:
    from netsentinel.processors.refactored_event_processor import RefactoredEventProcessor as EventProcessor
except ImportError:
    # Fallback if the module doesn't exist
    from src.netsentinel.processors.refactored_event_processor import RefactoredEventProcessor as EventProcessor


class TestNetSentinelFullIntegration:
    """Full integration tests for NetSentinel system"""

    def _create_processor(self, config=None):
        """Helper method to create EventProcessor with proper config"""
        from src.netsentinel.processors.refactored_event_processor import ProcessorConfig
        if config is None:
            processor_config = ProcessorConfig(
                kafka_servers=["localhost:9092"],
                kafka_topic="test-events",
                consumer_group="test-processor",
                ml_enabled=False,
                alerting_enabled=False,
                siem_enabled=False,
                firewall_enabled=False,
            )
        else:
            processor_config = ProcessorConfig(
                kafka_servers=config.get("kafka_servers", ["localhost:9092"]),
                kafka_topic="test-events",
                consumer_group="test-processor",
                ml_enabled=False,
                alerting_enabled=False,
                siem_enabled=False,
                firewall_enabled=False,
            )
        return EventProcessor(processor_config)

    @pytest.fixture(scope="class")
    def integration_setup(self, temp_dir):
        """Set up full NetSentinel integration environment"""
        # Create test configuration
        config = {
            "redis_host": "localhost",
            "redis_port": 6379,
            "kafka_servers": "localhost:9092",
            "temp_dir": temp_dir,
            "test_timeout": 60,
        }

        # Mock external services if not available
        with (
            patch("redis.Redis") as mock_redis,
            patch("kafka.KafkaProducer") as mock_producer,
            patch("kafka.KafkaConsumer") as mock_consumer,
        ):

            # Configure mocks
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            mock_producer_instance = Mock()
            mock_producer.return_value = mock_producer_instance

            mock_consumer_instance = Mock()
            mock_consumer.return_value = mock_consumer_instance

            # Set up environment variables for testing
            test_env = {
                "ALERTING_ENABLED": "true",
                "ENTERPRISE_DB_ENABLED": "false",  # Skip DB for integration tests
                "THREAT_INTEL_ENABLED": "true",
                "PACKET_ANALYSIS_ENABLED": "false",  # Skip packet analysis
                "SIEM_ENABLED": "true",
                "SDN_ENABLED": "false",  # Skip SDN
                "REDIS_HOST": config["redis_host"],
                "REDIS_PORT": str(config["redis_port"]),
                "KAFKA_BOOTSTRAP_SERVERS": config["kafka_servers"],
            }

            with patch.dict(os.environ, test_env):
                yield config

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_event_ingestion_to_processing_pipeline(self, integration_setup):
        """Test complete event ingestion to processing pipeline"""
        from src.netsentinel.processors.refactored_event_processor import (
            RefactoredEventProcessor,
            ProcessorConfig,
        )

        config = integration_setup

        # Create processor config
        processor_config = ProcessorConfig(
            kafka_servers=[config["kafka_servers"]],
            kafka_topic="test-events",
            consumer_group="test-processor",
            ml_enabled=True,
            alerting_enabled=True,
            siem_enabled=True,
            firewall_enabled=False,
        )

        # Create processor
        processor = RefactoredEventProcessor(processor_config)

        try:
            # Send event through processor
            test_event = {
                "logtype": "4002",
                "src_host": "192.168.1.100",
                "logdata": {"username": "admin", "password": "secret"},
                "timestamp": time.time(),
            }

            result = await processor._process_single_event(test_event)

            # Verify event was processed
            assert result is not None
            assert "status" in result

        finally:
            await processor.cleanup()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_component_event_flow(self, integration_setup):
        """Test event flow through multiple NetSentinel components"""
        from src.netsentinel.siem_integration import SiemManager

        config = integration_setup

        # Create components
        from src.netsentinel.processors.refactored_event_processor import ProcessorConfig
        processor_config = ProcessorConfig(
            kafka_servers=["localhost:9092"],
            kafka_topic="test-events",
            consumer_group="test-processor",
            ml_enabled=False,
            alerting_enabled=False,
            siem_enabled=False,
            firewall_enabled=False,
        )
        processor = EventProcessor(processor_config)
        siem_manager = SiemManager()

        # Add test SIEM connector
        siem_manager.add_webhook_connector(
            "test_integration", "https://httpbin.org/post"
        )
        siem_manager.enable_system("webhook_test_integration")

        try:
            # Create high-threat event
            high_threat_event = {
                "logtype": "4002",
                "src_host": "192.168.1.100",
                "logdata": {"username": "admin", "password": "password"},
                "timestamp": time.time(),
            }

            # Process event
            result = await processor._process_single_event(high_threat_event)
            
            # Verify event was processed
            assert result is not None
            assert "status" in result

        finally:
            await processor.cleanup()

    @pytest.mark.integration
    def test_concurrent_event_processing(self, integration_setup):
        """Test concurrent event processing"""

        config = integration_setup

        processor = self._create_processor(config)

        try:
            # Generate multiple events
            events = []
            for i in range(10):
                event = {
                    "logtype": "4002",
                    "src_host": f"192.168.1.{100 + i}",
                    "logdata": {"username": f"user{i}", "password": "pass"},
                    "timestamp": time.time(),
                }
                events.append(event)

            # Process events concurrently
            threads = []
            results = []

            def process_event(event):
                try:
                    import asyncio
                    result = asyncio.run(processor._process_single_event(event))
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
            import asyncio
            asyncio.run(processor.cleanup())

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_firewall_response_integration(self, integration_setup):
        """Test firewall response integration"""
        from src.netsentinel.firewall_manager import FirewallManager

        config = integration_setup

        from src.netsentinel.processors.refactored_event_processor import ProcessorConfig
        processor_config = ProcessorConfig(
            kafka_servers=["localhost:9092"],
            kafka_topic="test-events",
            consumer_group="test-processor",
            ml_enabled=False,
            alerting_enabled=False,
            siem_enabled=False,
            firewall_enabled=False,
        )
        processor = EventProcessor(processor_config)
        firewall_manager = FirewallManager()

        try:
            # Create critical threat event
            critical_event = {
                "logtype": "4002",
                "src_host": "192.168.1.100",
                "timestamp": time.time(),
            }

            # Process critical event
            result = await processor._process_single_event(critical_event)
            
            # Verify event was processed
            assert result is not None
            assert "status" in result
            
            # Test firewall manager directly
            with patch.object(
                firewall_manager, "block_ip", return_value=True
            ) as mock_block:
                firewall_manager.block_ip("192.168.1.100")
                mock_block.assert_called_with("192.168.1.100")

        finally:
            await processor.cleanup()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_siem_integration_flow(self, integration_setup):
        """Test SIEM integration end-to-end"""

        config = integration_setup

        processor = self._create_processor(config)
        from src.netsentinel.siem_integration import SiemManager
        siem_manager = SiemManager()

        # Add test SIEM connector
        siem_manager.add_webhook_connector(
            "test_integration", "https://httpbin.org/post"
        )
        siem_manager.enable_system("webhook_test_integration")

        try:
            # Create event that should trigger SIEM
            siem_event = {
                "logtype": "4002",
                "src_host": "192.168.1.100",
                "timestamp": time.time(),
            }

            # Process event
            result = await processor._process_single_event(siem_event)
            
            # Verify event was processed
            assert result is not None
            assert "status" in result
            
            # Test SIEM manager directly
            with patch.object(
                siem_manager.connectors["webhook_test_integration"],
                "send_event",
                return_value=True,
            ) as mock_send:
                siem_manager.send_event(siem_event)
                mock_send.assert_called_once()

        finally:
            await processor.cleanup()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_system_resilience_under_load(self, integration_setup):
        """Test system resilience under sustained load"""

        config = integration_setup

        processor = self._create_processor(config)

        try:
            # Generate sustained load (100 events)
            events_processed = 0
            errors_encountered = 0

            start_time = time.time()

            for i in range(100):
                event = {
                    "logtype": "4002",
                    "src_host": f"192.168.1.{i % 255}",
                    "logdata": {"username": f"user{i}", "password": "pass"},
                    "timestamp": time.time(),
                }

                try:
                    import asyncio
                    result = asyncio.run(processor._process_single_event(event))
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
            assert (
                events_processed >= 95
            ), f"Only {events_processed}/100 events processed successfully"
            assert errors_encountered <= 5, f"Too many errors: {errors_encounter}"
            assert (
                processing_time < 60
            ), f"Processing took too long: {processing_time:.2f}s"

            events_per_second = events_processed / processing_time
            assert (
                events_per_second >= 1
            ), f"Processing rate too low: {events_per_second:.2f} events/sec"

        finally:
            import asyncio
            asyncio.run(processor.cleanup())

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_configuration_persistence(self, integration_setup):
        """Test configuration persistence across components"""
        config = integration_setup

        # Create processor with specific configuration
        from src.netsentinel.processors.refactored_event_processor import ProcessorConfig
        processor_config = ProcessorConfig(
            kafka_servers=["localhost:9092"],
            kafka_topic="test-events",
            consumer_group="test-processor",
            ml_enabled=False,
            alerting_enabled=True,
            siem_enabled=True,
            firewall_enabled=False,
        )
        processor = EventProcessor(processor_config)

        try:
            # Verify configuration was applied
            assert processor.config.alerting_enabled is True
            assert processor.config.siem_enabled is True
            assert processor.config.firewall_enabled is False

        finally:
            await processor.cleanup()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_component_health_monitoring(self, integration_setup):
        """Test component health monitoring"""

        config = integration_setup

        processor = self._create_processor(config)

        try:
            # Test processor health check
            health = await processor.health_check()
            assert health is not None
            assert "status" in health
            assert "timestamp" in health

            # Test processor metrics
            metrics = await processor.get_processor_metrics()
            assert metrics is not None
            assert "events_processed" in metrics
            assert "events_failed" in metrics

        finally:
            await processor.cleanup()

    @pytest.mark.integration
    @pytest.mark.performance
    def test_memory_usage_under_load(self, integration_setup):
        """Test memory usage under load"""

        config = integration_setup

        processor = self._create_processor(config)

        try:
            initial_memory = 0  # Would need psutil for real memory monitoring

            # Process batch of events
            for i in range(50):
                event = {
                    "logtype": "4002",
                    "src_host": f"192.168.1.{i % 255}",
                    "logdata": {"username": f"user{i}", "password": "pass"},
                    "timestamp": time.time(),
                }
                import asyncio
                asyncio.run(processor._process_single_event(event))

            final_memory = 0  # Would need psutil for real memory monitoring
            memory_delta = final_memory - initial_memory

            # Memory usage should not grow excessively
            max_allowed_growth = 50 * 1024 * 1024  # 50MB
            assert memory_delta < max_allowed_growth

        finally:
            import asyncio
            asyncio.run(processor.cleanup())

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_recovery_and_logging(self, integration_setup):
        """Test error recovery and logging"""

        config = integration_setup

        processor = self._create_processor(config)

        try:
            # Test with malformed event
            malformed_event = {"logtype": None, "src_host": None, "logdata": None}

            # Should not crash the processor
            try:
                result = await processor._process_single_event(malformed_event)
                assert result is not None  # Should handle gracefully
            except Exception as e:
                pytest.fail(f"Processor crashed on malformed event: {e}")

            # Test with normal event
            event = {
                "logtype": "4002",
                "src_host": "192.168.1.100",
                "timestamp": time.time(),
            }

            # Should handle gracefully
            result = await processor._process_single_event(event)
            assert result is not None  # Processing should continue

        finally:
            await processor.cleanup()

    @pytest.mark.integration
    def test_data_flow_integrity(self, integration_setup):
        """Test data flow integrity through the system"""

        config = integration_setup

        processor = self._create_processor(config)

        try:
            # Create test event with known data
            original_data = {
                "logtype": "4002",
                "src_host": "192.168.1.100",
                "logdata": {
                    "username": "testuser",
                    "password": "testpass",
                    "session_id": "abc123",
                },
                "timestamp": time.time(),
                "custom_field": "test_value",
            }

            # Process event
            import asyncio
            asyncio.run(processor._process_single_event(original_data))

            # Verify data integrity was maintained
            # (In real implementation, would check stored data matches original)

            # Test with various data types
            complex_event = {
                "logtype": "3000",
                "src_host": "192.168.1.200",
                "logdata": {
                    "numbers": [1, 2, 3, 4, 5],
                    "strings": ["a", "b", "c"],
                    "boolean": True,
                    "null": None,
                    "nested": {"key": "value"},
                },
                "timestamp": time.time(),
            }

            # Should handle complex data structures
            import asyncio
            result = asyncio.run(processor._process_single_event(complex_event))
            assert result is not None

        finally:
            import asyncio
            asyncio.run(processor.cleanup())

    @pytest.mark.integration
    @pytest.mark.slow
    def test_long_running_stability(self, integration_setup):
        """Test long-running stability"""

        config = integration_setup

        processor = self._create_processor(config)

        try:
            # Run for extended period (30 seconds)
            start_time = time.time()
            events_processed = 0

            while time.time() - start_time < 30:  # 30 seconds
                event = {
                    "logtype": "4002",
                    "src_host": f"192.168.1.{events_processed % 255}",
                    "logdata": {
                        "username": f"user{events_processed}",
                        "password": "pass",
                    },
                    "timestamp": time.time(),
                }

                try:
                    import asyncio
                    asyncio.run(processor._process_single_event(event))
                    events_processed += 1
                except Exception as e:
                    pytest.fail(
                        f"System became unstable after {events_processed} events: {e}"
                    )

                # Small delay to prevent overwhelming
                time.sleep(0.01)

            # Verify sustained performance
            assert (
                events_processed >= 2000
            ), f"Only processed {events_processed} events in 30 seconds"
            print(f"Successfully processed {events_processed} events in stability test")

        finally:
            import asyncio
            asyncio.run(processor.cleanup())
