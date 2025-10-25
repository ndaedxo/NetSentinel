#!/usr/bin/env python3
"""
Firewall Manager for Automated IP Blocking
Integrates with iptables, ufw, and firewalld for automated threat response
"""

import subprocess
import time
import os
import re
import platform
import threading
from typing import Dict, List, Optional, Tuple, Any

# Import new core components
try:
    from .core.base import BaseComponent
    from .core.models import ValidationResult
    from .utils.centralized import (
        handle_errors_simple as handle_errors,
        create_error_context_simple as create_error_context,
        create_logger,
    )
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from core.models import ValidationResult
    from utils.centralized import (
        handle_errors_simple as handle_errors,
        create_error_context_simple as create_error_context,
        create_logger,
    )

# Create logger instance
logger = create_logger("firewall_manager", level="INFO")


class FirewallManager(BaseComponent):
    """
    Manages firewall rules for automated IP blocking in response to threats
    Supports iptables, ufw, and firewalld backends
    """

    def __init__(
        self,
        name: str = "firewall_manager",
        backend: str = "auto",
        block_duration: int = 3600,
        max_blocks: int = 1000,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize firewall manager

        Args:
            name: Component name
            backend: Firewall backend ('iptables', 'ufw', 'firewalld', 'auto')
            block_duration: Duration to block IPs in seconds (default: 1 hour)
            max_blocks: Maximum number of blocked IPs to maintain
            config: Additional configuration
        """
        super().__init__(name, config, logger)

        self.backend = backend if backend != "auto" else self._detect_backend()
        self.block_duration = block_duration
        self.max_blocks = max_blocks
        self.blocked_ips = {}  # ip -> block_time mapping
        self.chain_name = "NETSENTINEL_BLOCK"
        self._ip_lock = threading.RLock()  # Thread-safe access to blocked_ips
        self._cleanup_lock = threading.RLock()  # Separate lock for cleanup operations

        if self.backend:
            logger.info(f"Initialized firewall manager with {self.backend} backend")
            # Initialize firewall backend
            self._setup_firewall()
        else:
            logger.warning("No firewall backend available - firewall blocking disabled")
            self.backend = "none"

    def _detect_backend(self) -> Optional[str]:
        """Auto-detect available firewall backend"""
        # Check if we're on Windows - no native firewall backends available
        if platform.system() == "Windows":
            logger.warning("Windows detected - no native firewall backends available")
            return None

        backends = ["ufw", "firewalld", "iptables"]

        for backend in backends:
            try:
                result = subprocess.run(
                    [backend, "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Detected firewall backend: {backend}")
                    return backend
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ):
                continue

        logger.warning("No firewall backend detected")
        return None

    def _setup_firewall(self):
        """Setup firewall chain and rules"""
        try:
            if self.backend == "none":
                logger.info("Firewall backend disabled - no setup required")
                return
            elif self.backend == "iptables":
                self._setup_iptables()
            elif self.backend == "ufw":
                self._setup_ufw()
            elif self.backend == "firewalld":
                self._setup_firewalld()
            else:
                raise ValueError(f"Unsupported firewall backend: {self.backend}")

            logger.info(f"Firewall setup completed for {self.backend}")

        except Exception as e:
            logger.error(f"Failed to setup firewall: {e}")
            raise

    def _setup_iptables(self):
        """Setup iptables chain for NetSentinel blocking"""
        try:
            # Create custom chain if it doesn't exist
            result = subprocess.run(
                ["iptables", "-L", self.chain_name], capture_output=True, text=True
            )
            if result.returncode != 0:
                # Chain doesn't exist, create it
                subprocess.run(["iptables", "-N", self.chain_name], check=True)

            # Add jump rule to INPUT chain if not exists
            result = subprocess.run(
                ["iptables", "-C", "INPUT", "-j", self.chain_name], capture_output=True
            )
            if result.returncode != 0:
                # Rule doesn't exist, add it
                subprocess.run(
                    ["iptables", "-I", "INPUT", "1", "-j", self.chain_name], check=True
                )

            logger.info("iptables chain setup completed")

        except subprocess.CalledProcessError as e:
            logger.error(f"iptables setup failed: {e}")
            raise

    def _setup_ufw(self):
        """Setup UFW integration"""
        # UFW uses iptables underneath, we'll manage rules directly
        self._setup_iptables()

    def _setup_firewalld(self):
        """Setup firewalld integration"""
        try:
            # Create custom zone for NetSentinel
            subprocess.run(
                ["firewall-cmd", "--permanent", "--new-zone=netsentinel"],
                check=True,
                capture_output=True,
            )
            subprocess.run(["firewall-cmd", "--reload"], check=True)

            logger.info("firewalld zone setup completed")

        except subprocess.CalledProcessError as e:
            logger.error(f"firewalld setup failed: {e}")
            raise

    def block_ip(self, ip_address: str, reason: str = "threat_detection") -> bool:
        """
        Block an IP address

        Args:
            ip_address: IP address to block
            reason: Reason for blocking

        Returns:
            bool: True if successfully blocked, False otherwise
        """
        try:
            with self._ip_lock:
                # Clean up expired blocks first
                self._cleanup_expired_blocks()

                # Check if IP is already blocked
                if ip_address in self.blocked_ips:
                    logger.info(f"IP {ip_address} already blocked")
                    return True

                # Check if we've reached max blocks
                if len(self.blocked_ips) >= self.max_blocks:
                    logger.warning(
                        f"Maximum blocks ({self.max_blocks}) reached, cannot block {ip_address}"
                    )
                    return False

                # Block the IP
                if self.backend == "none":
                    logger.info(
                        f"Firewall backend disabled - simulating block for IP: {ip_address}"
                    )
                elif self.backend == "iptables" or self.backend == "ufw":
                    self._block_iptables(ip_address)
                elif self.backend == "firewalld":
                    self._block_firewalld(ip_address)

                # Record the block
                self.blocked_ips[ip_address] = {
                    "block_time": time.time(),
                    "reason": reason,
                    "backend": self.backend,
                }

                logger.info(f"Successfully blocked IP: {ip_address} (reason: {reason})")
                return True

        except Exception as e:
            logger.error(f"Failed to block IP {ip_address}: {e}")
            return False

    def _block_iptables(self, ip_address: str):
        """Block IP using iptables"""
        # Add drop rule to our custom chain
        subprocess.run(
            ["iptables", "-I", self.chain_name, "1", "-s", ip_address, "-j", "DROP"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _block_firewalld(self, ip_address: str):
        """Block IP using firewalld"""
        subprocess.run(
            ["firewall-cmd", "--zone=netsentinel", "--add-source", ip_address],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Set the zone to drop all traffic
        subprocess.run(
            ["firewall-cmd", "--zone=netsentinel", "--set-target=DROP"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def unblock_ip(self, ip_address: str) -> bool:
        """
        Unblock an IP address

        Args:
            ip_address: IP address to unblock

        Returns:
            bool: True if successfully unblocked, False otherwise
        """
        try:
            if ip_address not in self.blocked_ips:
                logger.warning(f"IP {ip_address} is not blocked")
                return False

            # Remove the block
            if self.backend == "iptables" or self.backend == "ufw":
                self._unblock_iptables(ip_address)
            elif self.backend == "firewalld":
                self._unblock_firewalld(ip_address)

            # Remove from our tracking
            del self.blocked_ips[ip_address]

            logger.info(f"Successfully unblocked IP: {ip_address}")
            return True

        except Exception as e:
            logger.error(f"Failed to unblock IP {ip_address}: {e}")
            return False

    def _unblock_iptables(self, ip_address: str):
        """Unblock IP using iptables"""
        # Remove drop rule from our custom chain
        subprocess.run(
            ["iptables", "-D", self.chain_name, "-s", ip_address, "-j", "DROP"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _unblock_firewalld(self, ip_address: str):
        """Unblock IP using firewalld"""
        subprocess.run(
            ["firewall-cmd", "--zone=netsentinel", "--remove-source", ip_address],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _cleanup_expired_blocks(self):
        """Remove expired IP blocks"""
        with self._cleanup_lock:
            current_time = time.time()
            expired_ips = []

            # Create a copy to avoid modifying dict during iteration
            with self._ip_lock:
                blocked_ips_copy = dict(self.blocked_ips)

            for ip, block_info in blocked_ips_copy.items():
                if current_time - block_info["block_time"] > self.block_duration:
                    expired_ips.append(ip)

            for ip in expired_ips:
                try:
                    self.unblock_ip(ip)
                    logger.info(f"Auto-unblocked expired IP: {ip}")
                except Exception as e:
                    logger.error(f"Failed to auto-unblock expired IP {ip}: {e}")

    def get_blocked_ips(self) -> Dict[str, Dict]:
        """
        Get list of currently blocked IPs

        Returns:
            Dict mapping IP addresses to block information
        """
        self._cleanup_expired_blocks()
        return self.blocked_ips.copy()

    def is_ip_blocked(self, ip_address: str) -> bool:
        """
        Check if an IP address is currently blocked

        Args:
            ip_address: IP address to check

        Returns:
            bool: True if blocked, False otherwise
        """
        self._cleanup_expired_blocks()
        return ip_address in self.blocked_ips

    def get_firewall_status(self) -> Dict:
        """
        Get firewall status and statistics

        Returns:
            Dict with firewall status information
        """
        return {
            "backend": self.backend,
            "blocked_ips_count": len(self.blocked_ips),
            "max_blocks": self.max_blocks,
            "block_duration_seconds": self.block_duration,
            "blocked_ips": list(self.blocked_ips.keys()),
        }

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize firewall manager resources"""
        # Already done in __init__
        pass

    async def _start_internal(self):
        """Start firewall manager internal operations"""
        # Firewall manager is ready to use after initialization
        pass

    async def _stop_internal(self):
        """Stop firewall manager internal operations"""
        # Cleanup will be handled in _cleanup
        pass

    async def _cleanup(self):
        """Cleanup firewall manager resources"""
        # Remove all blocked IPs on shutdown
        try:
            blocked_ips_copy = list(self.blocked_ips.keys())
            for ip in blocked_ips_copy:
                try:
                    self.unblock_ip(ip)
                except Exception as e:
                    logger.error(f"Error unblocking IP {ip} during cleanup: {e}")
        except Exception as e:
            logger.error(f"Error during firewall cleanup: {e}")


# Global firewall manager instance
firewall_manager = None


def get_firewall_manager() -> FirewallManager:
    """Get or create global firewall manager instance"""
    global firewall_manager
    if firewall_manager is None:
        firewall_manager = FirewallManager()
    return firewall_manager


def block_threat_ip(
    ip_address: str, threat_score: float, reason: str = "high_threat_score"
) -> bool:
    """
    Convenience function to block IPs based on threat score

    Args:
        ip_address: IP to block
        threat_score: Threat score (0-10 scale)
        reason: Reason for blocking

    Returns:
        bool: True if blocked, False otherwise
    """
    # Only block if threat score is high enough (configurable threshold)
    block_threshold = float(os.getenv("FIREWALL_BLOCK_THRESHOLD", "7.0"))

    if threat_score >= block_threshold:
        manager = get_firewall_manager()
        return manager.block_ip(ip_address, f"{reason}_score_{threat_score}")
    else:
        logger.debug(
            f"Threat score {threat_score} below block threshold {block_threshold} for IP {ip_address}"
        )
        return False
