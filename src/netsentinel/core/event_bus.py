#!/usr/bin/env python3
"""
Event Bus Implementation for NetSentinel
Implements Observer Pattern for decoupled event handling
"""

import asyncio
import time
import uuid
from typing import Dict, List, Callable, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict
import json

from ..core.exceptions import NetSentinelException
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("event_bus", level="INFO")
structured_logger = get_structured_logger("event_bus")


class EventPriority(Enum):
    """Event priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """Base event class"""

    event_id: str
    event_type: str
    timestamp: float
    data: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    source: str = "unknown"
    correlation_id: Optional[str] = None

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class EventHandler:
    """Event handler wrapper"""

    handler_id: str
    handler_function: Callable
    event_types: List[str]
    priority: int = 0
    is_async: bool = False
    is_active: bool = True

    async def handle(self, event: Event) -> None:
        """Handle event"""
        if not self.is_active:
            return

        try:
            if self.is_async:
                await self.handler_function(event)
            else:
                # Run sync handler in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.handler_function, event)

        except Exception as e:
            logger.error(f"Error in event handler {self.handler_id}: {e}")
            structured_logger.error(
                "Event handler error",
                **{
                    "handler_id": self.handler_id,
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    "error": str(e),
                },
            )


class EventBus:
    """Main event bus implementation"""

    def __init__(self, max_queue_size: int = 10000):
        self.max_queue_size = max_queue_size
        self.subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_tasks: List[asyncio.Task] = []
        self._lock = threading.RLock()
        self._statistics = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "handlers_executed": 0,
            "handlers_failed": 0,
        }

    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        priority: int = 0,
        handler_id: Optional[str] = None,
    ) -> str:
        """Subscribe to event type"""
        if handler_id is None:
            handler_id = f"{event_type}_{uuid.uuid4().hex[:8]}"

        # Check if handler is async
        is_async = asyncio.iscoroutinefunction(handler)

        event_handler = EventHandler(
            handler_id=handler_id,
            handler_function=handler,
            event_types=[event_type],
            priority=priority,
            is_async=is_async,
        )

        with self._lock:
            self.subscribers[event_type].append(event_handler)
            # Sort by priority (higher priority first)
            self.subscribers[event_type].sort(key=lambda x: x.priority, reverse=True)

        logger.info(f"Subscribed handler {handler_id} to event type {event_type}")
        return handler_id

    def unsubscribe(self, event_type: str, handler_id: str) -> bool:
        """Unsubscribe from event type"""
        with self._lock:
            if event_type in self.subscribers:
                for i, handler in enumerate(self.subscribers[event_type]):
                    if handler.handler_id == handler_id:
                        del self.subscribers[event_type][i]
                        logger.info(
                            f"Unsubscribed handler {handler_id} from event type {event_type}"
                        )
                        return True
        return False

    def deactivate_handler(self, handler_id: str) -> bool:
        """Deactivate handler"""
        with self._lock:
            for event_type, handlers in self.subscribers.items():
                for handler in handlers:
                    if handler.handler_id == handler_id:
                        handler.is_active = False
                        logger.info(f"Deactivated handler {handler_id}")
                        return True
        return False

    def activate_handler(self, handler_id: str) -> bool:
        """Activate handler"""
        with self._lock:
            for event_type, handlers in self.subscribers.items():
                for handler in handlers:
                    if handler.handler_id == handler_id:
                        handler.is_active = True
                        logger.info(f"Activated handler {handler_id}")
                        return True
        return False

    async def publish(self, event: Event) -> None:
        """Publish event to bus"""
        try:
            # Check queue size
            if self.event_queue.qsize() >= self.max_queue_size:
                logger.warning("Event queue is full, dropping event")
                return

            # Add to queue
            await self.event_queue.put(event)

            # Update statistics
            with self._lock:
                self._statistics["events_published"] += 1

            structured_logger.info(
                "Event published",
                {
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    "priority": event.priority.value,
                    "source": event.source,
                },
            )

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            with self._lock:
                self._statistics["events_failed"] += 1

    async def publish_sync(self, event: Event) -> None:
        """Publish event synchronously (immediate processing)"""
        try:
            await self._process_event(event)
        except Exception as e:
            logger.error(f"Failed to process event synchronously: {e}")
            with self._lock:
                self._statistics["events_failed"] += 1

    async def _process_event(self, event: Event) -> None:
        """Process event through handlers"""
        try:
            handlers = self.subscribers.get(event.event_type, [])

            if not handlers:
                logger.debug(f"No handlers for event type {event.event_type}")
                return

            # Process handlers in priority order
            for handler in handlers:
                try:
                    await handler.handle(event)

                    with self._lock:
                        self._statistics["handlers_executed"] += 1

                except Exception as e:
                    logger.error(f"Handler {handler.handler_id} failed: {e}")
                    with self._lock:
                        self._statistics["handlers_failed"] += 1

            # Update statistics
            with self._lock:
                self._statistics["events_processed"] += 1

        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")
            with self._lock:
                self._statistics["events_failed"] += 1

    async def _worker_loop(self) -> None:
        """Worker loop for processing events"""
        while self._running:
            try:
                # Get event from queue
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)

                # Process event
                await self._process_event(event)

                # Mark task as done
                self.event_queue.task_done()

            except asyncio.TimeoutError:
                # No events in queue, continue
                continue

            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(0.1)

    def start(self, worker_count: int = 3) -> None:
        """Start event bus"""
        if self._running:
            return

        self._running = True

        # Start worker tasks
        for i in range(worker_count):
            task = asyncio.create_task(self._worker_loop())
            self._worker_tasks.append(task)

        logger.info(f"Event bus started with {worker_count} workers")

    async def stop(self) -> None:
        """Stop event bus"""
        if not self._running:
            return

        self._running = False

        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

        logger.info("Event bus stopped")

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self._lock:
            return {
                "running": self._running,
                "queue_size": self.event_queue.qsize(),
                "max_queue_size": self.max_queue_size,
                "subscriber_count": sum(
                    len(handlers) for handlers in self.subscribers.values()
                ),
                "event_types": list(self.subscribers.keys()),
                "statistics": self._statistics.copy(),
            }

    def get_subscribers(self, event_type: str) -> List[Dict[str, Any]]:
        """Get subscribers for event type"""
        with self._lock:
            handlers = self.subscribers.get(event_type, [])
            return [
                {
                    "handler_id": handler.handler_id,
                    "priority": handler.priority,
                    "is_async": handler.is_async,
                    "is_active": handler.is_active,
                }
                for handler in handlers
            ]

    def clear_statistics(self) -> None:
        """Clear statistics"""
        with self._lock:
            self._statistics = {
                "events_published": 0,
                "events_processed": 0,
                "events_failed": 0,
                "handlers_executed": 0,
                "handlers_failed": 0,
            }


# Global event bus
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def create_event(
    event_type: str,
    data: Dict[str, Any],
    priority: EventPriority = EventPriority.NORMAL,
    source: str = "unknown",
    correlation_id: Optional[str] = None,
) -> Event:
    """Create event"""
    return Event(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        timestamp=time.time(),
        data=data,
        priority=priority,
        source=source,
        correlation_id=correlation_id,
    )


# Decorator for event handlers
def event_handler(event_type: str, priority: int = 0):
    """Decorator for event handlers"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Register handler
            bus = get_event_bus()
            handler_id = bus.subscribe(event_type, func, priority)
            return handler_id

        return wrapper

    return decorator


# Async decorator for event handlers
def async_event_handler(event_type: str, priority: int = 0):
    """Decorator for async event handlers"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Register handler
            bus = get_event_bus()
            handler_id = bus.subscribe(event_type, func, priority)
            return handler_id

        return wrapper

    return decorator
