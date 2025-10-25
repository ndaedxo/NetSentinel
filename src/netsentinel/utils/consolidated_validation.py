#!/usr/bin/env python3
"""
Consolidated validation utilities for NetSentinel
Eliminates code duplication across validation modules
"""

import re
import ipaddress
import email.utils
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import datetime, timedelta


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {"valid": self.valid, "errors": self.errors, "warnings": self.warnings}


class NetSentinelValidator:
    """Consolidated validator for all NetSentinel data types"""

    # Constants for validation
    MAX_EMAIL_LENGTH = 254
    MAX_DOMAIN_LENGTH = 253
    MAX_URL_LENGTH = 2048
    MAX_PORT = 65535
    MIN_PORT = 1
    MAX_TIMEOUT = 3600  # 1 hour
    MAX_RETRY_ATTEMPTS = 10

    # Hash length mappings
    HASH_LENGTHS = {"md5": 32, "sha1": 40, "sha256": 64, "sha512": 128}

    # Valid severity levels
    VALID_SEVERITIES = ["low", "medium", "high", "critical"]

    # Valid indicator types
    VALID_INDICATOR_TYPES = ["ip", "domain", "hash", "url", "email"]

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
        if not domain or len(domain) > NetSentinelValidator.MAX_DOMAIN_LENGTH:
            return False

        # Basic domain validation regex
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        return bool(re.match(pattern, domain))

    @staticmethod
    def validate_email(email_addr: str) -> bool:
        """Validate email address"""
        if not email_addr or len(email_addr) > NetSentinelValidator.MAX_EMAIL_LENGTH:
            return False

        try:
            parsed = email.utils.parseaddr(email_addr)
            return bool(parsed[1])  # Check if email part exists
        except Exception:
            return False

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL"""
        if not url or len(url) > NetSentinelValidator.MAX_URL_LENGTH:
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
            return (
                NetSentinelValidator.MIN_PORT
                <= port_int
                <= NetSentinelValidator.MAX_PORT
            )
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_timeout(timeout: Union[int, float]) -> bool:
        """Validate timeout value"""
        try:
            timeout_float = float(timeout)
            return 0 < timeout_float <= NetSentinelValidator.MAX_TIMEOUT
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_retry_attempts(attempts: Union[int, str]) -> bool:
        """Validate retry attempts"""
        try:
            attempts_int = int(attempts)
            return 0 <= attempts_int <= NetSentinelValidator.MAX_RETRY_ATTEMPTS
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_hash(hash_value: str, hash_type: str = "sha256") -> bool:
        """Validate hash value"""
        if not hash_value:
            return False

        expected_length = NetSentinelValidator.HASH_LENGTHS.get(hash_type.lower())
        if not expected_length:
            return False

        return len(hash_value) == expected_length and all(
            c in "0123456789abcdefABCDEF" for c in hash_value
        )

    @staticmethod
    def validate_severity(severity: str) -> bool:
        """Validate severity level"""
        return severity.lower() in NetSentinelValidator.VALID_SEVERITIES

    @staticmethod
    def validate_indicator_type(indicator_type: str) -> bool:
        """Validate indicator type"""
        return indicator_type.lower() in NetSentinelValidator.VALID_INDICATOR_TYPES

    @staticmethod
    def validate_confidence(confidence: Union[int, float]) -> bool:
        """Validate confidence score"""
        try:
            conf = float(confidence)
            return 0 <= conf <= 100
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_timestamp(timestamp: Union[int, float, str]) -> bool:
        """Validate timestamp"""
        try:
            ts = float(timestamp)
            # Check if timestamp is reasonable (not too far in past/future)
            now = datetime.now().timestamp()
            # Allow timestamps from 1970 to 2100
            return 0 <= ts <= 4102444800  # Jan 1, 2100
        except (ValueError, TypeError):
            return False

    def validate_config_value(self, key: str, value: Any) -> ValidationResult:
        """Validate configuration value based on key"""
        result = ValidationResult(valid=True)

        if key.endswith(".port"):
            if not self.validate_port(value):
                result.add_error(f"Invalid port number: {value}")
        elif key.endswith(".timeout"):
            if not self.validate_timeout(value):
                result.add_error(f"Invalid timeout value: {value}")
        elif key.endswith(".retry_attempts"):
            if not self.validate_retry_attempts(value):
                result.add_error(f"Invalid retry attempts: {value}")
        elif key.endswith(".host") or key.endswith(".address"):
            if not (self.validate_ip_address(value) or self.validate_domain(value)):
                result.add_error(f"Invalid host/address: {value}")
        elif key.endswith(".email"):
            if not self.validate_email(value):
                result.add_error(f"Invalid email address: {value}")
        elif key.endswith(".url"):
            if not self.validate_url(value):
                result.add_error(f"Invalid URL: {value}")
        elif key.endswith(".hash"):
            if not self.validate_hash(value):
                result.add_error(f"Invalid hash value: {value}")
        elif key.endswith(".severity"):
            if not self.validate_severity(value):
                result.add_error(f"Invalid severity level: {value}")
        elif key.endswith(".confidence"):
            if not self.validate_confidence(value):
                result.add_error(f"Invalid confidence value: {value}")

        return result

    def validate_event_data(self, event_data: Dict[str, Any]) -> ValidationResult:
        """Validate event data structure"""
        result = ValidationResult(valid=True)

        required_fields = ["id", "timestamp", "event_type", "source"]
        for field in required_fields:
            if field not in event_data:
                result.add_error(f"Missing required field: {field}")

        if "timestamp" in event_data:
            if not self.validate_timestamp(event_data["timestamp"]):
                result.add_error("Invalid timestamp format")

        if "severity" in event_data:
            if not self.validate_severity(event_data["severity"]):
                result.add_warning(f"Unknown severity level: {event_data['severity']}")

        return result

    def validate_alert_data(self, alert_data: Dict[str, Any]) -> ValidationResult:
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
            if not self.validate_timestamp(alert_data["timestamp"]):
                result.add_error("Invalid timestamp format")

        if "severity" in alert_data:
            if not self.validate_severity(alert_data["severity"]):
                result.add_warning(f"Unknown severity level: {alert_data['severity']}")

        return result

    def validate_threat_indicator(
        self, indicator_data: Dict[str, Any]
    ) -> ValidationResult:
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
            if not self.validate_indicator_type(indicator_data["indicator_type"]):
                result.add_error(
                    f"Invalid indicator type: {indicator_data['indicator_type']}"
                )

        if "confidence" in indicator_data:
            if not self.validate_confidence(indicator_data["confidence"]):
                result.add_error("Confidence must be between 0 and 100")

        return result

    def validate_network_event(self, event_data: Dict[str, Any]) -> ValidationResult:
        """Validate network event data"""
        result = ValidationResult(valid=True)

        # Check for required fields
        required_fields = ["event_type", "source_ip", "timestamp"]
        for field in required_fields:
            if field not in event_data:
                result.add_error(f"Missing required field: {field}")

        # Validate IP address
        if "source_ip" in event_data:
            if not self.validate_ip_address(event_data["source_ip"]):
                result.add_error(f"Invalid source IP: {event_data['source_ip']}")

        # Validate timestamp
        if "timestamp" in event_data:
            if not self.validate_timestamp(event_data["timestamp"]):
                result.add_error("Invalid timestamp format")

        # Validate port if present
        if "destination_port" in event_data:
            if not self.validate_port(event_data["destination_port"]):
                result.add_error(
                    f"Invalid destination port: {event_data['destination_port']}"
                )

        return result

    def validate_firewall_rule(self, rule_data: Dict[str, Any]) -> ValidationResult:
        """Validate firewall rule data"""
        result = ValidationResult(valid=True)

        required_fields = ["action", "source_ip"]
        for field in required_fields:
            if field not in rule_data:
                result.add_error(f"Missing required field: {field}")

        # Validate IP address
        if "source_ip" in rule_data:
            if not self.validate_ip_address(rule_data["source_ip"]):
                result.add_error(f"Invalid source IP: {rule_data['source_ip']}")

        # Validate action
        if "action" in rule_data:
            valid_actions = ["block", "unblock", "allow"]
            if rule_data["action"] not in valid_actions:
                result.add_error(f"Invalid action: {rule_data['action']}")

        # Validate duration if present
        if "duration" in rule_data:
            try:
                duration = int(rule_data["duration"])
                if duration < 0:
                    result.add_error("Duration must be non-negative")
            except (ValueError, TypeError):
                result.add_error("Invalid duration format")

        return result


# Global validator instance
_validator = NetSentinelValidator()


def get_validator() -> NetSentinelValidator:
    """Get the global validator instance"""
    return _validator


# Convenience functions for backward compatibility
def validate_ip_address(ip: str) -> bool:
    """Validate IP address"""
    return NetSentinelValidator.validate_ip_address(ip)


def validate_domain(domain: str) -> bool:
    """Validate domain name"""
    return NetSentinelValidator.validate_domain(domain)


def validate_email(email_addr: str) -> bool:
    """Validate email address"""
    return NetSentinelValidator.validate_email(email_addr)


def validate_url(url: str) -> bool:
    """Validate URL"""
    return NetSentinelValidator.validate_url(url)


def validate_port(port: Union[int, str]) -> bool:
    """Validate port number"""
    return NetSentinelValidator.validate_port(port)


def validate_severity(severity: str) -> bool:
    """Validate severity level"""
    return NetSentinelValidator.validate_severity(severity)


def validate_event_data(event_data: Dict[str, Any]) -> ValidationResult:
    """Validate event data structure"""
    return _validator.validate_event_data(event_data)


def validate_alert_data(alert_data: Dict[str, Any]) -> ValidationResult:
    """Validate alert data structure"""
    return _validator.validate_alert_data(alert_data)


def validate_threat_indicator(indicator_data: Dict[str, Any]) -> ValidationResult:
    """Validate threat indicator data"""
    return _validator.validate_threat_indicator(indicator_data)
