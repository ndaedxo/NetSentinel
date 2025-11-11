#!/usr/bin/env python3
"""
User Management and Role-Based Access Control for NetSentinel
Handles user storage, roles, permissions, and access control
"""

import time
import json
import re
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import threading
import os

from ..core.exceptions import NetSentinelException, AuthenticationError
from ..monitoring.logger import create_logger
from typing import Dict, List, Any

logger = create_logger("user_store", level="INFO")


def sanitize_input(input_str: str, max_length: int = 255) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks

    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(input_str, str):
        raise ValueError("Input must be a string")

    # Trim whitespace
    sanitized = input_str.strip()

    # Check length
    if len(sanitized) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")

    # Remove potentially dangerous characters
    # Allow alphanumeric, spaces, hyphens, underscores, dots, and @ for emails
    sanitized = re.sub(r'[^\w\s\-_.@]', '', sanitized)

    # Prevent common XSS patterns
    xss_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
    ]

    for pattern in xss_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

    return sanitized


def validate_email(email: str) -> str:
    """
    Validate and sanitize email address

    Args:
        email: Email address to validate

    Returns:
        Validated and sanitized email

    Raises:
        ValueError: If email is invalid
    """
    sanitized = sanitize_input(email, max_length=254)  # RFC 5321 limit

    # Basic email validation regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, sanitized):
        raise ValueError("Invalid email format")

    return sanitized


def validate_username(username: str) -> str:
    """
    Validate and sanitize username

    Args:
        username: Username to validate

    Returns:
        Validated and sanitized username

    Raises:
        ValueError: If username is invalid
    """
    sanitized = sanitize_input(username, max_length=50)

    # Username requirements: 3-50 characters, alphanumeric + underscore/hyphen
    if len(sanitized) < 3:
        raise ValueError("Username must be at least 3 characters long")

    if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
        raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")

    return sanitized


class Permission(Enum):
    """Permission enumeration for access control"""

    READ_EVENTS = "read:events"
    WRITE_EVENTS = "write:events"
    READ_ALERTS = "read:alerts"
    WRITE_ALERTS = "write:alerts"
    READ_CONFIG = "read:config"
    WRITE_CONFIG = "write:config"
    ADMIN = "admin"
    AUDIT = "audit"


class Role(Enum):
    """Role enumeration for user types"""

    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"
    AUDITOR = "auditor"


@dataclass
class User:
    """User information with roles and permissions"""

    user_id: str
    username: str
    email: str
    roles: List[Role] = field(default_factory=list)
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    password_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions

    def has_role(self, role: Role) -> bool:
        """Check if user has specific role"""
        return role in self.roles

    def add_permission(self, permission: Permission) -> None:
        """Add permission to user"""
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission) -> None:
        """Remove permission from user"""
        self.permissions.discard(permission)

    def add_role(self, role: Role) -> None:
        """Add role to user and grant role permissions"""
        if role not in self.roles:
            self.roles.append(role)
            # Add role permissions
            self.permissions.update(self._get_role_permissions(role))

    def remove_role(self, role: Role) -> None:
        """Remove role from user and revoke role permissions"""
        if role in self.roles:
            self.roles.remove(role)
            # Remove role permissions if not granted by other roles
            role_permissions = self._get_role_permissions(role)
            for perm in role_permissions:
                if not any(
                    self._get_role_permissions(r) for r in self.roles if r != role
                ):
                    self.permissions.discard(perm)

    def _get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get permissions associated with a role"""
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for serialization"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": [role.value for role in self.roles],
            "permissions": [perm.value for perm in self.permissions],
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "password_hash": self.password_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create user from dictionary"""
        # Convert string values back to enums
        roles = [Role(role) for role in data.get("roles", [])]
        permissions = {Permission(perm) for perm in data.get("permissions", [])}

        user = cls(
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            roles=roles,
            permissions=permissions,
            is_active=data.get("is_active", True),
            created_at=data.get("created_at", time.time()),
            last_login=data.get("last_login"),
            password_hash=data.get("password_hash"),
            metadata=data.get("metadata", {}),
        )
        return user


class CustomRole:
    """Custom role with permissions"""

    def __init__(self, role_id: str, name: str, description: str = None, permissions: List[str] = None):
        self.id = role_id
        self.name = name
        self.description = description or ""
        self.permissions = permissions or []
        self.is_system_role = False
        self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
            "is_system_role": self.is_system_role,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomRole":
        """Create from dictionary"""
        role = cls(
            role_id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            permissions=data.get("permissions", [])
        )
        role.is_system_role = data.get("is_system_role", False)
        role.created_at = data.get("created_at", time.time())
        role.updated_at = data.get("updated_at", time.time())
        return role


