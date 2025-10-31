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
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from pydantic import BaseModel

from ..core.base import BaseComponent
from ..monitoring.logger import create_logger
from .websocket_manager import WebSocketManager

logger = create_logger("websocket_server")


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

    async def websocket_endpoint(
        self,
        websocket: WebSocket,
        token: Optional[str] = None,  # Auth integration point
    ):
        """
        WebSocket endpoint handler
        Handles connection lifecycle and message routing

        Args:
            websocket: FastAPI WebSocket connection
            token: Authentication token (when auth is integrated)
        """
        connection_id = None

        try:
            # Authenticate connection if auth is configured
            if self.auth_dependency:
                # This would be replaced with actual auth logic when integrated
                # For now, it's a placeholder that accepts all connections
                logger.debug("WebSocket authentication check (placeholder)")
                # auth_result = await self.auth_dependency(token)
                # if not auth_result:
                #     await websocket.close(code=4001, reason="Authentication failed")
                #     return

            # Accept connection
            client_info = {
                "ip": getattr(websocket, 'client', {}).get('host', 'unknown'),
                "user_agent": getattr(websocket, 'headers', {}).get('user-agent', 'unknown'),
                "token": token,
                "connected_at": time.time()
            }

            connection_id = await self.websocket_manager.connect(websocket, client_info)

            logger.info(f"WebSocket connection established: {connection_id}")

            # Send welcome message
            welcome_msg = {
                "type": "connection.established",
                "data": {
                    "connection_id": connection_id,
                    "server_time": time.time(),
                    "available_channels": ["threats", "alerts", "status", "metrics"]
                }
            }
            await websocket.send_text(json.dumps(welcome_msg))

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
        allowed_channels = ["threats", "alerts", "status", "metrics", "events"]
        if channel not in allowed_channels:
            await self._send_error(websocket, f"Invalid channel: {channel}. Allowed: {allowed_channels}")
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
