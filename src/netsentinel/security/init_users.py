#!/usr/bin/env python3
"""
Initialize default users for NetSentinel
Creates admin and analyst users for testing and development
"""

import hashlib
import argparse
from typing import List

from .auth_manager import get_auth_manager
from .user_store import Role


def create_default_users(user_storage_path: str = None) -> None:
    """
    Create default users for testing

    Args:
        user_storage_path: Path to user storage file
    """
    auth_manager = get_auth_manager(user_storage_path=user_storage_path)

    default_users = [
        {
            "user_id": "user_admin",
            "username": "admin",
            "password": "admin123",  # Hash the password
            "email": "admin@netsentinel.local",
            "roles": [Role.ADMIN],
        },
        {
            "user_id": "user_analyst",
            "username": "analyst",
            "password": "analyst123",  # Hash the password
            "email": "analyst@netsentinel.local",
            "roles": [Role.ANALYST],
        },
        {
            "user_id": "user_viewer",
            "username": "viewer",
            "password": "viewer123",  # Hash the password
            "email": "viewer@netsentinel.local",
            "roles": [Role.VIEWER],
        },
    ]

    created_count = 0
    for user_data in default_users:
        try:
            # Hash password
            password_hash = hashlib.sha256(user_data["password"].encode()).hexdigest()

            # Check if user already exists
            existing_user = auth_manager.get_user_by_username(user_data["username"])
            if existing_user:
                print(f"User {user_data['username']} already exists, skipping...")
                continue

            # Create user
            user = auth_manager.create_user(
                user_id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
                password_hash=password_hash,
                roles=user_data["roles"],
            )

            print(f"Created user: {user.username} ({user.user_id}) with roles: {[r.value for r in user.roles]}")
            created_count += 1

        except Exception as e:
            print(f"Failed to create user {user_data['username']}: {e}")

    if created_count > 0:
        print(f"\nSuccessfully created {created_count} default users")
        print("\nDefault credentials:")
        print("  admin / admin123 (Admin role - full access)")
        print("  analyst / analyst123 (Analyst role - read/write access)")
        print("  viewer / viewer123 (Viewer role - read-only access)")
        print("\n⚠️  WARNING: These are default credentials for testing only!")
        print("   Change passwords in production and never use these defaults.")
    else:
        print("No new users created (users may already exist)")


def list_users(user_storage_path: str = None) -> None:
    """
    List all users in the system

    Args:
        user_storage_path: Path to user storage file
    """
    auth_manager = get_auth_manager(user_storage_path=user_storage_path)
    users = auth_manager.get_all_users()

    if not users:
        print("No users found")
        return

    print(f"Found {len(users)} users:")
    print("-" * 80)
    print(f"{'Username':<15} {'Email':<25} {'Roles':<20} {'Status':<10} {'Last Login'}")
    print("-" * 80)

    for user in users:
        roles_str = ", ".join([r.value for r in user.roles])
        status = "Active" if user.is_active else "Inactive"
        last_login = "Never" if not user.last_login else "Recent"
        print(f"{user.username:<15} {user.email:<25} {roles_str:<20} {status:<10} {last_login}")


def delete_user(username: str, user_storage_path: str = None) -> None:
    """
    Delete a user by username

    Args:
        username: Username to delete
        user_storage_path: Path to user storage file
    """
    auth_manager = get_auth_manager(user_storage_path=user_storage_path)

    user = auth_manager.get_user_by_username(username)
    if not user:
        print(f"User {username} not found")
        return

    # Note: In a real system, you'd want confirmation before deletion
    success = auth_manager.user_store.delete_user(user.user_id)
    if success:
        print(f"Deleted user: {username}")
    else:
        print(f"Failed to delete user: {username}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="NetSentinel User Management")
    parser.add_argument(
        "--storage-path",
        help="Path to user storage file (default: data/users.json)"
    )
    parser.add_argument(
        "--create-defaults",
        action="store_true",
        help="Create default test users"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all users"
    )
    parser.add_argument(
        "--delete",
        help="Delete user by username"
    )

    args = parser.parse_args()

    if args.create_defaults:
        create_default_users(args.storage_path)
    elif args.list:
        list_users(args.storage_path)
    elif args.delete:
        delete_user(args.delete, args.storage_path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
