#!/usr/bin/env python3
"""
WebSocket Server for NetSentinel
Handles WebSocket connections and real-time event broadcasting
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, Callable
from collections import defaultdict
import threading
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from pydantic import BaseModel

from ..core.base import BaseComponent
from ..monitoring.logger import create_logger
from .websocket_manager import WebSocketManager

logger = create_logger("websocket_server")


class ConnectionRateLimiter:
    """
    Rate limiter for WebSocket connections to prevent abuse
    """

    def __init__(self, max_connections_per_ip: int = 10, window_seconds: int = 60):
        self.max_connections_per_ip = max_connections_per_ip
        self.window_seconds = window_seconds
        self.connections: Dict[str, list] = defaultdict(list)
        self._lock = threading.RLock()

    def allow_connection(self, ip_address: str) -> bool:
        """
        Check if a connection from this IP should be allowed

        Args:
            ip_address: Client IP address

        Returns:
            bool: True if connection is allowed, False if rate limited
        """
        with self._lock:
            current_time = time.time()

            # Clean up old connection attempts
            self.connections[ip_address] = [
                timestamp for timestamp in self.connections[ip_address]
                if current_time - timestamp < self.window_seconds
            ]

            # Check if under limit
            if len(self.connections[ip_address]) < self.max_connections_per_ip:
                self.connections[ip_address].append(current_time)
                return True

            return False

    def get_connection_count(self, ip_address: str) -> int:
        """Get current connection count for an IP"""
        with self._lock:
            current_time = time.time()
            # Clean up old entries
            self.connections[ip_address] = [
                timestamp for timestamp in self.connections[ip_address]
                if current_time - timestamp < self.window_seconds
            ]
            return len(self.connections[ip_address])


class WebSocketMessage(BaseModel):
    """WebSocket message model"""

    type: str
    channel: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class WebSocketServer(BaseComponent):
    """
    WebSocket server component that handles real-time connections
    Integrates with FastAPI and WebSocketManager
    """

    def __init__(self, websocket_manager: WebSocketManager, config: Optional[Dict[str, Any]] = None):
        super().__init__("websocket_server", config or {})
        self.websocket_manager = websocket_manager
        self.auth_dependency: Optional[Callable] = None  # Will be set by auth integration
        self.auth_manager = None  # Will be set by auth integration
        self.rate_limiter = ConnectionRateLimiter(
            max_connections_per_ip=config.get("max_connections_per_ip", 10) if config else 10,
            window_seconds=config.get("rate_limit_window", 60) if config else 60
        )
        self._running = False

    async def _initialize(self):
        """Initialize WebSocket server"""
        if not self.websocket_manager:
            raise ValueError("WebSocketManager is required")

        logger.info("WebSocket server initialized")

    async def _start_internal(self):
        """Start WebSocket server operations"""
        logger.info("WebSocket server started")

    async def _stop_internal(self):
        """Stop WebSocket server"""
        logger.info("WebSocket server stopped")
        self._running = False

    def set_auth_dependency(self, auth_dependency: Callable):
        """
        Set authentication dependency for WebSocket connections
        This is an integration point for the auth system

        Args:
            auth_dependency: FastAPI dependency function for authentication
        """
        self.auth_dependency = auth_dependency
        logger.info("WebSocket authentication dependency configured")

    def set_auth_manager(self, auth_manager):
        """
        Set authentication manager for WebSocket connections
        Direct integration with NetSentinel auth system

        Args:
            auth_manager: AuthManager instance
        """
        self.auth_manager = auth_manager
        logger.info("WebSocket authentication manager configured")

    async def websocket_endpoint(
        self,
        websocket: WebSocket,
        token: Optional[str] = None,  # Auth integration point
        auto_subscribe: Optional[str] = None,  # Auto-subscribe to channel
        reconnect_id: Optional[str] = None,  # For connection recovery
    ):
        """
        WebSocket endpoint handler
        Handles connection lifecycle and message routing

        Args:
            websocket: FastAPI WebSocket connection
            token: Authentication token (when auth is integrated)
            auto_subscribe: Channel to automatically subscribe to (optional)
            reconnect_id: Previous connection ID for recovery (optional)
        """
        connection_id = None

        try:
            # Rate limiting check
            client_ip = getattr(websocket, 'client', {}).get('host', 'unknown')
            if not self.rate_limiter.allow_connection(client_ip):
                logger.warning(f"WebSocket connection rate limited for IP: {client_ip}")
                await websocket.close(code=4002, reason="Rate limit exceeded")
                return

            # Authenticate connection if auth is configured
            user = None
            if self.auth_manager and token:
                # Authenticate using NetSentinel auth manager
                client_ip = getattr(websocket, 'client', {}).get('host', 'unknown')
                user_agent = getattr(websocket, 'headers', {}).get('user-agent', 'unknown')
                user = self.auth_manager.authenticate_token(token, client_ip, user_agent)

                if not user:
                    logger.warning(f"WebSocket authentication failed for token: {token[:20]}...")
                    await websocket.close(code=4001, reason="Authentication failed")
                    return

                logger.info(f"WebSocket authenticated user: {user.username} ({user.user_id})")

            elif self.auth_dependency:
                # Fallback to dependency injection approach
                logger.debug("WebSocket authentication check (dependency)")
                # auth_result = await self.auth_dependency(token)
                # if not auth_result:
                #     await websocket.close(code=4001, reason="Authentication failed")
                #     return

            # Accept connection
            client_info = {
                "ip": getattr(websocket, 'client', {}).get('host', 'unknown'),
                "user_agent": getattr(websocket, 'headers', {}).get('user-agent', 'unknown'),
                "token": token,
                "connected_at": time.time(),
                "user_id": user.user_id if user else None,
                "username": user.username if user else None,
                "authenticated": user is not None
            }

            connection_id = await self.websocket_manager.connect(websocket, client_info)

            # Handle reconnection if reconnect_id is provided
            restored_subscriptions = []
            if reconnect_id and reconnect_id in self.websocket_manager.connection_health:
                # Restore previous subscriptions
                old_connection_info = self.websocket_manager.connection_health[reconnect_id]
                old_subscriptions = old_connection_info.get("subscriptions", set())

                for channel in old_subscriptions:
                    if await self._authorize_channel_access(websocket, connection_id, channel):
                        success = await self.websocket_manager.subscribe(websocket, channel, connection_id)
                        if success:
                            restored_subscriptions.append(channel)
                            logger.info(f"Restored subscription to channel '{channel}' for reconnected client {connection_id}")

                # Clean up old connection info after successful restoration
                if restored_subscriptions:
                    del self.websocket_manager.connection_health[reconnect_id]
                    logger.info(f"Restored {len(restored_subscriptions)} subscriptions for reconnected client {connection_id}")

            # Deliver queued messages to reconnected clients
            if reconnect_id or restored_subscriptions:
                delivered_count = await self.websocket_manager.deliver_queued_messages(websocket, connection_id)
                if delivered_count > 0:
                    logger.info(f"Delivered {delivered_count} queued messages to reconnected client {connection_id}")

            logger.info(f"WebSocket connection established: {connection_id}")

            # Send welcome message
            welcome_msg = {
                "type": "connection.established",
                "data": {
                    "connection_id": connection_id,
                    "server_time": time.time(),
                    "available_channels": ["threats", "alerts", "status", "metrics", "events", "network", "packets", "ml"],
                    "auto_subscribed": auto_subscribe if auto_subscribe else None,
                    "restored_subscriptions": restored_subscriptions if restored_subscriptions else None,
                    "reconnected": bool(reconnect_id and restored_subscriptions)
                }
            }
            await websocket.send_text(json.dumps(welcome_msg))

            # Auto-subscribe to channel if specified
            if auto_subscribe:
                try:
                    # Check authorization
                    if await self._authorize_channel_access(websocket, connection_id, auto_subscribe):
                        success = await self.websocket_manager.subscribe(websocket, auto_subscribe, connection_id)
                        if success:
                            logger.info(f"Auto-subscribed connection {connection_id} to channel '{auto_subscribe}'")
                            # Send subscription confirmation
                            sub_msg = {
                                "type": "subscribed",
                                "data": {
                                    "channel": auto_subscribe,
                                    "subscriber_count": self.websocket_manager.get_channel_subscribers(auto_subscribe),
                                    "auto_subscribed": True
                                }
                            }
                            await websocket.send_text(json.dumps(sub_msg))
                        else:
                            logger.warning(f"Failed to auto-subscribe connection {connection_id} to channel '{auto_subscribe}'")
                    else:
                        logger.warning(f"Auto-subscription denied for connection {connection_id} to channel '{auto_subscribe}'")
                        error_msg = {
                            "type": "error",
                            "data": {
                                "message": f"Access denied to channel: {auto_subscribe}",
                                "auto_subscription_failed": True
                            }
                        }
                        await websocket.send_text(json.dumps(error_msg))
                except Exception as e:
                    logger.error(f"Error during auto-subscription to {auto_subscribe}: {e}")

            # Handle incoming messages
            while True:
                try:
                    # Receive message with timeout
                    message_data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=30.0  # Keepalive timeout
                    )

                    await self._handle_message(websocket, connection_id, message_data)

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    ping_msg = {"type": "ping", "timestamp": time.time()}
                    await websocket.send_text(json.dumps(ping_msg))
                    continue

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {connection_id}")

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")

        finally:
            # Clean up connection
            if connection_id:
                await self.websocket_manager.disconnect(websocket, connection_id)

    async def _handle_message(self, websocket: WebSocket, connection_id: str, message_data: str):
        """
        Handle incoming WebSocket message

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
            message_data: Raw message data (JSON string)
        """
        try:
            # Parse message
            message = json.loads(message_data)
            msg_type = message.get("type", "unknown")
            channel = message.get("channel")
            data = message.get("data", {})

            logger.debug(f"Received WebSocket message: {msg_type} from {connection_id}")

            # Handle different message types
            if msg_type == "subscribe":
                await self._handle_subscribe(websocket, connection_id, channel, data)

            elif msg_type == "unsubscribe":
                await self._handle_unsubscribe(websocket, connection_id, channel, data)

            elif msg_type == "ping":
                await self._handle_ping(websocket, connection_id)

            elif msg_type == "status":
                await self._handle_status_request(websocket, connection_id)

            elif msg_type == "acknowledge":
                await self._handle_acknowledge(websocket, connection_id, data)

            elif msg_type == "compressed_message":
                await self._handle_compressed_message(websocket, connection_id, data)

            elif msg_type == "message_batch":
                await self._handle_message_batch(websocket, connection_id, data)

            else:
                # Unknown message type
                error_msg = {
                    "type": "error",
                    "data": {
                        "message": f"Unknown message type: {msg_type}",
                        "received_type": msg_type
                    }
                }
                await websocket.send_text(json.dumps(error_msg))

        except json.JSONDecodeError:
            # Invalid JSON
            error_msg = {
                "type": "error",
                "data": {
                    "message": "Invalid JSON format",
                    "received": message_data[:100]  # Truncate for logging
                }
            }
            await websocket.send_text(json.dumps(error_msg))

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            error_msg = {
                "type": "error",
                "data": {
                    "message": "Internal server error",
                    "error_id": f"ws_err_{int(time.time())}"
                }
            }
            await websocket.send_text(json.dumps(error_msg))

    async def _handle_subscribe(self, websocket: WebSocket, connection_id: str, channel: str, data: Dict[str, Any]):
        """
        Handle subscription request

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
            channel: Channel to subscribe to
            data: Additional subscription data
        """
        if not channel:
            await self._send_error(websocket, "Missing channel for subscription")
            return

        # Validate channel
        allowed_channels = ["threats", "alerts", "status", "metrics", "events", "network", "packets", "ml"]
        if channel not in allowed_channels:
            await self._send_error(websocket, f"Invalid channel: {channel}. Allowed: {allowed_channels}")
            return

        # Check authorization for channel subscription
        if not await self._authorize_channel_access(websocket, connection_id, channel):
            await self._send_error(websocket, f"Access denied to channel: {channel}")
            return

        # Subscribe
        success = await self.websocket_manager.subscribe(websocket, channel, connection_id)

        if success:
            response = {
                "type": "subscribed",
                "data": {
                    "channel": channel,
                    "subscriber_count": self.websocket_manager.get_channel_subscribers(channel)
                }
            }
        else:
            response = {
                "type": "error",
                "data": {
                    "message": f"Failed to subscribe to channel: {channel}"
                }
            }

        await websocket.send_text(json.dumps(response))

    async def _handle_unsubscribe(self, websocket: WebSocket, connection_id: str, channel: str, data: Dict[str, Any]):
        """
        Handle unsubscription request

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
            channel: Channel to unsubscribe from
            data: Additional unsubscription data
        """
        if not channel:
            await self._send_error(websocket, "Missing channel for unsubscription")
            return

        # Unsubscribe
        success = await self.websocket_manager.unsubscribe(websocket, channel, connection_id)

        if success:
            response = {
                "type": "unsubscribed",
                "data": {
                    "channel": channel,
                    "subscriber_count": self.websocket_manager.get_channel_subscribers(channel)
                }
            }
        else:
            response = {
                "type": "error",
                "data": {
                    "message": f"Failed to unsubscribe from channel: {channel}"
                }
            }

        await websocket.send_text(json.dumps(response))

    async def _handle_ping(self, websocket: WebSocket, connection_id: str):
        """
        Handle ping message

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
        """
        pong_msg = {
            "type": "pong",
            "timestamp": time.time()
        }
        await websocket.send_text(json.dumps(pong_msg))

    async def _handle_status_request(self, websocket: WebSocket, connection_id: str):
        """
        Handle status request

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
        """
        stats = self.websocket_manager.get_connection_stats()
        status_msg = {
            "type": "status",
            "data": {
                "websocket_stats": stats,
                "server_time": time.time(),
                "connection_id": connection_id
            }
        }
        await websocket.send_text(json.dumps(status_msg))

    async def _handle_acknowledge(self, websocket: WebSocket, connection_id: str, data: Dict[str, Any]):
        """
        Handle alert acknowledgment

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
            data: Acknowledgment data (alert_id, etc.)
        """
        try:
            alert_id = data.get("alert_id")
            if not alert_id:
                await self._send_error(websocket, "Missing alert_id for acknowledgment")
                return

            # Get user from connection info
            connection_info = self.websocket_manager.connection_health.get(connection_id, {})
            user_id = connection_info.get("user_id")
            username = connection_info.get("username", "unknown")

            if not user_id:
                await self._send_error(websocket, "Authentication required for alert acknowledgment")
                return

            # Check if alert manager is available
            try:
                from ..alerts import get_alert_manager
                alert_manager = get_alert_manager()
                if not alert_manager:
                    await self._send_error(websocket, "Alert system not available")
                    return

                # Attempt to acknowledge the alert
                success = alert_manager.acknowledge_alert(alert_id, username)

                if success:
                    response = {
                        "type": "acknowledged",
                        "data": {
                            "alert_id": alert_id,
                            "acknowledged_by": username,
                            "timestamp": time.time()
                        }
                    }
                    await websocket.send_text(json.dumps(response))

                    # Broadcast acknowledgment to other clients
                    broadcast_msg = {
                        "type": "alert.acknowledged",
                        "data": {
                            "alert_id": alert_id,
                            "acknowledged_by": username,
                            "timestamp": time.time()
                        }
                    }
                    await self.websocket_manager.broadcast("alerts", broadcast_msg)
                else:
                    await self._send_error(websocket, f"Failed to acknowledge alert: {alert_id}")

            except ImportError:
                await self._send_error(websocket, "Alert acknowledgment not supported")

        except Exception as e:
            logger.error(f"Error handling alert acknowledgment: {e}")
            await self._send_error(websocket, "Internal error during acknowledgment")

    async def _handle_compressed_message(self, websocket: WebSocket, connection_id: str, data: Dict[str, Any]):
        """
        Handle compressed message

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
            data: Compressed message data
        """
        try:
            compressed_data = data.get("data", "")
            if not compressed_data:
                await self._send_error(websocket, "Missing compressed data")
                return

            # Decompress the message
            decompressed_data = self.websocket_manager.decompress_message(compressed_data, True)

            # Process the decompressed message normally
            await self._handle_message(websocket, connection_id, json.dumps(decompressed_data))

        except Exception as e:
            logger.error(f"Error handling compressed message: {e}")
            await self._send_error(websocket, "Failed to decompress message")

    async def _handle_message_batch(self, websocket: WebSocket, connection_id: str, data: Dict[str, Any]):
        """
        Handle message batch

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
            data: Batch message data
        """
        try:
            messages = data.get("messages", [])
            batch_id = data.get("batch_id", "unknown")

            if not messages:
                await self._send_error(websocket, "Empty message batch")
                return

            processed = 0
            errors = 0

            for message in messages:
                try:
                    # Process each message in the batch
                    await self._handle_message(websocket, connection_id, json.dumps(message))
                    processed += 1
                except Exception as e:
                    logger.warning(f"Error processing message in batch {batch_id}: {e}")
                    errors += 1

            # Send batch acknowledgment
            response = {
                "type": "batch_processed",
                "data": {
                    "batch_id": batch_id,
                    "total_messages": len(messages),
                    "processed": processed,
                    "errors": errors,
                    "timestamp": time.time()
                }
            }
            await websocket.send_text(json.dumps(response))

            logger.info(f"Processed batch {batch_id}: {processed}/{len(messages)} messages")

        except Exception as e:
            logger.error(f"Error handling message batch: {e}")
            await self._send_error(websocket, "Failed to process message batch")

    async def _authorize_channel_access(self, websocket: WebSocket, connection_id: str, channel: str) -> bool:
        """
        Authorize access to a WebSocket channel

        Args:
            websocket: WebSocket connection
            connection_id: Connection identifier
            channel: Channel name

        Returns:
            bool: True if access is authorized, False otherwise
        """
        # Get user from connection info if available
        connection_info = self.websocket_manager.connection_health.get(connection_id, {})
        user_id = connection_info.get("user_id")

        # If no auth manager configured, allow access for basic channels
        if not self.auth_manager or not user_id:
            # Allow public channels for unauthenticated users
            public_channels = ["status"]  # Status channel is public
            return channel in public_channels

        # Get user object
        user = self.auth_manager.get_user(user_id)
        if not user:
            return False

        # Channel-specific authorization
        from ..security.user_store import Permission

        channel_permissions = {
            "threats": Permission.READ_EVENTS,  # Use existing permission for threats
            "alerts": Permission.READ_ALERTS,
            "metrics": Permission.READ_EVENTS,  # Use existing permission for metrics
            "events": Permission.READ_EVENTS,
            "status": Permission.READ_EVENTS,  # System status available to event readers
            "network": Permission.READ_EVENTS,  # Network traffic for event readers
            "packets": Permission.READ_EVENTS,  # Packet analysis for event readers
            "ml": Permission.READ_EVENTS,  # ML training status for event readers
        }

        required_permission = channel_permissions.get(channel)
        if not required_permission:
            return False

        return self.auth_manager.authorize(user, required_permission, f"websocket:{channel}")

    async def _send_error(self, websocket: WebSocket, message: str):
        """
        Send error message to client

        Args:
            websocket: WebSocket connection
            message: Error message
        """
        error_msg = {
            "type": "error",
            "data": {"message": message}
        }
        await websocket.send_text(json.dumps(error_msg))

    def get_connection_count(self) -> int:
        """
        Get current connection count

        Returns:
            count: Number of active connections
        """
        return len(self.websocket_manager.active_connections) if self.websocket_manager else 0

    def get_channel_stats(self) -> Dict[str, Any]:
        """
        Get channel subscription statistics

        Returns:
            stats: Channel statistics
        """
        return self.websocket_manager.get_connection_stats() if self.websocket_manager else {}