class UserStore:
    """
    User storage and management with role-based access control
    Supports in-memory and file-based persistence
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.users: Dict[str, User] = {}
        self.custom_roles: Dict[str, CustomRole] = {}
        self._lock = threading.RLock()
        self.storage_path = storage_path or "data/users.json"

        # Create storage directory if it doesn't exist
        if self.storage_path:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

        # Load users from storage
        self._load_users()

        # Initialize system roles if they don't exist
        self._initialize_system_roles()

    def _initialize_system_roles(self):
        """Initialize built-in system roles"""
        system_roles = {
            "viewer": {
                "name": "Viewer",
                "description": "Read-only access to basic features",
                "permissions": ["read:events", "read:alerts"]
            },
            "analyst": {
                "name": "Analyst",
                "description": "Read and write access to analysis features",
                "permissions": ["read:events", "write:events", "read:alerts", "write:alerts"]
            },
            "admin": {
                "name": "Administrator",
                "description": "Full system access and configuration",
                "permissions": ["read:events", "write:events", "read:alerts", "write:alerts", "read:config", "write:config", "admin"]
            },
            "auditor": {
                "name": "Auditor",
                "description": "Access to audit logs and compliance features",
                "permissions": ["read:events", "read:alerts", "read:config", "audit"]
            }
        }

        for role_id, role_data in system_roles.items():
            if role_id not in self.custom_roles:
                role = CustomRole(
                    role_id=role_id,
                    name=role_data["name"],
                    description=role_data["description"],
                    permissions=role_data["permissions"]
                )
                role.is_system_role = True
                self.custom_roles[role_id] = role

        self._save_users()  # Save system roles

    def create_user(
        self,
        user_id: str,
        username: str,
        email: str,
        password_hash: str,
        roles: Optional[List[Role]] = None,
        permissions: Optional[Set[Permission]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> User:
        """
        Create a new user

        Args:
            user_id: Unique user identifier
            username: Username for login
            email: User email
            password_hash: Hashed password
            roles: User roles
            permissions: Additional permissions
            metadata: Additional user metadata

        Returns:
            Created User object

        Raises:
            ValueError: If user already exists
        """
        with self._lock:
            # Validate and sanitize inputs
            validated_username = validate_username(username)
            validated_email = validate_email(email)

            if user_id in self.users:
                raise ValueError(f"User {user_id} already exists")
            if any(u.username == validated_username for u in self.users.values()):
                raise ValueError(f"Username {validated_username} already exists")

            user = User(
                user_id=user_id,
                username=validated_username,
                email=validated_email,
                roles=roles or [],
                permissions=permissions or set(),
                password_hash=password_hash,
                metadata=metadata or {},
            )

            # Add role permissions
            for role in user.roles:
                user.permissions.update(user._get_role_permissions(role))

            self.users[user_id] = user
            self._save_users()

            logger.info(f"Created user: {username} ({user_id})")
            return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        with self._lock:
            return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with self._lock:
            for user in self.users.values():
                if user.username == username:
                    return user
            return None

    def update_user(self, user_id: str, **updates) -> bool:
        """
        Update user attributes

        Args:
            user_id: User to update
            updates: Fields to update

        Returns:
            True if user was updated, False if not found
        """
        with self._lock:
            if user_id not in self.users:
                return False

            user = self.users[user_id]
            for key, value in updates.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            self._save_users()
            logger.info(f"Updated user: {user_id}")
            return True

    def delete_user(self, user_id: str) -> bool:
        """
        Delete user

        Args:
            user_id: User to delete

        Returns:
            True if user was deleted, False if not found
        """
        with self._lock:
            if user_id not in self.users:
                return False

            del self.users[user_id]
            self._save_users()
            logger.info(f"Deleted user: {user_id}")
            return True

    def authenticate_user(self, username: str, password_hash: str) -> Optional[User]:
        """
        Authenticate user with username and password hash

        Args:
            username: Username to authenticate
            password_hash: Password hash to verify

        Returns:
            User if authentication successful, None otherwise
        """
        user = self.get_user_by_username(username)
        if not user or not user.is_active:
            return None

        if user.password_hash != password_hash:
            return None

        # Update last login
        user.last_login = time.time()
        self._save_users()

        return user

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

    def add_user_role(self, user_id: str, role: Role) -> bool:
        """Add role to user"""
        with self._lock:
            user = self.users.get(user_id)
            if not user:
                return False

            user.add_role(role)
            self._save_users()
            return True

    def remove_user_role(self, user_id: str, role: Role) -> bool:
        """Remove role from user"""
        with self._lock:
            user = self.users.get(user_id)
            if not user:
                return False

            user.remove_role(role)
            self._save_users()
            return True

    def get_all_users(self) -> List[User]:
        """Get all users"""
        with self._lock:
            return list(self.users.values())

    def get_users_by_role(self, role: Role) -> List[User]:
        """Get users with specific role"""
        with self._lock:
            return [user for user in self.users.values() if user.has_role(role)]

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        return self.update_user(user_id, is_active=False)

    def activate_user(self, user_id: str) -> bool:
        """Activate user account"""
        return self.update_user(user_id, is_active=True)

    def _load_users(self) -> None:
        """Load users from storage file"""
        if not self.storage_path or not os.path.exists(self.storage_path):
            logger.info("No user storage file found, starting with empty user store")
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            for user_data in data.get("users", []):
                user = User.from_dict(user_data)
                self.users[user.user_id] = user

            logger.info(f"Loaded {len(self.users)} users from storage")

        except Exception as e:
            logger.error(f"Failed to load users from storage: {e}")

    def _save_users(self) -> None:
        """Save users to storage file"""
        if not self.storage_path:
            return

        try:
            data = {
                "users": [user.to_dict() for user in self.users.values()],
                "last_updated": time.time(),
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save users to storage: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get user store statistics"""
        with self._lock:
            total_users = len(self.users)
            active_users = sum(1 for u in self.users.values() if u.is_active)
            role_counts = {}

            for role in Role:
                role_counts[role.value] = len(self.get_users_by_role(role))

            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "role_counts": role_counts,
            }

    # RBAC (Role-Based Access Control) methods
    def create_custom_role(self, role_id: str, name: str, description: str = None, permissions: List[str] = None) -> CustomRole:
        """Create a new custom role"""
        with self._lock:
            if role_id in self.custom_roles:
                raise ValueError(f"Role {role_id} already exists")

            role = CustomRole(role_id, name, description, permissions)
            self.custom_roles[role_id] = role
            self._save_users()
            logger.info(f"Created custom role: {name} ({role_id})")
            return role

    def get_role(self, role_id: str) -> Optional[CustomRole]:
        """Get role by ID"""
        with self._lock:
            return self.custom_roles.get(role_id)

    def update_role(self, role_id: str, name: str = None, description: str = None, permissions: List[str] = None) -> bool:
        """Update role properties"""
        with self._lock:
            if role_id not in self.custom_roles:
                return False

            role = self.custom_roles[role_id]
            if role.is_system_role:
                raise ValueError("Cannot modify system roles")

            if name is not None:
                role.name = name
            if description is not None:
                role.description = description
            if permissions is not None:
                role.permissions = permissions

            role.updated_at = time.time()
            self._save_users()
            logger.info(f"Updated role: {role_id}")
            return True

    def delete_role(self, role_id: str) -> bool:
        """Delete a custom role"""
        with self._lock:
            if role_id not in self.custom_roles:
                return False

            role = self.custom_roles[role_id]
            if role.is_system_role:
                raise ValueError("Cannot delete system roles")

            # Remove role from all users
            for user in self.users.values():
                user.roles = [r for r in user.roles if r.value != role_id]

            del self.custom_roles[role_id]
            self._save_users()
            logger.info(f"Deleted role: {role_id}")
            return True

    def get_all_roles(self) -> List[CustomRole]:
        """Get all roles (system and custom)"""
        with self._lock:
            return list(self.custom_roles.values())

    def assign_user_roles(self, user_id: str, role_ids: List[str]) -> bool:
        """Assign roles to user"""
        with self._lock:
            if user_id not in self.users:
                return False

            user = self.users[user_id]
            user.roles = []

            for role_id in role_ids:
                if role_id in self.custom_roles:
                    # Convert string role_id to Role enum if it matches system roles
                    try:
                        role_enum = Role(role_id)
                        user.roles.append(role_enum)
                    except ValueError:
                        # Custom role - add as string (will be handled differently)
                        pass

            # Update permissions based on roles
            user.permissions = set()
            for role in user.roles:
                user.permissions.update(user._get_role_permissions(role))

            self._save_users()
            logger.info(f"Assigned roles to user {user_id}: {role_ids}")
            return True

    def get_user_effective_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get user's effective permissions with role breakdown"""
        with self._lock:
            if user_id not in self.users:
                return {}

            user = self.users[user_id]

            # Get direct permissions (not role-based)
            direct_permissions = []

            # Get role-based permissions
            role_permissions = {}
            for role in user.roles:
                role_permissions[role.value] = [p.value for p in user._get_role_permissions(role)]

            # Calculate effective permissions (union of all role permissions)
            effective_permissions = list(user.permissions)

            return {
                "direct_permissions": direct_permissions,
                "role_permissions": role_permissions,
                "effective_permissions": [p.value for p in effective_permissions]
            }

    def _load_users(self) -> None:
        """Load users from storage file"""
        if not self.storage_path or not os.path.exists(self.storage_path):
            logger.info("No user storage file found, starting with empty user store")
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Load users
            for user_data in data.get("users", []):
                user = User.from_dict(user_data)
                self.users[user.user_id] = user

            # Load custom roles
            for role_data in data.get("custom_roles", []):
                role = CustomRole.from_dict(role_data)
                self.custom_roles[role.id] = role

            logger.info(f"Loaded {len(self.users)} users and {len(self.custom_roles)} roles from storage")

        except Exception as e:
            logger.error(f"Failed to load users from storage: {e}")

    def _save_users(self) -> None:
        """Save users to storage file"""
        if not self.storage_path:
            return

        try:
            data = {
                "users": [user.to_dict() for user in self.users.values()],
                "custom_roles": [role.to_dict() for role in self.custom_roles.values()],
                "last_updated": time.time(),
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save users to storage: {e}")
