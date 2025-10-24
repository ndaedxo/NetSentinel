#!/usr/bin/env python3
"""
Event Sourcing Implementation for NetSentinel
Implements immutable event log and domain events for audit trail and replay capabilities
"""

import json
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import threading
from collections import defaultdict

from .exceptions import NetSentinelException, ProcessingError


class EventType(Enum):
    """Domain event types"""

    THREAT_DETECTED = "threat_detected"
    ALERT_CREATED = "alert_created"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_RESOLVED = "alert_resolved"
    FIREWALL_RULE_APPLIED = "firewall_rule_applied"
    ML_MODEL_UPDATED = "ml_model_updated"
    SYSTEM_CONFIGURATION_CHANGED = "system_configuration_changed"
    USER_ACTION = "user_action"
    SECURITY_INCIDENT = "security_incident"


@dataclass
class DomainEvent:
    """Base domain event"""

    event_id: str
    event_type: EventType
    aggregate_id: str
    aggregate_version: int
    timestamp: float
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class EventStream:
    """Event stream for an aggregate"""

    aggregate_id: str
    events: List[DomainEvent] = field(default_factory=list)
    version: int = 0

    def add_event(self, event: DomainEvent) -> None:
        """Add event to stream"""
        if event.aggregate_id != self.aggregate_id:
            raise ValueError("Event aggregate ID mismatch")
        if event.aggregate_version != self.version + 1:
            raise ValueError("Event version mismatch")

        self.events.append(event)
        self.version = event.aggregate_version


class EventStore:
    """Immutable event store for domain events"""

    def __init__(self, storage_backend: Optional[Any] = None):
        self.storage_backend = storage_backend or InMemoryEventStore()
        self._streams: Dict[str, EventStream] = {}
        self._subscribers: Dict[EventType, List[callable]] = defaultdict(list)
        self._lock = threading.RLock()

    async def append_event(self, event: DomainEvent) -> None:
        """Append event to store"""
        with self._lock:
            # Get or create stream
            if event.aggregate_id not in self._streams:
                self._streams[event.aggregate_id] = EventStream(event.aggregate_id)

            stream = self._streams[event.aggregate_id]
            stream.add_event(event)

            # Persist to backend
            await self.storage_backend.save_event(event)

            # Notify subscribers
            await self._notify_subscribers(event)

    async def get_events(
        self, aggregate_id: str, from_version: int = 0
    ) -> List[DomainEvent]:
        """Get events for an aggregate"""
        with self._lock:
            if aggregate_id not in self._streams:
                return []

            stream = self._streams[aggregate_id]
            return [
                event
                for event in stream.events
                if event.aggregate_version >= from_version
            ]

    async def get_events_by_type(
        self, event_type: EventType, limit: int = 100
    ) -> List[DomainEvent]:
        """Get events by type"""
        return await self.storage_backend.get_events_by_type(event_type, limit)

    async def get_events_since(
        self, timestamp: float, limit: int = 100
    ) -> List[DomainEvent]:
        """Get events since timestamp"""
        return await self.storage_backend.get_events_since(timestamp, limit)

    def subscribe(self, event_type: EventType, handler: callable) -> None:
        """Subscribe to event type"""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: callable) -> None:
        """Unsubscribe from event type"""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def _notify_subscribers(self, event: DomainEvent) -> None:
        """Notify all subscribers of an event"""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                # Log error but don't fail the event processing
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error in event handler {handler.__name__}: {e}")

    def get_aggregate_version(self, aggregate_id: str) -> int:
        """Get current version of aggregate"""
        with self._lock:
            if aggregate_id not in self._streams:
                return 0
            return self._streams[aggregate_id].version

    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event store statistics"""
        with self._lock:
            total_events = sum(len(stream.events) for stream in self._streams.values())
            event_types = defaultdict(int)
            for stream in self._streams.values():
                for event in stream.events:
                    event_types[event.event_type.value] += 1

            return {
                "total_events": total_events,
                "total_streams": len(self._streams),
                "events_by_type": dict(event_types),
                "oldest_event": min(
                    (
                        event.timestamp
                        for stream in self._streams.values()
                        for event in stream.events
                    ),
                    default=None,
                ),
                "newest_event": max(
                    (
                        event.timestamp
                        for stream in self._streams.values()
                        for event in stream.events
                    ),
                    default=None,
                ),
            }


class InMemoryEventStore:
    """In-memory event store backend"""

    def __init__(self):
        self._events: List[DomainEvent] = []
        self._lock = threading.RLock()

    async def save_event(self, event: DomainEvent) -> None:
        """Save event to memory"""
        with self._lock:
            self._events.append(event)

    async def get_events_by_type(
        self, event_type: EventType, limit: int = 100
    ) -> List[DomainEvent]:
        """Get events by type"""
        with self._lock:
            events = [event for event in self._events if event.event_type == event_type]
            return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]

    async def get_events_since(
        self, timestamp: float, limit: int = 100
    ) -> List[DomainEvent]:
        """Get events since timestamp"""
        with self._lock:
            events = [event for event in self._events if event.timestamp >= timestamp]
            return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]


class EventHandler(ABC):
    """Base class for event handlers"""

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Handle domain event"""
        pass


