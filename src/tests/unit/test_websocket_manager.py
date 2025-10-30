#!/usr/bin/env python3
"""
Unit tests for WebSocket Manager
"""

import asyncio
import json
import pytest
import pytest_asyncio
import time
from unittest.mock import Mock, AsyncMock
from src.netsentinel.processors.websocket_manager import WebSocketManager


class TestWebSocketManager:
    """Test cases for WebSocketManager"""

    @pytest_asyncio.fixture
    async def manager(self):
        """Create WebSocketManager instance"""
        manager = WebSocketManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_initialization(self, manager):
        """Test manager initialization"""
        assert manager.active_connections == set()
        assert manager.subscriptions == {}
        assert manager.messages_sent == 0
        assert manager.connections_accepted == 0

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test WebSocket connection acceptance"""
        connection_id = await manager.connect(mock_websocket)

        assert connection_id.startswith("ws_")
        assert mock_websocket in manager.active_connections
        assert manager.connections_accepted == 1
        assert connection_id in manager.connection_health

        # Verify health tracking
        health = manager.connection_health[connection_id]
        assert "connected_at" in health
        assert "subscriptions" in health
        assert health["messages_sent"] == 0

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test WebSocket disconnection"""
        # Connect first
        connection_id = await manager.connect(mock_websocket)
        assert mock_websocket in manager.active_connections

        # Disconnect
        await manager.disconnect(mock_websocket, connection_id)

        assert mock_websocket not in manager.active_connections
        assert manager.connections_closed == 1
        assert connection_id not in manager.connection_health

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, manager, mock_websocket):
        """Test channel subscription and unsubscription"""
        # Connect first
        connection_id = await manager.connect(mock_websocket)

        # Subscribe to channel
        success = await manager.subscribe(mock_websocket, "threats", connection_id)
        assert success
        assert mock_websocket in manager.subscriptions["threats"]
        assert "threats" in manager.connection_health[connection_id]["subscriptions"]

        # Subscribe to another channel
        success = await manager.subscribe(mock_websocket, "alerts", connection_id)
        assert success
        assert mock_websocket in manager.subscriptions["alerts"]
        assert "alerts" in manager.connection_health[connection_id]["subscriptions"]

        # Unsubscribe from first channel
        success = await manager.unsubscribe(mock_websocket, "threats", connection_id)
        assert success
        assert mock_websocket not in manager.subscriptions["threats"]
        assert "threats" not in manager.connection_health[connection_id]["subscriptions"]

        # Unsubscribe from non-existent channel should return False
        success = await manager.unsubscribe(mock_websocket, "nonexistent", connection_id)
        assert not success

    @pytest.mark.asyncio
    async def test_broadcast(self, manager, mock_websocket):
        """Test message broadcasting"""
        # Connect and subscribe
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(mock_websocket, "threats", connection_id)

        # Broadcast message
        data = {"type": "threat.new", "data": {"ip": "192.168.1.1"}}
        recipients = await manager.broadcast("threats", data)

        assert recipients == 1
        assert manager.messages_sent == 1
        mock_websocket.send_text.assert_called_once()

        # Verify message content
        call_args = mock_websocket.send_text.call_args[0][0]
        sent_data = json.loads(call_args)
        assert sent_data == data

    @pytest.mark.asyncio
    async def test_broadcast_no_subscribers(self, manager):
        """Test broadcasting to channel with no subscribers"""
        recipients = await manager.broadcast("empty_channel", {"test": "data"})
        assert recipients == 0
        assert manager.messages_sent == 0

    @pytest.mark.asyncio
    async def test_broadcast_with_disconnected_client(self, manager, mock_websocket):
        """Test broadcasting when client gets disconnected"""
        # Connect and subscribe
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(mock_websocket, "threats", connection_id)

        # Make websocket throw exception on send
        mock_websocket.send_text.side_effect = Exception("Connection lost")

        # Broadcast - should handle disconnected client
        recipients = await manager.broadcast("threats", {"test": "data"})

        # Should have 0 recipients due to disconnection cleanup
        assert recipients == 0
        assert manager.broadcast_errors == 1
        assert mock_websocket not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_threat_interface(self, manager, mock_websocket):
        """Test IWebSocketBroadcaster interface for threats"""
        # Connect and subscribe
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(mock_websocket, "threats", connection_id)

        # Broadcast threat
        threat_data = {
            "source_ip": "192.168.1.100",
            "threat_score": 8.5,
            "threat_level": "high"
        }
        await manager.broadcast_threat(threat_data)

        # Verify message format
        call_args = mock_websocket.send_text.call_args[0][0]
        sent_data = json.loads(call_args)
        assert sent_data["type"] == "threat.new"
        assert sent_data["data"] == threat_data
        assert "timestamp" in sent_data

    @pytest.mark.asyncio
    async def test_broadcast_alert_interface(self, manager, mock_websocket):
        """Test IWebSocketBroadcaster interface for alerts"""
        # Connect and subscribe
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(mock_websocket, "alerts", connection_id)

        # Broadcast alert
        alert_data = {
            "id": "alert_123",
            "severity": "critical",
            "message": "High threat detected"
        }
        await manager.broadcast_alert(alert_data)

        # Verify message format
        call_args = mock_websocket.send_text.call_args[0][0]
        sent_data = json.loads(call_args)
        assert sent_data["type"] == "alert.new"
        assert sent_data["data"] == alert_data
        assert "timestamp" in sent_data

    @pytest.mark.asyncio
    async def test_get_connection_stats(self, manager, mock_websocket):
        """Test connection statistics"""
        # Connect and subscribe
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(mock_websocket, "threats", connection_id)
        await manager.subscribe(mock_websocket, "alerts", connection_id)

        # Broadcast some messages
        await manager.broadcast("threats", {"test": "data"})
        await manager.broadcast("alerts", {"test": "data"})

        # Get stats
        stats = manager.get_connection_stats()

        assert stats["active_connections"] == 1
        assert stats["channels"] == 2
        assert stats["channel_subscriptions"]["threats"] == 1
        assert stats["channel_subscriptions"]["alerts"] == 1
        assert stats["total_messages_sent"] == 2
        assert stats["total_connections_accepted"] == 1
        assert stats["total_connections_closed"] == 0
        assert stats["broadcast_errors"] == 0

    @pytest.mark.asyncio
    async def test_get_channel_subscribers(self, manager, mock_websocket):
        """Test getting subscriber count for channels"""
        # No subscribers initially
        assert manager.get_channel_subscribers("threats") == 0

        # Connect and subscribe
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(mock_websocket, "threats", connection_id)

        assert manager.get_channel_subscribers("threats") == 1
        assert manager.get_channel_subscribers("alerts") == 0

    @pytest.mark.asyncio
    async def test_cleanup_on_disconnect(self, manager, mock_websocket):
        """Test that subscriptions are cleaned up on disconnect"""
        # Connect and subscribe to multiple channels
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(mock_websocket, "threats", connection_id)
        await manager.subscribe(mock_websocket, "alerts", connection_id)
        await manager.subscribe(mock_websocket, "metrics", connection_id)

        assert len(manager.subscriptions) == 3

        # Disconnect
        await manager.disconnect(mock_websocket, connection_id)

        # All subscriptions should be cleaned up
        assert len(manager.subscriptions) == 0
        for channel in ["threats", "alerts", "metrics"]:
            assert channel not in manager.subscriptions or len(manager.subscriptions[channel]) == 0
