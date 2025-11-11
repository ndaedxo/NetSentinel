#!/usr/bin/env python3
"""
WebSocket Manager for NetSentinel
Manages WebSocket connections, subscriptions, and real-time broadcasting
"""

import asyncio
import json
import time
import logging
import gzip
import base64
from typing import Dict, Any, Set, Optional, List, Deque
from collections import defaultdict, deque
import threading
from dataclasses import dataclass

from ..core.base import BaseComponent
from ..core.interfaces import IWebSocketBroadcaster
from ..core.event_bus import get_event_bus, Event
from ..monitoring.logger import create_logger

logger = create_logger("websocket_manager")


@dataclass
class QueuedMessage:
    """Message queued for offline clients"""
    message_id: str
    channel: str
    data: Dict[str, Any]
    timestamp: float
    priority: int = 1  # 1=normal, 2=high, 3=critical
    expires_at: Optional[float] = None


class MessageQueue:
    """Message queue for offline clients with persistence and replay"""

    def __init__(self, max_messages_per_client: int = 100, default_ttl: int = 3600):  # 1 hour default
        self.max_messages_per_client = max_messages_per_client
        self.default_ttl = default_ttl
        self.queues: Dict[str, Deque[QueuedMessage]] = defaultdict(lambda: deque(maxlen=max_messages_per_client))
        self._lock = threading.RLock()

    def enqueue_message(self, client_id: str, channel: str, data: Dict[str, Any],
                       priority: int = 1, ttl: Optional[int] = None) -> str:
        """Add message to client's queue"""
        with self._lock:
            message_id = f"msg_{int(time.time() * 1000)}_{client_id}"
            expires_at = time.time() + (ttl or self.default_ttl) if ttl or self.default_ttl else None

            message = QueuedMessage(
                message_id=message_id,
                channel=channel,
                data=data,
                timestamp=time.time(),
                priority=priority,
                expires_at=expires_at
            )

            # Add to queue (deque automatically handles max length)
            self.queues[client_id].append(message)

            logger.debug(f"Queued message {message_id} for client {client_id} on channel {channel}")
            return message_id

    def dequeue_messages(self, client_id: str, channel: Optional[str] = None,
                        max_messages: int = 50) -> List[QueuedMessage]:
        """Get messages from client's queue, optionally filtered by channel"""
        with self._lock:
            if client_id not in self.queues:
                return []

            messages = list(self.queues[client_id])
            current_time = time.time()

            # Filter out expired messages
            messages = [msg for msg in messages if msg.expires_at is None or msg.expires_at > current_time]

            # Filter by channel if specified
            if channel:
                messages = [msg for msg in messages if msg.channel == channel]

            # Sort by priority (highest first) then timestamp
            messages.sort(key=lambda x: (-x.priority, x.timestamp))

            # Return up to max_messages
            result = messages[:max_messages]

            # Remove returned messages from queue
            remaining = [msg for msg in self.queues[client_id] if msg not in result]
            self.queues[client_id].clear()
            self.queues[client_id].extend(remaining)

            logger.debug(f"Dequeued {len(result)} messages for client {client_id}")
            return result

    def get_queue_stats(self, client_id: str) -> Dict[str, Any]:
        """Get queue statistics for a client"""
        with self._lock:
            if client_id not in self.queues:
                return {"total_messages": 0, "channels": {}}

            messages = list(self.queues[client_id])
            current_time = time.time()

            # Count by channel
            channels = defaultdict(int)
            expired = 0

            for msg in messages:
                if msg.expires_at and msg.expires_at <= current_time:
                    expired += 1
                else:
                    channels[msg.channel] += 1

            return {
                "total_messages": len(messages) - expired,
                "expired_messages": expired,
                "channels": dict(channels),
                "oldest_message_age": time.time() - min((msg.timestamp for msg in messages), default=time.time())
            }

    def cleanup_expired_messages(self):
        """Remove expired messages from all queues"""
        with self._lock:
            current_time = time.time()
            cleaned_count = 0

            for client_id, queue in list(self.queues.items()):
                original_size = len(queue)
                # Keep only non-expired messages
                valid_messages = [msg for msg in queue if msg.expires_at is None or msg.expires_at > current_time]
                queue.clear()
                queue.extend(valid_messages)
                cleaned_count += original_size - len(queue)

                # Remove empty queues
                if not queue:
                    del self.queues[client_id]

            if cleaned_count > 0:
                logger.debug(f"Cleaned up {cleaned_count} expired messages")


