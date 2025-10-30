#!/usr/bin/env python3
"""
WebSocket Manager for NetSentinel
Manages WebSocket connections, subscriptions, and real-time broadcasting
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Set, Optional, List
from collections import defaultdict
import threading

from ..core.base import BaseComponent
from ..core.interfaces import IWebSocketBroadcaster
from ..core.event_bus import get_event_bus, Event
from ..monitoring.logger import create_logger

logger = create_logger("websocket_manager")


class WebSocketManager(BaseComponent, IWebSocketBroadcaster):
    """
    Manages WebSocket connections and broadcasts events to subscribed clients
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("websocket_manager", config or {})

        # Connection management
        self.active_connections: Set[Any] = set()  # WebSocket connections
        self.subscriptions: Dict[str, Set[Any]] = defaultdict(set)  # channel -> connections

        # Health monitoring
        self.connection_health: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

        # Metrics
        self.messages_sent = 0
        self.connections_accepted = 0
        self.connections_closed = 0
        self.broadcast_errors = 0

    async def _initialize(self):
        """Initialize WebSocket manager"""
        # Subscribe to event bus for real-time broadcasting
        self.event_bus = get_event_bus()

        # Subscribe to threat events
        self.event_bus.subscribe("threat.new", self._handle_threat_event)

        # Subscribe to alert events
        self.event_bus.subscribe("alert.new", self._handle_alert_event)

        # Subscribe to status events
        self.event_bus.subscribe("status.update", self._handle_status_event)

        logger.info("WebSocket manager initialized and subscribed to event bus")
        self.metrics_collector = None  # Will be set by parent if needed

    async def _stop_internal(self):
        """Stop WebSocket manager and close all connections"""
        logger.info("Stopping WebSocket manager...")

        # Close all active connections
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.close()
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

        # Clear collections
        self.active_connections.clear()
        self.subscriptions.clear()
        self.connection_health.clear()

        logger.info(f"WebSocket manager stopped. Closed {len(disconnected)} connections")

    async def connect(self, websocket: Any, client_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Accept a new WebSocket connection

        Args:
            websocket: WebSocket connection object
            client_info: Optional client information (IP, user agent, etc.)

        Returns:
            connection_id: Unique identifier for this connection
        """
        try:
            # Accept the connection
            await websocket.accept()

            # Generate connection ID
            connection_id = f"ws_{int(time.time() * 1000)}_{id(websocket)}"

            with self._lock:
                self.active_connections.add(websocket)
                self.connections_accepted += 1

                # Store connection health info
                self.connection_health[connection_id] = {
                    "connected_at": time.time(),
                    "last_ping": time.time(),
                    "client_info": client_info or {},
                    "subscriptions": set(),
                    "messages_sent": 0,
                    "errors": 0
                }

            logger.info(f"WebSocket connection accepted: {connection_id}")
            return connection_id

        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {e}")
            raise

    async def disconnect(self, websocket: Any, connection_id: Optional[str] = None) -> None:
        """
        Handle WebSocket disconnection

        Args:
            websocket: WebSocket connection object
            connection_id: Connection identifier (optional)
        """
        try:
            with self._lock:
                # Remove from active connections
                self.active_connections.discard(websocket)
                self.connections_closed += 1

                # Remove from all subscriptions
                for channel, connections in self.subscriptions.items():
                    if websocket in connections:
                        connections.discard(websocket)
                        if connection_id and connection_id in self.connection_health:
                            self.connection_health[connection_id]["subscriptions"].discard(channel)
                        logger.debug(f"Removed connection from channel: {channel}")

                # Clean up health tracking
                if connection_id and connection_id in self.connection_health:
                    del self.connection_health[connection_id]

            logger.info(f"WebSocket connection closed: {connection_id}")

        except Exception as e:
            logger.error(f"Error during WebSocket disconnection: {e}")

    async def subscribe(self, websocket: Any, channel: str, connection_id: Optional[str] = None) -> bool:
        """
        Subscribe a WebSocket connection to a channel

        Args:
            websocket: WebSocket connection object
            channel: Channel name to subscribe to
            connection_id: Connection identifier (optional)

        Returns:
            success: Whether subscription was successful
        """
        try:
            with self._lock:
                # Check if connection is still active
                if websocket not in self.active_connections:
                    logger.warning(f"Attempted to subscribe inactive connection to {channel}")
                    return False

                # Add to subscriptions
                self.subscriptions[channel].add(websocket)

                # Update health tracking
                if connection_id and connection_id in self.connection_health:
                    self.connection_health[connection_id]["subscriptions"].add(channel)

            logger.debug(f"WebSocket subscribed to channel '{channel}': {connection_id}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to channel {channel}: {e}")
            return False

    async def unsubscribe(self, websocket: Any, channel: str, connection_id: Optional[str] = None) -> bool:
        """
        Unsubscribe a WebSocket connection from a channel

        Args:
            websocket: WebSocket connection object
            channel: Channel name to unsubscribe from
            connection_id: Connection identifier (optional)

        Returns:
            success: Whether unsubscription was successful
        """
        try:
            with self._lock:
                # Remove from subscriptions
                if channel in self.subscriptions:
                    self.subscriptions[channel].discard(websocket)

                    # Update health tracking
                    if connection_id and connection_id in self.connection_health:
                        self.connection_health[connection_id]["subscriptions"].discard(channel)

                    logger.debug(f"WebSocket unsubscribed from channel '{channel}': {connection_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error unsubscribing from channel {channel}: {e}")
            return False

    async def broadcast(self, channel: str, data: Dict[str, Any]) -> int:
        """
        Broadcast data to all subscribers of a channel

        Args:
            channel: Channel name
            data: Data to broadcast

        Returns:
            recipients_count: Number of clients that received the message
        """
        try:
            message = json.dumps(data)
            recipients = 0
            disconnected = set()

            with self._lock:
                if channel not in self.subscriptions:
                    logger.debug(f"No subscribers for channel: {channel}")
                    return 0

                connections = self.subscriptions[channel].copy()

            # Send to all subscribers
            for websocket in connections:
                try:
                    await websocket.send_text(message)
                    recipients += 1
                    self.messages_sent += 1

                    # Update health tracking for individual connections
                    # Note: We don't have connection_id here, could be enhanced

                except Exception as e:
                    logger.warning(f"Failed to send message to WebSocket: {e}")
                    disconnected.add(websocket)
                    self.broadcast_errors += 1

            # Clean up disconnected websockets
            if disconnected:
                with self._lock:
                    for ws in disconnected:
                        self.active_connections.discard(ws)
                        for ch, connections in self.subscriptions.items():
                            connections.discard(ws)
                logger.info(f"Cleaned up {len(disconnected)} disconnected WebSocket connections")

            logger.debug(f"Broadcasted to {recipients} clients on channel '{channel}'")
            return recipients

        except Exception as e:
            logger.error(f"Error broadcasting to channel {channel}: {e}")
            self.broadcast_errors += 1
            return 0

    async def broadcast_threat(self, threat_data: Dict[str, Any]) -> None:
        """
        Broadcast threat detection to connected clients
        Implements IWebSocketBroadcaster interface
        """
        event_data = {
            "type": "threat.new",
            "data": threat_data,
            "timestamp": time.time()
        }
        await self.broadcast("threats", event_data)

    async def broadcast_alert(self, alert_data: Dict[str, Any]) -> None:
        """
        Broadcast alert to connected clients
        Implements IWebSocketBroadcaster interface
        """
        event_data = {
            "type": "alert.new",
            "data": alert_data,
            "timestamp": time.time()
        }
        await self.broadcast("alerts", event_data)

    async def ping_connections(self) -> Dict[str, int]:
        """
        Send ping to all active connections and check health

        Returns:
            health_stats: Dictionary with connection health statistics
        """
        healthy = 0
        unhealthy = 0
        disconnected = set()

        current_time = time.time()

        for websocket in list(self.active_connections):
            try:
                # FastAPI WebSocket ping/pong
                await asyncio.wait_for(websocket.send_text(json.dumps({"type": "ping"})), timeout=5.0)
                healthy += 1
            except Exception as e:
                logger.debug(f"Connection health check failed: {e}")
                unhealthy += 1
                disconnected.add(websocket)

        # Clean up unhealthy connections
        if disconnected:
            for ws in disconnected:
                await self.disconnect(ws)

        return {
            "healthy": healthy,
            "unhealthy": unhealthy,
            "disconnected": len(disconnected),
            "total": len(self.active_connections)
        }

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket connection statistics

        Returns:
            stats: Dictionary with connection statistics
        """
        with self._lock:
            channel_stats = {}
            for channel, connections in self.subscriptions.items():
                channel_stats[channel] = len(connections)

            return {
                "active_connections": len(self.active_connections),
                "channels": len(self.subscriptions),
                "channel_subscriptions": channel_stats,
                "total_messages_sent": self.messages_sent,
                "total_connections_accepted": self.connections_accepted,
                "total_connections_closed": self.connections_closed,
                "broadcast_errors": self.broadcast_errors,
                "uptime": time.time() - getattr(self, 'start_time', time.time())
            }

    def get_channel_subscribers(self, channel: str) -> int:
        """
        Get number of subscribers for a channel

        Args:
            channel: Channel name

        Returns:
            subscriber_count: Number of subscribers
        """
        with self._lock:
            return len(self.subscriptions.get(channel, set()))

    async def _handle_threat_event(self, event: Event):
        """
        Handle threat events from the event bus

        Args:
            event: Event bus event
        """
        try:
            # Broadcast threat to WebSocket clients
            await self.broadcast("threats", event.data)
        except Exception as e:
            logger.error(f"Error handling threat event: {e}")

    async def _handle_alert_event(self, event: Event):
        """
        Handle alert events from the event bus

        Args:
            event: Event bus event
        """
        try:
            # Broadcast alert to WebSocket clients
            await self.broadcast("alerts", event.data)
        except Exception as e:
            logger.error(f"Error handling alert event: {e}")

    async def _handle_status_event(self, event: Event):
        """
        Handle status events from the event bus

        Args:
            event: Event bus event
        """
        try:
            # Broadcast status to WebSocket clients
            await self.broadcast("status", event.data)
        except Exception as e:
            logger.error(f"Error handling status event: {e}")

    async def publish_threat_event(self, threat_data: Dict[str, Any]):
        """
        Publish threat event to event bus (alternative interface)

        Args:
            threat_data: Threat data to publish
        """
        if self.event_bus:
            from ..core.event_bus import create_event
            event = create_event("threat.new", threat_data)
            await self.event_bus.publish(event)

    async def publish_alert_event(self, alert_data: Dict[str, Any]):
        """
        Publish alert event to event bus (alternative interface)

        Args:
            alert_data: Alert data to publish
        """
        if self.event_bus:
            from ..core.event_bus import create_event
            event = create_event("alert.new", alert_data)
            await self.event_bus.publish(event)

    async def publish_status_event(self, status_data: Dict[str, Any]):
        """
        Publish status event to event bus (alternative interface)

        Args:
            status_data: Status data to publish
        """
        if self.event_bus:
            from ..core.event_bus import create_event
            event = create_event("status.update", status_data)
            await self.event_bus.publish(event)
