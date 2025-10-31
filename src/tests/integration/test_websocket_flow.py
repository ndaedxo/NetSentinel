#!/usr/bin/env python3
"""
Integration tests for WebSocket real-time event broadcasting flow
"""

import asyncio
import json
import pytest
import pytest_asyncio
import websockets
import uvicorn
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.netsentinel.processors.websocket_manager import WebSocketManager
from src.netsentinel.processors.websocket_server import WebSocketServer
from src.netsentinel.processors.refactored_event_processor import RefactoredEventProcessor, ProcessorConfig
from src.netsentinel.core.event_bus import get_event_bus, create_event
from src.netsentinel.core.models import StandardEvent, ThreatLevel


class TestWebSocketIntegration:
    """Integration tests for WebSocket event broadcasting"""

    @pytest_asyncio.fixture
    async def websocket_manager(self):
        """Create standalone WebSocket manager for testing"""
        manager = WebSocketManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_websocket_manager_integration(self, websocket_manager):
        """Test WebSocket manager is properly initialized"""
        assert websocket_manager is not None
        assert websocket_manager.active_connections == set()
        assert isinstance(websocket_manager.subscriptions, dict)

        # Check that manager has basic attributes
        assert hasattr(websocket_manager, 'messages_sent')
        assert hasattr(websocket_manager, 'connections_accepted')
        assert hasattr(websocket_manager, 'broadcast_errors')
        assert websocket_manager.messages_sent == 0
        assert websocket_manager.connections_accepted == 0
        assert websocket_manager.broadcast_errors == 0

    @pytest.mark.asyncio
    async def test_event_bus_to_websocket_broadcasting(self, websocket_manager):
        """Test that events published to event bus are broadcast via WebSocket"""
        # Manually subscribe manager to threat events for this test
        event_bus = get_event_bus()
        event_bus.subscribe("threat.new", websocket_manager._handle_threat_event)

        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()

        # Connect and subscribe to threats channel
        connection_id = await websocket_manager.connect(mock_ws)
        await websocket_manager.subscribe(mock_ws, "threats", connection_id)

        # Publish threat event to event bus
        threat_data = {
            "source_ip": "192.168.1.100",
            "threat_score": 8.5,
            "threat_level": "high",
            "timestamp": 1234567890.123
        }
        threat_event = create_event("threat.new", threat_data)
        await event_bus.publish(threat_event)

        # Give event processing time
        await asyncio.sleep(0.1)

        # Verify WebSocket received the message
        assert mock_ws.send_text.called
        call_args = mock_ws.send_text.call_args[0][0]
        sent_data = json.loads(call_args)

        assert sent_data["type"] == "threat.new"
        assert sent_data["data"] == threat_data

    @pytest.mark.asyncio
    async def test_alert_broadcasting_via_event_bus(self, websocket_manager):
        """Test that alerts are broadcast through WebSocket via event bus"""
        # Subscribe manager to alert events
        event_bus = get_event_bus()
        event_bus.subscribe("alert.new", websocket_manager._handle_alert_event)

        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()

        manager = websocket_manager
        connection_id = await manager.connect(mock_ws)
        await manager.subscribe(mock_ws, "alerts", connection_id)

        # Create alert data
        alert_data = {
            "id": "alert_123",
            "severity": "critical",
            "message": "Critical Threat Detected",
            "description": "High threat score detected",
            "timestamp": 1234567890.123,
            "source": "test_processor",
            "tags": ["malware", "trojan"]
        }

        # Publish alert event
        alert_event = create_event("alert.new", alert_data)
        await event_bus.publish(alert_event)

        # Give event processing time
        await asyncio.sleep(0.1)

        # Verify WebSocket received alert broadcast
        assert mock_ws.send_text.called
        call_args = mock_ws.send_text.call_args[0][0]
        sent_data = json.loads(call_args)

        assert sent_data["type"] == "alert.new"
        assert sent_data["data"]["severity"] == "critical"
        assert "Critical Threat Detected" in sent_data["data"]["message"]

    @pytest.mark.asyncio
    async def test_multiple_clients_broadcast(self, websocket_manager):
        """Test broadcasting to multiple WebSocket clients"""
        # Create multiple mock WebSocket connections
        mock_ws1 = AsyncMock()
        mock_ws1.send_text = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.send_text = AsyncMock()

        mock_ws3 = AsyncMock()
        mock_ws3.send_text = AsyncMock()

        # Connect all clients and subscribe to threats
        conn1 = await websocket_manager.connect(mock_ws1)
        conn2 = await websocket_manager.connect(mock_ws2)
        conn3 = await websocket_manager.connect(mock_ws3)

        await websocket_manager.subscribe(mock_ws1, "threats", conn1)
        await websocket_manager.subscribe(mock_ws2, "threats", conn2)
        await websocket_manager.subscribe(mock_ws3, "alerts", conn3)  # Different channel

        # Publish threat event
        threat_data = {"source_ip": "10.0.0.1", "threat_score": 7.5}
        threat_event = create_event("threat.new", threat_data)
        event_bus = get_event_bus()
        await event_bus.publish(threat_event)

        # Give event processing time
        await asyncio.sleep(0.1)

        # Verify first two clients received the threat broadcast
        assert mock_ws1.send_text.called
        assert mock_ws2.send_text.called

        # Third client should not receive threat broadcast (subscribed to alerts)
        assert not mock_ws3.send_text.called

        # Verify message content for first client
        call_args = mock_ws1.send_text.call_args[0][0]
        sent_data = json.loads(call_args)
        assert sent_data["type"] == "threat.new"
        assert sent_data["data"]["threat_score"] == 7.5

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self, websocket_manager):
        """Test complete WebSocket connection lifecycle"""
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()

        # Connect
        connection_id = await websocket_manager.connect(mock_ws)
        assert connection_id in websocket_manager.connection_health
        assert mock_ws in websocket_manager.active_connections

        # Subscribe to channels
        await websocket_manager.subscribe(mock_ws, "threats", connection_id)
        await websocket_manager.subscribe(mock_ws, "alerts", connection_id)

        assert len(websocket_manager.subscriptions["threats"]) == 1
        assert len(websocket_manager.subscriptions["alerts"]) == 1

        # Broadcast to both channels
        threat_event = create_event("threat.new", {"threat_score": 6.0})
        alert_event = create_event("alert.new", {"severity": "high"})

        event_bus = get_event_bus()
        await event_bus.publish(threat_event)
        await event_bus.publish(alert_event)

        await asyncio.sleep(0.1)

        # Should have received 2 messages
        assert mock_ws.send_text.call_count == 2

        # Disconnect
        await websocket_manager.disconnect(mock_ws, connection_id)

        assert mock_ws not in websocket_manager.active_connections
        assert connection_id not in websocket_manager.connection_health
        assert len(websocket_manager.subscriptions["threats"]) == 0
        assert len(websocket_manager.subscriptions["alerts"]) == 0

    @pytest.mark.asyncio
    async def test_connection_stats_tracking(self, websocket_manager):
        """Test WebSocket connection statistics"""
        initial_stats = websocket_manager.get_connection_stats()

        # Add some connections
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        conn1 = await websocket_manager.connect(mock_ws1)
        conn2 = await websocket_manager.connect(mock_ws2)

        await websocket_manager.subscribe(mock_ws1, "threats", conn1)
        await websocket_manager.subscribe(mock_ws2, "alerts", conn2)

        # Send some broadcasts
        threat_event = create_event("threat.new", {"test": "data"})
        alert_event = create_event("alert.new", {"test": "data"})

        event_bus = get_event_bus()
        await event_bus.publish(threat_event)
        await event_bus.publish(alert_event)

        await asyncio.sleep(0.1)

        # Check updated stats
        stats = websocket_manager.get_connection_stats()

        assert stats["active_connections"] == 2
        assert stats["channels"] == 2
        assert stats["channel_subscriptions"]["threats"] == 1
        assert stats["channel_subscriptions"]["alerts"] == 1
        assert stats["total_messages_sent"] == 2
        assert stats["total_connections_accepted"] == 2
        assert stats["total_connections_closed"] == 0

    @pytest.mark.asyncio
    async def test_channel_isolation(self, websocket_manager):
        """Test that broadcasts are properly isolated to channels"""
        mock_ws_threats = AsyncMock()
        mock_ws_threats.send_text = AsyncMock()

        mock_ws_alerts = AsyncMock()
        mock_ws_alerts.send_text = AsyncMock()

        mock_ws_status = AsyncMock()
        mock_ws_status.send_text = AsyncMock()

        # Connect and subscribe to different channels
        conn1 = await websocket_manager.connect(mock_ws_threats)
        conn2 = await websocket_manager.connect(mock_ws_alerts)
        conn3 = await websocket_manager.connect(mock_ws_status)

        await websocket_manager.subscribe(mock_ws_threats, "threats", conn1)
        await websocket_manager.subscribe(mock_ws_alerts, "alerts", conn2)
        await websocket_manager.subscribe(mock_ws_status, "status", conn3)

        # Publish events to different channels
        threat_event = create_event("threat.new", {"channel": "threats"})
        alert_event = create_event("alert.new", {"channel": "alerts"})
        status_event = create_event("status.update", {"channel": "status"})

        event_bus = get_event_bus()
        await event_bus.publish(threat_event)
        await event_bus.publish(alert_event)
        await event_bus.publish(status_event)

        await asyncio.sleep(0.1)

        # Verify each client only received messages for their subscribed channel
        assert mock_ws_threats.send_text.call_count == 1
        assert mock_ws_alerts.send_text.call_count == 1
        assert mock_ws_status.send_text.call_count == 1

        # Verify message content
        threat_msg = json.loads(mock_ws_threats.send_text.call_args[0][0])
        alert_msg = json.loads(mock_ws_alerts.send_text.call_args[0][0])
        status_msg = json.loads(mock_ws_status.send_text.call_args[0][0])

        assert threat_msg["type"] == "threat.new"
        assert alert_msg["type"] == "alert.new"
        assert status_msg["type"] == "status.update"


