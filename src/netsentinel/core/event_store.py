#!/usr/bin/env python3
"""
Event Store for NetSentinel
Implements Event Sourcing pattern for immutable event storage and replay
"""

import asyncio
import json
import logging
import uuid
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event type enumeration"""

    THREAT_DETECTED = "threat_detected"
    ALERT_CREATED = "alert_created"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_RESOLVED = "alert_resolved"
    IP_BLOCKED = "ip_blocked"
    IP_UNBLOCKED = "ip_unblocked"
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    CONFIGURATION_CHANGED = "configuration_changed"


@dataclass
class DomainEvent:
    """Domain event representing a business event"""

    id: str
    event_type: EventType
    aggregate_id: str
    aggregate_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    version: int
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        """Create event from dictionary"""
        return cls(
            id=data["id"],
            event_type=EventType(data["event_type"]),
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            data=data["data"],
            metadata=data["metadata"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            version=data["version"],
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
        )


class EventStore:
    """
    Event store for NetSentinel implementing Event Sourcing pattern
    Provides immutable event storage, replay capabilities, and event publishing
    """

    def __init__(self, storage_backend=None):
        self.storage_backend = storage_backend
        self.subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_history: List[DomainEvent] = []
        self.aggregate_versions: Dict[str, int] = {}
        self.lock = threading.RLock()
        self.logger = logging.getLogger(f"{__name__}.EventStore")

        # Initialize storage backend
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize storage backend"""
        if not self.storage_backend:
            # Use in-memory storage by default
            self.storage_backend = InMemoryEventStorage()

        self.logger.info("Event store initialized")

    async def append_event(self, event: DomainEvent) -> None:
        """Append event to store and notify subscribers"""
        with self.lock:
            # Validate event
            if not self._validate_event(event):
                raise ValueError(f"Invalid event: {event.id}")

            # Store event
            await self._store_event(event)

            # Update aggregate version
            self.aggregate_versions[event.aggregate_id] = event.version

            # Add to history
            self.event_history.append(event)

            # Notify subscribers
            await self._notify_subscribers(event)

            self.logger.debug(
                f"Event stored: {event.event_type.value} for {event.aggregate_id}"
            )

    def _validate_event(self, event: DomainEvent) -> bool:
        """Validate event before storing"""
        # Check required fields
        if not event.id or not event.aggregate_id or not event.event_type:
            return False

        # Check version consistency
        current_version = self.aggregate_versions.get(event.aggregate_id, 0)
        if event.version != current_version + 1:
            self.logger.warning(
                f"Version mismatch for {event.aggregate_id}: expected {current_version + 1}, got {event.version}"
            )
            return False

        return True

    async def _store_event(self, event: DomainEvent) -> None:
        """Store event in backend"""
        try:
            if hasattr(self.storage_backend, "store_event"):
                await self.storage_backend.store_event(event)
            else:
                # Default in-memory storage
                pass
        except Exception as e:
            self.logger.error(f"Failed to store event {event.id}: {e}")
            raise

    async def _notify_subscribers(self, event: DomainEvent) -> None:
        """Notify all subscribers of the event"""
        subscribers = self.subscribers.get(event.event_type, [])

        for subscriber in subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    subscriber(event)
            except Exception as e:
                self.logger.error(f"Error in event subscriber: {e}")

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Subscribe to specific event type"""
        self.subscribers[event_type].append(handler)
        self.logger.debug(f"Subscribed to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Unsubscribe from event type"""
        if handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)
            self.logger.debug(f"Unsubscribed from {event_type.value}")

    async def get_events(
        self, aggregate_id: str, from_version: int = 0
    ) -> List[DomainEvent]:
        """Get events for specific aggregate"""
        try:
            if hasattr(self.storage_backend, "get_events"):
                return await self.storage_backend.get_events(aggregate_id, from_version)
            else:
                # Filter from in-memory history
                return [
                    event
                    for event in self.event_history
                    if event.aggregate_id == aggregate_id
                    and event.version >= from_version
                ]
        except Exception as e:
            self.logger.error(f"Failed to get events for {aggregate_id}: {e}")
            return []

    async def get_events_by_type(
        self, event_type: EventType, limit: int = 100
    ) -> List[DomainEvent]:
        """Get events by type"""
        try:
            if hasattr(self.storage_backend, "get_events_by_type"):
                return await self.storage_backend.get_events_by_type(event_type, limit)
            else:
                # Filter from in-memory history
                events = [
                    event
                    for event in self.event_history
                    if event.event_type == event_type
                ]
                return events[-limit:] if limit else events
        except Exception as e:
            self.logger.error(f"Failed to get events by type {event_type.value}: {e}")
            return []

    async def replay_events(
        self, aggregate_id: str, from_version: int = 0
    ) -> List[DomainEvent]:
        """Replay events for aggregate reconstruction"""
        return await self.get_events(aggregate_id, from_version)

    def get_aggregate_version(self, aggregate_id: str) -> int:
        """Get current version of aggregate"""
        return self.aggregate_versions.get(aggregate_id, 0)

    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event store statistics"""
        event_counts = defaultdict(int)
        for event in self.event_history:
            event_counts[event.event_type.value] += 1

        return {
            "total_events": len(self.event_history),
            "event_counts": dict(event_counts),
            "aggregates": len(self.aggregate_versions),
            "subscribers": {
                event_type.value: len(handlers)
                for event_type, handlers in self.subscribers.items()
            },
        }


class InMemoryEventStorage:
    """In-memory event storage implementation"""

    def __init__(self):
        self.events: List[DomainEvent] = []
        self.aggregate_events: Dict[str, List[DomainEvent]] = defaultdict(list)

    async def store_event(self, event: DomainEvent) -> None:
        """Store event in memory"""
        self.events.append(event)
        self.aggregate_events[event.aggregate_id].append(event)

    async def get_events(
        self, aggregate_id: str, from_version: int = 0
    ) -> List[DomainEvent]:
        """Get events for aggregate"""
        return [
            event
            for event in self.aggregate_events[aggregate_id]
            if event.version >= from_version
        ]

    async def get_events_by_type(
        self, event_type: EventType, limit: int = 100
    ) -> List[DomainEvent]:
        """Get events by type"""
        events = [event for event in self.events if event.event_type == event_type]
        return events[-limit:] if limit else events


# Global event store instance
_event_store: Optional[EventStore] = None


def get_event_store() -> EventStore:
    """Get the global event store"""
    global _event_store
    if _event_store is None:
        _event_store = EventStore()
    return _event_store


def create_domain_event(
    event_type: EventType,
    aggregate_id: str,
    aggregate_type: str,
    data: Dict[str, Any],
    metadata: Dict[str, Any] = None,
    correlation_id: str = None,
    causation_id: str = None,
) -> DomainEvent:
    """Create a new domain event"""
    return DomainEvent(
        id=str(uuid.uuid4()),
        event_type=event_type,
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        data=data,
        metadata=metadata or {},
        timestamp=datetime.now(),
        version=1,  # Will be updated by event store
        correlation_id=correlation_id,
        causation_id=causation_id,
    )
