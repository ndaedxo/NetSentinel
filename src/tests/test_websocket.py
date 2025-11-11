#!/usr/bin/env python3
"""
WebSocket Testing Module for NetSentinel
Comprehensive tests for WebSocket server, manager, and client connections
"""

import asyncio
import json
import pytest
import time
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock

from netsentinel.processors.websocket_manager import WebSocketManager, MessageQueue, QueuedMessage
from netsentinel.processors.websocket_server import WebSocketServer, ConnectionRateLimiter


class MockWebSocket:
    """Mock WebSocket connection for testing"""

    def __init__(self, client_host: str = "127.0.0.1", client_port: int = 12345):
        self.client = Mock()
        self.client.host = client_host
        self.client.port = client_port
        self.headers = {"user-agent": "TestClient/1.0"}
        self.sent_messages = []
        self.closed = False

    async def accept(self):
        pass

    async def send_text(self, message: str):
        self.sent_messages.append(message)

    async def receive_text(self):
        await asyncio.sleep(1)  # Simulate waiting
        return json.dumps({"type": "ping"})

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True

    def __hash__(self):
        return hash(id(self))

    def __eq__(self, other):
        return self is other


class TestMessageQueue:
    """Test MessageQueue functionality"""

    def test_enqueue_dequeue_message(self):
        """Test basic message enqueue and dequeue"""
        queue = MessageQueue(max_messages_per_client=10, default_ttl=3600)

        # Enqueue a message
        message_id = queue.enqueue_message("client1", "threats", {"type": "threat.new", "data": "test"})
        assert message_id.startswith("msg_")

        # Dequeue messages
        messages = queue.dequeue_messages("client1")
        assert len(messages) == 1
        assert messages[0].channel == "threats"
        assert messages[0].data["type"] == "threat.new"

        # Queue should be empty now
        messages = queue.dequeue_messages("client1")
        assert len(messages) == 0

    def test_message_expiration(self):
        """Test message expiration"""
        queue = MessageQueue(max_messages_per_client=10, default_ttl=1)  # 1 second TTL

        # Enqueue a message
        queue.enqueue_message("client1", "threats", {"type": "threat.new"})

        # Message should still be available
        messages = queue.dequeue_messages("client1")
        assert len(messages) == 1

        # Re-enqueue and wait for expiration
        queue.enqueue_message("client1", "threats", {"type": "threat.new"})
        time.sleep(2)  # Wait longer than TTL

        # Clean up expired messages
        queue.cleanup_expired_messages()

        # Should have no messages
        messages = queue.dequeue_messages("client1")
        assert len(messages) == 0

    def test_message_priority(self):
        """Test message prioritization"""
        queue = MessageQueue()

        # Enqueue messages with different priorities
        queue.enqueue_message("client1", "threats", {"type": "normal"}, priority=1)
        queue.enqueue_message("client1", "threats", {"type": "high"}, priority=2)
        queue.enqueue_message("client1", "threats", {"type": "critical"}, priority=3)

        messages = queue.dequeue_messages("client1")

        # Should be ordered by priority (highest first)
        assert len(messages) == 3
        assert messages[0].data["type"] == "critical"
        assert messages[1].data["type"] == "high"
        assert messages[2].data["type"] == "normal"

    def test_queue_capacity_limits(self):
        """Test queue capacity limits"""
        queue = MessageQueue(max_messages_per_client=2)

        # Enqueue more messages than capacity
        queue.enqueue_message("client1", "threats", {"msg": "1"})
        queue.enqueue_message("client1", "threats", {"msg": "2"})
        queue.enqueue_message("client1", "threats", {"msg": "3"})  # Should be dropped

        messages = queue.dequeue_messages("client1")
        assert len(messages) == 2  # Only 2 messages should remain


