#!/usr/bin/env python3
"""
Unit tests for NetSentinel base components
Tests the foundational architecture components
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

from netsentinel.core.base import (
    BaseComponent,
    BaseManager,
    BaseProcessor,
    BaseNotifier,
    ComponentState,
)
from netsentinel.core.models import (
    StandardEvent,
    StandardAlert,
    create_event,
    create_alert,
)
from netsentinel.core.error_handler import NetSentinelErrorHandler, ErrorContext


class TestBaseComponent:
    """Test cases for BaseComponent"""

    @pytest.fixture
    def component(self):
        """Create a test component"""

        class TestComponent(BaseComponent):
            async def _initialize(self):
                self.initialized = True

            async def _start_internal(self):
                self.started = True

            async def _stop_internal(self):
                self.stopped = True

        return TestComponent("test_component")

    def test_initialization(self, component):
        """Test component initialization"""
        assert component.name == "test_component"
        assert component.state == ComponentState.STOPPED
        assert component.metrics.operations_count == 0

    @pytest.mark.asyncio
    async def test_lifecycle(self, component):
        """Test component lifecycle"""
        # Start component
        success = await component.start()
        assert success is True
        assert component.state == ComponentState.RUNNING
        assert component.initialized is True
        assert component.started is True

        # Check health
        assert component.is_healthy() is True

        # Stop component
        success = await component.stop()
        assert success is True
        assert component.state == ComponentState.STOPPED
        assert component.stopped is True

    @pytest.mark.asyncio
    async def test_dependency_management(self, component):
        """Test dependency management"""
        # Create dependency
        dependency = Mock(spec=BaseComponent)
        dependency.name = "test_dependency"  # Add name attribute
        dependency.state = ComponentState.STOPPED  # Set to STOPPED so it will be started
        dependency.start = AsyncMock(return_value=True)

        # Add dependency
        component.add_dependency(dependency)
        assert len(component._dependencies) == 1

        # Start component (should start dependency first)
        await component.start()
        dependency.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self, component):
        """Test error handling"""
        # Add error handler
        error_handler = Mock()
        component.add_error_handler(error_handler)

        # Simulate error
        error = Exception("Test error")
        await component._handle_error(error)

        # Error handler should be called
        error_handler.assert_called_once_with(error, component)

    def test_metrics(self, component):
        """Test metrics collection"""
        metrics = component.get_metrics()

        assert "name" in metrics
        assert "state" in metrics
        assert "uptime" in metrics
        assert "operations_count" in metrics
        assert "errors_count" in metrics
        assert metrics["name"] == "test_component"


class TestBaseManager:
    """Test cases for BaseManager"""

    @pytest.fixture
    def manager(self):
        """Create a test manager"""

        class TestManager(BaseManager):
            async def _initialize(self):
                pass

            async def _start_internal(self):
                pass

            async def _stop_internal(self):
                pass

        return TestManager("test_manager")

    def test_service_registration(self, manager):
        """Test service registration"""
        service = Mock()

        # Register service
        manager.register_service("test_service", service)
        assert "test_service" in manager._services

        # Get service
        retrieved_service = manager.get_service("test_service")
        assert retrieved_service is service

        # List services
        services = manager.list_services()
        assert "test_service" in services

    def test_service_management(self, manager):
        """Test service management"""
        service1 = Mock()
        service2 = Mock()

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)

        assert len(manager.list_services()) == 2
        assert manager.get_service("service1") is service1
        assert manager.get_service("service2") is service2
        assert manager.get_service("nonexistent") is None


class TestBaseProcessor:
    """Test cases for BaseProcessor"""

    @pytest.fixture
    def processor(self):
        """Create a test processor"""

        class TestProcessor(BaseProcessor):
            def __init__(self):
                super().__init__("test_processor")
                self.processed_items = []

            async def _initialize(self):
                pass

            async def _start_internal(self):
                # Call parent implementation to start workers
                await super()._start_internal()

            async def _stop_internal(self):
                # Call parent implementation to stop workers
                await super()._stop_internal()

            async def _process_item(self, item):
                self.processed_items.append(item)

        return TestProcessor()

    @pytest.mark.asyncio
    async def test_item_processing(self, processor):
        """Test item processing"""
        # Start processor
        await processor.start()

        # Queue items
        item1 = "test_item_1"
        item2 = "test_item_2"

        await processor.queue_item(item1)
        await processor.queue_item(item2)

        # Wait for processing with multiple attempts
        for _ in range(10):  # Try up to 10 times
            await asyncio.sleep(0.1)
            if len(processor.processed_items) >= 2:
                break

        # Check items were processed
        assert len(processor.processed_items) == 2
        assert item1 in processor.processed_items
        assert item2 in processor.processed_items

    @pytest.mark.asyncio
    async def test_queue_overflow(self, processor):
        """Test queue overflow handling"""
        # Start processor
        await processor.start()

        # Fill queue beyond capacity
        for i in range(processor._processing_queue.maxsize + 10):
            success = await processor.queue_item(f"item_{i}")
            if i < processor._processing_queue.maxsize:
                assert success is True
            else:
                assert success is False  # Queue should be full


class TestBaseNotifier:
    """Test cases for BaseNotifier"""

    @pytest.fixture
    def notifier(self):
        """Create a test notifier"""

        class TestNotifier(BaseNotifier):
            def __init__(self):
                super().__init__("test_notifier")
                self.sent_notifications = []

            async def _initialize(self):
                pass

            async def _start_internal(self):
                # Call parent implementation to start workers
                await super()._start_internal()

            async def _stop_internal(self):
                # Call parent implementation to stop workers
                await super()._stop_internal()

            async def _send_notification_internal(self, notification):
                self.sent_notifications.append(notification)
                return True

        return TestNotifier()

    @pytest.mark.asyncio
    async def test_notification_sending(self, notifier):
        """Test notification sending"""
        # Start notifier
        await notifier.start()

        # Send notifications
        notification1 = {"type": "alert", "message": "Test alert 1"}
        notification2 = {"type": "warning", "message": "Test warning 1"}

        success1 = await notifier.send_notification(notification1)
        success2 = await notifier.send_notification(notification2)

        assert success1 is True
        assert success2 is True

        # Wait for processing with multiple attempts
        for _ in range(10):  # Try up to 10 times
            await asyncio.sleep(0.1)
            if len(notifier.sent_notifications) >= 2:
                break

        # Check notifications were sent
        assert len(notifier.sent_notifications) == 2
        assert notification1 in notifier.sent_notifications
        assert notification2 in notifier.sent_notifications


class TestStandardModels:
    """Test cases for standard data models"""

    def test_standard_event_creation(self):
        """Test standard event creation"""
        event = create_event(
            event_type="test_event",
            source="test_source",
            data={"key": "value"},
            severity="medium",
        )

        assert event.event_type == "test_event"
        assert event.source == "test_source"
        assert event.data["key"] == "value"
        assert event.severity == "medium"
        assert event.id is not None
        assert event.timestamp > 0

    def test_standard_event_validation(self):
        """Test standard event validation"""
        # Valid event
        event = create_event("test", "source", {"data": "value"})
        validation = event.validate()
        assert validation.valid is True

        # Invalid event (missing required fields)
        event = StandardEvent(id="", timestamp=0, event_type="", source="", data={})
        validation = event.validate()
        assert validation.valid is False
        assert len(validation.errors) > 0

    def test_standard_alert_creation(self):
        """Test standard alert creation"""
        alert = create_alert(
            title="Test Alert",
            description="Test description",
            severity="high",
            source="test_source",
            event_data={"key": "value"},
        )

        assert alert.title == "Test Alert"
        assert alert.description == "Test description"
        assert alert.severity == "high"
        assert alert.source == "test_source"
        assert alert.id is not None
        assert alert.timestamp > 0
        assert alert.acknowledged is False
        assert alert.resolved is False

    def test_alert_acknowledgment(self):
        """Test alert acknowledgment"""
        alert = create_alert("Test", "Description", "medium", "source", {})

        # Acknowledge alert
        success = alert.acknowledge("user123")
        assert success is True
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "user123"
        assert alert.acknowledged_at is not None

        # Try to acknowledge again (should fail)
        success = alert.acknowledge("user456")
        assert success is False

    def test_alert_resolution(self):
        """Test alert resolution"""
        alert = create_alert("Test", "Description", "medium", "source", {})

        # Resolve alert
        success = alert.resolve("user123")
        assert success is True
        assert alert.resolved is True
        assert alert.resolved_by == "user123"
        assert alert.resolved_at is not None

        # Try to resolve again (should fail)
        success = alert.resolve("user456")
        assert success is False


class TestErrorHandler:
    """Test cases for error handler"""

    @pytest.fixture
    def error_handler(self):
        """Create error handler"""
        return NetSentinelErrorHandler()

    def test_error_handler_initialization(self, error_handler):
        """Test error handler initialization"""
        assert error_handler.metrics.total_errors == 0
        assert len(error_handler.error_handlers) > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, error_handler):
        """Test error handling"""
        context = ErrorContext(component="test_component", operation="test_operation")

        # Use the custom ConnectionError from NetSentinel
        from netsentinel.core.exceptions import ConnectionError
        error = ConnectionError("Test connection error")
        result = await error_handler.handle_error(error, context)

        assert result["status"] == "connection_error"
        assert result["component"] == "test_component"
        assert result["message"] == "Test connection error"

    def test_retry_decorator(self, error_handler):
        """Test retry decorator"""
        call_count = 0

        @error_handler.retry_with_backoff(max_attempts=3, base_delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Test error")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count == 3

    def test_metrics_tracking(self, error_handler):
        """Test error metrics tracking"""
        context = ErrorContext("test", "operation")

        # Simulate errors
        error_handler._update_metrics(ConnectionError("test"), context)
        error_handler._update_metrics(ValueError("test"), context)

        metrics = error_handler.get_error_metrics()
        assert metrics["total_errors"] == 2
        assert "ConnectionError" in metrics["errors_by_type"]
        assert "ValueError" in metrics["errors_by_type"]


class TestComponentIntegration:
    """Integration tests for components"""

    @pytest.mark.asyncio
    async def test_component_lifecycle_integration(self):
        """Test complete component lifecycle"""

        # Create manager
        class TestManager(BaseManager):
            async def _initialize(self):
                self.services = {}

            async def _start_internal(self):
                pass

            async def _stop_internal(self):
                pass

        manager = TestManager("integration_manager")

        # Create processor
        class TestProcessor(BaseProcessor):
            def __init__(self, manager):
                super().__init__("integration_processor")
                self.manager = manager
                self.processed = []

            async def _initialize(self):
                pass

            async def _start_internal(self):
                # Call parent implementation to start workers
                await super()._start_internal()

            async def _stop_internal(self):
                # Call parent implementation to stop workers
                await super()._stop_internal()

            async def _process_item(self, item):
                self.processed.append(item)

        processor = TestProcessor(manager)

        # Add dependency
        processor.add_dependency(manager)

        # Start components
        await manager.start()
        await processor.start()

        # Process items
        await processor.queue_item("test_item")
        
        # Wait for processing with multiple attempts
        for _ in range(10):  # Try up to 10 times
            await asyncio.sleep(0.1)
            if len(processor.processed) >= 1:
                break

        # Verify processing
        assert len(processor.processed) == 1
        assert "test_item" in processor.processed

        # Stop components
        await processor.stop()
        await manager.stop()

        # Verify stopped
        assert processor.state == ComponentState.STOPPED
        assert manager.state == ComponentState.STOPPED
