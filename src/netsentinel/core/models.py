#!/usr/bin/env python3
"""
Standardized data models for NetSentinel
Unified data structures across all components
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import ipaddress
import re
from datetime import datetime


class EventSeverity(Enum):
    """Event severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(Enum):
    """Standard event types"""

    SSH_LOGIN = "ssh_login"
    HTTP_REQUEST = "http_request"
    FTP_LOGIN = "ftp_login"
    TELNET_LOGIN = "telnet_login"
    MYSQL_LOGIN = "mysql_login"
    PACKET_ANOMALY = "packet_anomaly"
    THREAT_DETECTED = "threat_detected"
    ALERT_CREATED = "alert_created"
    IP_BLOCKED = "ip_blocked"


class ThreatLevel(Enum):
    """Threat level classifications"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of data validation"""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

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


@dataclass
class StandardEvent:
    """Unified event model for all NetSentinel events"""

    id: str
    timestamp: float
    event_type: str
    source: str
    data: Dict[str, Any]
    severity: str = "medium"
    tags: List[str] = field(default_factory=list)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation and setup"""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()
        if not isinstance(self.tags, list):
            self.tags = []
        if not isinstance(self.data, dict):
            self.data = {}
        if not isinstance(self.metadata, dict):
            self.metadata = {}

    def validate(self) -> ValidationResult:
        """Validate event data"""
        result = ValidationResult(valid=True)

        # Required fields validation
        if not self.id:
            result.add_error("Event ID is required")

        if not self.timestamp:
            result.add_error("Timestamp is required")
        elif not isinstance(self.timestamp, (int, float)):
            result.add_error("Timestamp must be numeric")
        elif self.timestamp <= 0:
            result.add_error("Timestamp must be positive")

        if not self.event_type:
            result.add_error("Event type is required")
        elif not isinstance(self.event_type, str):
            result.add_error("Event type must be string")

        if not self.source:
            result.add_error("Source is required")
        elif not isinstance(self.source, str):
            result.add_error("Source must be string")

        # Severity validation
        if self.severity not in [s.value for s in EventSeverity]:
            result.add_warning(f"Unknown severity level: {self.severity}")
            # Set to default severity if invalid
            self.severity = "medium"

        # Data validation
        if not isinstance(self.data, dict):
            result.add_error("Data must be a dictionary")

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StandardEvent":
        """Create from dictionary"""
        return cls(**data)

    def is_recent(self, max_age_seconds: int = 3600) -> bool:
        """Check if event is recent"""
        return time.time() - self.timestamp <= max_age_seconds

    def get_age_seconds(self) -> float:
        """Get event age in seconds"""
        return time.time() - self.timestamp


@dataclass
class StandardAlert:
    """Unified alert model"""

    id: str
    title: str
    description: str
    severity: str
    source: str
    timestamp: float
    event_data: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    acknowledged: bool = False
    resolved: bool = False
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    escalation_level: int = 0
    last_notification: Optional[float] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization setup"""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()
        if not isinstance(self.tags, list):
            self.tags = []
        if not isinstance(self.event_data, dict):
            self.event_data = {}
        if not isinstance(self.metadata, dict):
            self.metadata = {}

    def validate(self) -> ValidationResult:
        """Validate alert data"""
        result = ValidationResult(valid=True)

        # Required fields validation
        if not self.id:
            result.add_error("Alert ID is required")

        if not self.title:
            result.add_error("Alert title is required")
        elif not isinstance(self.title, str):
            result.add_error("Alert title must be string")

        if not self.description:
            result.add_error("Alert description is required")
        elif not isinstance(self.description, str):
            result.add_error("Alert description must be string")

        if not self.severity:
            result.add_error("Alert severity is required")
        elif self.severity not in [s.value for s in EventSeverity]:
            result.add_warning(f"Unknown severity level: {self.severity}")
            # Set to default severity if invalid
            self.severity = "medium"

        if not self.source:
            result.add_error("Alert source is required")
        elif not isinstance(self.source, str):
            result.add_error("Alert source must be string")

        if not self.timestamp:
            result.add_error("Alert timestamp is required")
        elif not isinstance(self.timestamp, (int, float)):
            result.add_error("Alert timestamp must be numeric")

        # Boolean field validation
        if not isinstance(self.acknowledged, bool):
            result.add_error("Acknowledged must be boolean")

        if not isinstance(self.resolved, bool):
            result.add_error("Resolved must be boolean")

        return result

    def acknowledge(self, user_id: str) -> bool:
        """Acknowledge the alert"""
        if self.acknowledged:
            return False

        self.acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_at = time.time()
        return True

    def resolve(self, user_id: str) -> bool:
        """Resolve the alert"""
        if self.resolved:
            return False

        self.resolved = True
        self.resolved_by = user_id
        self.resolved_at = time.time()
        return True

    def is_expired(self, ttl_seconds: int = 86400) -> bool:
        """Check if alert is expired"""
        return time.time() - self.timestamp > ttl_seconds

    def should_escalate(self, escalation_delays: List[int]) -> bool:
        """Check if alert should be escalated"""
        if self.acknowledged or self.resolved:
            return False

        if self.escalation_level >= len(escalation_delays):
            return False

        delay = escalation_delays[self.escalation_level]
        return (
            time.time() - self.last_notification > delay
            if self.last_notification
            else True
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StandardAlert":
        """Create from dictionary"""
        return cls(**data)


@dataclass
class ThreatIndicator:
    """Threat intelligence indicator"""

    indicator: str
    indicator_type: str  # 'ip', 'domain', 'hash', 'url'
    threat_type: str  # 'malware', 'phishing', 'botnet', etc.
    confidence: int  # 0-100
    source: str
    description: str = ""
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization setup"""
        if self.first_seen is None:
            self.first_seen = time.time()
        if self.last_seen is None:
            self.last_seen = time.time()
        if not isinstance(self.tags, list):
            self.tags = []
        if not isinstance(self.raw_data, dict):
            self.raw_data = {}

    def validate(self) -> ValidationResult:
        """Validate threat indicator"""
        result = ValidationResult(valid=True)

        if not self.indicator:
            result.add_error("Indicator is required")

        if not self.indicator_type:
            result.add_error("Indicator type is required")
        elif self.indicator_type not in ["ip", "domain", "hash", "url", "email"]:
            result.add_error(f"Invalid indicator type: {self.indicator_type}")

        if not self.threat_type:
            result.add_error("Threat type is required")

        if not isinstance(self.confidence, int):
            result.add_error("Confidence must be integer")
        elif not 0 <= self.confidence <= 100:
            result.add_error("Confidence must be between 0 and 100")

        if not self.source:
            result.add_error("Source is required")

        # Validate IP addresses
        if self.indicator_type == "ip":
            try:
                ipaddress.ip_address(self.indicator)
            except ValueError:
                result.add_error(f"Invalid IP address: {self.indicator}")

        return result

    def is_expired(self, max_age_days: int = 30) -> bool:
        """Check if indicator is expired"""
        if not self.last_seen:
            return True
        expiry_time = time.time() - (max_age_days * 24 * 3600)
        return self.last_seen < expiry_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThreatIndicator":
        """Create from dictionary"""
        return cls(**data)


class DataValidator:
    """Centralized data validation"""

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
    def validate_email(email: str) -> bool:
        """Validate email address"""
        if not email or len(email) > 254:
            return False

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL"""
        if not url or len(url) > 2048:
            return False

        pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(pattern, url))

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


