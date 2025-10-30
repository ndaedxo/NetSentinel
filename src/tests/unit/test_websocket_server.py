#!/usr/bin/env python3
"""
Unit tests for WebSocket Server
"""

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.netsentinel.processors.websocket_server import WebSocketServer
from src.netsentinel.processors.websocket_manager import WebSocketManager


class TestWebSocketServer:
    """Test cases for WebSocketServer"""

    @pytest_asyncio.fixture
    async def manager(self):
        """Create WebSocketManager instance"""
        manager = WebSocketManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest_asyncio.fixture
    async def server(self, manager):
        """Create WebSocketServer instance"""
        server = WebSocketServer(manager)
        await server.start()
        yield server
        await server.stop()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = AsyncMock()
        ws.client = {"host": "127.0.0.1"}
        ws.headers = {"user-agent": "test-client"}
        ws.receive_text = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_initialization(self, server, manager):
        """Test server initialization"""
        assert server.websocket_manager == manager
        assert server.auth_dependency is None
        assert server._running is False

    @pytest.mark.asyncio
    async def test_set_auth_dependency(self, server):
        """Test setting authentication dependency"""
        mock_auth = Mock()
        server.set_auth_dependency(mock_auth)
        assert server.auth_dependency == mock_auth

    @pytest.mark.asyncio
    async def test_websocket_endpoint_connection(self, server, mock_websocket, manager):
        """Test basic WebSocket connection handling"""
        # Mock successful connection
        mock_websocket.receive_text.side_effect = [
            json.dumps({"type": "ping"}),  # First message
            asyncio.CancelledError()  # End connection
        ]

        # Run endpoint (will be cancelled by side effect)
        with pytest.raises(asyncio.CancelledError):
            await server.websocket_endpoint(mock_websocket)

        # Verify connection was accepted
        assert mock_websocket in manager.active_connections

        # Verify welcome message was sent
        welcome_call = mock_websocket.send_text.call_args_list[0][0][0]
        welcome_data = json.loads(welcome_call)
        assert welcome_data["type"] == "connection.established"
        assert "connection_id" in welcome_data["data"]

    @pytest.mark.asyncio
    async def test_message_handling_subscribe(self, server, mock_websocket, manager):
        """Test subscription message handling"""
        # Setup connection
        connection_id = await manager.connect(mock_websocket)

        # Test subscribe message
        subscribe_msg = {
            "type": "subscribe",
            "channel": "threats"
        }

        await server._handle_message(mock_websocket, connection_id, json.dumps(subscribe_msg))

        # Verify subscription response
        response_call = mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_call)
        assert response_data["type"] == "subscribed"
        assert response_data["data"]["channel"] == "threats"

        # Verify actual subscription
        assert mock_websocket in manager.subscriptions["threats"]

    @pytest.mark.asyncio
    async def test_message_handling_unsubscribe(self, server, mock_websocket, manager):
        """Test unsubscription message handling"""
        # Setup connection and subscription
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(mock_websocket, "threats", connection_id)

        # Test unsubscribe message
        unsubscribe_msg = {
            "type": "unsubscribe",
            "channel": "threats"
        }

        await server._handle_message(mock_websocket, connection_id, json.dumps(unsubscribe_msg))

        # Verify unsubscription response
        response_call = mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_call)
        assert response_data["type"] == "unsubscribed"
        assert response_data["data"]["channel"] == "threats"

        # Verify actual unsubscription
        assert mock_websocket not in manager.subscriptions["threats"]

    @pytest.mark.asyncio
    async def test_message_handling_ping(self, server, mock_websocket, manager):
        """Test ping message handling"""
        # Setup connection
        connection_id = await manager.connect(mock_websocket)

        # Test ping message
        ping_msg = {"type": "ping"}

        await server._handle_message(mock_websocket, connection_id, json.dumps(ping_msg))

        # Verify pong response
        response_call = mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_call)
        assert response_data["type"] == "pong"
        assert "timestamp" in response_data

    @pytest.mark.asyncio
    async def test_message_handling_status(self, server, mock_websocket, manager):
        """Test status request handling"""
        # Setup connection
        connection_id = await manager.connect(mock_websocket)

        # Test status message
        status_msg = {"type": "status"}

        await server._handle_message(mock_websocket, connection_id, json.dumps(status_msg))

        # Verify status response
        response_call = mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_call)
        assert response_data["type"] == "status"
        assert "websocket_stats" in response_data["data"]
        assert "server_time" in response_data["data"]
        assert response_data["data"]["connection_id"] == connection_id

    @pytest.mark.asyncio
    async def test_message_handling_invalid_json(self, server, mock_websocket, manager):
        """Test handling of invalid JSON"""
        # Setup connection
        connection_id = await manager.connect(mock_websocket)

        # Test invalid JSON
        await server._handle_message(mock_websocket, connection_id, "invalid json")

        # Verify error response
        response_call = mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_call)
        assert response_data["type"] == "error"
        assert "Invalid JSON format" in response_data["data"]["message"]

    @pytest.mark.asyncio
    async def test_message_handling_unknown_type(self, server, mock_websocket, manager):
        """Test handling of unknown message type"""
        # Setup connection
        connection_id = await manager.connect(mock_websocket)

        # Test unknown message type
        unknown_msg = {"type": "unknown_command"}

        await server._handle_message(mock_websocket, connection_id, json.dumps(unknown_msg))

        # Verify error response
        response_call = mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_call)
        assert response_data["type"] == "error"
        assert "Unknown message type" in response_data["data"]["message"]

    @pytest.mark.asyncio
    async def test_subscribe_invalid_channel(self, server, mock_websocket, manager):
        """Test subscription to invalid channel"""
        # Setup connection
        connection_id = await manager.connect(mock_websocket)

        # Test subscribe to invalid channel
        subscribe_msg = {
            "type": "subscribe",
            "channel": "invalid_channel"
        }

        await server._handle_message(mock_websocket, connection_id, json.dumps(subscribe_msg))

        # Verify error response
        response_call = mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_call)
        assert response_data["type"] == "error"
        assert "Invalid channel" in response_data["data"]["message"]

    @pytest.mark.asyncio
    async def test_subscribe_missing_channel(self, server, mock_websocket, manager):
        """Test subscription with missing channel"""
        # Setup connection
        connection_id = await manager.connect(mock_websocket)

        # Test subscribe without channel
        subscribe_msg = {"type": "subscribe"}

        await server._handle_message(mock_websocket, connection_id, json.dumps(subscribe_msg))

        # Verify error response
        response_call = mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_call)
        assert response_data["type"] == "error"
        assert "Missing channel for subscription" in response_data["data"]["message"]

    @pytest.mark.asyncio
    async def test_get_connection_count(self, server, mock_websocket, manager):
        """Test getting connection count"""
        assert server.get_connection_count() == 0

        # Connect a websocket
        await manager.connect(mock_websocket)
        assert server.get_connection_count() == 1

    @pytest.mark.asyncio
    async def test_get_channel_stats(self, server, mock_websocket, manager):
        """Test getting channel statistics"""
        # Connect and subscribe
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(mock_websocket, "threats", connection_id)

        stats = server.get_channel_stats()
        assert stats["active_connections"] == 1
        assert stats["channels"] == 1
        assert stats["channel_subscriptions"]["threats"] == 1
