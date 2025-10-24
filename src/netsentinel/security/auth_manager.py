#!/usr/bin/env python3
"""
Security and Authentication Manager for NetSentinel
Implements JWT validation, RBAC, and audit logging with proper error handling
Designed for maintainability and preventing code debt
"""

import asyncio
import time
import jwt
import hashlib
import hmac
from typing import Dict, List, Optional, Any, Union, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
from datetime import datetime, timedelta
import uuid

from ..core.exceptions import (
    NetSentinelException,
    ConfigurationError,
    AuthenticationError,
)
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("auth_manager", level="INFO")
structured_logger = get_structured_logger("auth_manager")


class Permission(Enum):
    """Permission enumeration"""

    READ_EVENTS = "read:events"
    WRITE_EVENTS = "write:events"
    READ_ALERTS = "read:alerts"
    WRITE_ALERTS = "write:alerts"
    READ_CONFIG = "read:config"
    WRITE_CONFIG = "write:config"
    ADMIN = "admin"
    AUDIT = "audit"


class Role(Enum):
    """Role enumeration"""

    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"
    AUDITOR = "auditor"


@dataclass
class User:
    """User information"""

    user_id: str
    username: str
    email: str
    roles: List[Role] = field(default_factory=list)
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission"""
        return permission in self.permissions

    def has_role(self, role: Role) -> bool:
        """Check if user has role"""
        return role in self.roles

    def add_permission(self, permission: Permission) -> None:
        """Add permission to user"""
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission) -> None:
        """Remove permission from user"""
        self.permissions.discard(permission)

    def add_role(self, role: Role) -> None:
        """Add role to user"""
        if role not in self.roles:
            self.roles.append(role)
            # Add role permissions
            self.permissions.update(self._get_role_permissions(role))

    def remove_role(self, role: Role) -> None:
        """Remove role from user"""
        if role in self.roles:
            self.roles.remove(role)
            # Remove role permissions
            role_permissions = self._get_role_permissions(role)
            for perm in role_permissions:
                # Only remove if not granted by other roles
                if not any(
                    self._get_role_permissions(r) for r in self.roles if r != role
                ):
                    self.permissions.discard(perm)

    def _get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get permissions for role"""
        role_permissions = {
            Role.VIEWER: {Permission.READ_EVENTS, Permission.READ_ALERTS},
            Role.ANALYST: {
                Permission.READ_EVENTS,
                Permission.WRITE_EVENTS,
                Permission.READ_ALERTS,
                Permission.WRITE_ALERTS,
            },
            Role.ADMIN: {
                Permission.READ_EVENTS,
                Permission.WRITE_EVENTS,
                Permission.READ_ALERTS,
                Permission.WRITE_ALERTS,
                Permission.READ_CONFIG,
                Permission.WRITE_CONFIG,
                Permission.ADMIN,
            },
            Role.AUDITOR: {
                Permission.READ_EVENTS,
                Permission.READ_ALERTS,
                Permission.READ_CONFIG,
                Permission.AUDIT,
            },
        }
        return role_permissions.get(role, set())


@dataclass
class AuditLog:
    """Audit log entry"""

    log_id: str
    user_id: str
    action: str
    resource: str
    timestamp: float
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

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