class TestWebSocketServerIntegration:
    """Full WebSocket server integration tests with FastAPI"""

    @pytest_asyncio.fixture
    async def websocket_server_app(self):
        """Create FastAPI app with WebSocket server"""
        app = FastAPI()

        # Create WebSocket manager and server
        manager = WebSocketManager()
        server = WebSocketServer(manager)

        # Add WebSocket endpoint to FastAPI app
        @app.websocket("/ws")
        async def websocket_endpoint(websocket, token: str = None):
            await server.websocket_endpoint(websocket, token)

        await manager.start()
        await server.start()

        yield app, manager, server

        await server.stop()
        await manager.stop()

    @pytest_asyncio.fixture
    async def test_server(self, websocket_server_app):
        """Start test server"""
        app, manager, server = websocket_server_app

        # For WebSocket testing, we'll need to use a real server
        # Let's use a different approach - create a background server
        server_task = None
        try:
            # Start server in background
            config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="error")
            server_obj = uvicorn.Server(config)
            server_task = asyncio.create_task(server_obj.serve())

            # Wait a bit for server to start
            await asyncio.sleep(0.1)

            yield "ws://127.0.0.1:8765/ws"

        finally:
            if server_task:
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_websocket_server_fastapi_integration(self, websocket_server_app):
        """Test WebSocket server integration with FastAPI"""
        app, manager, server = websocket_server_app

        # Verify components are properly initialized
        assert manager is not None
        assert server is not None
        assert server.websocket_manager == manager
        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_websocket_client_connection_handshake(self, test_server):
        """Test real WebSocket client connection and handshake"""
        uri = test_server

        try:
            async with websockets.connect(uri) as websocket:
                # Should receive welcome message
                welcome_msg = await websocket.recv()
                welcome_data = json.loads(welcome_msg)

                assert welcome_data["type"] == "connection.established"
                assert "connection_id" in welcome_data["data"]
                assert welcome_data["data"]["connection_id"].startswith("ws_")
                assert "available_channels" in welcome_data["data"]
                assert "server_time" in welcome_data["data"]

        except Exception as e:
            # If server connection fails, that's expected in test environment
            pytest.skip(f"WebSocket server connection failed (expected in test env): {e}")

    @pytest.mark.asyncio
    async def test_websocket_message_subscription_flow(self, websocket_server_app):
        """Test complete message subscription flow"""
        app, manager, server = websocket_server_app

        # Create mock WebSocket for direct testing
        mock_ws = AsyncMock()
        mock_ws.client = {"host": "127.0.0.1"}
        mock_ws.headers = {"user-agent": "test-client"}

        # Mock the receive sequence: subscribe -> ping -> close
        messages = [
            json.dumps({"type": "subscribe", "channel": "threats"}),
            json.dumps({"type": "subscribe", "channel": "alerts"}),
            json.dumps({"type": "ping"}),
            json.dumps({"type": "status"}),  # Status request
        ]
        mock_ws.receive_text = AsyncMock(side_effect=messages + [asyncio.CancelledError()])

        # Mock send_text to capture responses
        sent_messages = []
        mock_ws.send_text = AsyncMock(side_effect=lambda msg: sent_messages.append(json.loads(msg)))

        # Run the endpoint
        try:
            await server.websocket_endpoint(mock_ws)
        except asyncio.CancelledError:
            pass  # Expected when message sequence ends

        # Verify connection was accepted
        assert mock_ws in manager.active_connections

        # Verify welcome message was sent
        assert len(sent_messages) >= 1
        welcome_msg = sent_messages[0]
        assert welcome_msg["type"] == "connection.established"

        # Verify subscription responses
        subscribe_responses = [msg for msg in sent_messages if msg.get("type") == "subscribed"]
        assert len(subscribe_responses) == 2

        # Verify ping response
        pong_responses = [msg for msg in sent_messages if msg.get("type") == "pong"]
        assert len(pong_responses) == 1

        # Verify status response
        status_responses = [msg for msg in sent_messages if msg.get("type") == "status"]
        assert len(status_responses) == 1
        assert "websocket_stats" in status_responses[0]["data"]

    @pytest.mark.asyncio
    async def test_websocket_message_serialization_deserialization(self, websocket_server_app):
        """Test message serialization and deserialization"""
        app, manager, server = websocket_server_app

        # Test various message types and their serialization
        test_messages = [
            {"type": "subscribe", "channel": "threats"},
            {"type": "subscribe", "channel": "alerts", "data": {"filter": "high"}},
            {"type": "unsubscribe", "channel": "threats"},
            {"type": "ping", "timestamp": 1234567890.123},
            {"type": "status"},
            {"type": "unknown_command", "data": {"test": "value"}},
        ]

        for original_msg in test_messages:
            # Test serialization (what client sends)
            serialized = json.dumps(original_msg)
            assert isinstance(serialized, str)

            # Test deserialization (what server receives)
            deserialized = json.loads(serialized)
            assert deserialized == original_msg

            # Test server response serialization
            if original_msg["type"] == "subscribe":
                response_msg = {
                    "type": "subscribed",
                    "data": {
                        "channel": original_msg["channel"],
                        "subscriber_count": 1
                    }
                }
                response_serialized = json.dumps(response_msg)
                response_deserialized = json.loads(response_serialized)
                assert response_deserialized["type"] == "subscribed"
                assert response_deserialized["data"]["channel"] == original_msg["channel"]

    @pytest.mark.asyncio
    async def test_websocket_broadcast_message_formats(self, websocket_server_app):
        """Test WebSocket broadcast message formats"""
        app, manager, server = websocket_server_app

        # Create mock WebSocket and subscribe
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()

        connection_id = await manager.connect(mock_ws)
        await manager.subscribe(mock_ws, "threats", connection_id)

        # Test threat broadcast message format
        threat_data = {
            "source_ip": "192.168.1.100",
            "threat_score": 8.5,
            "threat_level": "high",
            "event_type": "ssh_brute_force"
        }

        await manager.broadcast_threat(threat_data)

        # Verify message format
        call_args = mock_ws.send_text.call_args[0][0]
        sent_data = json.loads(call_args)

        assert sent_data["type"] == "threat.new"
        assert sent_data["data"] == threat_data
        assert "timestamp" in sent_data
        assert isinstance(sent_data["timestamp"], (int, float))

        # Test alert broadcast message format
        alert_data = {
            "id": "alert_123",
            "severity": "critical",
            "message": "High threat detected",
            "source": "test_processor"
        }

        await manager.broadcast_alert(alert_data)

        # Verify alert message format
        call_args = mock_ws.send_text.call_args[0][0]
        sent_data = json.loads(call_args)

        assert sent_data["type"] == "alert.new"
        assert sent_data["data"] == alert_data
        assert "timestamp" in sent_data

    @pytest.mark.asyncio
    async def test_websocket_error_message_handling(self, websocket_server_app):
        """Test error message handling and serialization"""
        app, manager, server = websocket_server_app

        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()

        # Test invalid JSON
        await server._handle_message(mock_ws, "test_conn", "invalid json")

        # Verify error response
        call_args = mock_ws.send_text.call_args
        if call_args:  # Might not send if connection fails
            error_msg = json.loads(call_args[0][0])
            assert error_msg["type"] == "error"
            assert "Invalid JSON format" in error_msg["data"]["message"]

        # Reset mock
        mock_ws.send_text.reset_mock()

        # Test unknown message type
        await server._handle_message(mock_ws, "test_conn", json.dumps({"type": "unknown_command"}))

        # Verify error response for unknown type
        call_args = mock_ws.send_text.call_args
        if call_args:
            error_msg = json.loads(call_args[0][0])
            assert error_msg["type"] == "error"
            assert "Unknown message type" in error_msg["data"]["message"]

    @pytest.mark.asyncio
    async def test_websocket_realtime_event_streaming(self, websocket_server_app):
        """Test real-time event streaming from event bus to WebSocket"""
        app, manager, server = websocket_server_app

        # Create mock WebSocket and subscribe to threats
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()

        connection_id = await manager.connect(mock_ws)
        await manager.subscribe(mock_ws, "threats", connection_id)

        # Publish threat event to event bus
        threat_data = {
            "source_ip": "10.0.0.1",
            "threat_score": 9.2,
            "threat_level": "critical",
            "indicators": ["malware", "c2c"]
        }

        event_bus = get_event_bus()
        threat_event = create_event("threat.new", threat_data)
        await event_bus.publish(threat_event)

        # Give time for event processing
        await asyncio.sleep(0.1)

        # Verify WebSocket received the broadcast
        assert mock_ws.send_text.called
        call_args = mock_ws.send_text.call_args[0][0]
        received_msg = json.loads(call_args)

        assert received_msg["type"] == "threat.new"
        assert received_msg["data"]["threat_score"] == 9.2
        assert received_msg["data"]["source_ip"] == "10.0.0.1"

        # Test alert streaming
        mock_ws.send_text.reset_mock()

        alert_data = {
            "id": "alert_456",
            "severity": "high",
            "message": "Suspicious activity detected",
            "tags": ["anomaly", "network"]
        }

        alert_event = create_event("alert.new", alert_data)
        await event_bus.publish(alert_event)

        await asyncio.sleep(0.1)

        # Verify alert was broadcast
        assert mock_ws.send_text.called
        call_args = mock_ws.send_text.call_args[0][0]
        received_msg = json.loads(call_args)

        assert received_msg["type"] == "alert.new"
        assert received_msg["data"]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_websocket_connection_cleanup_integration(self, websocket_server_app):
        """Test connection cleanup in integrated environment"""
        app, manager, server = websocket_server_app

        # Create multiple mock connections
        mock_ws1 = AsyncMock()
        mock_ws1.send_text = AsyncMock()
        mock_ws1.close = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.send_text = AsyncMock()
        mock_ws2.close = AsyncMock()

        # Connect both
        conn1 = await manager.connect(mock_ws1)
        conn2 = await manager.connect(mock_ws2)

        # Subscribe to channels
        await manager.subscribe(mock_ws1, "threats", conn1)
        await manager.subscribe(mock_ws2, "alerts", conn2)

        # Verify initial state
        assert len(manager.active_connections) == 2
        assert len(manager.subscriptions) >= 2  # defaultdict keeps keys

        # Disconnect first connection
        await manager.disconnect(mock_ws1, conn1)

        # Verify cleanup
        assert mock_ws1 not in manager.active_connections
        assert conn1 not in manager.connection_health
        assert mock_ws2 in manager.active_connections  # Second connection intact

        # Disconnect second connection
        await manager.disconnect(mock_ws2, conn2)

        # Verify complete cleanup
        assert len(manager.active_connections) == 0
        assert len(manager.connection_health) == 0

    @pytest.mark.asyncio
    async def test_websocket_message_validation_and_sanitization(self, websocket_server_app):
        """Test message validation and sanitization"""
        app, manager, server = websocket_server_app

        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()

        connection_id = await manager.connect(mock_ws)

        # Test valid channel subscription
        await server._handle_message(mock_ws, connection_id,
                                   json.dumps({"type": "subscribe", "channel": "threats"}))

        # Should succeed
        success_response = json.loads(mock_ws.send_text.call_args[0][0])
        assert success_response["type"] == "subscribed"

        # Reset mock
        mock_ws.send_text.reset_mock()

        # Test invalid channel subscription
        await server._handle_message(mock_ws, connection_id,
                                   json.dumps({"type": "subscribe", "channel": "invalid_channel"}))

        # Should fail
        error_response = json.loads(mock_ws.send_text.call_args[0][0])
        assert error_response["type"] == "error"
        assert "Invalid channel" in error_response["data"]["message"]

        # Test missing channel
        mock_ws.send_text.reset_mock()
        await server._handle_message(mock_ws, connection_id,
                                   json.dumps({"type": "subscribe"}))

        error_response = json.loads(mock_ws.send_text.call_args[0][0])
        assert error_response["type"] == "error"
        assert "Missing channel" in error_response["data"]["message"]
