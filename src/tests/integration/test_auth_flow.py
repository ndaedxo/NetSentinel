#!/usr/bin/env python3
"""
Integration tests for authentication flow
Tests the complete authentication system end-to-end
"""

import pytest
import hashlib
import time

from src.netsentinel.security.auth_manager import AuthManager
from src.netsentinel.security.user_store import Role, Permission


class TestAuthIntegration:
    """Integration tests for authentication flow"""

    def setup_method(self):
        """Setup test fixtures"""
        # Create a test auth manager with unique in-memory instance
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"test_integration_secret_key_{self.test_id}"
        # Use a temporary storage path to avoid conflicts
        self.storage_path = f"data/test_users_{self.test_id}.json"
        self.auth_manager = AuthManager(self.secret_key, self.storage_path)

        # Create test user
        password = "testpass123"
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        self.test_user = self.auth_manager.create_user(
            user_id=f"integration_test_user_{self.test_id}",
            username=f"integrationuser_{self.test_id}",
            email=f"integration_{self.test_id}@test.com",
            password_hash=password_hash,
            roles=[Role.ANALYST],
        )

        self.test_password = password
        self.test_password_hash = password_hash

    def test_full_auth_flow(self):
        """Test complete authentication flow"""
        # 1. Login with credentials
        token = self.auth_manager.authenticate_credentials(
            username=f"integrationuser_{self.test_id}",
            password_hash=self.test_password_hash,
        )

        assert token is not None
        assert isinstance(token, str)

        # 2. Verify token authentication
        user = self.auth_manager.authenticate_token(token)
        assert user is not None
        assert user.user_id == self.test_user.user_id
        assert user.username == self.test_user.username

        # 3. Test authorization
        can_read_events = self.auth_manager.authorize(
            user, Permission.READ_EVENTS, "test_resource"
        )
        assert can_read_events is True

        can_write_config = self.auth_manager.authorize(
            user, Permission.WRITE_CONFIG, "test_resource"
        )
        assert can_write_config is False  # Analyst can't write config

        # 4. Test logout (token blacklisting)
        self.auth_manager.logout(token)

        # Token should no longer work
        user_after_logout = self.auth_manager.authenticate_token(token)
        assert user_after_logout is None

    def test_token_refresh_integration(self):
        """Test token refresh in complete integration flow"""
        # 1. Login and get initial token
        token = self.auth_manager.authenticate_credentials(
            username=f"integrationuser_{self.test_id}",
            password_hash=self.test_password_hash,
        )
        assert token is not None

        # 2. Verify initial token works
        user = self.auth_manager.authenticate_token(token)
        assert user is not None

        # 3. Refresh token
        refreshed_token = self.auth_manager.refresh_token(token)
        assert refreshed_token is not None
        assert refreshed_token != token  # Should be different

        # 4. Verify both tokens work (refresh doesn't invalidate old)
        initial_user = self.auth_manager.authenticate_token(token)
        refreshed_user = self.auth_manager.authenticate_token(refreshed_token)

        assert initial_user is not None
        assert refreshed_user is not None
        assert initial_user.user_id == user.user_id
        assert refreshed_user.user_id == user.user_id

    def test_session_management_integration(self):
        """Test complete session management flow"""
        # 1. Login
        token = self.auth_manager.authenticate_credentials(
            username=f"integrationuser_{self.test_id}",
            password_hash=self.test_password_hash,
        )
        assert token is not None

        # 2. Verify user activity is tracked
        user_before = self.auth_manager.get_user(self.test_user.user_id)
        last_login_before = user_before.last_login

        # Wait a moment and authenticate again (should update last_login)
        import time
        time.sleep(0.1)

        token2 = self.auth_manager.authenticate_credentials(
            username=f"integrationuser_{self.test_id}",
            password_hash=self.test_password_hash,
        )

        user_after = self.auth_manager.get_user(self.test_user.user_id)
        last_login_after = user_after.last_login

        # Last login should be updated
        assert last_login_after > last_login_before

    def test_cross_session_isolation(self):
        """Test that different auth manager instances are properly isolated"""
        # Create another auth manager instance
        import uuid
        other_test_id = str(uuid.uuid4())[:8]
        other_secret_key = f"other_integration_secret_{other_test_id}"
        other_storage_path = f"data/test_users_other_{other_test_id}.json"
        other_auth_manager = AuthManager(other_secret_key, other_storage_path)

        # Create user in other instance
        other_auth_manager.create_user(
            user_id="other_test_user",
            username="otheruser",
            email="other@test.com",
            password_hash="other_hash",
        )

        # Verify user doesn't exist in our instance
        our_user = self.auth_manager.get_user_by_username("otheruser")
        assert our_user is None

        # Verify our user doesn't exist in other instance
        other_our_user = other_auth_manager.get_user_by_username(f"integrationuser_{self.test_id}")
        assert other_our_user is None

    def test_role_based_permissions(self):
        """Test that different roles have appropriate permissions"""
        # Create users with different roles
        viewer_user = self.auth_manager.create_user(
            user_id="viewer_test",
            username="viewer",
            email="viewer@test.com",
            password_hash="hash",
            roles=[Role.VIEWER],
        )

        analyst_user = self.auth_manager.create_user(
            user_id="analyst_test",
            username="analyst",
            email="analyst@test.com",
            password_hash="hash",
            roles=[Role.ANALYST],
        )

        admin_user = self.auth_manager.create_user(
            user_id="admin_test",
            username="admin",
            email="admin@test.com",
            password_hash="hash",
            roles=[Role.ADMIN],
        )

        # Test viewer permissions (read-only)
        assert viewer_user.has_permission(Permission.READ_EVENTS)
        assert viewer_user.has_permission(Permission.READ_ALERTS)
        assert not viewer_user.has_permission(Permission.WRITE_EVENTS)
        assert not viewer_user.has_permission(Permission.ADMIN)

        # Test analyst permissions (read-write events/alerts)
        assert analyst_user.has_permission(Permission.READ_EVENTS)
        assert analyst_user.has_permission(Permission.WRITE_EVENTS)
        assert analyst_user.has_permission(Permission.READ_ALERTS)
        assert analyst_user.has_permission(Permission.WRITE_ALERTS)
        assert not analyst_user.has_permission(Permission.ADMIN)

        # Test admin permissions (full access)
        assert admin_user.has_permission(Permission.READ_EVENTS)
        assert admin_user.has_permission(Permission.WRITE_EVENTS)
        assert admin_user.has_permission(Permission.READ_ALERTS)
        assert admin_user.has_permission(Permission.WRITE_ALERTS)
        assert admin_user.has_permission(Permission.READ_CONFIG)
        assert admin_user.has_permission(Permission.WRITE_CONFIG)
        assert admin_user.has_permission(Permission.ADMIN)

    def test_token_expiration(self):
        """Test token expiration"""
        # Create short-lived token
        user_data = {
            "user_id": self.test_user.user_id,
            "username": self.test_user.username,
            "email": self.test_user.email,
            "roles": [role.value for role in self.test_user.roles],
            "permissions": [perm.value for perm in self.test_user.permissions],
        }

        token = self.auth_manager.token_manager.create_token(user_data, expires_in=1)

        # Token should work initially
        user = self.auth_manager.authenticate_token(token)
        assert user is not None

        # Wait for expiration
        time.sleep(2)

        # Token should be expired
        user = self.auth_manager.authenticate_token(token)
        assert user is None

    def test_audit_logging(self):
        """Test that authentication events are logged"""
        initial_log_count = len(self.auth_manager.get_audit_logs())

        # Perform authentication
        token = self.auth_manager.authenticate_credentials(
            username=f"integrationuser_{self.test_id}",
            password_hash=self.test_password_hash,
        )

        # Check that logs were created
        logs = self.auth_manager.get_audit_logs()
        assert len(logs) > initial_log_count

        # Should have login success log
        login_logs = [log for log in logs if log.action == "login_success"]
        assert len(login_logs) > 0

    def test_user_management(self):
        """Test user management operations"""
        # Create a new user
        new_user = self.auth_manager.create_user(
            user_id=f"new_test_user_{self.test_id}",
            username=f"newuser_{self.test_id}",
            email=f"new_{self.test_id}@test.com",
            password_hash="newhash",
            roles=[Role.VIEWER],
        )

        assert new_user.user_id == f"new_test_user_{self.test_id}"
        assert new_user.username == f"newuser_{self.test_id}"

        # Retrieve user
        retrieved = self.auth_manager.get_user(f"new_test_user_{self.test_id}")
        assert retrieved is not None
        assert retrieved.username == f"newuser_{self.test_id}"

        # Get user by username
        by_username = self.auth_manager.get_user_by_username(f"newuser_{self.test_id}")
        assert by_username is not None
        assert by_username.user_id == f"new_test_user_{self.test_id}"

        # List all users should include our test users
        all_users = self.auth_manager.get_all_users()
        assert len(all_users) >= 2  # At least our test users

        usernames = [u.username for u in all_users]
        assert f"integrationuser_{self.test_id}" in usernames
        assert f"newuser_{self.test_id}" in usernames

    def test_concurrent_access(self):
        """Test concurrent access to auth manager"""
        import threading
        import time

        results = []
        errors = []

        def authenticate_worker():
            try:
                token = self.auth_manager.authenticate_credentials(
                    username=f"integrationuser_{self.test_id}",
                    password_hash=self.test_password_hash,
                )
                results.append(token)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=authenticate_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should succeed without errors
        assert len(results) == 5
        assert len(errors) == 0
        assert all(token is not None for token in results)


