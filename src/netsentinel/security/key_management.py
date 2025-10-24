#!/usr/bin/env python3
"""
Key Management System for NetSentinel
Implements comprehensive key management with rotation, storage, and security
Designed for maintainability and preventing code debt
"""

import asyncio
import time
import threading
import hashlib
import hmac
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import base64
import secrets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import ssl
import socket

from ..core.exceptions import NetSentinelException, ConfigurationError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("key_management", level="INFO")
structured_logger = get_structured_logger("key_management")


class KeyPurpose(Enum):
    """Key purpose enumeration"""

    ENCRYPTION = "encryption"
    SIGNING = "signing"
    AUTHENTICATION = "authentication"
    API_KEY = "api_key"
    JWT_SECRET = "jwt_secret"
    DATABASE = "database"


class KeyStatus(Enum):
    """Key status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_ROTATION = "pending_rotation"


@dataclass
class KeyMetadata:
    """Key metadata"""

    key_id: str
    purpose: KeyPurpose
    status: KeyStatus
    created_at: float
    expires_at: Optional[float] = None
    last_used: Optional[float] = None
    rotation_count: int = 0
    created_by: str = "system"
    tags: List[str] = field(default_factory=list)
    description: str = ""

    @property
    def is_expired(self) -> bool:
        """Check if key is expired"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def age_days(self) -> float:
        """Get key age in days"""
        return (time.time() - self.created_at) / (24 * 3600)


@dataclass
class KeyPolicy:
    """Key policy configuration"""

    max_key_age: int = 365  # days
    rotation_interval: int = 90  # days
    min_key_length: int = 256  # bits
    require_rotation: bool = True
    allow_export: bool = False
    require_approval: bool = False
    audit_required: bool = True


