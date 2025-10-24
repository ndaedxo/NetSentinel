#!/usr/bin/env python3
"""
Consolidated validation utilities for NetSentinel
Eliminates duplication and provides consistent validation across the system
"""

import re
import ipaddress
import email.utils
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation operation"""

    valid: bool
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def add_error(self, error: str):
        """Add validation error"""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str):
        """Add validation warning"""
        self.warnings.append(warning)


class ConsolidatedValidator:
    """Consolidated validator for all NetSentinel validation needs"""

    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """Validate IP address"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_domain(domain: str) -> bool:
        """Validate domain name"""
        if not domain or len(domain) > 253:
            return False

        # Basic domain validation regex
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        return bool(re.match(pattern, domain))

    @staticmethod
    def validate_email(email_addr: str) -> bool:
        """Validate email address"""
        if not email_addr or len(email_addr) > 254:
            return False

        try:
            email.utils.parseaddr(email_addr)
            return bool(email.utils.parseaddr(email_addr)[1])
        except Exception:
            return False

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL"""
        if not url or len(url) > 2048:
            return False

        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def validate_port(port: Union[int, str]) -> bool:
        """Validate port number"""
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_timeout(timeout: Union[int, float]) -> bool:
        """Validate timeout value"""
        try:
            timeout_float = float(timeout)
            return 0 < timeout_float <= 3600  # Max 1 hour
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_retry_attempts(attempts: Union[int, str]) -> bool:
        """Validate retry attempts"""
        try:
            attempts_int = int(attempts)
            return 0 <= attempts_int <= 10  # Max 10 attempts
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_hash(hash_value: str, hash_type: str = "sha256") -> bool:
        """Validate hash value"""
        if not hash_value:
            return False

        expected_lengths = {"md5": 32, "sha1": 40, "sha256": 64, "sha512": 128}

        expected_length = expected_lengths.get(hash_type.lower())
        if not expected_length:
            return False

        return len(hash_value) == expected_length and all(
            c in "0123456789abcdefABCDEF" for c in hash_value
        )

    @staticmethod
    def validate_event_data(event_data: Dict[str, Any]) -> ValidationResult:
        """Validate event data structure"""
        result = ValidationResult(valid=True)

        required_fields = ["id", "timestamp", "event_type", "source"]
        for field in required_fields:
            if field not in event_data:
                result.add_error(f"Missing required field: {field}")

        if "timestamp" in event_data:
            try:
                float(event_data["timestamp"])
            except (ValueError, TypeError):
                result.add_error("Invalid timestamp format")

        if "severity" in event_data:
            valid_severities = ["low", "medium", "high", "critical"]
            if event_data["severity"] not in valid_severities:
                result.add_warning(f"Unknown severity level: {event_data['severity']}")

        return result

    @staticmethod
    def validate_alert_data(alert_data: Dict[str, Any]) -> ValidationResult:
        """Validate alert data structure"""
        result = ValidationResult(valid=True)

        required_fields = [
            "id",
            "title",
            "description",
            "severity",
            "source",
            "timestamp",
        ]
        for field in required_fields:
            if field not in alert_data:
                result.add_error(f"Missing required field: {field}")

        if "timestamp" in alert_data:
            try:
                float(alert_data["timestamp"])
            except (ValueError, TypeError):
                result.add_error("Invalid timestamp format")

        if "severity" in alert_data:
            valid_severities = ["low", "medium", "high", "critical"]
            if alert_data["severity"] not in valid_severities:
                result.add_warning(f"Unknown severity level: {alert_data['severity']}")

        return result

    @staticmethod
    def validate_threat_indicator(indicator_data: Dict[str, Any]) -> ValidationResult:
        """Validate threat indicator data"""
        result = ValidationResult(valid=True)

        required_fields = [
            "indicator",
            "indicator_type",
            "threat_type",
            "confidence",
            "source",
        ]
        for field in required_fields:
            if field not in indicator_data:
                result.add_error(f"Missing required field: {field}")

        if "indicator_type" in indicator_data:
            valid_types = ["ip", "domain", "hash", "url", "email"]
            if indicator_data["indicator_type"] not in valid_types:
                result.add_error(
                    f"Invalid indicator type: {indicator_data['indicator_type']}"
                )

        if "confidence" in indicator_data:
            try:
                confidence = int(indicator_data["confidence"])
                if not 0 <= confidence <= 100:
                    result.add_error("Confidence must be between 0 and 100")
            except (ValueError, TypeError):
                result.add_error("Invalid confidence value")

        return result

    @staticmethod
    def validate_config_value(key: str, value: Any) -> ValidationResult:
        """Validate configuration value based on key"""
        result = ValidationResult(valid=True)

        if key.endswith(".port"):
            if not ConsolidatedValidator.validate_port(value):
                result.add_error(f"Invalid port number: {value}")
        elif key.endswith(".timeout"):
            if not ConsolidatedValidator.validate_timeout(value):
                result.add_error(f"Invalid timeout value: {value}")
        elif key.endswith(".retry_attempts"):
            if not ConsolidatedValidator.validate_retry_attempts(value):
                result.add_error(f"Invalid retry attempts: {value}")
        elif key.endswith(".host") or key.endswith(".address"):
            if not (
                ConsolidatedValidator.validate_ip_address(value)
                or ConsolidatedValidator.validate_domain(value)
            ):
                result.add_error(f"Invalid host/address: {value}")
        elif key.endswith(".email"):
            if not ConsolidatedValidator.validate_email(value):
                result.add_error(f"Invalid email address: {value}")
        elif key.endswith(".url"):
            if not ConsolidatedValidator.validate_url(value):
                result.add_error(f"Invalid URL: {value}")
        elif key.endswith(".hash"):
            if not ConsolidatedValidator.validate_hash(value):
                result.add_error(f"Invalid hash value: {value}")

        return result


# Global validator instance
validator = ConsolidatedValidator()
