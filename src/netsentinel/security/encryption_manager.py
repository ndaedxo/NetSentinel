#!/usr/bin/env python3
"""
Encryption Manager for NetSentinel
Implements comprehensive encryption for data at rest and in transit
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
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import ssl
import socket

from ..core.exceptions import NetSentinelException, ConfigurationError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("encryption_manager", level="INFO")
structured_logger = get_structured_logger("encryption_manager")


class EncryptionAlgorithm(Enum):
    """Encryption algorithm enumeration"""

    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"
    CHACHA20_POLY1305 = "chacha20_poly1305"


class KeyType(Enum):
    """Key type enumeration"""

    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    MASTER = "master"


@dataclass
class EncryptionConfig:
    """Encryption configuration"""

    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_size: int = 256
    iv_size: int = 16
    tag_size: int = 16
    key_rotation_days: int = 90
    max_key_age: int = 365  # days
    encryption_enabled: bool = True


@dataclass
class EncryptionKey:
    """Encryption key representation"""

    key_id: str
    key_type: KeyType
    algorithm: EncryptionAlgorithm
    key_data: bytes
    created_at: float
    expires_at: Optional[float] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

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


class SymmetricEncryption:
    """Symmetric encryption implementation"""

    def __init__(self, config: EncryptionConfig):
        self.config = config
        self._lock = threading.RLock()

    def generate_key(self, key_id: str) -> EncryptionKey:
        """Generate symmetric encryption key"""
        try:
            if self.config.algorithm == EncryptionAlgorithm.AES_256_GCM:
                key_data = Fernet.generate_key()
            elif self.config.algorithm == EncryptionAlgorithm.AES_256_CBC:
                key_data = secrets.token_bytes(32)  # 256 bits
            elif self.config.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
                key_data = secrets.token_bytes(32)  # 256 bits
            else:
                raise ValueError(f"Unsupported algorithm: {self.config.algorithm}")

            key = EncryptionKey(
                key_id=key_id,
                key_type=KeyType.SYMMETRIC,
                algorithm=self.config.algorithm,
                key_data=key_data,
                created_at=time.time(),
                expires_at=time.time() + (self.config.key_rotation_days * 24 * 3600),
            )

            logger.info(f"Generated symmetric key: {key_id}")
            return key

        except Exception as e:
            logger.error(f"Failed to generate symmetric key: {e}")
            raise

    def encrypt(self, data: bytes, key: EncryptionKey) -> bytes:
        """Encrypt data with symmetric key"""
        try:
            with self._lock:
                if key.is_expired:
                    raise ValueError("Key has expired")

                if self.config.algorithm == EncryptionAlgorithm.AES_256_GCM:
                    return self._encrypt_aes_gcm(data, key.key_data)
                elif self.config.algorithm == EncryptionAlgorithm.AES_256_CBC:
                    return self._encrypt_aes_cbc(data, key.key_data)
                elif self.config.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
                    return self._encrypt_chacha20_poly1305(data, key.key_data)
                else:
                    raise ValueError(f"Unsupported algorithm: {self.config.algorithm}")

        except Exception as e:
            logger.error(f"Symmetric encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: bytes, key: EncryptionKey) -> bytes:
        """Decrypt data with symmetric key"""
        try:
            with self._lock:
                if key.is_expired:
                    raise ValueError("Key has expired")

                if self.config.algorithm == EncryptionAlgorithm.AES_256_GCM:
                    return self._decrypt_aes_gcm(encrypted_data, key.key_data)
                elif self.config.algorithm == EncryptionAlgorithm.AES_256_CBC:
                    return self._decrypt_aes_cbc(encrypted_data, key.key_data)
                elif self.config.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
                    return self._decrypt_chacha20_poly1305(encrypted_data, key.key_data)
                else:
                    raise ValueError(f"Unsupported algorithm: {self.config.algorithm}")

        except Exception as e:
            logger.error(f"Symmetric decryption failed: {e}")
            raise

    def _encrypt_aes_gcm(self, data: bytes, key: bytes) -> bytes:
        """Encrypt with AES-GCM"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        aesgcm = AESGCM(key)
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM
        encrypted_data = aesgcm.encrypt(iv, data, None)
        return iv + encrypted_data

    def _decrypt_aes_gcm(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt with AES-GCM"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        aesgcm = AESGCM(key)
        iv = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return aesgcm.decrypt(iv, ciphertext, None)

    def _encrypt_aes_cbc(self, data: bytes, key: bytes) -> bytes:
        """Encrypt with AES-CBC"""
        iv = secrets.token_bytes(16)  # 128-bit IV for CBC
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Pad data to block size
        padding_length = 16 - (len(data) % 16)
        padded_data = data + bytes([padding_length] * padding_length)

        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        return iv + encrypted_data

    def _decrypt_aes_cbc(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt with AES-CBC"""
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove padding
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]

    def _encrypt_chacha20_poly1305(self, data: bytes, key: bytes) -> bytes:
        """Encrypt with ChaCha20-Poly1305"""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

        chacha = ChaCha20Poly1305(key)
        iv = secrets.token_bytes(12)  # 96-bit IV
        encrypted_data = chacha.encrypt(iv, data, None)
        return iv + encrypted_data

    def _decrypt_chacha20_poly1305(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt with ChaCha20-Poly1305"""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

        chacha = ChaCha20Poly1305(key)
        iv = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return chacha.decrypt(iv, ciphertext, None)


class AsymmetricEncryption:
    """Asymmetric encryption implementation"""

    def __init__(self, config: EncryptionConfig):
        self.config = config
        self._lock = threading.RLock()

    def generate_key_pair(self, key_id: str) -> Tuple[EncryptionKey, EncryptionKey]:
        """Generate asymmetric key pair"""
        try:
            if self.config.algorithm == EncryptionAlgorithm.RSA_2048:
                key_size = 2048
            elif self.config.algorithm == EncryptionAlgorithm.RSA_4096:
                key_size = 4096
            else:
                raise ValueError(f"Unsupported algorithm: {self.config.algorithm}")

            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=key_size, backend=default_backend()
            )

            # Get public key
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

            # Create key objects
            private_key_obj = EncryptionKey(
                key_id=f"{key_id}_private",
                key_type=KeyType.ASYMMETRIC,
                algorithm=self.config.algorithm,
                key_data=private_key_data,
                created_at=time.time(),
                expires_at=time.time() + (self.config.key_rotation_days * 24 * 3600),
            )

            public_key_obj = EncryptionKey(
                key_id=f"{key_id}_public",
                key_type=KeyType.ASYMMETRIC,
                algorithm=self.config.algorithm,
                key_data=public_key_data,
                created_at=time.time(),
                expires_at=time.time() + (self.config.key_rotation_days * 24 * 3600),
            )

            logger.info(f"Generated asymmetric key pair: {key_id}")
            return private_key_obj, public_key_obj

        except Exception as e:
            logger.error(f"Failed to generate asymmetric key pair: {e}")
            raise

    def encrypt(self, data: bytes, public_key: EncryptionKey) -> bytes:
        """Encrypt data with public key"""
        try:
            with self._lock:
                if public_key.is_expired:
                    raise ValueError("Public key has expired")

                # Load public key
                key = serialization.load_pem_public_key(
                    public_key.key_data, backend=default_backend()
                )

                # Encrypt data
                encrypted_data = key.encrypt(
                    data,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None,
                    ),
                )

                return encrypted_data

        except Exception as e:
            logger.error(f"Asymmetric encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: bytes, private_key: EncryptionKey) -> bytes:
        """Decrypt data with private key"""
        try:
            with self._lock:
                if private_key.is_expired:
                    raise ValueError("Private key has expired")

                # Load private key
                key = serialization.load_pem_private_key(
                    private_key.key_data, password=None, backend=default_backend()
                )

                # Decrypt data
                decrypted_data = key.decrypt(
                    encrypted_data,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None,
                    ),
                )

                return decrypted_data

        except Exception as e:
            logger.error(f"Asymmetric decryption failed: {e}")
            raise


