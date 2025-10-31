#!/usr/bin/env python3
"""
JWT Token Management for NetSentinel
Handles token creation, validation, and blacklisting
"""

import time
import jwt
import uuid
from typing import Dict, Any, Optional
import threading

from ..core.exceptions import AuthenticationError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("token_manager", level="INFO")
structured_logger = get_structured_logger("token_manager")


class TokenManager:
    """
    JWT token management with blacklisting support
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_blacklist: set[str] = set()
        self._lock = threading.RLock()

    def create_token(
        self,
        user_data: Dict[str, Any],
        expires_in: int = 3600,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create JWT access token

        Args:
            user_data: User information (user_id, username, email, roles, permissions)
            expires_in: Token expiration time in seconds
            additional_claims: Additional claims to include

        Returns:
            JWT token string
        """
        try:
            now = time.time()
            payload = {
                "user_id": user_data.get("user_id"),
                "username": user_data.get("username"),
                "email": user_data.get("email"),
                "roles": user_data.get("roles", []),
                "permissions": user_data.get("permissions", []),
                "iat": now,
                "exp": now + expires_in,
                "jti": str(uuid.uuid4()),  # JWT ID for blacklisting
            }

            if additional_claims:
                payload.update(additional_claims)

            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

            logger.info(
                f"JWT token created for user {user_data.get('username', 'unknown')} "
                f"(expires in {expires_in}s)"
            )

            return token

        except Exception as e:
            logger.error(f"Failed to create JWT token: {e}")
            raise AuthenticationError(f"Failed to create token: {e}")

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token and return payload

        Args:
            token: JWT token string

        Returns:
            Token payload if valid, None if invalid/expired/blacklisted
        """
        try:
            with self._lock:
                # Check blacklist
                if token in self.token_blacklist:
                    logger.warning("Token is blacklisted")
                    return None

                # Decode and validate token
                payload = jwt.decode(
                    token, self.secret_key, algorithms=[self.algorithm]
                )

                # Check expiration
                if payload.get("exp", 0) < time.time():
                    logger.warning("Token has expired")
                    return None

                return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return None

    def refresh_token(self, token: str, new_expires_in: int = 3600) -> Optional[str]:
        """
        Create a new token with extended expiration from existing valid token

        Args:
            token: Current valid token
            new_expires_in: New expiration time

        Returns:
            New token if refresh successful, None otherwise
        """
        try:
            payload = self.validate_token(token)
            if not payload:
                return None

            # Remove old token claims that shouldn't carry over
            refresh_payload = payload.copy()
            refresh_payload.pop("iat", None)
            refresh_payload.pop("exp", None)
            refresh_payload.pop("jti", None)

            return self.create_token(refresh_payload, new_expires_in)

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None

    def blacklist_token(self, token: str) -> None:
        """
        Add token to blacklist (for logout/revocation)

        Args:
            token: Token to blacklist
        """
        try:
            with self._lock:
                self.token_blacklist.add(token)
                logger.info(f"Token blacklisted: {token[:20]}...")

        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")

    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted

        Args:
            token: Token to check

        Returns:
            True if blacklisted
        """
        with self._lock:
            return token in self.token_blacklist

    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get token information without full validation

        Args:
            token: JWT token

        Returns:
            Token info dict or None if invalid
        """
        try:
            # Decode without verification for info only
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False}
            )
            return {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "expires_at": payload.get("exp"),
                "issued_at": payload.get("iat"),
                "is_expired": payload.get("exp", 0) < time.time(),
                "is_blacklisted": self.is_token_blacklisted(token),
            }
        except Exception:
            return None

    def cleanup_expired_blacklist(self) -> int:
        """
        Remove expired tokens from blacklist (maintenance)

        Returns:
            Number of tokens removed
        """
        try:
            with self._lock:
                # This is a basic cleanup - in production you might want more sophisticated
                # blacklist management (e.g., database-backed)
                initial_count = len(self.token_blacklist)
                # For now, just log - actual cleanup would require tracking expiration
                logger.info(f"Blacklist cleanup: {initial_count} tokens in blacklist")
                return 0  # Placeholder
        except Exception as e:
            logger.error(f"Blacklist cleanup error: {e}")
            return 0
