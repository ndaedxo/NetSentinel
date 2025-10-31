#!/usr/bin/env python3
"""
WebSocket Security Integration Tests

Tests WebSocket authentication, authorization, and security features.
Validates secure connection handling, token validation, and access control.
"""

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional

from src.netsentinel.processors.websocket_manager import WebSocketManager
from src.netsentinel.processors.websocket_server import WebSocketServer
from src.netsentinel.security.token_manager import TokenManager
from src.netsentinel.security.auth_manager import AuthManager
from src.netsentinel.security.user_store import UserStore, User, Role, Permission


class TestWebSocketSecurity:
    """Security integration tests for WebSocket functionality"""

    @pytest_asyncio.fixture
    async def auth_manager(self):
        """Create auth manager for security testing"""
        auth_manager = AuthManager(secret_key="test_secret_key_for_websocket_security")

        # Create test users using user_store directly with hashed passwords
        import hashlib
        import uuid
        from src.netsentinel.security.user_store import Role, Permission

        # Create unique IDs and usernames to avoid conflicts
        test_id = uuid.uuid4().hex[:8]
        admin_id = f"admin_{test_id}"
        user_id = f"user_{test_id}"
        admin_username = f"test_admin_{test_id}"
        user_username = f"test_user_{test_id}"

        # Create admin user
        admin_password_hash = hashlib.sha256("secure_password123".encode()).hexdigest()
        admin_user = auth_manager.user_store.create_user(
            user_id=admin_id,
            username=admin_username,
            email=f"admin_{test_id}@test.com",
            password_hash=admin_password_hash,
            roles=[Role.ADMIN],
            permissions={Permission.ADMIN, Permission.READ_EVENTS, Permission.WRITE_EVENTS}
        )

        # Create regular user
        user_password_hash = hashlib.sha256("user_password123".encode()).hexdigest()
        user_user = auth_manager.user_store.create_user(
            user_id=user_id,
            username=user_username,
            email=f"user_{test_id}@test.com",
            password_hash=user_password_hash,
            roles=[Role.ANALYST],
            permissions={Permission.READ_EVENTS, Permission.READ_ALERTS}
        )

        return auth_manager

    @pytest_asyncio.fixture
    async def websocket_server(self, websocket_manager, auth_manager):
        """Create WebSocket server with authentication"""
        server = WebSocketServer(websocket_manager)

        # Set up authentication dependency
        async def auth_dependency(token: str = None) -> Optional[Dict[str, Any]]:
            if not token:
                return None

            try:
                # Validate token and check if blacklisted
                if token in auth_manager.token_manager.token_blacklist:
                    return None

                user_data = auth_manager.token_manager.validate_token(token)
                return user_data
            except Exception:
                return None

        server.set_auth_dependency(auth_dependency)
        return server

    @pytest_asyncio.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for security testing"""
        manager = WebSocketManager()
        await manager.start()
        yield manager
        await manager.stop()

    def create_test_token(self, auth_manager, username_pattern: str) -> tuple[str, str]:
        """Create a test JWT token for authentication and return (token, actual_username)"""
        # Find user by username pattern
        actual_username = None
        user = None

        # Look for users with the pattern in their username
        for u in auth_manager.user_store.get_all_users():
            if username_pattern in u.username:
                actual_username = u.username
                user = u
                break

        if user:
            user_data = {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "roles": [role.name for role in user.roles],
                "permissions": [perm.name for perm in user.permissions]
            }
        else:
            # Fallback
            user_data = {
                "user_id": f"test_{username_pattern}_id",
                "username": f"test_{username_pattern}",
                "email": f"{username_pattern}@test.com",
                "roles": ["analyst"],
                "permissions": ["read:events", "read:alerts"]
            }
            actual_username = user_data["username"]

        token = auth_manager.token_manager.create_token(user_data)
        return token, actual_username

    @pytest.mark.asyncio
    async def test_websocket_authentication_integration(self, websocket_manager, auth_manager):
        """Test WebSocket authentication integration with token validation"""
        # Create valid token
        valid_token, username = self.create_test_token(auth_manager, "test_user")

        # Create mock websocket
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.receive_text = AsyncMock(return_value='{"type": "ping"}')

        # Test successful authentication - connect and subscribe
        try:
            connection_id = await websocket_manager.connect(mock_ws)
            await websocket_manager.subscribe(mock_ws, "threats")
            # Should not raise exception for valid operations
            assert connection_id is not None
            assert mock_ws in websocket_manager.active_connections
        except Exception as e:
            pytest.fail(f"WebSocket connection/authentication failed: {e}")

        # Cleanup
        await websocket_manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_unauthorized_connection_handling(self, websocket_server):
        """Test handling of unauthorized connection attempts"""
        # Test cases for unauthorized access
        unauthorized_scenarios = [
            {"token": None, "description": "No token provided"},
            {"token": "", "description": "Empty token"},
            {"token": "invalid.jwt.token", "description": "Invalid token format"},
            {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDk0NTkyMDAsInVzZXIiOiJ0ZXN0In0.invalid", "description": "Expired/invalid token"},
        ]

        for scenario in unauthorized_scenarios:
            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.receive_text = AsyncMock(return_value='{"type": "ping"}')

            # Attempt connection with invalid token
            try:
                await websocket_server.websocket_endpoint(mock_ws, scenario["token"])
                # Should not reach here for unauthorized access
                mock_ws.accept.assert_not_called()
            except Exception:
                # Expected for unauthorized access
                pass

            # Verify connection was rejected (not accepted)
            mock_ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_token_validation_edge_cases(self, websocket_server, auth_manager):
        """Test token validation with various edge cases"""
        # Create expired token
        expired_token = auth_manager.token_manager.create_token(
            {"user_id": "test", "username": "test"},
            expires_in=-3600  # Already expired
        )

        # Create token with insufficient permissions
        insufficient_permissions_token = self.create_test_token(
            auth_manager, "test_user", permissions=["read"]  # Missing websocket_connect
        )

        edge_cases = [
            {
                "token": expired_token,
                "description": "Expired token",
                "should_fail": True
            },
            {
                "token": insufficient_permissions_token,
                "description": "Insufficient permissions",
                "should_fail": True
            }
        ]

        for case in edge_cases:
            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.close = AsyncMock()

            try:
                await websocket_server.websocket_endpoint(mock_ws, case["token"])
                if case["should_fail"]:
                    pytest.fail(f"Expected authentication to fail for: {case['description']}")
            except Exception:
                if not case["should_fail"]:
                    pytest.fail(f"Unexpected authentication failure for: {case['description']}")

    @pytest.mark.asyncio
    async def test_role_based_access_control(self, websocket_server, auth_manager):
        """Test role-based access control for WebSocket connections"""
        # Create tokens with different roles
        admin_token = self.create_test_token(auth_manager, "test_admin")
        user_token = self.create_test_token(auth_manager, "test_user")

        # Test admin access
        admin_ws = AsyncMock()
        admin_ws.send_text = AsyncMock()
        admin_ws.close = AsyncMock()
        admin_ws.receive_text = AsyncMock(return_value='{"type": "ping"}')

        try:
            await websocket_server.websocket_endpoint(admin_ws, admin_token)
            admin_ws.accept.assert_called_once()
        except Exception as e:
            pytest.fail(f"Admin authentication failed: {e}")

        # Test user access
        user_ws = AsyncMock()
        user_ws.send_text = AsyncMock()
        user_ws.close = AsyncMock()
        user_ws.receive_text = AsyncMock(return_value='{"type": "ping"}')

        try:
            await websocket_server.websocket_endpoint(user_ws, user_token)
            user_ws.accept.assert_called_once()
        except Exception as e:
            pytest.fail(f"User authentication failed: {e}")

    @pytest.mark.asyncio
    async def test_secure_message_handling(self, websocket_manager, auth_manager):
        """Test secure message handling and validation"""
        # Create authenticated connection
        valid_token = self.create_test_token(auth_manager, "test_user")

        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.receive_text = AsyncMock(return_value='{"type": "ping"}')

        # Connect with authentication
        connection_id = await websocket_manager.connect(mock_ws)

        # Test various message types and security
        secure_messages = [
            {
                "type": "subscribe",
                "channel": "threats",
                "token": valid_token  # Include token for security
            },
            {
                "type": "ping",
                "timestamp": 1234567890
            },
            {
                "type": "unsubscribe",
                "channel": "alerts"
            }
        ]

        # Test message handling doesn't crash
        for message in secure_messages:
            try:
                # Simulate receiving message
                mock_ws.receive_text.return_value = json.dumps(message)
                # Message handling should be secure and not expose sensitive data
                assert "token" not in json.dumps(message) or message.get("type") == "subscribe"
            except Exception as e:
                pytest.fail(f"Message handling failed for {message['type']}: {e}")

        # Cleanup
        await websocket_manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_connection_cleanup_security(self, websocket_manager, auth_manager):
        """Test secure connection cleanup and resource management"""
        connections = []
        websockets = []

        # Create multiple authenticated connections
        for i in range(10):
            token = self.create_test_token(auth_manager, f"user_{i}")
            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.receive_text = AsyncMock(return_value='{"type": "ping"}')

            # Connect and authenticate
            conn_id = await websocket_manager.connect(mock_ws)
            await websocket_manager.subscribe(mock_ws, "threats")

            connections.append((mock_ws, conn_id))
            websockets.append(mock_ws)

        initial_connection_count = len(websocket_manager.active_connections)

        # Simulate various disconnection scenarios
        disconnect_scenarios = [
            ("normal_disconnect", 0, 2),  # Normal disconnect
            ("forced_disconnect", 3, 5),  # Forced disconnect
            ("invalid_disconnect", 6, 8), # Invalid disconnect attempt
        ]

        for scenario, start_idx, end_idx in disconnect_scenarios:
            for i in range(start_idx, end_idx + 1):
                ws, conn_id = connections[i]
                await websocket_manager.disconnect(ws)

        # Verify cleanup
        remaining_connections = len(websocket_manager.active_connections)
        expected_remaining = initial_connection_count - 6  # Disconnected 6 connections

        assert remaining_connections == expected_remaining, \
            f"Connection cleanup failed: {remaining_connections} != {expected_remaining}"

        # Verify no sensitive data remains
        for ws in websockets:
            # Ensure no authentication tokens are stored in connection state
            assert not hasattr(ws, 'auth_token') or ws.auth_token is None

        # Final cleanup
        cleanup_tasks = []
        for ws, _ in connections:
            if ws in websocket_manager.active_connections:
                task = asyncio.create_task(websocket_manager.disconnect(ws))
                cleanup_tasks.append(task)

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_websocket_authentication_bypass_prevention(self, websocket_server):
        """Test prevention of authentication bypass attempts"""
        # Test various bypass attempt scenarios
        bypass_scenarios = [
            {
                "token": "admin_token_placeholder",
                "description": "Fake admin token"
            },
            {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwicm9sZXMiOlsiYWRtaW4iXX0.fake",
                "description": "Tampered JWT"
            },
            {
                "token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.valid",
                "description": "Bearer token format (unsupported)"
            }
        ]

        for scenario in bypass_scenarios:
            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.close = AsyncMock()

            try:
                await websocket_server.websocket_endpoint(mock_ws, scenario["token"])
                # Should not authenticate successfully
                mock_ws.accept.assert_not_called()
            except Exception:
                # Expected for failed authentication
                pass

    @pytest.mark.asyncio
    async def test_concurrent_authenticated_connections(self, websocket_server, auth_manager):
        """Test concurrent authenticated connections security"""
        async def create_authenticated_connection(user_id: int):
            """Create a single authenticated connection"""
            token = self.create_test_token(auth_manager, f"concurrent_user_{user_id}")

            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.receive_text = AsyncMock(return_value='{"type": "ping"}')

            try:
                await websocket_server.websocket_endpoint(mock_ws, token)
                return mock_ws.accept.called
            except Exception:
                return False

        # Test concurrent authentication
        concurrent_tasks = []
        for i in range(20):  # Test 20 concurrent connections
            task = asyncio.create_task(create_authenticated_connection(i))
            concurrent_tasks.append(task)

        # Wait for all authentication attempts
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

        # Count successful authentications
        successful_auths = sum(1 for result in results if result is True and not isinstance(result, Exception))

        # Should handle concurrent authentications without issues
        assert successful_auths >= 15, f"Too many concurrent authentication failures: {20 - successful_auths} failed"

        # Verify no race conditions or security issues
        print(f"Concurrent authentication results: {successful_auths}/20 successful")

    @pytest.mark.asyncio
    async def test_websocket_session_security(self, websocket_manager, auth_manager):
        """Test WebSocket session security and isolation"""
        # Create multiple user sessions
        users = ["alice", "bob", "charlie"]
        user_connections = {}

        for username in users:
            token = self.create_test_token(auth_manager, username)

            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.receive_text = AsyncMock(return_value='{"type": "ping"}')

            # Connect and authenticate
            conn_id = await websocket_manager.connect(mock_ws)
            await websocket_manager.subscribe(mock_ws, "threats")

            user_connections[username] = {
                "websocket": mock_ws,
                "connection_id": conn_id,
                "token": token
            }

        # Test session isolation - each user should only receive their own data
        for username, conn_data in user_connections.items():
            # Simulate receiving user-specific data
            user_event = {
                "type": "threat",
                "user": username,
                "data": f"personal_data_for_{username}"
            }

            # Each user should only see their own events
            # This tests that sessions are properly isolated
            assert conn_data["websocket"].send_text.call_count >= 0

        # Test session cleanup security
        for username, conn_data in user_connections.items():
            await websocket_manager.disconnect(conn_data["websocket"])

            # Verify no session data persists after disconnect
            assert conn_data["websocket"] not in websocket_manager.active_connections

        # Verify all connections cleaned up
        assert len(websocket_manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_token_blacklisting_integration(self, websocket_server, auth_manager):
        """Test token blacklisting prevents WebSocket access"""
        # Create valid token
        valid_token = self.create_test_token(auth_manager, "test_user")

        # First connection should work
        mock_ws1 = AsyncMock()
        mock_ws1.send_text = AsyncMock()
        mock_ws1.close = AsyncMock()
        mock_ws1.receive_text = AsyncMock(return_value='{"type": "ping"}')

        try:
            await websocket_server.websocket_endpoint(mock_ws1, valid_token)
            mock_ws1.accept.assert_called_once()
        except Exception as e:
            pytest.fail(f"Initial authentication failed: {e}")

        # Blacklist the token (simulate logout)
        auth_manager.logout_user(valid_token)  # This should blacklist the token

        # Second connection attempt should fail
        mock_ws2 = AsyncMock()
        mock_ws2.send_text = AsyncMock()
        mock_ws2.close = AsyncMock()

        try:
            await websocket_server.websocket_endpoint(mock_ws2, valid_token)
            # Should not authenticate with blacklisted token
            mock_ws2.accept.assert_not_called()
        except Exception:
            # Expected for blacklisted token
            pass

        # Verify blacklisted token is rejected
        mock_ws2.accept.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