class KeyStore:
    """Secure key storage"""

    def __init__(self, storage_backend: str = "memory"):
        self.storage_backend = storage_backend
        self.keys: Dict[str, bytes] = {}
        self.metadata: Dict[str, KeyMetadata] = {}
        self._lock = threading.RLock()
        self._encryption_key: Optional[bytes] = None

    def _encrypt_key(self, key_data: bytes) -> bytes:
        """Encrypt key data for storage using AES-GCM"""
        if not self._encryption_key:
            # Generate encryption key if not exists
            self._encryption_key = secrets.token_bytes(32)

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            aesgcm = AESGCM(self._encryption_key)
            iv = secrets.token_bytes(12)  # 96-bit IV for GCM
            encrypted_data = aesgcm.encrypt(iv, key_data, None)
            return iv + encrypted_data
        except ImportError:
            # Fallback to simple XOR if cryptography not available
            encrypted = bytearray()
            for i, byte in enumerate(key_data):
                encrypted.append(
                    byte ^ self._encryption_key[i % len(self._encryption_key)]
                )
            return bytes(encrypted)

    def _decrypt_key(self, encrypted_data: bytes) -> bytes:
        """Decrypt key data from storage using AES-GCM"""
        if not self._encryption_key:
            raise ValueError("No encryption key available")

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            aesgcm = AESGCM(self._encryption_key)
            iv = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            return aesgcm.decrypt(iv, ciphertext, None)
        except ImportError:
            # Fallback to simple XOR if cryptography not available
            decrypted = bytearray()
            for i, byte in enumerate(encrypted_data):
                decrypted.append(
                    byte ^ self._encryption_key[i % len(self._encryption_key)]
                )
            return bytes(decrypted)

    def store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata) -> None:
        """Store key securely"""
        with self._lock:
            # Encrypt key data
            encrypted_key = self._encrypt_key(key_data)
            self.keys[key_id] = encrypted_key
            self.metadata[key_id] = metadata

            logger.info(f"Stored key: {key_id}")

    def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve key"""
        with self._lock:
            if key_id not in self.keys:
                return None

            # Decrypt key data
            encrypted_key = self.keys[key_id]
            return self._decrypt_key(encrypted_key)

    def delete_key(self, key_id: str) -> bool:
        """Delete key"""
        with self._lock:
            if key_id in self.keys:
                del self.keys[key_id]
                del self.metadata[key_id]
                logger.info(f"Deleted key: {key_id}")
                return True
            return False

    def get_key_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        """Get key metadata"""
        with self._lock:
            return self.metadata.get(key_id)

    def list_keys(self, purpose: Optional[KeyPurpose] = None) -> List[str]:
        """List all keys"""
        with self._lock:
            if purpose is None:
                return list(self.keys.keys())
            else:
                return [
                    key_id
                    for key_id, metadata in self.metadata.items()
                    if metadata.purpose == purpose
                ]

    def update_metadata(self, key_id: str, metadata: KeyMetadata) -> None:
        """Update key metadata"""
        with self._lock:
            if key_id in self.metadata:
                self.metadata[key_id] = metadata
                logger.info(f"Updated metadata for key: {key_id}")


class KeyGenerator:
    """Key generation utilities"""

    def __init__(self):
        self._lock = threading.RLock()

    def generate_symmetric_key(self, length: int = 256) -> bytes:
        """Generate symmetric key"""
        with self._lock:
            return secrets.token_bytes(length // 8)

    def generate_asymmetric_key_pair(self, key_size: int = 2048) -> Tuple[bytes, bytes]:
        """Generate asymmetric key pair"""
        with self._lock:
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=key_size, backend=default_backend()
            )

            public_key = private_key.public_key()

            # Serialize keys
            private_key_data = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            public_key_data = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            return private_key_data, public_key_data

    def generate_api_key(self, length: int = 32) -> str:
        """Generate API key"""
        with self._lock:
            return secrets.token_urlsafe(length)

    def generate_jwt_secret(self, length: int = 64) -> str:
        """Generate JWT secret"""
        with self._lock:
            return secrets.token_urlsafe(length)

    def derive_key_from_password(
        self, password: str, salt: bytes, length: int = 32
    ) -> bytes:
        """Derive key from password using PBKDF2"""
        with self._lock:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=length,
                salt=salt,
                iterations=100000,
                backend=default_backend(),
            )
            return kdf.derive(password.encode())


class KeyRotationManager:
    """Key rotation management"""

    def __init__(self, key_store: KeyStore, policy: KeyPolicy):
        self.key_store = key_store
        self.policy = policy
        self._lock = threading.RLock()
        self._rotation_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = {
            "total_rotations": 0,
            "successful_rotations": 0,
            "failed_rotations": 0,
            "keys_rotated": 0,
        }

    def should_rotate_key(self, key_id: str) -> bool:
        """Check if key should be rotated"""
        metadata = self.key_store.get_key_metadata(key_id)
        if not metadata:
            return False

        # Check age
        if metadata.age_days > self.policy.rotation_interval:
            return True

        # Check if rotation is required
        if self.policy.require_rotation and metadata.rotation_count == 0:
            return True

        return False

    async def rotate_key(self, key_id: str, new_key_data: bytes) -> bool:
        """Rotate key"""
        try:
            with self._lock:
                # Get current metadata
                metadata = self.key_store.get_key_metadata(key_id)
                if not metadata:
                    return False

                # Create new metadata
                new_metadata = KeyMetadata(
                    key_id=f"{key_id}_v{metadata.rotation_count + 1}",
                    purpose=metadata.purpose,
                    status=KeyStatus.ACTIVE,
                    created_at=time.time(),
                    expires_at=time.time() + (self.policy.max_key_age * 24 * 3600),
                    rotation_count=metadata.rotation_count + 1,
                    created_by=metadata.created_by,
                    tags=metadata.tags,
                    description=metadata.description,
                )

                # Store new key
                self.key_store.store_key(
                    new_metadata.key_id, new_key_data, new_metadata
                )

                # Mark old key as inactive
                metadata.status = KeyStatus.INACTIVE
                self.key_store.update_metadata(key_id, metadata)

                # Update statistics
                self.stats["total_rotations"] += 1
                self.stats["successful_rotations"] += 1
                self.stats["keys_rotated"] += 1

                logger.info(f"Rotated key: {key_id} -> {new_metadata.key_id}")
                return True

        except Exception as e:
            self.stats["failed_rotations"] += 1
            logger.error(f"Key rotation failed for {key_id}: {e}")
            return False

    async def rotate_all_eligible_keys(self) -> List[str]:
        """Rotate all eligible keys"""
        rotated_keys = []

        for key_id in self.key_store.list_keys():
            if self.should_rotate_key(key_id):
                # Generate new key
                metadata = self.key_store.get_key_metadata(key_id)
                if metadata:
                    if metadata.purpose == KeyPurpose.ENCRYPTION:
                        # Generate new encryption key
                        generator = KeyGenerator()
                        new_key_data = generator.generate_symmetric_key()
                    elif metadata.purpose == KeyPurpose.SIGNING:
                        # Generate new signing key
                        generator = KeyGenerator()
                        new_key_data, _ = generator.generate_asymmetric_key_pair()
                    else:
                        # Generate generic key
                        generator = KeyGenerator()
                        new_key_data = generator.generate_symmetric_key()

                    # Rotate key
                    if await self.rotate_key(key_id, new_key_data):
                        rotated_keys.append(key_id)

        return rotated_keys

    async def start_rotation_task(self) -> None:
        """Start automatic rotation task"""
        if self._rotation_task is None:
            self._rotation_task = asyncio.create_task(self._rotation_loop())

    async def stop_rotation_task(self) -> None:
        """Stop automatic rotation task"""
        if self._rotation_task:
            self._rotation_task.cancel()
            try:
                await self._rotation_task
            except asyncio.CancelledError:
                pass
            self._rotation_task = None

    async def _rotation_loop(self) -> None:
        """Rotation loop"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                await self.rotate_all_eligible_keys()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rotation loop error: {e}")
                await asyncio.sleep(60)

    def get_rotation_statistics(self) -> Dict[str, Any]:
        """Get rotation statistics"""
        with self._lock:
            return self.stats.copy()


class KeyManagementSystem:
    """Main key management system"""

    def __init__(self, policy: Optional[KeyPolicy] = None):
        self.policy = policy or KeyPolicy()
        self.key_store = KeyStore()
        self.key_generator = KeyGenerator()
        self.rotation_manager = KeyRotationManager(self.key_store, self.policy)
        self._lock = threading.RLock()

    def create_key(
        self,
        key_id: str,
        purpose: KeyPurpose,
        key_data: Optional[bytes] = None,
        expires_in_days: Optional[int] = None,
        created_by: str = "system",
        tags: Optional[List[str]] = None,
        description: str = "",
    ) -> KeyMetadata:
        """Create new key"""
        try:
            with self._lock:
                # Generate key if not provided
                if key_data is None:
                    if purpose == KeyPurpose.ENCRYPTION:
                        key_data = self.key_generator.generate_symmetric_key()
                    elif purpose == KeyPurpose.SIGNING:
                        key_data, _ = self.key_generator.generate_asymmetric_key_pair()
                    elif purpose == KeyPurpose.API_KEY:
                        key_data = self.key_generator.generate_api_key().encode()
                    elif purpose == KeyPurpose.JWT_SECRET:
                        key_data = self.key_generator.generate_jwt_secret().encode()
                    else:
                        key_data = self.key_generator.generate_symmetric_key()

                # Create metadata
                expires_at = None
                if expires_in_days:
                    expires_at = time.time() + (expires_in_days * 24 * 3600)

                metadata = KeyMetadata(
                    key_id=key_id,
                    purpose=purpose,
                    status=KeyStatus.ACTIVE,
                    created_at=time.time(),
                    expires_at=expires_at,
                    created_by=created_by,
                    tags=tags or [],
                    description=description,
                )

                # Store key
                self.key_store.store_key(key_id, key_data, metadata)

                logger.info(f"Created key: {key_id} for purpose: {purpose.value}")
                return metadata

        except Exception as e:
            logger.error(f"Key creation failed: {e}")
            raise

    def get_key(self, key_id: str) -> Optional[bytes]:
        """Get key data"""
        return self.key_store.retrieve_key(key_id)

    def get_key_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        """Get key metadata"""
        return self.key_store.get_key_metadata(key_id)

    def revoke_key(self, key_id: str) -> bool:
        """Revoke key"""
        try:
            metadata = self.key_store.get_key_metadata(key_id)
            if metadata:
                metadata.status = KeyStatus.REVOKED
                self.key_store.update_metadata(key_id, metadata)
                logger.info(f"Revoked key: {key_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Key revocation failed: {e}")
            return False

    def delete_key(self, key_id: str) -> bool:
        """Delete key"""
        return self.key_store.delete_key(key_id)

    def list_keys(self, purpose: Optional[KeyPurpose] = None) -> List[str]:
        """List keys"""
        return self.key_store.list_keys(purpose)

    async def rotate_key(self, key_id: str) -> bool:
        """Rotate key"""
        metadata = self.key_store.get_key_metadata(key_id)
        if not metadata:
            return False

        # Generate new key
        if metadata.purpose == KeyPurpose.ENCRYPTION:
            new_key_data = self.key_generator.generate_symmetric_key()
        elif metadata.purpose == KeyPurpose.SIGNING:
            new_key_data, _ = self.key_generator.generate_asymmetric_key_pair()
        else:
            new_key_data = self.key_generator.generate_symmetric_key()

        return await self.rotation_manager.rotate_key(key_id, new_key_data)

    async def start(self) -> None:
        """Start key management system"""
        await self.rotation_manager.start_rotation_task()
        logger.info("Started key management system")

    async def stop(self) -> None:
        """Stop key management system"""
        await self.rotation_manager.stop_rotation_task()
        logger.info("Stopped key management system")

    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        with self._lock:
            total_keys = len(self.key_store.list_keys())
            active_keys = len(
                [
                    key_id
                    for key_id in self.key_store.list_keys()
                    if self.key_store.get_key_metadata(key_id)
                    and self.key_store.get_key_metadata(key_id).status
                    == KeyStatus.ACTIVE
                ]
            )

            return {
                "policy": {
                    "max_key_age": self.policy.max_key_age,
                    "rotation_interval": self.policy.rotation_interval,
                    "require_rotation": self.policy.require_rotation,
                },
                "keys": {
                    "total": total_keys,
                    "active": active_keys,
                    "inactive": total_keys - active_keys,
                },
                "rotation": self.rotation_manager.get_rotation_statistics(),
            }


# Global key management system
_key_management_system: Optional[KeyManagementSystem] = None


def get_key_management_system() -> KeyManagementSystem:
    """Get global key management system"""
    global _key_management_system
    if _key_management_system is None:
        _key_management_system = KeyManagementSystem()
    return _key_management_system
