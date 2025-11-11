#!/usr/bin/env python3
"""
Authentication middleware for NetSentinel
Provides decorators and utilities for protecting FastAPI endpoints
"""

import functools
from typing import Optional, Dict, Any, Callable
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .auth_manager import get_auth_manager
from .user_store import User, Permission, Role
from ..monitoring.logger import create_logger
import time
from typing import Dict, Optional, List
import threading
from dataclasses import dataclass

logger = create_logger("auth_middleware", level="INFO")

# FastAPI security scheme
security = HTTPBearer(auto_error=False)


@dataclass
class Session:
    """User session information"""
    session_id: str
    user_id: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: float = None
    last_activity: float = None
    is_active: bool = True
    expires_at: Optional[float] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.last_activity is None:
            self.last_activity = time.time()


class SessionManager:
    """
    Session management for tracking user sessions
    Provides session creation, validation, and cleanup
    """

    def __init__(self, session_timeout: int = 3600 * 24 * 7):  # 7 days default
        self.sessions: Dict[str, Session] = {}
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> list of session_ids
        self.session_timeout = session_timeout
        self._lock = threading.RLock()

    def create_session(
        self,
        user_id: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Session:
        """Create a new session for user"""
        with self._lock:
            import uuid
            session_id = str(uuid.uuid4())

            session = Session(
                session_id=session_id,
                user_id=user_id,
                user_agent=user_agent,
                ip_address=ip_address,
                expires_at=time.time() + self.session_timeout
            )

            self.sessions[session_id] = session

            # Track user's sessions
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = []
            self.user_sessions[user_id].append(session_id)

            logger.info(f"Created session {session_id} for user {user_id}")
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session and session.is_active:
                # Check if session has expired
                if session.expires_at and time.time() > session.expires_at:
                    self.deactivate_session(session_id)
                    return None
                return session
            return None

    def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity time"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session and session.is_active:
                session.last_activity = time.time()
                # Extend expiration if close to expiry
                if session.expires_at and (session.expires_at - time.time()) < 3600:  # Less than 1 hour left
                    session.expires_at = time.time() + self.session_timeout
                return True
            return False

    def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a session"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.is_active = False
                logger.info(f"Deactivated session {session_id} for user {session.user_id}")
                return True
            return False

    def deactivate_user_sessions(self, user_id: str, exclude_session_id: Optional[str] = None) -> int:
        """Deactivate all sessions for a user"""
        with self._lock:
            deactivated_count = 0
            if user_id in self.user_sessions:
                session_ids = self.user_sessions[user_id].copy()
                for session_id in session_ids:
                    if session_id != exclude_session_id:
                        if self.deactivate_session(session_id):
                            deactivated_count += 1
            return deactivated_count

    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user"""
        with self._lock:
            session_ids = self.user_sessions.get(user_id, [])
            active_sessions = []
            for session_id in session_ids:
                session = self.get_session(session_id)
                if session:
                    active_sessions.append(session)
            return active_sessions

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        with self._lock:
            expired_sessions = []
            current_time = time.time()

            for session_id, session in self.sessions.items():
                if not session.is_active or (session.expires_at and current_time > session.expires_at):
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                session = self.sessions[session_id]
                if session.user_id in self.user_sessions:
                    self.user_sessions[session.user_id] = [
                        sid for sid in self.user_sessions[session.user_id] if sid != session_id
                    ]
                del self.sessions[session_id]

            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

            return len(expired_sessions)

    def get_session_stats(self) -> Dict[str, int]:
        """Get session statistics"""
        with self._lock:
            total_sessions = len(self.sessions)
            active_sessions = sum(1 for s in self.sessions.values() if s.is_active)
            expired_sessions = total_sessions - active_sessions
            unique_users = len(self.user_sessions)

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": expired_sessions,
                "unique_users": unique_users
            }


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


class RateLimiter:
    """
    Simple in-memory rate limiter for API keys
    Tracks requests per minute for each API key
    """

    def __init__(self):
        self.requests: Dict[str, list] = {}
        self._lock = threading.RLock()

    def is_allowed(self, key_id: str, limit_per_minute: int) -> bool:
        """
        Check if API key is within rate limit

        Args:
            key_id: API key identifier
            limit_per_minute: Maximum requests per minute

        Returns:
            True if request is allowed, False if rate limited
        """
        with self._lock:
            now = time.time()
            minute_ago = now - 60  # 60 seconds ago

            # Get or create request history for this key
            if key_id not in self.requests:
                self.requests[key_id] = []

            # Remove requests older than 1 minute
            self.requests[key_id] = [
                timestamp for timestamp in self.requests[key_id]
                if timestamp > minute_ago
            ]

            # Check if under limit
            if len(self.requests[key_id]) < limit_per_minute:
                # Add current request
                self.requests[key_id].append(now)
                return True

            return False

    def get_remaining_requests(self, key_id: str, limit_per_minute: int) -> int:
        """
        Get remaining requests for API key in current minute window

        Args:
            key_id: API key identifier
            limit_per_minute: Maximum requests per minute

        Returns:
            Number of remaining requests
        """
        with self._lock:
            now = time.time()
            minute_ago = now - 60

            if key_id not in self.requests:
                return limit_per_minute

            # Clean old requests
            self.requests[key_id] = [
                timestamp for timestamp in self.requests[key_id]
                if timestamp > minute_ago
            ]

            used_requests = len(self.requests[key_id])
            return max(0, limit_per_minute - used_requests)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Optional[Request] = None,
) -> Optional[User]:
    """
    FastAPI dependency to get current authenticated user

    Args:
        credentials: HTTP Bearer token credentials
        request: FastAPI request object

    Returns:
        User object if authenticated, raises HTTPException otherwise
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_manager = get_auth_manager()

    # Extract IP and user agent from request
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    # Authenticate token
    user = auth_manager.authenticate_token(
        credentials.credentials,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update session activity if session tracking is enabled
    if request:
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            session_manager = get_session_manager()
            session_manager.update_session_activity(session_id)

    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Optional[Request] = None,
) -> Optional[User]:
    """
    FastAPI dependency to get current user if authenticated (optional)

    Args:
        credentials: HTTP Bearer token credentials
        request: FastAPI request object

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    auth_manager = get_auth_manager()

    # Extract IP and user agent from request
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    # Authenticate token (no exception on failure)
    user = auth_manager.authenticate_token(
        credentials.credentials,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return user


def require_permission(permission: Permission):
    """
    Decorator factory to require specific permission

    Args:
        permission: Required permission

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (injected by FastAPI dependency)
            user = None
            for arg in args:
                if isinstance(arg, User):
                    user = arg
                    break

            # Check if user is in kwargs
            if "current_user" in kwargs:
                user = kwargs["current_user"]

            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required",
                )

            auth_manager = get_auth_manager()

            # Get request info from kwargs if available
            request = kwargs.get("request")
            ip_address = None
            user_agent = None
            if request:
                ip_address = getattr(request.client, "host", None)
                user_agent = getattr(request.headers, "get", lambda x: None)("user-agent")

            # Check permission
            if not auth_manager.authorize(
                user,
                permission,
                f"{func.__module__}.{func.__name__}",
                ip_address=ip_address,
                user_agent=user_agent,
            ):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission.value}",
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_role(role: Role):
    """
    Decorator factory to require specific role

    Args:
        role: Required role

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs
            user = None
            for arg in args:
                if isinstance(arg, User):
                    user = arg
                    break

            if "current_user" in kwargs:
                user = kwargs["current_user"]

            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required",
                )

            # Check role via permissions
            if not user.has_role(role):
                raise HTTPException(
                    status_code=403,
                    detail=f"Role required: {role.value}",
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication (any authenticated user)

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user from kwargs
        user = None
        for arg in args:
            if isinstance(arg, User):
                user = arg
                break

        if "current_user" in kwargs:
            user = kwargs["current_user"]

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
            )

        return await func(*args, **kwargs)

    return wrapper


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin role

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    return require_role(Role.ADMIN)(func)


def require_analyst(func: Callable) -> Callable:
    """
    Decorator to require analyst role or higher

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user from kwargs
        user = None
        for arg in args:
            if isinstance(arg, User):
                user = arg
                break

        if "current_user" in kwargs:
            user = kwargs["current_user"]

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
            )

        # Check if user has analyst or admin role
        if not (user.has_role(Role.ANALYST) or user.has_role(Role.ADMIN)):
            raise HTTPException(
                status_code=403,
                detail="Analyst or Admin role required",
            )

        return await func(*args, **kwargs)

    return wrapper


def require_auditor(func: Callable) -> Callable:
    """
    Decorator to require auditor role or higher

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user from kwargs
        user = None
        for arg in args:
            if isinstance(arg, User):
                user = arg
                break

        if "current_user" in kwargs:
            user = kwargs["current_user"]

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
            )

        # Check if user has auditor, analyst, or admin role
        allowed_roles = {Role.AUDITOR, Role.ANALYST, Role.ADMIN}
        if not any(user.has_role(role) for role in allowed_roles):
            raise HTTPException(
                status_code=403,
                detail="Auditor, Analyst, or Admin role required",
            )

        return await func(*args, **kwargs)

    return wrapper


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin role

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user from kwargs
        user = None
        for arg in args:
            if isinstance(arg, User):
                user = arg
                break

        if "current_user" in kwargs:
            user = kwargs["current_user"]

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
            )

        # Check if user has admin role
        if not user.has_role(Role.ADMIN):
            raise HTTPException(
                status_code=403,
                detail="Admin role required",
            )

        return await func(*args, **kwargs)

    return wrapper


class AuthMiddleware:
    """
    Authentication middleware class for custom integration
    """

    def __init__(self):
        self.auth_manager = get_auth_manager()

    def authenticate_request(self, token: str, ip_address: str = None, user_agent: str = None) -> Optional[User]:
        """
        Authenticate a request with token

        Args:
            token: JWT token
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            User object if authenticated, None otherwise
        """
        return self.auth_manager.authenticate_token(token, ip_address, user_agent)

    def authorize_user(self, user: User, permission: Permission, resource: str,
                      ip_address: str = None, user_agent: str = None) -> bool:
        """
        Authorize user for permission

        Args:
            user: User to authorize
            permission: Required permission
            resource: Resource being accessed
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            True if authorized, False otherwise
        """
        return self.auth_manager.authorize(user, permission, resource, ip_address, user_agent)

    def check_permission(self, user: User, permission: Permission) -> bool:
        """
        Check if user has permission (without logging)

        Args:
            user: User to check
            permission: Permission to check

        Returns:
            True if user has permission
        """
        return user.has_permission(permission)

    def check_role(self, user: User, role: Role) -> bool:
        """
        Check if user has role (without logging)

        Args:
            user: User to check
            role: Role to check

        Returns:
            True if user has role
        """
        return user.has_role(role)


# Global middleware instance
_auth_middleware: Optional[AuthMiddleware] = None


def get_auth_middleware() -> AuthMiddleware:
    """
    Get global auth middleware instance (singleton pattern)

    Returns:
        AuthMiddleware instance
    """
    global _auth_middleware
    if _auth_middleware is None:
        _auth_middleware = AuthMiddleware()
    return _auth_middleware


# Convenience functions for common auth checks
def is_authenticated(token: str) -> bool:
    """
    Check if token is valid (convenience function)

    Args:
        token: JWT token

    Returns:
        True if token is valid
    """
    auth_manager = get_auth_manager()
    return auth_manager.authenticate_token(token) is not None


def has_permission(token: str, permission: Permission) -> bool:
    """
    Check if token has permission (convenience function)

    Args:
        token: JWT token
        permission: Permission to check

    Returns:
        True if token is valid and has permission
    """
    auth_manager = get_auth_manager()
    user = auth_manager.authenticate_token(token)
    if not user:
        return False
    return user.has_permission(permission)


def has_role(token: str, role: Role) -> bool:
    """
    Check if token has role (convenience function)

    Args:
        token: JWT token
        role: Role to check

    Returns:
        True if token is valid and has role
    """
    auth_manager = get_auth_manager()
    user = auth_manager.authenticate_token(token)
    if not user:
        return False
    return user.has_role(role)


def authenticate_api_key(api_key: str) -> Optional[tuple]:
    """
    Authenticate API key and return (user, key_data) if valid

    Args:
        api_key: API key string

    Returns:
        Tuple of (user, key_data) if valid, None otherwise
    """
    try:
        auth_manager = get_auth_manager()

        # Find user with this API key
        all_users = auth_manager.get_all_users()

        for user in all_users:
            api_keys = user.metadata.get("api_keys", {})
            for key_id, key_data in api_keys.items():
                if key_data.get("key") == api_key:
                    # Check if key is active
                    if not key_data.get("is_active", True):
                        return None

                    # Check expiration
                    expires_at = key_data.get("expires_at")
                    if expires_at and time.time() > expires_at:
                        return None

                    return user, key_data

        return None

    except Exception as e:
        logger.error(f"API key authentication error: {e}")
        return None


def check_api_key_rate_limit(user: User, key_data: dict, request: Request) -> bool:
    """
    Check if API key request is within rate limits

    Args:
        user: User object
        key_data: API key data
        request: FastAPI request object

    Returns:
        True if allowed, False if rate limited
    """
    try:
        rate_limit = key_data.get("rate_limit")
        if not rate_limit:
            return True  # No rate limit set

        key_id = key_data.get("id")
        if not key_id:
            return True

        rate_limiter = get_rate_limiter()

        if not rate_limiter.is_allowed(key_id, rate_limit):
            logger.warning(f"Rate limit exceeded for API key {key_id}")
            return False

        return True

    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        return False  # Fail safe - allow request if rate limiting fails


def track_api_key_usage(user: User, key_data: dict, request: Request) -> None:
    """
    Track API key usage for analytics

    Args:
        user: User object
        key_data: API key data
        request: FastAPI request object
    """
    try:
        auth_manager = get_auth_manager()
        key_id = key_data.get("id")
        if not key_id:
            return

        # Update usage count and history
        updated_metadata = user.metadata.copy()
        api_keys = updated_metadata.get("api_keys", {})
        if key_id in api_keys:
            key_info = api_keys[key_id]
            key_info["usage_count"] = key_info.get("usage_count", 0) + 1
            key_info["last_used"] = time.time()

            # Add to usage history
            usage_history = key_info.get("usage_history", [])
            usage_history.append(time.time())

            # Keep only last 1000 entries to prevent memory issues
            if len(usage_history) > 1000:
                usage_history = usage_history[-1000:]

            key_info["usage_history"] = usage_history
            updated_metadata["api_keys"] = api_keys

            # Update user metadata (async operation, don't block response)
            try:
                auth_manager.user_store.update_user(user.user_id, metadata=updated_metadata)
            except Exception as update_error:
                logger.error(f"Failed to update API key usage: {update_error}")

    except Exception as e:
        logger.error(f"API key usage tracking error: {e}")


def require_api_key_permission(permission: str):
    """
    Decorator factory to require API key with specific permission

    Args:
        permission: Required permission

    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise HTTPException(
                    status_code=400,
                    detail="Request object required for API key authentication"
                )

            # Check for API key in headers
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                raise HTTPException(
                    status_code=401,
                    detail="API key required",
                    headers={"WWW-Authenticate": "X-API-Key"}
                )

            # Authenticate API key
            auth_result = authenticate_api_key(api_key)
            if not auth_result:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired API key"
                )

            user, key_data = auth_result

            # Check rate limit
            if not check_api_key_rate_limit(user, key_data, request):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )

            # Check permission
            key_permissions = key_data.get("permissions", [])
            if permission not in key_permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"API key missing required permission: {permission}"
                )

            # Track usage
            track_api_key_usage(user, key_data, request)

            # Add user and key data to kwargs
            kwargs["api_user"] = user
            kwargs["api_key_data"] = key_data

            return await func(*args, **kwargs)

        return wrapper
    return decorator