class JWTManager:
    """JWT token management"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_blacklist: Set[str] = set()
        self._lock = threading.RLock()

    def create_token(
        self,
        user: User,
        expires_in: int = 3600,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create JWT token"""
        try:
            now = time.time()
            payload = {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "roles": [role.value for role in user.roles],
                "permissions": [perm.value for perm in user.permissions],
                "iat": now,
                "exp": now + expires_in,
                "jti": str(uuid.uuid4()),  # JWT ID for blacklisting
            }

            if additional_claims:
                payload.update(additional_claims)

            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

            structured_logger.info(
                "JWT token created",
                {
                    "user_id": user.user_id,
                    "username": user.username,
                    "expires_in": expires_in,
                },
            )

            return token

        except Exception as e:
            logger.error(f"Failed to create JWT token: {e}")
            raise AuthenticationError(f"Failed to create token: {e}")

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token"""
        try:
            with self._lock:
                # Check blacklist
                if token in self.token_blacklist:
                    return None

                # Decode and validate token
                payload = jwt.decode(
                    token, self.secret_key, algorithms=[self.algorithm]
                )

                # Check expiration
                if payload.get("exp", 0) < time.time():
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

    def blacklist_token(self, token: str) -> None:
        """Blacklist token"""
        try:
            with self._lock:
                self.token_blacklist.add(token)
                logger.info(f"Token blacklisted: {token[:20]}...")

        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")

    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        with self._lock:
            return token in self.token_blacklist


class RBACManager:
    """Role-Based Access Control manager"""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self._lock = threading.RLock()

    def create_user(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: Optional[List[Role]] = None,
        permissions: Optional[Set[Permission]] = None,
    ) -> User:
        """Create user"""
        with self._lock:
            if user_id in self.users:
                raise ValueError(f"User {user_id} already exists")

            user = User(
                user_id=user_id,
                username=username,
                email=email,
                roles=roles or [],
                permissions=permissions or set(),
            )

            # Add role permissions
            for role in user.roles:
                user.permissions.update(self._get_role_permissions(role))

            self.users[user_id] = user

            logger.info(f"Created user: {username} ({user_id})")
            return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        with self._lock:
            return self.users.get(user_id)

    def update_user(self, user_id: str, **updates) -> bool:
        """Update user"""
        with self._lock:
            if user_id not in self.users:
                return False

            user = self.users[user_id]
            for key, value in updates.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            logger.info(f"Updated user: {user_id}")
            return True

    def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        with self._lock:
            if user_id not in self.users:
                return False

            del self.users[user_id]
            logger.info(f"Deleted user: {user_id}")
            return True

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has permission"""
        with self._lock:
            user = self.users.get(user_id)
            if not user or not user.is_active:
                return False

            return user.has_permission(permission)

    def check_role(self, user_id: str, role: Role) -> bool:
        """Check if user has role"""
        with self._lock:
            user = self.users.get(user_id)
            if not user or not user.is_active:
                return False

            return user.has_role(role)

    def _get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get permissions for role"""
        role_permissions = {
            Role.VIEWER: {Permission.READ_EVENTS, Permission.READ_ALERTS},
            Role.ANALYST: {
                Permission.READ_EVENTS,
                Permission.WRITE_EVENTS,
                Permission.READ_ALERTS,
                Permission.WRITE_ALERTS,
            },
            Role.ADMIN: {
                Permission.READ_EVENTS,
                Permission.WRITE_EVENTS,
                Permission.READ_ALERTS,
                Permission.WRITE_ALERTS,
                Permission.READ_CONFIG,
                Permission.WRITE_CONFIG,
                Permission.ADMIN,
            },
            Role.AUDITOR: {
                Permission.READ_EVENTS,
                Permission.READ_ALERTS,
                Permission.READ_CONFIG,
                Permission.AUDIT,
            },
        }
        return role_permissions.get(role, set())

    def get_all_users(self) -> List[User]:
        """Get all users"""
        with self._lock:
            return list(self.users.values())


class AuditLogger:
    """Audit logging system"""

    def __init__(self):
        self.logs: List[AuditLog] = []
        self._lock = threading.RLock()
        self._max_logs = 10000  # Prevent memory issues

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
                    self.logs = self.logs[-self._max_logs :]

            # Log to structured logger
            structured_logger.info(
                "Audit log entry",
                {
                    "log_id": log_entry.log_id,
                    "user_id": user_id,
                    "action": action,
                    "resource": resource,
                    "success": success,
                    "ip_address": ip_address,
                },
            )

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


class AuthManager:
    """Main authentication and authorization manager"""

    def __init__(self, secret_key: str):
        self.jwt_manager = JWTManager(secret_key)
        self.rbac_manager = RBACManager()
        self.audit_logger = AuditLogger()
        self._lock = threading.RLock()

    async def authenticate(
        self,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[User]:
        """Authenticate user with token"""
        try:
            # Validate token
            payload = self.jwt_manager.validate_token(token)
            if not payload:
                self.audit_logger.log_action(
                    user_id="unknown",
                    action="authentication_failed",
                    resource="auth",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "invalid_token"},
                )
                return None

            # Get user
            user_id = payload.get("user_id")
            user = self.rbac_manager.get_user(user_id)

            if not user or not user.is_active:
                self.audit_logger.log_action(
                    user_id=user_id or "unknown",
                    action="authentication_failed",
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
                action="authentication_success",
                resource="auth",
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return user

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.audit_logger.log_action(
                user_id="unknown",
                action="authentication_error",
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
        roles: Optional[List[Role]] = None,
        permissions: Optional[Set[Permission]] = None,
    ) -> User:
        """Create user"""
        user = self.rbac_manager.create_user(
            user_id, username, email, roles, permissions
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

    def create_token(
        self,
        user: User,
        expires_in: int = 3600,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create JWT token for user"""
        return self.jwt_manager.create_token(user, expires_in, additional_claims)

    def revoke_token(self, token: str) -> None:
        """Revoke token"""
        self.jwt_manager.blacklist_token(token)

        # Log token revocation
        self.audit_logger.log_action(
            user_id="system",
            action="token_revoked",
            resource="auth",
            success=True,
            details={"token": token[:20] + "..."},
        )

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
            "users": len(self.rbac_manager.get_all_users()),
            "audit_logs": self.audit_logger.get_statistics(),
            "jwt_blacklist_size": len(self.jwt_manager.token_blacklist),
        }


# Global auth manager
_auth_manager: Optional[AuthManager] = None


def get_auth_manager(secret_key: Optional[str] = None) -> AuthManager:
    """Get global auth manager"""
    global _auth_manager
    if _auth_manager is None:
        if not secret_key:
            # Generate a secure random key if none provided
            import secrets

            secret_key = secrets.token_urlsafe(32)
            logger.warning(
                "Generated random secret key. In production, use a proper secret key."
            )
        _auth_manager = AuthManager(secret_key)
    return _auth_manager