class ThreatDetectionEventHandler(EventHandler):
    """Handler for threat detection events"""

    def __init__(self, alert_manager, firewall_manager):
        self.alert_manager = alert_manager
        self.firewall_manager = firewall_manager

    async def handle(self, event: DomainEvent) -> None:
        """Handle threat detection event"""
        if event.event_type == EventType.THREAT_DETECTED:
            # Create alert
            alert_data = {
                "threat_type": event.data.get("threat_type"),
                "source_ip": event.data.get("source_ip"),
                "severity": event.data.get("severity"),
                "confidence": event.data.get("confidence"),
                "timestamp": event.timestamp,
            }

            await self.alert_manager.create_alert(
                title=f"Threat Detected: {event.data.get('threat_type')}",
                description=f"Threat detected from {event.data.get('source_ip')}",
                severity=event.data.get("severity", "medium"),
                source="threat_detection",
                event_data=alert_data,
            )

            # Apply firewall rule if high severity
            if event.data.get("severity") == "high":
                await self.firewall_manager.block_ip(
                    event.data.get("source_ip"), reason="High severity threat detected"
                )


class AlertEventHandler(EventHandler):
    """Handler for alert events"""

    def __init__(self, notification_service):
        self.notification_service = notification_service

    async def handle(self, event: DomainEvent) -> None:
        """Handle alert event"""
        if event.event_type == EventType.ALERT_CREATED:
            # Send notifications
            await self.notification_service.send_alert_notification(event.data)

        elif event.event_type == EventType.ALERT_ACKNOWLEDGED:
            # Log acknowledgment
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"Alert {event.aggregate_id} acknowledged by {event.data.get('user_id')}"
            )

        elif event.event_type == EventType.ALERT_RESOLVED:
            # Log resolution
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"Alert {event.aggregate_id} resolved by {event.data.get('user_id')}"
            )


class EventReplay:
    """Event replay for rebuilding state"""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    async def replay_events(self, aggregate_id: str, from_version: int = 0) -> Any:
        """Replay events to rebuild aggregate state"""
        events = await self.event_store.get_events(aggregate_id, from_version)

        # Rebuild state from events
        state = {}
        for event in events:
            state = self._apply_event(state, event)

        return state

    def _apply_event(self, state: Dict[str, Any], event: DomainEvent) -> Dict[str, Any]:
        """Apply event to state"""
        # This would be implemented based on specific business logic
        # For now, just merge event data into state
        state.update(event.data)
        state["version"] = event.aggregate_version
        state["last_updated"] = event.timestamp

        return state


# Global event store instance
_event_store: Optional[EventStore] = None


def get_event_store() -> EventStore:
    """Get global event store instance"""
    global _event_store
    if _event_store is None:
        _event_store = EventStore()
    return _event_store


def create_domain_event(
    event_type: EventType,
    aggregate_id: str,
    aggregate_version: int,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> DomainEvent:
    """Create a domain event"""
    return DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        aggregate_id=aggregate_id,
        aggregate_version=aggregate_version,
        timestamp=time.time(),
        data=data,
        metadata=metadata or {},
    )