class WebSocketManager(BaseComponent, IWebSocketBroadcaster):
    """
    Manages WebSocket connections and broadcasts events to subscribed clients
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("websocket_manager", config or {})

        # Connection management
        self.active_connections: Set[Any] = set()  # WebSocket connections
        self.subscriptions: Dict[str, Set[Any]] = defaultdict(set)  # channel -> connections
        self.websocket_to_connection_id: Dict[Any, str] = {}  # websocket -> connection_id

        # Message queuing for offline clients
        self.message_queue = MessageQueue(
            max_messages_per_client=config.get("max_queued_messages_per_client", 100) if config else 100,
            default_ttl=config.get("message_queue_ttl", 3600) if config else 3600
        )

        # Health monitoring
        self.connection_health: Dict[str, Dict[str, Any]] = {}
        # Subscription history for offline queuing (preserved after disconnect)
        self.subscription_history: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

        # Metrics
        self.messages_sent = 0
        self.connections_accepted = 0
        self.connections_closed = 0
        self.broadcast_errors = 0
        self.queued_messages = 0
        self.delivered_queued_messages = 0

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

        # Subscribe to ML training events
        self.event_bus.subscribe("ml.training.status", self._handle_ml_training_event)
        self.event_bus.subscribe("ml.model.metrics", self._handle_ml_metrics_event)

        # Subscribe to database events
        self.event_bus.subscribe("db.event_stored", self._handle_db_event)

        # Subscribe to SIEM events
        self.event_bus.subscribe("siem.event_forwarded", self._handle_siem_event)
        self.event_bus.subscribe("siem.event_failed", self._handle_siem_event)

        # Start periodic cleanup task
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

        logger.info("WebSocket manager initialized and subscribed to event bus")
        self.metrics_collector = None  # Will be set by parent if needed

    async def _start_internal(self):
        """Start WebSocket manager operations"""
        logger.info("WebSocket manager started")

    async def _stop_internal(self):
        """Stop WebSocket manager and close all connections"""
        logger.info("Stopping WebSocket manager...")

        # Cancel cleanup task
        if hasattr(self, 'cleanup_task') and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

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
        self.websocket_to_connection_id.clear()
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

                # Store websocket to connection_id mapping
                self.websocket_to_connection_id[websocket] = connection_id

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

                # Remove websocket to connection_id mapping
                if websocket in self.websocket_to_connection_id:
                    del self.websocket_to_connection_id[websocket]

                # Remove from all subscriptions
                for channel, connections in self.subscriptions.items():
                    if websocket in connections:
                        connections.discard(websocket)
                        if connection_id and connection_id in self.connection_health:
                            self.connection_health[connection_id]["subscriptions"].discard(channel)
                        logger.debug(f"Removed connection from channel: {channel}")

                # Clean up empty channels
                empty_channels = [ch for ch, connections in list(self.subscriptions.items()) if len(connections) == 0]
                for channel in empty_channels:
                    del self.subscriptions[channel]

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

                # Update subscription history for offline queuing
                if connection_id:
                    self.subscription_history[connection_id].add(channel)

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
                # Remove from subscriptions (if channel exists)
                if channel in self.subscriptions:
                    self.subscriptions[channel].discard(websocket)

                    # Clean up empty channels
                    if len(self.subscriptions[channel]) == 0:
                        del self.subscriptions[channel]

                    # Update health tracking
                    if connection_id and connection_id in self.connection_health:
                        self.connection_health[connection_id]["subscriptions"].discard(channel)

                    logger.debug(f"WebSocket unsubscribed from channel '{channel}': {connection_id}")
                
                # Return True even if already unsubscribed (idempotent operation)
                return True

        except Exception as e:
            logger.error(f"Error unsubscribing from channel {channel}: {e}")
            return False

    async def broadcast(self, channel: str, data: Dict[str, Any], queue_for_offline: bool = True) -> int:
        """
        Broadcast data to all subscribers of a channel

        Args:
            channel: Channel name
            data: Data to broadcast
            queue_for_offline: Whether to queue messages for offline subscribers

        Returns:
            recipients_count: Number of clients that received the message
        """
        try:
            # Compress message if it's large
            message, is_compressed = self.compress_message(data)
            recipients = 0
            disconnected = set()

            with self._lock:
                if channel not in self.subscriptions:
                    logger.debug(f"No subscribers for channel: {channel}")
                    return 0

                connections = self.subscriptions[channel].copy()

                # If queue_for_offline is enabled, queue for subscribers who aren't currently connected
                if queue_for_offline:
                    # Get all clients who have ever subscribed to this channel (from subscription history)
                    all_subscribers = set()
                    for conn_id, channels in self.subscription_history.items():
                        if channel in channels:
                            all_subscribers.add(conn_id)

                    # Queue for offline subscribers (those not in active connections)
                    active_client_ids = set()
                    for ws in connections:
                        if ws in self.websocket_to_connection_id:
                            active_client_ids.add(self.websocket_to_connection_id[ws])

                    offline_subscribers = all_subscribers - active_client_ids

                    for client_id in offline_subscribers:
                        priority = self.prioritize_message(channel, data)
                        self.message_queue.enqueue_message(client_id, channel, data, priority=priority)
                        self.queued_messages += 1

            # Send to all active subscribers
            for websocket in connections:
                try:
                    # Send message with compression metadata if compressed
                    if is_compressed:
                        compressed_message = json.dumps({
                            "type": "compressed_message",
                            "compressed": True,
                            "data": message
                        })
                        await websocket.send_text(compressed_message)
                    else:
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
                        # Clean up websocket to connection_id mapping and health tracking
                        if ws in self.websocket_to_connection_id:
                            conn_id = self.websocket_to_connection_id[ws]
                            if conn_id in self.connection_health:
                                del self.connection_health[conn_id]
                            del self.websocket_to_connection_id[ws]
                        # Remove from all subscriptions
                        for ch, connections in self.subscriptions.items():
                            connections.discard(ws)

                        # Clean up empty channels
                        empty_channels = [ch for ch, connections in list(self.subscriptions.items()) if len(connections) == 0]
                        for channel in empty_channels:
                            del self.subscriptions[channel]
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
                connection_id = self.websocket_to_connection_id.get(ws)
                await self.disconnect(ws, connection_id)

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

    async def deliver_queued_messages(self, websocket: Any, connection_id: str, channel: Optional[str] = None) -> int:
        """
        Deliver queued messages to a reconnected client

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
            channel: Optional channel filter

        Returns:
            messages_delivered: Number of messages delivered
        """
        try:
            queued_messages = self.message_queue.dequeue_messages(connection_id, channel)
            delivered = 0

            for message in queued_messages:
                try:
                    # Convert message back to JSON format
                    message_data = {
                        "type": message.data.get("type", "queued_message"),
                        "data": message.data,
                        "timestamp": message.timestamp,
                        "queued": True,
                        "message_id": message.message_id,
                        "channel": message.channel
                    }

                    await websocket.send_text(json.dumps(message_data))
                    delivered += 1
                    self.delivered_queued_messages += 1

                except Exception as e:
                    logger.warning(f"Failed to deliver queued message {message.message_id}: {e}")
                    continue

            if delivered > 0:
                logger.info(f"Delivered {delivered} queued messages to client {connection_id}")

            return delivered

        except Exception as e:
            logger.error(f"Error delivering queued messages to {connection_id}: {e}")
            return 0

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
                "queued_messages": self.queued_messages,
                "delivered_queued_messages": self.delivered_queued_messages,
                "uptime": time.time() - getattr(self, 'start_time', time.time())
            }

    def filter_message(self, channel: str, data: Dict[str, Any], client_permissions: Set[str]) -> bool:
        """
        Filter messages based on client permissions and content

        Args:
            channel: Message channel
            data: Message data
            client_permissions: Client's permissions

        Returns:
            should_send: Whether the client should receive this message
        """
        # Channel-based filtering
        channel_filters = {
            "threats": lambda data, perms: "READ_THREATS" in perms or "ADMIN" in perms,
            "alerts": lambda data, perms: "READ_ALERTS" in perms or "ADMIN" in perms,
            "metrics": lambda data, perms: "READ_METRICS" in perms or "ADMIN" in perms,
            "status": lambda data, perms: True,  # System status is generally available
            "network": lambda data, perms: "READ_NETWORK_TRAFFIC" in perms or "ADMIN" in perms,
            "packets": lambda data, perms: "READ_PACKETS" in perms or "ADMIN" in perms,
        }

        filter_func = channel_filters.get(channel)
        if filter_func:
            return filter_func(data, client_permissions)

        return True  # Default to allowing messages

    def prioritize_message(self, channel: str, data: Dict[str, Any]) -> int:
        """
        Determine message priority for queuing

        Args:
            channel: Message channel
            data: Message data

        Returns:
            priority: Message priority (1=normal, 2=high, 3=critical)
        """
        # Priority based on message type and channel
        msg_type = data.get("type", "")

        # Critical alerts and threats
        if msg_type in ["alert.critical", "threat.critical"] or channel == "alerts":
            return 3

        # High priority for active threats and system issues
        if msg_type in ["threat.new", "system.error", "system.warning"]:
            return 2

        # Normal priority for metrics and status updates
        return 1

    def compress_message(self, data: Dict[str, Any], min_size: int = 1024) -> tuple[str, bool]:
        """
        Compress message if it's above minimum size

        Args:
            data: Message data
            min_size: Minimum size threshold for compression

        Returns:
            tuple: (message_string, is_compressed)
        """
        try:
            message = json.dumps(data)
            if len(message) < min_size:
                return message, False

            # Compress the message
            compressed = gzip.compress(message.encode('utf-8'))
            # Base64 encode for safe WebSocket transmission
            encoded = base64.b64encode(compressed).decode('utf-8')

            # Only use compression if it's actually smaller
            if len(encoded) < len(message):
                return encoded, True
            else:
                return message, False

        except Exception as e:
            logger.warning(f"Failed to compress message: {e}")
            return json.dumps(data), False

    def decompress_message(self, message: str, is_compressed: bool) -> Dict[str, Any]:
        """
        Decompress message if it was compressed

        Args:
            message: Message string
            is_compressed: Whether the message is compressed

        Returns:
            data: Decompressed message data
        """
        try:
            if not is_compressed:
                return json.loads(message)

            # Decode and decompress
            compressed = base64.b64decode(message)
            decompressed = gzip.decompress(compressed)
            return json.loads(decompressed.decode('utf-8'))

        except Exception as e:
            logger.warning(f"Failed to decompress message: {e}")
            return json.loads(message)  # Fallback to treating as uncompressed

    def create_message_batch(self, messages: List[Dict[str, Any]], max_batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Create message batches for efficient transmission

        Args:
            messages: List of messages to batch
            max_batch_size: Maximum messages per batch

        Returns:
            batches: List of message batches
        """
        if len(messages) <= max_batch_size:
            return [{
                "type": "message_batch",
                "messages": messages,
                "batch_size": len(messages),
                "timestamp": time.time()
            }]

        # Split into batches
        batches = []
        for i in range(0, len(messages), max_batch_size):
            batch = messages[i:i + max_batch_size]
            batches.append({
                "type": "message_batch",
                "messages": batch,
                "batch_size": len(batch),
                "batch_id": f"batch_{int(time.time() * 1000)}_{i}",
                "timestamp": time.time()
            })

        return batches

    def get_connection_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive connection analytics

        Returns:
            analytics: Connection analytics data
        """
        with self._lock:
            current_time = time.time()
            analytics = {
                "timestamp": current_time,
                "active_connections": len(self.active_connections),
                "total_connections_accepted": self.connections_accepted,
                "total_connections_closed": self.connections_closed,
                "channels": {},
                "client_analytics": {},
                "performance_metrics": {
                    "messages_per_second": self.messages_sent / max(1, current_time - getattr(self, 'start_time', current_time)),
                    "broadcast_errors_rate": self.broadcast_errors / max(1, self.messages_sent),
                    "queue_utilization": len(self.message_queue.queues) if hasattr(self.message_queue, 'queues') else 0,
                }
            }

            # Channel analytics
            for channel, connections in self.subscriptions.items():
                analytics["channels"][channel] = {
                    "active_subscribers": len(connections),
                    "subscriber_ids": list(self.websocket_to_connection_id.get(ws, "unknown") for ws in connections)
                }

            # Client analytics
            for conn_id, health in self.connection_health.items():
                analytics["client_analytics"][conn_id] = {
                    "connected_at": health.get("connected_at"),
                    "last_ping": health.get("last_ping"),
                    "subscriptions": list(health.get("subscriptions", set())),
                    "messages_sent": health.get("messages_sent", 0),
                    "connection_age": current_time - health.get("connected_at", current_time),
                    "client_info": health.get("client_info", {})
                }

            return analytics

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get WebSocket performance metrics

        Returns:
            metrics: Performance metrics
        """
        current_time = time.time()
        uptime = current_time - getattr(self, 'start_time', current_time)

        return {
            "uptime_seconds": uptime,
            "connections": {
                "active": len(self.active_connections),
                "total_accepted": self.connections_accepted,
                "total_closed": self.connections_closed,
                "acceptance_rate": self.connections_accepted / max(1, uptime),
                "closure_rate": self.connections_closed / max(1, uptime)
            },
            "messages": {
                "total_sent": self.messages_sent,
                "total_queued": self.queued_messages,
                "total_delivered_from_queue": self.delivered_queued_messages,
                "send_rate": self.messages_sent / max(1, uptime),
                "queue_delivery_rate": self.delivered_queued_messages / max(1, self.queued_messages) if self.queued_messages > 0 else 0
            },
            "errors": {
                "broadcast_errors": self.broadcast_errors,
                "error_rate": self.broadcast_errors / max(1, self.messages_sent)
            },
            "channels": {
                "total_channels": len(self.subscriptions),
                "total_subscriptions": sum(len(connections) for connections in self.subscriptions.values())
            }
        }

    async def _periodic_cleanup(self):
        """Periodic cleanup of expired messages and health monitoring"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes

                # Clean up expired queued messages
                self.message_queue.cleanup_expired_messages()

                # Clean up stale connection health data
                current_time = time.time()
                stale_threshold = 3600  # 1 hour

                with self._lock:
                    stale_connections = []
                    for conn_id, health in list(self.connection_health.items()):
                        if conn_id not in self.websocket_to_connection_id.values():
                            # Connection no longer exists
                            connected_at = health.get("connected_at", 0)
                            if current_time - connected_at > stale_threshold:
                                stale_connections.append(conn_id)

                    for conn_id in stale_connections:
                        logger.debug(f"Removing stale connection health data for {conn_id}")
                        del self.connection_health[conn_id]

                logger.debug("Periodic cleanup completed")

            except asyncio.CancelledError:
                logger.info("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying

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

    async def _handle_ml_training_event(self, event):
        """
        Handle ML training status events from the event bus

        Args:
            event: Event bus event
        """
        try:
            # Broadcast ML training status to WebSocket clients
            await self.broadcast("ml", event.data)
        except Exception as e:
            logger.error(f"Error handling ML training event: {e}")

    async def _handle_ml_metrics_event(self, event):
        """
        Handle ML model metrics events from the event bus

        Args:
            event: Event bus event
        """
        try:
            # Broadcast ML metrics to WebSocket clients
            await self.broadcast("metrics", event.data)
        except Exception as e:
            logger.error(f"Error handling ML metrics event: {e}")

    async def _handle_db_event(self, event):
        """
        Handle database events from the event bus

        Args:
            event: Event bus event
        """
        try:
            # Broadcast database events to WebSocket clients
            event_data = event.data
            event_type = event_data.get("event_type", "unknown")

            # Route to appropriate channels based on event type
            if event_type == "events":
                await self.broadcast("events", event_data)
            elif event_type == "metrics":
                await self.broadcast("metrics", event_data)
            else:
                # Generic database events go to events channel
                await self.broadcast("events", event_data)
        except Exception as e:
            logger.error(f"Error handling database event: {e}")

    async def _handle_siem_event(self, event):
        """
        Handle SIEM events from the event bus

        Args:
            event: Event bus event
        """
        try:
            # Broadcast SIEM events to WebSocket clients
            await self.broadcast("events", event.data)
        except Exception as e:
            logger.error(f"Error handling SIEM event: {e}")

    async def broadcast_threat_score(self, threat_score_data: Dict[str, Any]):
        """
        Broadcast threat score updates for live dashboards

        Args:
            threat_score_data: Threat score data to broadcast
        """
        event_data = {
            "type": "threat.score",
            "data": threat_score_data,
            "timestamp": time.time()
        }
        await self.broadcast("threats", event_data)

    async def broadcast_metrics(self, metrics_data: Dict[str, Any]):
        """
        Broadcast metrics updates for live dashboards

        Args:
            metrics_data: Metrics data to broadcast
        """
        event_data = {
            "type": "metrics.update",
            "data": metrics_data,
            "timestamp": time.time()
        }
        await self.broadcast("metrics", event_data)

    async def broadcast_network_traffic(self, traffic_data: Dict[str, Any]):
        """
        Broadcast network traffic updates

        Args:
            traffic_data: Network traffic data to broadcast
        """
        event_data = {
            "type": "network.traffic",
            "data": traffic_data,
            "timestamp": time.time()
        }
        await self.broadcast("network", event_data)

    async def broadcast_packet_analysis(self, packet_data: Dict[str, Any]):
        """
        Broadcast packet analysis results

        Args:
            packet_data: Packet analysis data to broadcast
        """
        event_data = {
            "type": "packet.analysis",
            "data": packet_data,
            "timestamp": time.time()
        }
        await self.broadcast("packets", event_data)