class KeyManager:
    """Encryption key management"""

    def __init__(self, config: EncryptionConfig):
        self.config = config
        self.keys: Dict[str, EncryptionKey] = {}
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None

    def add_key(self, key: EncryptionKey) -> None:
        """Add encryption key"""
        with self._lock:
            self.keys[key.key_id] = key
            logger.info(f"Added encryption key: {key.key_id}")

    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Get encryption key"""
        with self._lock:
            return self.keys.get(key_id)

    def remove_key(self, key_id: str) -> bool:
        """Remove encryption key"""
        with self._lock:
            if key_id in self.keys:
                del self.keys[key_id]
                logger.info(f"Removed encryption key: {key_id}")
                return True
            return False

    def get_active_keys(self) -> List[EncryptionKey]:
        """Get active encryption keys"""
        with self._lock:
            return [
                key
                for key in self.keys.values()
                if key.is_active and not key.is_expired
            ]

    def get_expired_keys(self) -> List[EncryptionKey]:
        """Get expired encryption keys"""
        with self._lock:
            return [key for key in self.keys.values() if key.is_expired]

    def rotate_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Rotate encryption key"""
        with self._lock:
            old_key = self.keys.get(key_id)
            if not old_key:
                return None

            # Deactivate old key
            old_key.is_active = False

            # Generate new key
            if old_key.key_type == KeyType.SYMMETRIC:
                symmetric = SymmetricEncryption(self.config)
                new_key = symmetric.generate_key(f"{key_id}_rotated")
            else:
                asymmetric = AsymmetricEncryption(self.config)
                new_key, _ = asymmetric.generate_key_pair(f"{key_id}_rotated")

            # Add new key
            self.keys[new_key.key_id] = new_key

            logger.info(f"Rotated key: {key_id} -> {new_key.key_id}")
            return new_key

    async def cleanup_expired_keys(self) -> None:
        """Cleanup expired keys"""
        with self._lock:
            expired_keys = self.get_expired_keys()
            for key in expired_keys:
                del self.keys[key.key_id]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired keys")

    async def start_cleanup_task(self) -> None:
        """Start cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        """Cleanup loop"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1 hour
                await self.cleanup_expired_keys()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Key cleanup error: {e}")
                await asyncio.sleep(60)

    def get_statistics(self) -> Dict[str, Any]:
        """Get key manager statistics"""
        with self._lock:
            active_keys = len(self.get_active_keys())
            expired_keys = len(self.get_expired_keys())
            total_keys = len(self.keys)

            return {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "expired_keys": expired_keys,
                "key_types": {
                    key_type.value: len(
                        [k for k in self.keys.values() if k.key_type == key_type]
                    )
                    for key_type in KeyType
                },
            }


