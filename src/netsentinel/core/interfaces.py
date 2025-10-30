#!/usr/bin/env python3
"""
Interface definitions for NetSentinel components
Provides standardized contracts for all system components
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

# Import Event and Alert classes from models.py to avoid duplication
try:
    from .models import StandardEvent as Event, StandardAlert as Alert
except ImportError:
    # Fallback for circular import issues
    Event = None
    Alert = None


@dataclass
class ThreatIndicator:
    """Standardized threat indicator structure"""

    indicator: str
    indicator_type: str
    threat_type: str
    confidence: int
    source: str
    description: str = ""
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class IEventProcessor(ABC):
    """Interface for event processors"""

    @abstractmethod
    async def process_event(self, event: Event) -> Event:
        """Process an event and return enhanced event"""
        pass

    @abstractmethod
    async def get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing metrics"""
        pass


class IAlertManager(ABC):
    """Interface for alert managers"""

    @abstractmethod
    async def create_alert(self, alert: Alert) -> bool:
        """Create a new alert"""
        pass

    @abstractmethod
    async def get_alerts(self, filters: Optional[Dict[str, Any]] = None) -> List[Alert]:
        """Get alerts with optional filters"""
        pass

    @abstractmethod
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        pass

    @abstractmethod
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        pass


class IFirewallManager(ABC):
    """Interface for firewall managers"""

    @abstractmethod
    async def block_ip(self, ip: str, duration: int = 3600, reason: str = "") -> bool:
        """Block an IP address"""
        pass

    @abstractmethod
    async def unblock_ip(self, ip: str) -> bool:
        """Unblock an IP address"""
        pass

    @abstractmethod
    async def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        pass

    @abstractmethod
    async def get_blocked_ips(self) -> List[str]:
        """Get list of blocked IPs"""
        pass


class IThreatIntelligence(ABC):
    """Interface for threat intelligence systems"""

    @abstractmethod
    async def check_indicator(
        self, indicator: str, indicator_type: str
    ) -> Optional[ThreatIndicator]:
        """Check if indicator is known threat"""
        pass

    @abstractmethod
    async def add_indicator(self, indicator: ThreatIndicator) -> bool:
        """Add new threat indicator"""
        pass

    @abstractmethod
    async def get_indicators(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[ThreatIndicator]:
        """Get threat indicators with optional filters"""
        pass

    @abstractmethod
    async def update_feeds(self) -> bool:
        """Update threat intelligence feeds"""
        pass


class IMLDetector(ABC):
    """Interface for ML anomaly detection"""

    @abstractmethod
    async def analyze_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze event and return anomaly score"""
        pass

    @abstractmethod
    async def train_on_events(self, events: List[Dict[str, Any]]) -> bool:
        """Train model on events"""
        pass


# Removed unused IDataStore interface - use specific database implementations

# Removed unused INotifier interface - use AlertManager and specific notification handlers


class IWebSocketBroadcaster(ABC):
    """Interface for real-time event broadcasting"""

    @abstractmethod
    async def broadcast_threat(self, threat_data: Dict[str, Any]) -> None:
        """Broadcast threat to connected clients"""
        pass

    @abstractmethod
    async def broadcast_alert(self, alert_data: Dict[str, Any]) -> None:
        """Broadcast alert to connected clients"""
        pass


class IMLDetector(ABC):
    """Interface for ML anomaly detection"""

    @abstractmethod
    async def analyze_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze event and return anomaly score"""
        pass

    @abstractmethod
    async def train_on_events(self, events: List[Dict[str, Any]]) -> bool:
        """Train model on events"""
        pass


class IAuthProvider(ABC):
    """Interface for authentication"""

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> Optional[str]:
        """Authenticate user and return token"""
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token"""
        pass