# Factory functions for creating standard objects
def create_event(
    event_type: str,
    source: str,
    data: Dict[str, Any],
    severity: str = "medium",
    **kwargs,
) -> StandardEvent:
    """Create a standard event"""
    # Extract timestamp from kwargs if provided, otherwise use current time
    timestamp = kwargs.pop("timestamp", time.time())

    return StandardEvent(
        id=str(uuid.uuid4()),
        timestamp=timestamp,
        event_type=event_type,
        source=source,
        data=data,
        severity=severity,
        **kwargs,
    )


def create_alert(
    title: str,
    description: str,
    severity: str,
    source: str,
    event_data: Dict[str, Any],
    **kwargs,
) -> StandardAlert:
    """Create a standard alert"""
    return StandardAlert(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        severity=severity,
        source=source,
        timestamp=time.time(),
        event_data=event_data,
        **kwargs,
    )


def create_threat_indicator(
    indicator: str,
    indicator_type: str,
    threat_type: str,
    confidence: int,
    source: str,
    **kwargs,
) -> ThreatIndicator:
    """Create a threat indicator"""
    return ThreatIndicator(
        indicator=indicator,
        indicator_type=indicator_type,
        threat_type=threat_type,
        confidence=confidence,
        source=source,
        **kwargs,
    )
