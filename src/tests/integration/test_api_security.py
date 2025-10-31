#!/usr/bin/env python3
"""
API Security Integration Tests for NetSentinel
Tests authentication, authorization, and security middleware
"""

import pytest
import hashlib
import time

from src.netsentinel.security.auth_manager import AuthManager
from src.netsentinel.security.user_store import Role, Permission


class TestAPISecurity:
    """Test API security middleware and authorization"""

    def setup_method(self):
        """Setup test fixtures"""
        # Create isolated auth manager
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"api_security_test_{self.test_id}"
        self.storage_path = f"data/test_users_api_security_{self.test_id}.json"
        self.auth_manager = AuthManager(self.secret_key, self.storage_path)

        # Create test users with different roles
        self.viewer_user = self.auth_manager.create_user(
            user_id=f"viewer_user_{self.test_id}",
            username=f"viewer_{self.test_id}",
            email=f"viewer_{self.test_id}@test.com",
            password_hash=hashlib.sha256("viewerpass".encode()).hexdigest(),
            roles=[Role.VIEWER],
        )

        self.analyst_user = self.auth_manager.create_user(
            user_id=f"analyst_user_{self.test_id}",
            username=f"analyst_{self.test_id}",
            email=f"analyst_{self.test_id}@test.com",
            password_hash=hashlib.sha256("analystpass".encode()).hexdigest(),
            roles=[Role.ANALYST],
        )

        self.admin_user = self.auth_manager.create_user(
            user_id=f"admin_user_{self.test_id}",
            username=f"admin_{self.test_id}",
            email=f"admin_{self.test_id}@test.com",
            password_hash=hashlib.sha256("adminpass".encode()).hexdigest(),
            roles=[Role.ADMIN],
        )

        # Get tokens for different users
        self.viewer_token = self.auth_manager.authenticate_credentials(
            f"viewer_{self.test_id}",
            hashlib.sha256("viewerpass".encode()).hexdigest(),
        )

        self.analyst_token = self.auth_manager.authenticate_credentials(
            f"analyst_{self.test_id}",
            hashlib.sha256("analystpass".encode()).hexdigest(),
        )

        self.admin_token = self.auth_manager.authenticate_credentials(
            f"admin_{self.test_id}",
            hashlib.sha256("adminpass".encode()).hexdigest(),
        )

        # Temporarily replace the global auth manager for testing
        import src.netsentinel.security.auth_manager as auth_module
        self.original_get_auth_manager = auth_module.get_auth_manager
        auth_module._auth_manager = self.auth_manager  # Set our test instance

    def teardown_method(self):
        """Restore original auth manager"""
        import src.netsentinel.security.auth_manager as auth_module
        auth_module._auth_manager = None  # Reset to None so get_auth_manager creates new instance

    def test_token_authentication_for_different_roles(self):
        """Test that tokens authenticate correctly for different user roles"""
        # Test viewer token
        viewer_user = self.auth_manager.authenticate_token(self.viewer_token)
        assert viewer_user is not None
        assert viewer_user.username == f"viewer_{self.test_id}"
        assert viewer_user.has_role(Role.VIEWER)

        # Test analyst token
        analyst_user = self.auth_manager.authenticate_token(self.analyst_token)
        assert analyst_user is not None
        assert analyst_user.username == f"analyst_{self.test_id}"
        assert analyst_user.has_role(Role.ANALYST)

        # Test admin token
        admin_user = self.auth_manager.authenticate_token(self.admin_token)
        assert admin_user is not None
        assert admin_user.username == f"admin_{self.test_id}"
        assert admin_user.has_role(Role.ADMIN)

    def test_invalid_token_rejection(self):
        """Test that invalid tokens are properly rejected"""
        invalid_tokens = [
            "invalid_token",
            "",
            None,
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",  # Valid JWT but not our token
        ]

        for invalid_token in invalid_tokens:
            user = self.auth_manager.authenticate_token(invalid_token)
            assert user is None, f"Invalid token '{invalid_token}' should be rejected"

    def test_expired_token_handling(self):
        """Test that expired tokens are properly rejected"""
        # Create a short-lived token (1 second)
        expired_token = self.auth_manager.token_manager.create_token({
            "user_id": self.viewer_user.user_id,
            "username": self.viewer_user.username,
        }, expires_in=1)

        # Token should work initially
        user = self.auth_manager.authenticate_token(expired_token)
        assert user is not None

        # Wait for expiration
        time.sleep(2)

        # Token should now be expired
        user = self.auth_manager.authenticate_token(expired_token)
        assert user is None

    def test_role_based_permissions_integration(self):
        """Test that role-based permissions work correctly in integration"""
        # Test viewer permissions (read-only)
        viewer_user = self.auth_manager.authenticate_token(self.viewer_token)
        assert viewer_user.has_permission(Permission.READ_EVENTS)
        assert viewer_user.has_permission(Permission.READ_ALERTS)
        assert not viewer_user.has_permission(Permission.WRITE_EVENTS)
        assert not viewer_user.has_permission(Permission.ADMIN)

        # Test analyst permissions (read-write events/alerts)
        analyst_user = self.auth_manager.authenticate_token(self.analyst_token)
        assert analyst_user.has_permission(Permission.READ_EVENTS)
        assert analyst_user.has_permission(Permission.WRITE_EVENTS)
        assert analyst_user.has_permission(Permission.READ_ALERTS)
        assert analyst_user.has_permission(Permission.WRITE_ALERTS)
        assert not analyst_user.has_permission(Permission.ADMIN)

        # Test admin permissions (full access)
        admin_user = self.auth_manager.authenticate_token(self.admin_token)
        assert admin_user.has_permission(Permission.READ_EVENTS)
        assert admin_user.has_permission(Permission.WRITE_EVENTS)
        assert admin_user.has_permission(Permission.READ_ALERTS)
        assert admin_user.has_permission(Permission.WRITE_ALERTS)
        assert admin_user.has_permission(Permission.READ_CONFIG)
        assert admin_user.has_permission(Permission.WRITE_CONFIG)
        assert admin_user.has_permission(Permission.ADMIN)

    def test_token_refresh_integration(self):
        """Test token refresh functionality in integration"""
        # Refresh the viewer token
        refreshed_token = self.auth_manager.refresh_token(self.viewer_token)

        assert refreshed_token is not None
        assert refreshed_token != self.viewer_token  # Should be different

        # Both old and new tokens should work (refresh doesn't invalidate old)
        old_user = self.auth_manager.authenticate_token(self.viewer_token)
        new_user = self.auth_manager.authenticate_token(refreshed_token)

        assert old_user is not None
        assert new_user is not None
        assert old_user.user_id == self.viewer_user.user_id
        assert new_user.user_id == self.viewer_user.user_id

    def test_logout_invalidates_tokens(self):
        """Test that logout properly invalidates tokens"""
        # Verify token works before logout
        user = self.auth_manager.authenticate_token(self.viewer_token)
        assert user is not None

        # Logout the token
        self.auth_manager.logout(self.viewer_token)

        # Token should no longer work
        user = self.auth_manager.authenticate_token(self.viewer_token)
        assert user is None

    def test_audit_logging_for_security_events(self):
        """Test that security events are properly audited"""
        initial_count = len(self.auth_manager.get_audit_logs())

        # Perform authentication
        user = self.auth_manager.authenticate_credentials(
            f"viewer_{self.test_id}",
            hashlib.sha256("viewerpass".encode()).hexdigest(),
        )

        # Check that audit logs were created
        logs = self.auth_manager.get_audit_logs()
        assert len(logs) > initial_count

        # Should have login success log
        login_logs = [log for log in logs if log.action == "login_success"]
        assert len(login_logs) > 0

    def test_concurrent_authentication_security(self):
        """Test that authentication works securely under concurrent access"""
        import threading

        results = []
        errors = []

        def authenticate_worker():
            try:
                token = self.auth_manager.authenticate_credentials(
                    f"viewer_{self.test_id}",
                    hashlib.sha256("viewerpass".encode()).hexdigest(),
                )
                results.append(token)
            except Exception as e:
                errors.append(e)

        # Start multiple threads trying to authenticate simultaneously
        threads = []
        for i in range(10):
            thread = threading.Thread(target=authenticate_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should succeed without errors
        assert len(results) == 10
        assert len(errors) == 0
        assert all(token is not None for token in results)

    def test_user_session_isolation(self):
        """Test that different user sessions are properly isolated"""
        # Each user should get different tokens
        assert self.viewer_token != self.analyst_token
        assert self.viewer_token != self.admin_token
        assert self.analyst_token != self.admin_token

        # Each token should authenticate to the correct user
        viewer_user = self.auth_manager.authenticate_token(self.viewer_token)
        analyst_user = self.auth_manager.authenticate_token(self.analyst_token)
        admin_user = self.auth_manager.authenticate_token(self.admin_token)

        assert viewer_user.username == f"viewer_{self.test_id}"
        assert analyst_user.username == f"analyst_{self.test_id}"
        assert admin_user.username == f"admin_{self.test_id}"

    def test_password_security_workflow(self):
        """Test password security workflow (current implementation)"""
        # Use the same password hash that was used to create the user
        correct_password_hash = hashlib.sha256("viewerpass".encode()).hexdigest()

        # Test successful authentication
        token = self.auth_manager.authenticate_credentials(
            f"viewer_{self.test_id}",
            correct_password_hash,
        )
        assert token is not None

        # Test failed authentication with wrong hash
        wrong_token = self.auth_manager.authenticate_credentials(
            f"viewer_{self.test_id}",
            "wrong_hash",
        )
        assert wrong_token is None

    def test_rate_limiting_concept(self):
        """Test rate limiting concept (placeholder for future implementation)"""
        # This would test rate limiting if implemented
        # For now, just verify multiple rapid authentications work
        for i in range(20):
            token = self.auth_manager.authenticate_credentials(
                f"viewer_{self.test_id}",
                hashlib.sha256("viewerpass".encode()).hexdigest(),
            )
            assert token is not None

    def test_middleware_integration_ready(self):
        """Test that middleware components are ready for integration"""
        # Test that we can import middleware functions
        try:
            from src.netsentinel.security.middleware import get_current_user, require_auth, require_analyst
            assert callable(get_current_user)
            assert callable(require_auth)
            assert callable(require_analyst)
        except ImportError:
            pytest.skip("Middleware not fully implemented yet")