class EncryptionManager:
    """Main encryption manager"""

    def __init__(self, config: Optional[EncryptionConfig] = None):
        self.config = config or EncryptionConfig()
        self.symmetric = SymmetricEncryption(self.config)
        self.asymmetric = AsymmetricEncryption(self.config)
        self.key_manager = KeyManager(self.config)
        self._lock = threading.RLock()

    def encrypt_data(self, data: bytes, key_id: str) -> bytes:
        """Encrypt data"""
        if not self.config.encryption_enabled:
            return data

        key = self.key_manager.get_key(key_id)
        if not key:
            raise ValueError(f"Key not found: {key_id}")

        if key.key_type == KeyType.SYMMETRIC:
            return self.symmetric.encrypt(data, key)
        else:
            return self.asymmetric.encrypt(data, key)

    def decrypt_data(self, encrypted_data: bytes, key_id: str) -> bytes:
        """Decrypt data"""
        if not self.config.encryption_enabled:
            return encrypted_data

        key = self.key_manager.get_key(key_id)
        if not key:
            raise ValueError(f"Key not found: {key_id}")

        if key.key_type == KeyType.SYMMETRIC:
            return self.symmetric.decrypt(encrypted_data, key)
        else:
            return self.asymmetric.decrypt(encrypted_data, key)

    def generate_symmetric_key(self, key_id: str) -> EncryptionKey:
        """Generate symmetric key"""
        key = self.symmetric.generate_key(key_id)
        self.key_manager.add_key(key)
        return key

    def generate_asymmetric_key_pair(
        self, key_id: str
    ) -> Tuple[EncryptionKey, EncryptionKey]:
        """Generate asymmetric key pair"""
        private_key, public_key = self.asymmetric.generate_key_pair(key_id)
        self.key_manager.add_key(private_key)
        self.key_manager.add_key(public_key)
        return private_key, public_key

    def rotate_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Rotate encryption key"""
        return self.key_manager.rotate_key(key_id)

    async def start(self) -> None:
        """Start encryption manager"""
        await self.key_manager.start_cleanup_task()
        logger.info("Started encryption manager")

    async def stop(self) -> None:
        """Stop encryption manager"""
        await self.key_manager.stop_cleanup_task()
        logger.info("Stopped encryption manager")

    def get_statistics(self) -> Dict[str, Any]:
        """Get encryption manager statistics"""
        return {
            "config": {
                "algorithm": self.config.algorithm.value,
                "encryption_enabled": self.config.encryption_enabled,
                "key_rotation_days": self.config.key_rotation_days,
            },
            "key_manager": self.key_manager.get_statistics(),
        }


# Global encryption manager
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager
