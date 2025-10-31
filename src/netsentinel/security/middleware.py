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

logger = create_logger("auth_middleware", level="INFO")

# FastAPI security scheme
security = HTTPBearer(auto_error=False)


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
