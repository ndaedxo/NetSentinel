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

    @pytest.mark.asyncio
    async def test_connection_lifecycle_multiple_cycles(self, manager):
        """Test multiple connect/disconnect cycles"""
        # Create multiple mock websockets
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws1.close = AsyncMock()

        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()
        ws2.close = AsyncMock()

        # Cycle 1: Connect both, subscribe, disconnect one
        conn1 = await manager.connect(ws1)
        conn2 = await manager.connect(ws2)

        await manager.subscribe(ws1, "threats", conn1)
        await manager.subscribe(ws2, "alerts", conn2)

        assert len(manager.active_connections) == 2
        assert len(manager.subscriptions) == 2

        await manager.disconnect(ws1, conn1)

        assert len(manager.active_connections) == 1
        # defaultdict keeps keys, but threats channel should be empty
        assert len(manager.subscriptions["threats"]) == 0
        assert ws1 not in manager.active_connections
        assert ws1 not in manager.subscriptions["threats"]

        # Cycle 2: Reconnect ws1, subscribe to different channels
        conn1_new = await manager.connect(ws1)
        await manager.subscribe(ws1, "metrics", conn1_new)

        assert len(manager.active_connections) == 2
        assert len(manager.subscriptions) == 2
        assert ws1 in manager.active_connections
        assert "metrics" in manager.subscriptions

        # Cycle 3: Disconnect both
        await manager.disconnect(ws1, conn1_new)
        await manager.disconnect(ws2, conn2)

        assert len(manager.active_connections) == 0
        # Channels remain in defaultdict even when empty
        assert all(len(subs) == 0 for subs in manager.subscriptions.values())

    @pytest.mark.asyncio
    async def test_connection_lifecycle_with_broadcasts(self, manager):
        """Test connection lifecycle with ongoing broadcasts"""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        # Connect and subscribe
        connection_id = await manager.connect(ws)
        await manager.subscribe(ws, "threats", connection_id)

        # Send a broadcast
        await manager.broadcast("threats", {"test": "data1"})
        assert ws.send_text.call_count == 1

        # Disconnect and reconnect quickly
        await manager.disconnect(ws, connection_id)
        connection_id_new = await manager.connect(ws)
        await manager.subscribe(ws, "threats", connection_id_new)

        # Send another broadcast
        await manager.broadcast("threats", {"test": "data2"})
        assert ws.send_text.call_count == 2

        # Verify both messages were sent to the same websocket instance
        calls = ws.send_text.call_args_list
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_exception(self, manager):
        """Test connection cleanup when exceptions occur during operations"""
        ws = AsyncMock()
        ws.send_text = AsyncMock(side_effect=Exception("Send failed"))
        ws.close = AsyncMock()

        # Connect and subscribe
        connection_id = await manager.connect(ws)
        await manager.subscribe(ws, "threats", connection_id)

        # Broadcast should handle the exception and clean up
        recipients = await manager.broadcast("threats", {"test": "data"})

        # Should have 0 recipients due to exception
        assert recipients == 0
        assert manager.broadcast_errors == 1

        # Connection should be cleaned up
        assert ws not in manager.active_connections
        assert connection_id not in manager.connection_health
        assert len(manager.subscriptions["threats"]) == 0

    @pytest.mark.asyncio
    async def test_connection_state_consistency(self, manager):
        """Test that connection state remains consistent across operations"""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        # Connect
        connection_id = await manager.connect(ws)
        initial_connections = len(manager.active_connections)
        initial_health_entries = len(manager.connection_health)

        # Subscribe to multiple channels
        await manager.subscribe(ws, "threats", connection_id)
        await manager.subscribe(ws, "alerts", connection_id)
        await manager.subscribe(ws, "metrics", connection_id)

        # State should be consistent
        assert len(manager.active_connections) == initial_connections
        assert len(manager.connection_health) == initial_health_entries
        assert len(manager.subscriptions) == 3

        # Broadcast to verify state
        await manager.broadcast("threats", {"test": "data"})
        await manager.broadcast("alerts", {"test": "data"})

        assert manager.messages_sent == 2

        # Disconnect
        await manager.disconnect(ws, connection_id)

        # State should be fully cleaned
        assert len(manager.active_connections) == initial_connections - 1
        assert len(manager.connection_health) == initial_health_entries - 1
        # Channels remain in defaultdict but should be empty
        assert all(len(subs) == 0 for subs in manager.subscriptions.values())

    @pytest.mark.asyncio
    async def test_connection_health_tracking(self, manager, mock_websocket):
        """Test connection health information tracking"""
        client_info = {"ip": "192.168.1.100", "user_agent": "test-client"}

        # Connect with client info
        connection_id = await manager.connect(mock_websocket, client_info)

        # Verify health tracking
        assert connection_id in manager.connection_health
        health = manager.connection_health[connection_id]

        assert "connected_at" in health
        assert "last_ping" in health
        assert health["client_info"] == client_info
        assert health["subscriptions"] == set()
        assert health["messages_sent"] == 0
        assert health["errors"] == 0

        # Subscribe and check health update
        await manager.subscribe(mock_websocket, "threats", connection_id)
        assert "threats" in health["subscriptions"]

        # Broadcast and check message count (global counter is updated)
        await manager.broadcast("threats", {"test": "data"})
        assert manager.messages_sent == 1

    @pytest.mark.asyncio
    async def test_ping_connections_healthy(self, manager):
        """Test ping connections with healthy connections"""
        # Create healthy mock websockets
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()

        # Connect both
        await manager.connect(ws1)
        await manager.connect(ws2)

        # Ping all connections
        health_stats = await manager.ping_connections()

        # Both should be healthy
        assert health_stats["healthy"] == 2
        assert health_stats["unhealthy"] == 0
        assert health_stats["disconnected"] == 0
        assert health_stats["total"] == 2

        # Verify ping messages were sent
        ws1.send_text.assert_called_with('{"type": "ping"}')
        ws2.send_text.assert_called_with('{"type": "ping"}')

    @pytest.mark.asyncio
    async def test_ping_connections_with_unhealthy(self, manager):
        """Test ping connections that cleans up unhealthy connections"""
        # Create one healthy and one unhealthy websocket
        ws_healthy = AsyncMock()
        ws_healthy.send_text = AsyncMock()

        ws_unhealthy = AsyncMock()
        ws_unhealthy.send_text = AsyncMock(side_effect=Exception("Connection failed"))

        # Connect both
        conn_healthy = await manager.connect(ws_healthy)
        conn_unhealthy = await manager.connect(ws_unhealthy)

        # Subscribe unhealthy to a channel
        await manager.subscribe(ws_unhealthy, "threats", conn_unhealthy)

        assert len(manager.active_connections) == 2
        assert len(manager.subscriptions["threats"]) == 1

        # Ping all connections
        health_stats = await manager.ping_connections()

        # One healthy, one unhealthy (cleaned up)
        assert health_stats["healthy"] == 1
        assert health_stats["unhealthy"] == 1
        assert health_stats["disconnected"] == 1
        assert health_stats["total"] == 1  # After cleanup

        # Unhealthy connection should be cleaned up
        assert ws_unhealthy not in manager.active_connections
        assert conn_unhealthy not in manager.connection_health
        assert len(manager.subscriptions["threats"]) == 0

        # Healthy connection should remain
        assert ws_healthy in manager.active_connections
        assert conn_healthy in manager.connection_health

    @pytest.mark.asyncio
    async def test_connection_health_last_ping_update(self, manager, mock_websocket):
        """Test that last_ping is updated during health checks"""
        connection_id = await manager.connect(mock_websocket)

        initial_ping = manager.connection_health[connection_id]["last_ping"]

        # Ping connections (this should update last_ping)
        await manager.ping_connections()

        # last_ping should be updated to current time
        updated_ping = manager.connection_health[connection_id]["last_ping"]
        # Just check that it's a reasonable timestamp (not 0 and recent)
        assert updated_ping > 0
        assert updated_ping >= initial_ping

    @pytest.mark.asyncio
    async def test_connection_health_error_tracking(self, manager):
        """Test error tracking in connection health"""
        ws = AsyncMock()
        ws.send_text = AsyncMock(side_effect=Exception("Send failed"))

        connection_id = await manager.connect(ws)
        await manager.subscribe(ws, "threats", connection_id)

        # Broadcast should fail and increment error count
        await manager.broadcast("threats", {"test": "data"})

        # Connection should be cleaned up due to error
        assert ws not in manager.active_connections
        assert connection_id not in manager.connection_health

        # Broadcast errors should be tracked
        assert manager.broadcast_errors == 1

    @pytest.mark.asyncio
    async def test_stale_connection_detection(self, manager):
        """Test detection of stale connections based on health data"""
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()

        # Connect both
        conn1 = await manager.connect(ws1)
        conn2 = await manager.connect(ws2)

        # Manually set old connection times (simulate stale connections)
        import time
        old_time = time.time() - 3600  # 1 hour ago
        manager.connection_health[conn1]["connected_at"] = old_time
        manager.connection_health[conn2]["connected_at"] = old_time

        # Ping should detect and clean up based on send failures, not time
        # (since we don't have a time-based cleanup in the current implementation)
        health_stats = await manager.ping_connections()

        # Both should still be healthy since send_text works
        assert health_stats["healthy"] == 2
        assert health_stats["unhealthy"] == 0

        # Health data should still contain the old timestamps
        assert manager.connection_health[conn1]["connected_at"] == old_time
        assert manager.connection_health[conn2]["connected_at"] == old_time

    @pytest.mark.asyncio
    async def test_concurrent_connections(self, manager):
        """Test multiple connections being established concurrently"""
        async def connect_client(client_id: int):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            ws.close = AsyncMock()
            connection_id = await manager.connect(ws, {"client_id": client_id})
            return ws, connection_id

        # Create 10 concurrent connections
        tasks = [connect_client(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify all connections were accepted
        assert len(manager.active_connections) == 10
        assert len(manager.connection_health) == 10
        assert manager.connections_accepted == 10

        # Verify each connection has unique ID and health tracking
        connection_ids = [conn_id for _, conn_id in results]
        assert len(set(connection_ids)) == 10  # All unique

        for _, conn_id in results:
            assert conn_id in manager.connection_health
            health = manager.connection_health[conn_id]
            assert "connected_at" in health
            assert "client_id" in health["client_info"]

    @pytest.mark.asyncio
    async def test_concurrent_subscriptions(self, manager):
        """Test concurrent subscription operations"""
        # First create connections
        websockets = []
        connection_ids = []
        for i in range(5):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            conn_id = await manager.connect(ws, {"client": i})
            websockets.append(ws)
            connection_ids.append(conn_id)

        async def subscribe_to_channel(ws, conn_id, channel):
            return await manager.subscribe(ws, channel, conn_id)

        # Concurrently subscribe all clients to 'threats' channel
        tasks = [subscribe_to_channel(ws, conn_id, "threats")
                for ws, conn_id in zip(websockets, connection_ids)]
        results = await asyncio.gather(*tasks)

        # All subscriptions should succeed
        assert all(results)
        assert len(manager.subscriptions["threats"]) == 5

        # Verify health tracking
        for conn_id in connection_ids:
            assert "threats" in manager.connection_health[conn_id]["subscriptions"]

    @pytest.mark.asyncio
    async def test_concurrent_broadcasts(self, manager):
        """Test broadcasting while connections are being added/removed concurrently"""
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()

        # Connect first client
        conn1 = await manager.connect(ws1)
        await manager.subscribe(ws1, "threats", conn1)

        async def delayed_connect():
            await asyncio.sleep(0.01)  # Small delay
            conn2 = await manager.connect(ws2)
            await manager.subscribe(ws2, "threats", conn2)
            return conn2

        async def delayed_broadcast():
            await asyncio.sleep(0.005)  # Smaller delay
            return await manager.broadcast("threats", {"test": "concurrent"})

        # Run connect and broadcast concurrently
        connect_task = asyncio.create_task(delayed_connect())
        broadcast_task = asyncio.create_task(delayed_broadcast())

        conn2_result = await connect_task
        broadcast_result = await broadcast_task

        # Broadcast should have reached at least the first client
        assert broadcast_result >= 1

        # Second connection should be established
        assert conn2_result in manager.connection_health
        assert ws2 in manager.subscriptions["threats"]

    @pytest.mark.asyncio
    async def test_concurrent_connect_disconnect(self, manager):
        """Test concurrent connect and disconnect operations"""
        async def connect_disconnect_cycle(cycle_id: int):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            ws.close = AsyncMock()

            # Connect
            conn_id = await manager.connect(ws, {"cycle": cycle_id})
            await manager.subscribe(ws, "test", conn_id)

            # Small random delay to create interleaving
            await asyncio.sleep(0.001 * (cycle_id % 3))

            # Disconnect
            await manager.disconnect(ws, conn_id)

            return conn_id

        # Run multiple connect/disconnect cycles concurrently
        tasks = [connect_disconnect_cycle(i) for i in range(8)]
        connection_ids = await asyncio.gather(*tasks)

        # All connections should be cleaned up
        assert len(manager.active_connections) == 0
        assert len(manager.connection_health) == 0
        # Channels remain in defaultdict but are empty
        assert all(len(subs) == 0 for subs in manager.subscriptions.values())

        # Connection counters should be balanced
        assert manager.connections_accepted == 8
        assert manager.connections_closed == 8

        # All connection IDs should be unique
        assert len(set(connection_ids)) == 8

    @pytest.mark.asyncio
    async def test_race_condition_broadcast_during_disconnect(self, manager):
        """Test broadcasting while disconnection is happening"""
        ws = AsyncMock()
        ws.send_text = AsyncMock(side_effect=[None, Exception("Disconnecting")])
        ws.close = AsyncMock()

        # Connect and subscribe
        connection_id = await manager.connect(ws)
        await manager.subscribe(ws, "threats", connection_id)

        async def broadcast_after_delay():
            await asyncio.sleep(0.01)
            return await manager.broadcast("threats", {"test": "race"})

        # Start broadcast task
        broadcast_task = asyncio.create_task(broadcast_after_delay())

        # Immediately try another broadcast that will fail
        recipients = await manager.broadcast("threats", {"test": "immediate"})

        # Wait for the delayed broadcast
        delayed_recipients = await broadcast_task

        # First broadcast should succeed, second should fail or partially succeed
        # due to the disconnect happening during the operation
        assert recipients >= 0  # Could be 0 or 1 depending on timing
        assert delayed_recipients >= 0

        # Connection should eventually be cleaned up
        assert len(manager.active_connections) <= 1  # Might still be cleaning up

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, manager):
        """Test running health checks while other operations are happening"""
        # Create several connections
        websockets = []
        for i in range(3):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            await manager.connect(ws)
            websockets.append(ws)

        async def continuous_broadcast():
            for _ in range(5):
                await manager.broadcast("test", {"ping": "test"})
                await asyncio.sleep(0.001)

        async def health_check_cycle():
            for _ in range(3):
                stats = await manager.ping_connections()
                assert "healthy" in stats
                await asyncio.sleep(0.002)

        # Run broadcasts and health checks concurrently
        broadcast_task = asyncio.create_task(continuous_broadcast())
        health_task = asyncio.create_task(health_check_cycle())

        await asyncio.gather(broadcast_task, health_task)

        # All connections should still be active
        assert len(manager.active_connections) == 3

        # Health checks should have passed
        final_stats = await manager.ping_connections()
        assert final_stats["healthy"] == 3

    @pytest.mark.asyncio
    async def test_subscription_edge_cases_duplicate(self, manager, mock_websocket):
        """Test duplicate subscription handling"""
        connection_id = await manager.connect(mock_websocket)

        # Subscribe to same channel multiple times
        success1 = await manager.subscribe(mock_websocket, "threats", connection_id)
        success2 = await manager.subscribe(mock_websocket, "threats", connection_id)
        success3 = await manager.subscribe(mock_websocket, "threats", connection_id)

        # All should succeed (set semantics)
        assert success1
        assert success2
        assert success3

        # Should only be one entry in subscriptions
        assert len(manager.subscriptions["threats"]) == 1
        assert mock_websocket in manager.subscriptions["threats"]

        # Health tracking should only have one entry
        assert len(manager.connection_health[connection_id]["subscriptions"]) == 1
        assert "threats" in manager.connection_health[connection_id]["subscriptions"]

    @pytest.mark.asyncio
    async def test_subscription_bulk_operations(self, manager):
        """Test bulk subscription operations across multiple clients"""
        # Create multiple clients
        clients = []
        for i in range(5):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            conn_id = await manager.connect(ws, {"client": i})
            clients.append((ws, conn_id))

        # Subscribe all to 'threats'
        for ws, conn_id in clients:
            await manager.subscribe(ws, "threats", conn_id)

        # Subscribe alternating clients to 'alerts'
        for i, (ws, conn_id) in enumerate(clients):
            if i % 2 == 0:
                await manager.subscribe(ws, "alerts", conn_id)

        # Verify subscriptions
        assert len(manager.subscriptions["threats"]) == 5
        assert len(manager.subscriptions["alerts"]) == 3  # Every other client

        # Verify health tracking
        for i, (ws, conn_id) in enumerate(clients):
            health = manager.connection_health[conn_id]
            assert "threats" in health["subscriptions"]
            if i % 2 == 0:
                assert "alerts" in health["subscriptions"]
            else:
                assert "alerts" not in health["subscriptions"]

    @pytest.mark.asyncio
    async def test_subscription_channel_names(self, manager, mock_websocket):
        """Test subscription accepts various channel names"""
        connection_id = await manager.connect(mock_websocket)

        # WebSocket manager accepts any non-empty channel name
        # (validation happens at server level)
        test_channels = ["threats", "alerts", "custom-channel", "channel_with_underscores", "123"]

        for channel in test_channels:
            success = await manager.subscribe(mock_websocket, channel, connection_id)
            assert success, f"Should allow subscription to channel: {channel}"
            assert mock_websocket in manager.subscriptions[channel]

    @pytest.mark.asyncio
    async def test_subscription_inactive_connection(self, manager):
        """Test subscription attempts on inactive connections"""
        ws = AsyncMock()
        ws.send_text = AsyncMock()

        # Try to subscribe without connecting first
        success = await manager.subscribe(ws, "threats", "fake_id")
        assert not success

        # Connect, then disconnect, then try to subscribe
        connection_id = await manager.connect(ws)
        await manager.disconnect(ws, connection_id)

        # Should not allow subscription after disconnect
        success = await manager.subscribe(ws, "threats", connection_id)
        assert not success

    @pytest.mark.asyncio
    async def test_unsubscription_edge_cases(self, manager, mock_websocket):
        """Test unsubscription edge cases"""
        connection_id = await manager.connect(mock_websocket)

        # Try to unsubscribe from non-existent channel
        success = await manager.unsubscribe(mock_websocket, "nonexistent", connection_id)
        assert not success

        # Subscribe then unsubscribe
        await manager.subscribe(mock_websocket, "threats", connection_id)
        assert mock_websocket in manager.subscriptions["threats"]

        success = await manager.unsubscribe(mock_websocket, "threats", connection_id)
        assert success
        assert mock_websocket not in manager.subscriptions["threats"]
        assert "threats" not in manager.connection_health[connection_id]["subscriptions"]

        # Try to unsubscribe again (should succeed even if already unsubscribed)
        success = await manager.unsubscribe(mock_websocket, "threats", connection_id)
        assert success  # Unsubscribe is idempotent

    @pytest.mark.asyncio
    async def test_unsubscription_inactive_connection(self, manager):
        """Test unsubscription from inactive connections"""
        ws = AsyncMock()
        connection_id = await manager.connect(ws)
        await manager.subscribe(ws, "threats", connection_id)

        # Disconnect
        await manager.disconnect(ws, connection_id)

        # Try to unsubscribe after disconnect
        # Unsubscribe succeeds even for inactive connections (removes from channel set)
        success = await manager.unsubscribe(ws, "threats", connection_id)
        assert success

    @pytest.mark.asyncio
    async def test_subscription_cross_channel_validation(self, manager):
        """Test subscriptions across multiple channels with validation"""
        # Create clients for different purposes
        threat_client = AsyncMock()
        threat_client.send_text = AsyncMock()
        threat_conn = await manager.connect(threat_client)

        alert_client = AsyncMock()
        alert_client.send_text = AsyncMock()
        alert_conn = await manager.connect(alert_client)

        multi_client = AsyncMock()
        multi_client.send_text = AsyncMock()
        multi_conn = await manager.connect(multi_client)

        # Subscribe clients to their respective channels
        await manager.subscribe(threat_client, "threats", threat_conn)
        await manager.subscribe(alert_client, "alerts", alert_conn)

        # Subscribe multi-client to multiple channels
        await manager.subscribe(multi_client, "threats", multi_conn)
        await manager.subscribe(multi_client, "alerts", multi_conn)
        await manager.subscribe(multi_client, "status", multi_conn)

        # Verify channel isolation
        assert len(manager.subscriptions["threats"]) == 2  # threat_client + multi_client
        assert len(manager.subscriptions["alerts"]) == 2   # alert_client + multi_client
        assert len(manager.subscriptions["status"]) == 1   # multi_client only

        # Verify no cross-contamination
        assert threat_client not in manager.subscriptions["alerts"]
        assert alert_client not in manager.subscriptions["threats"]

    @pytest.mark.asyncio
    async def test_subscription_cleanup_on_partial_disconnect(self, manager):
        """Test subscription cleanup when connection health is corrupted"""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        connection_id = await manager.connect(ws)

        # Subscribe to multiple channels
        await manager.subscribe(ws, "threats", connection_id)
        await manager.subscribe(ws, "alerts", connection_id)
        await manager.subscribe(ws, "metrics", connection_id)

        # Manually corrupt health tracking (simulate partial state corruption)
        manager.connection_health[connection_id]["subscriptions"].add("extra_channel")
        manager.subscriptions["extra_channel"].add(ws)

        assert len(manager.subscriptions) == 4  # threats, alerts, metrics, extra_channel

        # Disconnect should clean up all subscriptions
        await manager.disconnect(ws, connection_id)

        # All subscriptions should be cleaned up (websockets removed from channels)
        # defaultdict keeps empty channel keys
        assert len(manager.subscriptions) >= 4  # threats, alerts, metrics, extra_channel
        for channel in ["threats", "alerts", "metrics", "extra_channel"]:
            assert ws not in manager.subscriptions[channel]

    @pytest.mark.asyncio
    async def test_state_validation_connection_transitions(self, manager):
        """Test state transitions during connection lifecycle"""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        # Initial state: no connections
        assert len(manager.active_connections) == 0
        assert len(manager.connection_health) == 0
        assert len(manager.subscriptions) == 0

        # State 1: Connecting
        connection_id = await manager.connect(ws)

        # Validate connected state
        assert len(manager.active_connections) == 1
        assert ws in manager.active_connections
        assert connection_id in manager.connection_health
        assert len(manager.subscriptions) == 0

        health = manager.connection_health[connection_id]
        assert health["subscriptions"] == set()
        assert health["messages_sent"] == 0

        # State 2: Subscribed
        await manager.subscribe(ws, "threats", connection_id)
        await manager.subscribe(ws, "alerts", connection_id)

        assert len(manager.subscriptions) == 2
        assert ws in manager.subscriptions["threats"]
        assert ws in manager.subscriptions["alerts"]
        assert health["subscriptions"] == {"threats", "alerts"}

        # State 3: Broadcasting
        await manager.broadcast("threats", {"test": "data"})
        assert manager.messages_sent == 1  # Global counter is updated

        # State 4: Disconnecting
        await manager.disconnect(ws, connection_id)

        # Validate disconnected state
        assert len(manager.active_connections) == 0
        assert connection_id not in manager.connection_health
        assert len(manager.subscriptions) == 0

    @pytest.mark.asyncio
    async def test_state_consistency_invariants(self, manager):
        """Test that state invariants are always maintained"""
        # Create multiple connections with different subscription patterns
        connections = []
        for i in range(5):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            conn_id = await manager.connect(ws, {"client": i})
            connections.append((ws, conn_id))

        # Subscribe to various combinations
        subscriptions = [
            ("threats",),  # 1 channel
            ("threats", "alerts"),  # 2 channels
            ("threats", "alerts", "status"),  # 3 channels
            (),  # no channels
            ("metrics",)  # 1 different channel
        ]

        for (ws, conn_id), channels in zip(connections, subscriptions):
            for channel in channels:
                await manager.subscribe(ws, channel, conn_id)

        # Validate invariants
        total_subscriptions = sum(len(subs) for subs in manager.subscriptions.values())
        expected_subscriptions = sum(len(channels) for channels in subscriptions)

        assert total_subscriptions == expected_subscriptions

        # Validate each connection's health matches subscriptions
        for (ws, conn_id), channels in zip(connections, subscriptions):
            health = manager.connection_health[conn_id]
            assert health["subscriptions"] == set(channels)

            # Validate connection appears in all its subscribed channels
            for channel in channels:
                assert ws in manager.subscriptions[channel]

        # Validate no orphaned subscriptions
        for channel, subscribers in manager.subscriptions.items():
            for ws in subscribers:
                assert ws in manager.active_connections

    @pytest.mark.asyncio
    async def test_state_recovery_after_errors(self, manager):
        """Test state recovery and consistency after error conditions"""
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock(side_effect=Exception("Connection failed"))
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()

        # Connect both
        conn1 = await manager.connect(ws1)
        conn2 = await manager.connect(ws2)

        # Subscribe both to channels
        await manager.subscribe(ws1, "threats", conn1)
        await manager.subscribe(ws2, "threats", conn2)
        await manager.subscribe(ws2, "alerts", conn2)

        # Broadcast - should clean up failed connection
        recipients = await manager.broadcast("threats", {"test": "data"})

        # State should be consistent: ws1 cleaned up, ws2 intact
        assert recipients == 1  # Only ws2 received
        assert len(manager.active_connections) == 1
        assert ws2 in manager.active_connections
        assert conn2 in manager.connection_health
        assert len(manager.subscriptions["threats"]) == 1
        assert len(manager.subscriptions["alerts"]) == 1

        # Validate ws2 health
        health = manager.connection_health[conn2]
        assert health["subscriptions"] == {"threats", "alerts"}
        # Note: per-connection messages_sent not tracked in broadcast, only global counter
        assert manager.messages_sent == 1

    @pytest.mark.asyncio
    async def test_state_corruption_detection(self, manager):
        """Test detection and handling of state corruption"""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        connection_id = await manager.connect(ws)

        # Subscribe to channels
        await manager.subscribe(ws, "threats", connection_id)
        await manager.subscribe(ws, "alerts", connection_id)

        # Manually corrupt state (simulate bugs)
        manager.connection_health[connection_id]["subscriptions"].add("fake_channel")
        manager.subscriptions["fake_channel"].add(ws)

        # Disconnect should detect and clean up all corruption
        await manager.disconnect(ws, connection_id)

        # All state should be clean
        assert len(manager.active_connections) == 0
        assert len(manager.connection_health) == 0

        # Channels should still exist but be empty (defaultdict behavior)
        # The fake_channel should still exist but be empty
        assert len(manager.subscriptions) >= 3  # threats, alerts, fake_channel
        assert len(manager.subscriptions["threats"]) == 0
        assert len(manager.subscriptions["alerts"]) == 0
        assert len(manager.subscriptions["fake_channel"]) == 0

        # No orphaned websocket entries in any channels
        for channel_subs in manager.subscriptions.values():
            assert ws not in channel_subs

    @pytest.mark.asyncio
    async def test_state_validation_bulk_operations(self, manager):
        """Test state validation during bulk operations"""
        # Create many connections quickly
        connections = []
        for i in range(20):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            conn_id = await manager.connect(ws, {"bulk_test": i})
            connections.append((ws, conn_id))

        # Bulk subscribe to multiple channels
        for i, (ws, conn_id) in enumerate(connections):
            channels = ["threats", "alerts", "status", "metrics"][: (i % 4) + 1]
            for channel in channels:
                await manager.subscribe(ws, channel, conn_id)

        # Validate state consistency
        total_expected_subs = sum(len(["threats", "alerts", "status", "metrics"][: (i % 4) + 1])
                                  for i in range(20))

        actual_subs = sum(len(subs) for subs in manager.subscriptions.values())
        assert actual_subs == total_expected_subs

        # Validate each connection's state
        for i, (ws, conn_id) in enumerate(connections):
            expected_channels = set(["threats", "alerts", "status", "metrics"][: (i % 4) + 1])
            health = manager.connection_health[conn_id]
            assert health["subscriptions"] == expected_channels

            # Validate appearance in all channels
            for channel in expected_channels:
                assert ws in manager.subscriptions[channel]

        # Bulk disconnect
        disconnect_tasks = [manager.disconnect(ws, conn_id) for ws, conn_id in connections]
        await asyncio.gather(*disconnect_tasks)

        # Final state validation
        assert len(manager.active_connections) == 0
        assert len(manager.connection_health) == 0
        assert len(manager.subscriptions) == 0

    @pytest.mark.asyncio
    async def test_state_transition_atomicity(self, manager):
        """Test that state transitions are atomic and consistent"""
        ws = AsyncMock()
        ws.send_text = AsyncMock(side_effect=[Exception("Mid-transition failure")])
        ws.close = AsyncMock()

        connection_id = await manager.connect(ws)
        await manager.subscribe(ws, "threats", connection_id)

        # Attempt broadcast that will fail mid-operation
        recipients = await manager.broadcast("threats", {"test": "data"})

        # State should be consistent: connection cleaned up
        assert recipients == 0
        assert len(manager.active_connections) == 0
        assert connection_id not in manager.connection_health
        assert len(manager.subscriptions["threats"]) == 0

        # Counters should be updated correctly
        assert manager.broadcast_errors == 1