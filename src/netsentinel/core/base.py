#!/usr/bin/env python3
"""
Base classes and interfaces for NetSentinel components
Provides consistent architecture patterns across all modules
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import threading
from contextlib import asynccontextmanager

T = TypeVar("T")


class ComponentState(Enum):
    """Component lifecycle states"""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class BaseConfig:
    """Base configuration class for all NetSentinel components"""

    pass


@dataclass
class ComponentMetrics:
    """Component performance metrics"""

    start_time: float = field(default_factory=time.time)
    uptime: float = 0.0
    operations_count: int = 0
    errors_count: int = 0
    last_operation_time: Optional[float] = None
    memory_usage: float = 0.0

    def update_uptime(self):
        """Update uptime calculation"""
        self.uptime = time.time() - self.start_time


class BaseComponent(ABC):
    """Base class for all NetSentinel components"""

    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.name = name
        self.config = config or {}
        self.logger = logger or logging.getLogger(f"netsentinel.{name}")
        self.state = ComponentState.STOPPED
        self.metrics = ComponentMetrics()
        self._lock = threading.RLock()
        self._dependencies: List[BaseComponent] = []
        self._error_handlers: List[callable] = []

    def add_dependency(self, component: "BaseComponent"):
        """Add a component dependency"""
        with self._lock:
            if component not in self._dependencies:
                self._dependencies.append(component)
                self.logger.debug(f"Added dependency: {component.name}")

    def add_error_handler(self, handler: callable):
        """Add error handler"""
        with self._lock:
            self._error_handlers.append(handler)

    async def start(self) -> bool:
        """Start the component"""
        with self._lock:
            if self.state != ComponentState.STOPPED:
                self.logger.warning(
                    f"Component {self.name} is not stopped, current state: {self.state}"
                )
                return False

            try:
                self.state = ComponentState.STARTING
                self.logger.info(f"Starting component: {self.name}")

                # Start dependencies first
                for dep in self._dependencies:
                    if dep.state != ComponentState.RUNNING:
                        await dep.start()

                # Initialize component
                await self._initialize()

                # Start component-specific logic
                await self._start_internal()

                self.state = ComponentState.RUNNING
                self.metrics.start_time = time.time()
                self.logger.info(f"Component {self.name} started successfully")
                return True

            except Exception as e:
                self.state = ComponentState.ERROR
                self.logger.error(f"Failed to start component {self.name}: {e}")
                await self._handle_error(e)
                return False

    async def stop(self) -> bool:
        """Stop the component"""
        with self._lock:
            if self.state not in [ComponentState.RUNNING, ComponentState.ERROR]:
                self.logger.warning(
                    f"Component {self.name} is not running, current state: {self.state}"
                )
                return False

            try:
                self.state = ComponentState.STOPPING
                self.logger.info(f"Stopping component: {self.name}")

                # Stop component-specific logic
                await self._stop_internal()

                # Cleanup
                await self._cleanup()

                self.state = ComponentState.STOPPED
                self.logger.info(f"Component {self.name} stopped successfully")
                return True

            except Exception as e:
                self.logger.error(f"Error stopping component {self.name}: {e}")
                await self._handle_error(e)
                return False

    def is_healthy(self) -> bool:
        """Check if component is healthy"""
        return self.state == ComponentState.RUNNING

    def get_metrics(self) -> Dict[str, Any]:
        """Get component metrics"""
        self.metrics.update_uptime()
        return {
            "name": self.name,
            "state": self.state.value,
            "uptime": self.metrics.uptime,
            "operations_count": self.metrics.operations_count,
            "errors_count": self.metrics.errors_count,
            "memory_usage": self.metrics.memory_usage,
            "dependencies": [dep.name for dep in self._dependencies],
        }

    async def _handle_error(self, error: Exception):
        """Handle component errors"""
        self.metrics.errors_count += 1
        self.logger.error(f"Component {self.name} error: {error}")

        # Call registered error handlers
        for handler in self._error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(error, self)
                else:
                    handler(error, self)
            except Exception as e:
                self.logger.error(f"Error in error handler: {e}")

        # Use local error handling to avoid circular imports
        try:
            context = {
                "operation": "component_error",
                "module": self.name,
                "additional_data": {"component_state": self.state.value},
            }
            self.logger.error(f"Component {self.name} error: {error}", extra=context)
        except Exception as e:
            self.logger.error(f"Error in error handler: {e}")
            # Don't let error handler errors propagate

    @abstractmethod
    async def _initialize(self):
        """Initialize component-specific resources"""
        pass

    @abstractmethod
    async def _start_internal(self):
        """Start component-specific logic"""
        pass

    @abstractmethod
    async def _stop_internal(self):
        """Stop component-specific logic"""
        pass

    async def _cleanup(self):
        """Cleanup component resources"""
        # Clean up dependencies
        for dep in self._dependencies:
            try:
                if dep.state != ComponentState.STOPPED:
                    await dep.stop()
            except Exception as e:
                self.logger.error(f"Error stopping dependency {dep.name}: {e}")

        # Clear error handlers
        self._error_handlers.clear()


class BaseManager(BaseComponent):
    """Base class for all managers"""

    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(name, config, logger)
        self._services: Dict[str, Any] = {}
        self._service_lock = threading.RLock()

    def register_service(self, name: str, service: Any):
        """Register a service"""
        with self._service_lock:
            self._services[name] = service
            self.logger.debug(f"Registered service: {name}")

    def get_service(self, name: str) -> Optional[Any]:
        """Get a registered service"""
        with self._service_lock:
            return self._services.get(name)

    def list_services(self) -> List[str]:
        """List all registered services"""
        with self._service_lock:
            return list(self._services.keys())


class BaseProcessor(BaseComponent):
    """Base class for event processors"""

    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(name, config, logger)
        self._processing_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._worker_tasks: List[asyncio.Task] = []
        self._max_workers = self.config.get("max_workers", 3)
        self._processing_semaphore = asyncio.Semaphore(self._max_workers)

    async def _start_internal(self):
        """Start processing workers"""
        for i in range(self._max_workers):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(task)
        self.logger.info(f"Started {self._max_workers} processing workers")

    async def _stop_internal(self):
        """Stop processing workers"""
        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        self.logger.info("Stopped all processing workers")

    async def _worker_loop(self, worker_name: str):
        """Worker loop for processing items"""
        self.logger.debug(f"Started worker: {worker_name}")

        while self.state == ComponentState.RUNNING:
            try:
                # Get item from queue with timeout
                item = await asyncio.wait_for(self._processing_queue.get(), timeout=1.0)

                self.logger.debug(f"Worker {worker_name} retrieved item from queue: {item}")

                # Process item with semaphore
                async with self._processing_semaphore:
                    await self._process_item(item)

                # Mark task as done
                self._processing_queue.task_done()
                self.metrics.operations_count += 1
                self.metrics.last_operation_time = time.time()

            except asyncio.TimeoutError:
                # No items in queue, continue
                continue
            except Exception as e:
                self.logger.error(f"Error in worker {worker_name}: {e}")
                await self._handle_error(e)

    async def queue_item(self, item: Any) -> bool:
        """Queue an item for processing"""
        try:
            self._processing_queue.put_nowait(item)
            self.logger.debug(f"Queued item for processing: {item}")
            return True
        except asyncio.QueueFull:
            self.logger.warning(f"Processing queue is full, dropping item")
            return False

    @abstractmethod
    async def _process_item(self, item: Any):
        """Process a single item"""
        pass


class BaseNotifier(BaseComponent):
    """Base class for notification systems"""

    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(name, config, logger)
        self._notification_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._retry_attempts = self.config.get("retry_attempts", 3)
        self._retry_delay = self.config.get("retry_delay", 1.0)

    async def send_notification(self, notification: Dict[str, Any]) -> bool:
        """Send a notification"""
        try:
            self._notification_queue.put_nowait(notification)
            return True
        except asyncio.QueueFull:
            self.logger.warning("Notification queue is full, dropping notification")
            return False

    async def _start_internal(self):
        """Start notification processing"""
        # Start notification worker
        self._notification_task = asyncio.create_task(self._notification_worker())
        self.logger.info("Started notification processing")

    async def _stop_internal(self):
        """Stop notification processing"""
        if hasattr(self, "_notification_task"):
            self._notification_task.cancel()
            try:
                await self._notification_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped notification processing")

    async def _notification_worker(self):
        """Process notifications from queue"""
        while self.state == ComponentState.RUNNING:
            try:
                notification = await asyncio.wait_for(
                    self._notification_queue.get(), timeout=1.0
                )

                await self._send_notification_internal(notification)
                self._notification_queue.task_done()
                self.metrics.operations_count += 1

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")
                await self._handle_error(e)

    @abstractmethod
    async def _send_notification_internal(self, notification: Dict[str, Any]) -> bool:
        """Send notification implementation"""
        pass


class ResourceManager:
    """Centralized resource management"""

    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._cleanup_handlers: Dict[str, callable] = {}
        self._lock = threading.RLock()

    def register_resource(
        self, name: str, resource: Any, cleanup_handler: Optional[callable] = None
    ):
        """Register a resource with optional cleanup handler"""
        with self._lock:
            self._resources[name] = resource
            if cleanup_handler:
                self._cleanup_handlers[name] = cleanup_handler

    def get_resource(self, name: str) -> Optional[Any]:
        """Get a registered resource"""
        with self._lock:
            return self._resources.get(name)

    async def start(self):
        """Start resource manager (no-op for now)"""
        pass

    async def stop(self):
        """Stop resource manager and cleanup all resources"""
        await self.cleanup_all()

    async def cleanup_all(self):
        """Cleanup all registered resources"""
        with self._lock:
            cleanup_handlers_copy = dict(self._cleanup_handlers)
            for name, handler in cleanup_handlers_copy.items():
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                except Exception as e:
                    logging.error(f"Error cleaning up resource {name}: {e}")

            self._resources.clear()
            self._cleanup_handlers.clear()

        logging.info("All resources cleaned up successfully")

    def get_resource_metrics(self) -> Dict[str, Any]:
        """Get resource manager metrics"""
        with self._lock:
            return {
                "total_resources": len(self._resources),
                "resources": list(self._resources.keys()),
                "cleanup_handlers": len(self._cleanup_handlers),
            }


# Global resource manager
_resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager"""
    return _resource_manager


@asynccontextmanager
async def managed_component(component: BaseComponent):
    """Context manager for component lifecycle"""
    try:
        await component.start()
        yield component
    finally:
        await component.stop()
