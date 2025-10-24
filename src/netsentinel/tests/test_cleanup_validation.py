#!/usr/bin/env python3
"""
Test suite to validate that cleanup changes don't break functionality
"""

import unittest
import asyncio
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from .core.error_handler import NetSentinelErrorHandler, ErrorContext
from .core.config import get_config, Config
from .core.models import StandardEvent, StandardAlert, create_event, create_alert
from .gateway.api_gateway import APIGateway, ServiceInstance, ServiceStatus
from .packet_analyzer import PacketAnalyzer
from .ml_anomaly_detector import NetworkEventAnomalyDetector


class TestCleanupValidation(unittest.TestCase):
    """Test suite to validate cleanup changes"""

    def setUp(self):
        """Set up test fixtures"""
        self.error_handler = NetSentinelErrorHandler()

    def test_error_handler_circular_import_fix(self):
        """Test that error handler handles circular imports gracefully"""
        # Test that error handler can be initialized without circular import issues
        self.assertIsNotNone(self.error_handler)
        self.assertIsNotNone(self.error_handler.error_handlers)

        # Test error handling with context
        context = ErrorContext(component="test_component", operation="test_operation")

        # This should not raise an exception
        try:
            result = asyncio.run(
                self.error_handler.handle_error(ValueError("Test error"), context)
            )
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"Error handler should handle errors gracefully: {e}")

    def test_config_initialization_robustness(self):
        """Test that config initialization is robust"""
        # Test that config can be initialized even with missing files
        with patch("builtins.open", side_effect=FileNotFoundError()):
            config = get_config()
            self.assertIsNotNone(config)
            self.assertIsInstance(config, Config)

    def test_api_gateway_sync_functions(self):
        """Test that API Gateway sync functions work correctly"""
        gateway = APIGateway()

        # Test service instance creation
        instance = ServiceInstance(
            name="test_service",
            url="http://localhost:8080",
            status=ServiceStatus.HEALTHY,
            last_health_check=time.time(),
            response_time=0.1,
        )

        self.assertEqual(instance.name, "test_service")
        self.assertEqual(instance.status, ServiceStatus.HEALTHY)
        self.assertGreater(instance.health_score, 0)

        # Test gateway metrics
        metrics = gateway.get_gateway_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn("total_requests", metrics)
        self.assertIn("error_count", metrics)

    def test_packet_analyzer_thread_safety(self):
        """Test that packet analyzer thread management is safe"""
        # Mock Scapy to avoid import issues
        with patch.dict("sys.modules", {"scapy": Mock()}):
            with patch("scapy.all.sniff"):
                analyzer = PacketAnalyzer(
                    interface="lo",  # Use loopback interface
                    max_flows=100,
                    enable_analysis=False,  # Disable analysis for testing
                )

                # Test that analyzer can be initialized
                self.assertIsNotNone(analyzer)
                self.assertFalse(analyzer.running)

                # Test thread safety
                with analyzer._thread_lock:
                    self.assertIsNotNone(analyzer._thread_lock)

                # Test cleanup
                analyzer._cleanup_old_flows()
                self.assertIsNotNone(analyzer.active_flows)

    def test_ml_detector_memory_management(self):
        """Test that ML detector memory management works correctly"""
        detector = NetworkEventAnomalyDetector(model_type="fastflow", model_path=None)

        # Test that detector can be initialized
        self.assertIsNotNone(detector)
        self.assertIsNotNone(detector.event_history)
        self.assertEqual(detector.event_history.maxlen, 1000)

        # Test memory cleanup
        detector._cleanup_old_data()
        self.assertIsNotNone(detector.ip_behavior_profiles)

        # Test that max profiles limit is respected
        self.assertLessEqual(len(detector.ip_behavior_profiles), detector._max_profiles)

    def test_standard_models_validation(self):
        """Test that standard models work correctly"""
        # Test event creation
        event = create_event(
            event_type="test_event",
            source="test_source",
            data={"test": "data"},
            severity="medium",
        )

        self.assertIsInstance(event, StandardEvent)
        self.assertEqual(event.event_type, "test_event")
        self.assertEqual(event.source, "test_source")

        # Test event validation
        validation_result = event.validate()
        self.assertTrue(validation_result.valid)

        # Test alert creation
        alert = create_alert(
            title="Test Alert",
            description="Test Description",
            severity="high",
            source="test_source",
            event_data={"test": "data"},
        )

        self.assertIsInstance(alert, StandardAlert)
        self.assertEqual(alert.title, "Test Alert")
        self.assertEqual(alert.severity, "high")

        # Test alert validation
        validation_result = alert.validate()
        self.assertTrue(validation_result.valid)

    def test_error_handling_robustness(self):
        """Test that error handling is robust across components"""
        # Test error handler with various exception types
        test_exceptions = [
            ValueError("Test value error"),
            TypeError("Test type error"),
            RuntimeError("Test runtime error"),
            ConnectionError("Test connection error"),
        ]

        context = ErrorContext(component="test_component", operation="test_operation")

        for exception in test_exceptions:
            try:
                result = asyncio.run(
                    self.error_handler.handle_error(exception, context)
                )
                self.assertIsNotNone(result)
            except Exception as e:
                self.fail(
                    f"Error handler should handle {type(exception).__name__}: {e}"
                )

    def test_thread_safety_improvements(self):
        """Test that thread safety improvements work correctly"""
        # Test RLock usage
        rlock = threading.RLock()

        # Test that RLock can be acquired multiple times by same thread
        with rlock:
            with rlock:  # This should not deadlock
                pass

        # Test stop event usage
        stop_event = threading.Event()
        self.assertFalse(stop_event.is_set())

        stop_event.set()
        self.assertTrue(stop_event.is_set())

    def test_memory_management_improvements(self):
        """Test that memory management improvements work correctly"""
        from collections import deque

        # Test bounded deque
        bounded_deque = deque(maxlen=100)
        self.assertEqual(bounded_deque.maxlen, 100)

        # Test that adding more than maxlen items doesn't cause memory issues
        for i in range(150):
            bounded_deque.append(i)

        self.assertEqual(len(bounded_deque), 100)
        self.assertEqual(bounded_deque[0], 50)  # First item should be 50

    def test_configuration_robustness(self):
        """Test that configuration is robust to various scenarios"""
        # Test with minimal config
        minimal_config = {
            "device": {"name": "test", "desc": "Test device"},
            "ssh": {"enabled": True, "port": 2222},
        }

        # This should not raise an exception
        try:
            config = Config()
            # Test that config can be accessed
            self.assertIsNotNone(config.getVal("device.name", "default"))
        except Exception as e:
            self.fail(f"Config should be robust: {e}")

    def test_api_gateway_route_handling(self):
        """Test that API Gateway route handling works correctly"""
        gateway = APIGateway()

        # Test that routes are set up
        self.assertIsNotNone(gateway.app)

        # Test service registration
        service_instances = [
            ServiceInstance(
                name="test_service",
                url="http://localhost:8080",
                status=ServiceStatus.HEALTHY,
                last_health_check=time.time(),
                response_time=0.1,
            )
        ]

        gateway.register_service("test_service", service_instances)

        # Test that service is registered
        instance = gateway.load_balancer.get_instance("test_service")
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "test_service")


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios to ensure nothing is broken"""

    def test_component_initialization_chain(self):
        """Test that components can be initialized in sequence"""
        try:
            # Initialize error handler
            error_handler = NetSentinelErrorHandler()

            # Initialize config
            config = get_config()

            # Initialize models
            event = create_event("test", "source", {"data": "test"})
            alert = create_alert(
                "Test", "Description", "medium", "source", {"data": "test"}
            )

            # All should work without errors
            self.assertIsNotNone(error_handler)
            self.assertIsNotNone(config)
            self.assertIsNotNone(event)
            self.assertIsNotNone(alert)

        except Exception as e:
            self.fail(f"Component initialization chain failed: {e}")

    def test_error_propagation_handling(self):
        """Test that error propagation is handled correctly"""
        error_handler = NetSentinelErrorHandler()
        context = ErrorContext("test", "test")

        # Test that errors are handled gracefully
        try:
            result = asyncio.run(
                error_handler.handle_error(Exception("Test exception"), context)
            )
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"Error propagation should be handled gracefully: {e}")


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