class TestWebSocketManager:
    """Test WebSocketManager functionality"""

    def test_connection_management(self):
        """Test connection accept/disconnect"""
        manager = WebSocketManager()

        # Mock websocket
        ws = MockWebSocket()

        # Test connection
        connection_id = asyncio.run(manager.connect(ws))
        assert connection_id.startswith("ws_")
        assert ws in manager.active_connections
        assert connection_id in manager.connection_health

        # Test disconnection
        asyncio.run(manager.disconnect(ws, connection_id))
        assert ws not in manager.active_connections
        assert connection_id not in manager.connection_health

    def test_channel_subscription(self):
        """Test channel subscription/unsubscription"""
        manager = WebSocketManager()
        ws = MockWebSocket()

        # Connect first
        connection_id = asyncio.run(manager.connect(ws))

        # Subscribe to channel
        success = asyncio.run(manager.subscribe(ws, "threats", connection_id))
        assert success
        assert ws in manager.subscriptions["threats"]

        # Unsubscribe
        success = asyncio.run(manager.unsubscribe(ws, "threats", connection_id))
        assert success
        assert ws not in manager.subscriptions["threats"]

    def test_message_broadcasting(self):
        """Test message broadcasting to subscribers"""
        manager = WebSocketManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        # Connect both clients
        conn_id1 = asyncio.run(manager.connect(ws1))
        conn_id2 = asyncio.run(manager.connect(ws2))

        # Subscribe both to threats channel
        asyncio.run(manager.subscribe(ws1, "threats", conn_id1))
        asyncio.run(manager.subscribe(ws2, "threats", conn_id2))

        # Broadcast message
        test_data = {"type": "threat.new", "data": {"threat": "test"}}
        recipients = asyncio.run(manager.broadcast("threats", test_data))

        assert recipients == 2
        assert len(ws1.sent_messages) == 1
        assert len(ws2.sent_messages) == 1

        # Verify message content
        sent_message = json.loads(ws1.sent_messages[0])
        assert sent_message["type"] == "threat.new"
        assert sent_message["data"]["threat"] == "test"

    def test_message_queuing_for_offline_clients(self):
        """Test queuing messages for offline subscribers"""
        manager = WebSocketManager()
        ws = MockWebSocket()

        # Connect and subscribe
        connection_id = asyncio.run(manager.connect(ws))
        asyncio.run(manager.subscribe(ws, "threats", connection_id))

        # Disconnect
        asyncio.run(manager.disconnect(ws, connection_id))

        # Broadcast message (should be queued)
        test_data = {"type": "threat.new", "data": {"threat": "offline_test"}}
        recipients = asyncio.run(manager.broadcast("threats", test_data))

        assert recipients == 0  # No active recipients

        # Check that message was queued
        assert manager.queued_messages == 1

    def test_connection_analytics(self):
        """Test connection analytics generation"""
        manager = WebSocketManager()
        ws = MockWebSocket()

        # Connect and subscribe
        connection_id = asyncio.run(manager.connect(ws))
        asyncio.run(manager.subscribe(ws, "threats", connection_id))

        # Get analytics
        analytics = manager.get_connection_analytics()

        assert analytics["active_connections"] == 1
        assert "threats" in analytics["channels"]
        assert connection_id in analytics["client_analytics"]

    def test_performance_metrics(self):
        """Test performance metrics generation"""
        manager = WebSocketManager()

        # Simulate some activity
        manager.messages_sent = 100
        manager.connections_accepted = 10
        manager.broadcast_errors = 2

        metrics = manager.get_performance_metrics()

        assert metrics["messages"]["total_sent"] == 100
        assert metrics["connections"]["total_accepted"] == 10
        assert metrics["errors"]["broadcast_errors"] == 2
        assert "send_rate" in metrics["messages"]
        assert "error_rate" in metrics["errors"]


class TestWebSocketServer:
    """Test WebSocketServer functionality"""

    def test_rate_limiting(self):
        """Test connection rate limiting"""
        rate_limiter = ConnectionRateLimiter(max_connections_per_ip=2, window_seconds=1)

        # Allow first connection
        assert rate_limiter.allow_connection("127.0.0.1")

        # Allow second connection
        assert rate_limiter.allow_connection("127.0.0.1")

        # Block third connection
        assert not rate_limiter.allow_connection("127.0.0.1")

        # Different IP should be allowed
        assert rate_limiter.allow_connection("192.168.1.1")

    def test_message_filtering(self):
        """Test message filtering based on permissions"""
        manager = WebSocketManager()

        # Test filtering logic
        client_permissions = {"READ_THREATS", "READ_ALERTS"}

        # Should allow threats
        assert manager.filter_message("threats", {}, client_permissions)

        # Should allow alerts
        assert manager.filter_message("alerts", {}, client_permissions)

        # Should deny metrics (no permission)
        assert not manager.filter_message("metrics", {}, client_permissions)

        # Should allow status (public)
        assert manager.filter_message("status", {}, set())

    def test_message_prioritization(self):
        """Test message priority determination"""
        manager = WebSocketManager()

        # Critical alert
        assert manager.prioritize_message("alerts", {"type": "alert.critical"}) == 3

        # High priority threat
        assert manager.prioritize_message("threats", {"type": "threat.new"}) == 2

        # Normal priority
        assert manager.prioritize_message("status", {"type": "status.update"}) == 1

    def test_compression(self):
        """Test message compression"""
        manager = WebSocketManager()

        # Small message (shouldn't compress)
        small_data = {"type": "test", "data": "small"}
        compressed, is_compressed = manager.compress_message(small_data, min_size=100)
        assert not is_compressed

        # Large message (should compress)
        large_data = {"type": "test", "data": "x" * 1000}
        compressed, is_compressed = manager.compress_message(large_data, min_size=100)
        assert is_compressed

        # Test decompression
        decompressed = manager.decompress_message(compressed, is_compressed)
        assert decompressed == large_data