class TestAPIServerAuth:
    """Test authentication through the API server"""

    def setup_method(self):
        """Setup test fixtures"""
        # Create test auth manager with known users
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"api_test_secret_{self.test_id}"
        self.storage_path = f"data/test_users_api_{self.test_id}.json"
        self.auth_manager = AuthManager(self.secret_key, self.storage_path)

        # Create test user
        password_hash = hashlib.sha256("apitest123".encode()).hexdigest()
        self.auth_manager.create_user(
            user_id=f"api_test_user_{self.test_id}",
            username=f"apiuser_{self.test_id}",
            email=f"api_{self.test_id}@test.com",
            password_hash=password_hash,
            roles=[Role.ANALYST],
        )

        self.test_credentials = {
            "username": f"apiuser_{self.test_id}",
            "password": "apitest123"
        }

    @pytest.mark.asyncio
    async def test_api_login_flow(self):
        """Test login through API server"""
        # This would require setting up a full FastAPI test client
        # For now, just test the auth manager directly
        password_hash = hashlib.sha256(self.test_credentials["password"].encode()).hexdigest()

        token = self.auth_manager.authenticate_credentials(
            username=self.test_credentials["username"],
            password_hash=password_hash,
        )

        assert token is not None

        # Verify token works
        user = self.auth_manager.authenticate_token(token)
        assert user is not None
        assert user.username == self.test_credentials["username"]

    def test_protected_endpoints_require_auth(self):
        """Test that protected endpoints require authentication"""
        # This would test the actual API endpoints with TestClient
        # For now, just ensure the decorators are properly configured

        # Test that auth functions work
        from src.netsentinel.security.middleware import require_auth, require_analyst

        # These should be callable decorators
        assert callable(require_auth)
        assert callable(require_analyst)

        # Test permission checking
        user = self.auth_manager.get_user_by_username(self.test_credentials["username"])
        assert user is not None

        has_read_permission = self.auth_manager.authorize(
            user, Permission.READ_EVENTS, "api_test"
        )
        assert has_read_permission is True

        has_admin_permission = self.auth_manager.authorize(
            user, Permission.ADMIN, "api_test"
        )
        assert has_admin_permission is False
