#!/usr/bin/env python3
"""
Unit tests for TokenManager
"""

import pytest
import time
from unittest.mock import patch

from src.netsentinel.security.token_manager import TokenManager
from src.netsentinel.security.user_store import Role


class TestTokenManager:
    """Test cases for TokenManager"""

    def setup_method(self):
        """Setup test fixtures"""
        self.secret_key = "test_secret_key_12345"
        self.manager = TokenManager(self.secret_key)

    def test_create_token(self):
        """Test token creation"""
        user_data = {
            "user_id": "user123",
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["admin"],
            "permissions": ["read:events", "write:events"],
        }

        token = self.manager.create_token(user_data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token contains expected claims
        payload = self.manager.validate_token(token)
        assert payload is not None
        assert payload["user_id"] == "user123"
        assert payload["username"] == "testuser"
        assert payload["email"] == "test@example.com"
        assert payload["roles"] == ["admin"]
        assert payload["permissions"] == ["read:events", "write:events"]

    def test_validate_token(self):
        """Test token validation"""
        user_data = {
            "user_id": "user123",
            "username": "testuser",
        }

        token = self.manager.create_token(user_data)
        payload = self.manager.validate_token(token)

        assert payload is not None
        assert payload["user_id"] == "user123"
        assert payload["username"] == "testuser"

    def test_validate_expired_token(self):
        """Test validation of expired token"""
        user_data = {"user_id": "user123"}

        # Create token that expires in 1 second
        token = self.manager.create_token(user_data, expires_in=1)

        # Token should be valid initially
        assert self.manager.validate_token(token) is not None

        # Wait for expiration
        time.sleep(2)

        # Token should now be invalid
        assert self.manager.validate_token(token) is None

    def test_validate_blacklisted_token(self):
        """Test validation of blacklisted token"""
        user_data = {"user_id": "user123"}

        token = self.manager.create_token(user_data)
        assert self.manager.validate_token(token) is not None

        # Blacklist the token
        self.manager.blacklist_token(token)

        # Token should now be invalid
        assert self.manager.validate_token(token) is None
        assert self.manager.is_token_blacklisted(token)

    def test_refresh_token(self):
        """Test token refresh"""
        user_data = {"user_id": "user123", "username": "testuser"}

        original_token = self.manager.create_token(user_data, expires_in=300)
        original_payload = self.manager.validate_token(original_token)

        # Refresh the token
        new_token = self.manager.refresh_token(original_token)

        assert new_token is not None
        assert new_token != original_token

        # New token should be valid
        new_payload = self.manager.validate_token(new_token)
        assert new_payload is not None
        assert new_payload["user_id"] == "user123"
        assert new_payload["username"] == "testuser"

    def test_refresh_invalid_token(self):
        """Test refresh of invalid token"""
        result = self.manager.refresh_token("invalid_token")
        assert result is None

    def test_refresh_expired_token(self):
        """Test refresh of expired token"""
        user_data = {"user_id": "user123"}

        # Create token that expires immediately
        expired_token = self.manager.create_token(user_data, expires_in=1)
        time.sleep(2)

        # Should not be able to refresh expired token
        result = self.manager.refresh_token(expired_token)
        assert result is None

    def test_get_token_info(self):
        """Test getting token information"""
        user_data = {"user_id": "user123"}

        token = self.manager.create_token(user_data, expires_in=300)
        info = self.manager.get_token_info(token)

        assert info is not None
        assert info["user_id"] == "user123"
        assert info["is_expired"] is False
        assert info["is_blacklisted"] is False

    def test_get_token_info_invalid(self):
        """Test getting info for invalid token"""
        info = self.manager.get_token_info("invalid_token")
        assert info is None

    def test_blacklist_operations(self):
        """Test blacklist operations"""
        token1 = "token1"
        token2 = "token2"

        # Initially not blacklisted
        assert not self.manager.is_token_blacklisted(token1)
        assert not self.manager.is_token_blacklisted(token2)

        # Blacklist token1
        self.manager.blacklist_token(token1)
        assert self.manager.is_token_blacklisted(token1)
        assert not self.manager.is_token_blacklisted(token2)

        # Blacklist token2
        self.manager.blacklist_token(token2)
        assert self.manager.is_token_blacklisted(token1)
        assert self.manager.is_token_blacklisted(token2)

    def test_different_secrets(self):
        """Test that different secrets produce different tokens"""
        manager1 = TokenManager("secret1")
        manager2 = TokenManager("secret2")

        user_data = {"user_id": "user123"}

        token1 = manager1.create_token(user_data)
        token2 = manager2.create_token(user_data)

        # Tokens should be different
        assert token1 != token2

        # Each manager can only validate its own tokens
        assert manager1.validate_token(token1) is not None
        assert manager1.validate_token(token2) is None
        assert manager2.validate_token(token1) is None
        assert manager2.validate_token(token2) is not None
