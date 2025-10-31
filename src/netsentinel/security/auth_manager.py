#!/usr/bin/env python3
"""
Authentication Manager for NetSentinel
Orchestrates authentication, authorization, and audit logging
"""

import time
from typing import Dict, List, Optional, Any
import threading
import uuid

from .token_manager import TokenManager
from .user_store import UserStore, User, Role, Permission
from ..core.exceptions import AuthenticationError
from ..core.interfaces import IAuthProvider
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("auth_manager", level="INFO")
structured_logger = get_structured_logger("auth_manager")


class AuditLog:
    """Audit log entry"""

    def __init__(
        self,
        log_id: str,
        user_id: str,
        action: str,
        resource: str,
        timestamp: float,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.log_id = log_id
        self.user_id = user_id
        self.action = action
        self.resource = resource
        self.timestamp = timestamp
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.success = success
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "log_id": self.log_id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "timestamp": self.timestamp,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "details": self.details,
        }


class AuditLogger:
    """Audit logging system"""

    def __init__(self, max_logs: int = 10000):
        self.logs: List[AuditLog] = []
        self._lock = threading.RLock()
        self._max_logs = max_logs

    def log_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log user action"""
        try:
            log_entry = AuditLog(
                log_id=str(uuid.uuid4()),
                user_id=user_id,
                action=action,
                resource=resource,
                timestamp=time.time(),
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                details=details or {},
            )

            with self._lock:
                self.logs.append(log_entry)

                # Prevent memory issues
                if len(self.logs) > self._max_logs:
                    self.logs = self.logs[-self._max_logs:]

            # Log to structured logger (safely handle data types)
            try:
                log_data = {
                    "log_id": str(log_entry.log_id),
                    "user_id": str(user_id),
                    "action": str(action),
                    "resource": str(resource),
                    "success": bool(success),
                    "ip_address": str(ip_address) if ip_address else None,
                    "timestamp": log_entry.timestamp,
                }
                structured_logger.info("Audit log entry", log_data)
            except Exception as log_error:
                # If structured logging fails, continue with regular logging
                logger.warning(f"Structured logging failed: {log_error}")
                logger.info(f"Audit: {user_id} {action} {resource} success={success}")

        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")

    def get_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs with filters"""
        with self._lock:
            filtered_logs = self.logs

            if user_id:
                filtered_logs = [log for log in filtered_logs if log.user_id == user_id]

            if action:
                filtered_logs = [log for log in filtered_logs if log.action == action]

            if resource:
                filtered_logs = [
                    log for log in filtered_logs if log.resource == resource
                ]

            if start_time:
                filtered_logs = [
                    log for log in filtered_logs if log.timestamp >= start_time
                ]

            if end_time:
                filtered_logs = [
                    log for log in filtered_logs if log.timestamp <= end_time
                ]

            return filtered_logs[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics"""
        with self._lock:
            total_logs = len(self.logs)
            successful_logs = sum(1 for log in self.logs if log.success)
            failed_logs = total_logs - successful_logs

            # Count by action
            action_counts = {}
            for log in self.logs:
                action_counts[log.action] = action_counts.get(log.action, 0) + 1

            return {
                "total_logs": total_logs,
                "successful_logs": successful_logs,
                "failed_logs": failed_logs,
                "success_rate": successful_logs / max(1, total_logs),
                "action_counts": action_counts,
            }


class AuthManager(IAuthProvider):
    """
    Main authentication and authorization manager
    Implements IAuthProvider interface and orchestrates token management, user store, and audit logging
    """

    def __init__(
        self,
        secret_key: str,
        user_storage_path: Optional[str] = None
    ):
        self.token_manager = TokenManager(secret_key)
        self.user_store = UserStore(user_storage_path)
        self.audit_logger = AuditLogger()
        self._lock = threading.RLock()

    def authenticate_credentials(
        self,
        username: str,
        password_hash: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Authenticate user with username and password hash

        Returns:
            JWT token if authentication successful, None otherwise
        """
        try:
            # Authenticate user
            user = self.user_store.authenticate_user(username, password_hash)
            if not user:
                self.audit_logger.log_action(
                    user_id="unknown",
                    action="login_failed",
                    resource="auth",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"username": username, "reason": "invalid_credentials"},
                )
                return None

            # Create token
            user_data = {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "roles": [role.value for role in user.roles],
                "permissions": [perm.value for perm in user.permissions],
            }

            token = self.token_manager.create_token(user_data)

            # Log successful login
            self.audit_logger.log_action(
                user_id=user.user_id,
                action="login_success",
                resource="auth",
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"username": username},
            )

            return token

        except Exception as e:
            logger.error(f"Credential authentication error: {e}")
            self.audit_logger.log_action(
                user_id="unknown",
                action="login_error",
                resource="auth",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"username": username, "error": str(e)},
            )
            return None

    def authenticate_token(
        self,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[User]:
        """
        Authenticate user with JWT token

        Returns:
            User object if token valid, None otherwise
        """
        try:
            # Validate token
            payload = self.token_manager.validate_token(token)
            if not payload:
                self.audit_logger.log_action(
                    user_id="unknown",
                    action="token_auth_failed",
                    resource="auth",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "invalid_token"},
                )
                return None

            # Get user
            user_id = payload.get("user_id")
            user = self.user_store.get_user(user_id)

            if not user or not user.is_active:
                self.audit_logger.log_action(
                    user_id=user_id or "unknown",
                    action="token_auth_failed",
                    resource="auth",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "user_not_found_or_inactive"},
                )
                return None

            # Update last login
            user.last_login = time.time()

            # Log successful authentication
            self.audit_logger.log_action(
                user_id=user_id,
                action="token_auth_success",
                resource="auth",
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return user

        except Exception as e:
            logger.error(f"Token authentication error: {e}")
            self.audit_logger.log_action(
                user_id="unknown",
                action="token_auth_error",
                resource="auth",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"error": str(e)},
            )
            return None

    def authorize(
        self,
        user: User,
        permission: Permission,
        resource: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Authorize user action"""
        try:
            has_permission = user.has_permission(permission)

            # Log authorization attempt
            self.audit_logger.log_action(
                user_id=user.user_id,
                action="authorization_check",
                resource=resource,
                success=has_permission,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"permission": permission.value},
            )

            return has_permission

        except Exception as e:
            logger.error(f"Authorization error: {e}")
            return False

    def create_user(
        self,
        user_id: str,
        username: str,
        email: str,
        password_hash: str,
        roles: Optional[List[Role]] = None,
        permissions: Optional[List[Permission]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> User:
        """Create user"""
        user = self.user_store.create_user(
            user_id, username, email, password_hash, roles, set(permissions or []), metadata
        )

        # Log user creation
        self.audit_logger.log_action(
            user_id=user_id,
            action="user_created",
            resource="user_management",
            success=True,
            details={"username": username, "email": email},
        )

        return user

    def refresh_token(self, token: str) -> Optional[str]:
        """Refresh JWT token"""
        return self.token_manager.refresh_token(token)

    def revoke_token(self, token: str) -> None:
        """Revoke token"""
        self.token_manager.blacklist_token(token)

        # Log token revocation
        self.audit_logger.log_action(
            user_id="system",
            action="token_revoked",
            resource="auth",
            success=True,
            details={"token": token[:20] + "..."},
        )

    def logout(
        self,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Logout user by revoking token"""
        try:
            # Get user from token before revoking
            payload = self.token_manager.validate_token(token)
            user_id = payload.get("user_id") if payload else "unknown"

            # Revoke token
            self.revoke_token(token)

            # Log logout
            self.audit_logger.log_action(
                user_id=user_id,
                action="logout",
                resource="auth",
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        except Exception as e:
            logger.error(f"Logout error: {e}")

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.user_store.get_user(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.user_store.get_user_by_username(username)

    def get_all_users(self) -> List[User]:
        """Get all users"""
        return self.user_store.get_all_users()

    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs"""
        return self.audit_logger.get_logs(
            user_id, action, resource, start_time, end_time, limit
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        return {
            "users": self.user_store.get_statistics(),
            "audit_logs": self.audit_logger.get_statistics(),
            "tokens": {
                "blacklist_size": len(self.token_manager.token_blacklist),
            },
        }

    # IAuthProvider interface implementation
    async def authenticate(self, credentials: Dict[str, str]) -> Optional[str]:
        """
        Authenticate user with credentials (IAuthProvider interface)

        Args:
            credentials: Dict containing username and password

        Returns:
            JWT token if authentication successful, None otherwise
        """
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            return None

        # Hash password for comparison
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        return self.authenticate_credentials(username, password_hash)

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token (IAuthProvider interface)

        Args:
            token: JWT token to validate

        Returns:
            Token payload if valid, None otherwise
        """
        payload = self.token_manager.validate_token(token)
        if payload:
            return payload
        return None


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager(secret_key: Optional[str] = None, user_storage_path: Optional[str] = None) -> AuthManager:
    """
    Get global auth manager instance (singleton pattern)

    Args:
        secret_key: JWT secret key (generated if not provided)
        user_storage_path: Path for user storage file

    Returns:
        AuthManager instance
    """
    global _auth_manager
    if _auth_manager is None:
        if not secret_key:
            # Generate a secure random key if none provided
            import secrets

            secret_key = secrets.token_urlsafe(32)
            logger.warning(
                "Generated random secret key. In production, use a proper secret key."
            )
        _auth_manager = AuthManager(secret_key, user_storage_path)
    return _auth_manager
