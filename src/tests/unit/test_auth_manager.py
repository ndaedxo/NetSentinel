#!/usr/bin/env python3
"""
Unit tests for AuthManager
"""

import pytest
import hashlib
import time

from src.netsentinel.security.auth_manager import AuthManager
from src.netsentinel.security.user_store import Role, Permission


class TestAuthManager:
    """Test cases for AuthManager"""

    def setup_method(self):
        """Setup test fixtures"""
        # Create a fresh auth manager for each test with unique instance
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"test_secret_key_{self.test_id}"
        # Use temporary storage path to avoid conflicts
        self.storage_path = f"data/test_users_unit_{self.test_id}.json"
        self.auth_manager = AuthManager(self.secret_key, self.storage_path)

    def test_create_user(self):
        """Test user creation"""
        user = self.auth_manager.create_user(
            user_id="test_user_1",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            roles=[Role.ANALYST],
        )

        assert user.user_id == "test_user_1"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert Role.ANALYST in user.roles
        assert user.has_permission(Permission.READ_EVENTS)
        assert user.has_permission(Permission.WRITE_EVENTS)

    def test_authenticate_credentials_success(self):
        """Test successful credential authentication"""
        # Create a test user
        password = "testpass123"
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        self.auth_manager.create_user(
            user_id="test_user_auth",
            username="testuser",
            email="test@example.com",
            password_hash=password_hash,
            roles=[Role.VIEWER],
        )

        # Authenticate
        token = self.auth_manager.authenticate_credentials(
            username="testuser",
            password_hash=password_hash,
        )

        assert token is not None
        assert isinstance(token, str)

    def test_authenticate_credentials_failure(self):
        """Test failed credential authentication"""
        # Wrong password
        token = self.auth_manager.authenticate_credentials(
            username="nonexistent",
            password_hash="wrong_hash",
        )

        assert token is None

    def test_authenticate_token_success(self):
        """Test successful token authentication"""
        # Create user and get token
        password_hash = hashlib.sha256("password".encode()).hexdigest()
        user = self.auth_manager.create_user(
            user_id="test_user_token",
            username="tokenuser",
            email="token@example.com",
            password_hash=password_hash,
            roles=[Role.ADMIN],
        )

        token = self.auth_manager.authenticate_credentials(
            username="tokenuser",
            password_hash=password_hash,
        )

        # Authenticate with token
        authenticated_user = self.auth_manager.authenticate_token(token)

        assert authenticated_user is not None
        assert authenticated_user.user_id == user.user_id
        assert authenticated_user.username == user.username

    def test_authenticate_token_failure(self):
        """Test failed token authentication"""
        user = self.auth_manager.authenticate_token("invalid_token")
        assert user is None

    def test_authorize_success(self):
        """Test successful authorization"""
        # Create admin user
        user = self.auth_manager.create_user(
            user_id="test_admin",
            username="adminuser",
            email="admin@example.com",
            password_hash="hash",
            roles=[Role.ADMIN],
        )

        # Should be able to read events
        result = self.auth_manager.authorize(
            user, Permission.READ_EVENTS, "test_resource"
        )
        assert result is True

    def test_authorize_failure(self):
        """Test failed authorization"""
        # Create viewer user
        user = self.auth_manager.create_user(
            user_id="test_viewer",
            username="vieweruser",
            email="viewer@example.com",
            password_hash="hash",
            roles=[Role.VIEWER],
        )

        # Should NOT be able to write events
        result = self.auth_manager.authorize(
            user, Permission.WRITE_EVENTS, "test_resource"
        )
        assert result is False

    def test_logout(self):
        """Test user logout"""
        # Create user and login
        password_hash = hashlib.sha256("password".encode()).hexdigest()
        self.auth_manager.create_user(
            user_id="test_logout",
            username="logoutuser",
            email="logout@example.com",
            password_hash=password_hash,
        )

        token = self.auth_manager.authenticate_credentials(
            username="logoutuser",
            password_hash=password_hash,
        )

        # Verify token works
        user = self.auth_manager.authenticate_token(token)
        assert user is not None

        # Logout
        self.auth_manager.logout(token)

        # Token should no longer work
        user = self.auth_manager.authenticate_token(token)
        assert user is None

    def test_get_user(self):
        """Test getting user by ID"""
        created_user = self.auth_manager.create_user(
            user_id="test_get_user",
            username="getuser",
            email="get@example.com",
            password_hash="hash",
        )

        retrieved_user = self.auth_manager.get_user("test_get_user")

        assert retrieved_user is not None
        assert retrieved_user.user_id == created_user.user_id
        assert retrieved_user.username == created_user.username

    def test_get_user_by_username(self):
        """Test getting user by username"""
        created_user = self.auth_manager.create_user(
            user_id="test_get_by_username",
            username="uniqueusername",
            email="unique@example.com",
            password_hash="hash",
        )

        retrieved_user = self.auth_manager.get_user_by_username("uniqueusername")

        assert retrieved_user is not None
        assert retrieved_user.user_id == created_user.user_id

    def test_get_all_users(self):
        """Test getting all users"""
        initial_count = len(self.auth_manager.get_all_users())

        self.auth_manager.create_user(
            user_id="test_all_1",
            username="user1",
            email="user1@example.com",
            password_hash="hash1",
        )

        self.auth_manager.create_user(
            user_id="test_all_2",
            username="user2",
            email="user2@example.com",
            password_hash="hash2",
        )

        all_users = self.auth_manager.get_all_users()
        assert len(all_users) == initial_count + 2

        usernames = [u.username for u in all_users]
        assert "user1" in usernames
        assert "user2" in usernames

    def test_user_role_permissions(self):
        """Test that roles grant appropriate permissions"""
        # Test admin user
        admin_user = self.auth_manager.create_user(
            user_id="test_admin_perms",
            username="adminperms",
            email="admin@example.com",
            password_hash="hash",
            roles=[Role.ADMIN],
        )

        assert admin_user.has_role(Role.ADMIN)
        assert admin_user.has_permission(Permission.ADMIN)
        assert admin_user.has_permission(Permission.READ_CONFIG)
        assert admin_user.has_permission(Permission.WRITE_CONFIG)

        # Test analyst user
        analyst_user = self.auth_manager.create_user(
            user_id="test_analyst_perms",
            username="analystperms",
            email="analyst@example.com",
            password_hash="hash",
            roles=[Role.ANALYST],
        )

        assert analyst_user.has_role(Role.ANALYST)
        assert analyst_user.has_permission(Permission.READ_EVENTS)
        assert analyst_user.has_permission(Permission.WRITE_EVENTS)
        assert not analyst_user.has_permission(Permission.ADMIN)

        # Test viewer user
        viewer_user = self.auth_manager.create_user(
            user_id="test_viewer_perms",
            username="viewerperms",
            email="viewer@example.com",
            password_hash="hash",
            roles=[Role.VIEWER],
        )

        assert viewer_user.has_role(Role.VIEWER)
        assert viewer_user.has_permission(Permission.READ_EVENTS)
        assert not viewer_user.has_permission(Permission.WRITE_EVENTS)
        assert not viewer_user.has_permission(Permission.ADMIN)

    def test_duplicate_user_creation(self):
        """Test that duplicate users cannot be created"""
        self.auth_manager.create_user(
            user_id="test_duplicate",
            username="dupeuser",
            email="dupe@example.com",
            password_hash="hash",
        )

        # Try to create user with same ID
        with pytest.raises(ValueError):
            self.auth_manager.create_user(
                user_id="test_duplicate",
                username="different",
                email="different@example.com",
                password_hash="hash",
            )

        # Try to create user with same username
        with pytest.raises(ValueError):
            self.auth_manager.create_user(
                user_id="different_id",
                username="dupeuser",
                email="different@example.com",
                password_hash="hash",
            )

    def test_password_hash_verification_workflow(self):
        """Test password hash verification through authentication"""
        # Create a user with a specific password hash
        password_hash = "test_password_hash_123"
        user = self.auth_manager.create_user(
            user_id="password_test_user",
            username="passwordtest",
            email="password@example.com",
            password_hash=password_hash,
        )

        # Test successful authentication with correct hash
        token = self.auth_manager.authenticate_credentials(
            username="passwordtest",
            password_hash=password_hash,
        )
        assert token is not None

        # Test failed authentication with wrong hash
        wrong_token = self.auth_manager.authenticate_credentials(
            username="passwordtest",
            password_hash="wrong_hash",
        )
        assert wrong_token is None

    def test_jwt_token_validation(self):
        """Test JWT token generation and validation"""
        # Create a user
        user = self.auth_manager.create_user(
            user_id="jwt_test_user",
            username="jwttest",
            email="jwt@example.com",
            password_hash="hash",
            roles=[Role.ADMIN],
        )

        # Generate token
        token = self.auth_manager.token_manager.create_token({
            "user_id": user.user_id,
            "username": user.username,
            "roles": [role.value for role in user.roles],
            "permissions": [perm.value for perm in user.permissions],
        })

        # Validate token
        payload = self.auth_manager.token_manager.validate_token(token)
        assert payload is not None
        assert payload["user_id"] == user.user_id
        assert payload["username"] == user.username
        assert Role.ADMIN.value in payload["roles"]

    def test_audit_logging_functionality(self):
        """Test audit logging functionality"""
        initial_count = len(self.auth_manager.get_audit_logs())

        # Perform some actions that should be logged
        user = self.auth_manager.create_user(
            user_id="audit_test_user",
            username="audittest",
            email="audit@example.com",
            password_hash="hash",
        )

        # Check that user creation was logged
        logs = self.auth_manager.get_audit_logs()
        assert len(logs) > initial_count

        # Check for user creation log
        creation_logs = [log for log in logs if log.action == "user_created"]
        assert len(creation_logs) > 0

        # Check log details
        log = creation_logs[-1]  # Get the most recent one
        assert log.user_id == "audit_test_user"
        assert log.success is True

    def test_token_expiration_handling(self):
        """Test that expired tokens are properly rejected"""
        user = self.auth_manager.create_user(
            user_id="expire_test_user",
            username="expiretest",
            email="expire@example.com",
            password_hash="hash",
        )

        # Create short-lived token (1 second)
        token = self.auth_manager.token_manager.create_token({
            "user_id": user.user_id,
            "username": user.username,
        }, expires_in=1)

        # Token should work initially
        authenticated_user = self.auth_manager.authenticate_token(token)
        assert authenticated_user is not None

        # Wait for expiration
        import time
        time.sleep(2)

        # Token should now be expired
        authenticated_user = self.auth_manager.authenticate_token(token)
        assert authenticated_user is None

    def test_role_based_permissions_edge_cases(self):
        """Test edge cases in role-based permissions"""
        # Test user with no roles
        no_role_user = self.auth_manager.create_user(
            user_id="no_role_user",
            username="norole",
            email="norole@example.com",
            password_hash="hash",
            roles=[],  # No roles
        )

        # Should have no permissions
        assert not no_role_user.has_permission(Permission.READ_EVENTS)
        assert not no_role_user.has_permission(Permission.WRITE_EVENTS)
        assert not no_role_user.has_permission(Permission.ADMIN)

        # Test multiple roles
        multi_role_user = self.auth_manager.create_user(
            user_id="multi_role_user",
            username="multirole",
            email="multirole@example.com",
            password_hash="hash",
            roles=[Role.VIEWER, Role.ANALYST],  # Multiple roles
        )

        # Should have combined permissions
        assert multi_role_user.has_permission(Permission.READ_EVENTS)
        assert multi_role_user.has_permission(Permission.WRITE_EVENTS)  # From ANALYST
        assert not multi_role_user.has_permission(Permission.ADMIN)

    def test_audit_log_to_dict_conversion(self):
        """Test audit log to_dict method"""
        from src.netsentinel.security.auth_manager import AuditLog

        audit_log = AuditLog(
            log_id="test_log_123",
            user_id="test_user_123",
            action="login_success",
            resource="auth_system",
            timestamp=1234567890.0,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            success=True,
            details={"extra": "info"}
        )

        log_dict = audit_log.to_dict()
        assert log_dict["log_id"] == "test_log_123"
        assert log_dict["user_id"] == "test_user_123"
        assert log_dict["action"] == "login_success"
        assert log_dict["success"] is True
        assert log_dict["details"]["extra"] == "info"

    def test_auth_manager_refresh_token(self):
        """Test token refresh functionality"""
        # Create user and get initial token
        user = self.auth_manager.create_user(
            user_id="refresh_test_user",
            username="refreshtest",
            email="refresh@example.com",
            password_hash="hash",
        )

        # Get initial token
        initial_token = self.auth_manager.authenticate_credentials(
            username="refreshtest",
            password_hash="hash",
        )

        # Refresh token
        refreshed_token = self.auth_manager.refresh_token(initial_token)

        # Both tokens should work (refresh doesn't invalidate old token)
        initial_user = self.auth_manager.authenticate_token(initial_token)
        refreshed_user = self.auth_manager.authenticate_token(refreshed_token)

        assert initial_user is not None
        assert refreshed_user is not None
        assert initial_user.user_id == user.user_id
        assert refreshed_user.user_id == user.user_id

        # Tokens should be different
        assert initial_token != refreshed_token

    def test_auth_manager_user_activity_tracking(self):
        """Test user activity tracking and last login updates"""
        # Create user
        user = self.auth_manager.create_user(
            user_id="activity_test_user",
            username="activitytest",
            email="activity@example.com",
            password_hash="hash",
        )

        initial_last_login = user.last_login

        # Authenticate user (should update last_login)
        token = self.auth_manager.authenticate_credentials(
            username="activitytest",
            password_hash="hash",
        )

        # Get updated user
        updated_user = self.auth_manager.get_user("activity_test_user")

        # Last login should be updated
        assert updated_user.last_login != initial_last_login
        assert updated_user.last_login is not None