class TestWebSocketIntegration:
    """Integration tests for WebSocket components"""

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self):
        """Test complete WebSocket connection lifecycle"""
        manager = WebSocketManager()
        server = WebSocketServer(manager)

        # Mock WebSocket
        ws = MockWebSocket()

        # Simulate connection
        connection_id = await manager.connect(ws)
        assert connection_id in manager.connection_health

        # Simulate message handling (this would normally be done by the server)
        # For this test, we'll just verify the manager state

        # Disconnect
        await manager.disconnect(ws, connection_id)
        assert connection_id not in manager.connection_health

    def test_message_batch_creation(self):
        """Test message batching functionality"""
        manager = WebSocketManager()

        messages = [
            {"type": "threat.new", "data": "msg1"},
            {"type": "threat.new", "data": "msg2"},
            {"type": "threat.new", "data": "msg3"},
        ]

        batches = manager.create_message_batch(messages, max_batch_size=2)

        assert len(batches) == 2
        assert batches[0]["batch_size"] == 2
        assert batches[1]["batch_size"] == 1
        assert "batch_id" in batches[0]


# Performance benchmarks
class TestWebSocketPerformance:
    """Performance tests for WebSocket components"""

    def test_broadcast_performance(self):
        """Test broadcast performance with multiple subscribers"""
        manager = WebSocketManager()

        # Create multiple mock connections
        connections = []
        for i in range(10):
            ws = MockWebSocket(f"127.0.0.{i}")
            connections.append(ws)
            connection_id = asyncio.run(manager.connect(ws))
            asyncio.run(manager.subscribe(ws, "threats", connection_id))

        # Measure broadcast time
        test_data = {"type": "threat.new", "data": {"threat": "perf_test"}}

        start_time = time.time()
        recipients = asyncio.run(manager.broadcast("threats", test_data))
        end_time = time.time()

        assert recipients == 10
        broadcast_time = end_time - start_time
        assert broadcast_time < 0.1  # Should complete in less than 100ms

    def test_queue_performance(self):
        """Test message queue performance"""
        queue = MessageQueue(max_messages_per_client=1000)

        # Queue many messages
        start_time = time.time()
        for i in range(1000):
            queue.enqueue_message(f"client{i%10}", "threats", {"msg": i})

        queue_time = time.time() - start_time
        assert queue_time < 1.0  # Should complete in less than 1 second

        # Dequeue messages
        start_time = time.time()
        total_messages = 0
        for i in range(10):
            messages = queue.dequeue_messages(f"client{i}")
            total_messages += len(messages)

        dequeue_time = time.time() - start_time
        assert total_messages == 1000
        assert dequeue_time < 0.5  # Should complete in less than 500ms


if __name__ == "__main__":
    # Run basic functionality tests
    print("Running WebSocket tests...")

    # Test MessageQueue
    queue_test = TestMessageQueue()
    queue_test.test_enqueue_dequeue_message()
    queue_test.test_message_expiration()
    queue_test.test_message_priority()
    queue_test.test_queue_capacity_limits()
    print("✓ MessageQueue tests passed")

    # Test WebSocketManager
    manager_test = TestWebSocketManager()
    manager_test.test_connection_management()
    manager_test.test_channel_subscription()
    manager_test.test_message_broadcasting()
    manager_test.test_message_queuing_for_offline_clients()
    manager_test.test_connection_analytics()
    manager_test.test_performance_metrics()
    print("✓ WebSocketManager tests passed")

    # Test WebSocketServer
    server_test = TestWebSocketServer()
    server_test.test_rate_limiting()
    server_test.test_message_filtering()
    server_test.test_message_prioritization()
    server_test.test_compression()
    print("✓ WebSocketServer tests passed")

    # Test integration
    integration_test = TestWebSocketIntegration()
    asyncio.run(integration_test.test_full_connection_lifecycle())
    integration_test.test_message_batch_creation()
    print("✓ Integration tests passed")

    # Performance tests
    perf_test = TestWebSocketPerformance()
    perf_test.test_broadcast_performance()
    perf_test.test_queue_performance()
    print("✓ Performance tests passed")

    print("\n🎉 All WebSocket tests completed successfully!")
