#!/usr/bin/env python3
"""
Threat Storage for NetSentinel
Redis-based threat intelligence storage and retrieval
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from ..core.base import BaseComponent
from ..core.models import ThreatLevel, StandardEvent
from ..core.error_handler import handle_errors, create_error_context
from ..monitoring.logger import create_logger

logger = create_logger("threat_storage", level="INFO")


@dataclass
class ThreatRecord:
    """Threat record stored in Redis"""

    ip_address: str
    threat_score: float
    threat_level: ThreatLevel
    event_count: int
    last_seen: float
    first_seen: float
    indicators: List[str]
    recent_events: List[Dict[str, Any]]
    correlation_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        data = asdict(self)
        data["threat_level"] = self.threat_level.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThreatRecord":
        """Create from dictionary"""
        data_copy = data.copy()
        data_copy["threat_level"] = ThreatLevel(data_copy["threat_level"])
        return cls(**data_copy)


@dataclass
class CorrelationRecord:
    """Event correlation record"""

    ip_address: str
    events: List[Dict[str, Any]]
    correlation_score: float
    pattern_detected: Optional[str]
    created_at: float
    expires_at: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorrelationRecord":
        """Create from dictionary"""
        return cls(**data)


class ThreatStorage(BaseComponent):
    """
    Redis-based threat intelligence storage
    Stores and retrieves threat data with TTL-based cleanup
    """

    def __init__(
        self,
        name: str = "threat_storage",
        redis_host: str = "redis",
        redis_port: int = 6379,
        redis_password: str = "",
        threat_ttl: int = 3600,  # 1 hour
        correlation_ttl: int = 1800,  # 30 minutes
        max_events_per_ip: int = 100,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, config, logger)

        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password
        self.threat_ttl = threat_ttl
        self.correlation_ttl = correlation_ttl
        self.max_events_per_ip = max_events_per_ip

        # Redis client will be initialized in _initialize
        self.redis_client = None

    async def _initialize(self):
        """Initialize Redis connection"""
        try:
            import redis.asyncio as redis

            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password if self.redis_password else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=20,
            )

            # Test connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")

        except ImportError:
            logger.error("Redis client not available. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def _start_internal(self):
        """Start threat storage operations"""
        logger.info("Threat storage started")

    async def _stop_internal(self):
        """Stop threat storage operations"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Threat storage stopped")

    async def _cleanup(self):
        """Cleanup resources"""
        # Connection cleanup handled in _stop_internal
        pass

    async def store_threat(
        self,
        ip_address: str,
        threat_score: float,
        threat_level: ThreatLevel,
        event: StandardEvent,
        indicators: List[str] = None,
    ) -> bool:
        """Store threat information for an IP address"""
        try:
            if not self.redis_client:
                return False

            indicators = indicators or []

            # Get existing threat record
            threat_key = f"threat:{ip_address}"
            existing_data = await self.redis_client.get(threat_key)

            if existing_data:
                # Update existing record
                existing_record = ThreatRecord.from_dict(json.loads(existing_data))

                # Update threat score (weighted average)
                total_events = existing_record.event_count + 1
                existing_record.threat_score = (
                    (existing_record.threat_score * existing_record.event_count)
                    + threat_score
                ) / total_events

                # Update threat level to the higher of the two
                threat_levels = ["low", "medium", "high", "critical"]
                if threat_levels.index(threat_level.value) > threat_levels.index(
                    existing_record.threat_level.value
                ):
                    existing_record.threat_level = threat_level

                existing_record.event_count = total_events
                existing_record.last_seen = time.time()
                existing_record.indicators.extend(indicators)
                existing_record.indicators = list(
                    set(existing_record.indicators)
                )  # Remove duplicates

                # Add recent event
                event_data = {
                    "event_type": event.event_type,
                    "timestamp": event.timestamp,
                    "data": event.data,
                    "threat_score": threat_score,
                }
                existing_record.recent_events.append(event_data)
                existing_record.recent_events = existing_record.recent_events[
                    -self.max_events_per_ip :
                ]

                threat_record = existing_record

            else:
                # Create new record
                threat_record = ThreatRecord(
                    ip_address=ip_address,
                    threat_score=threat_score,
                    threat_level=threat_level,
                    event_count=1,
                    last_seen=time.time(),
                    first_seen=time.time(),
                    indicators=indicators,
                    recent_events=[
                        {
                            "event_type": event.event_type,
                            "timestamp": event.timestamp,
                            "data": event.data,
                            "threat_score": threat_score,
                        }
                    ],
                    correlation_id=f"corr_{ip_address}_{int(time.time())}",
                )

            # Store in Redis with TTL
            await self.redis_client.setex(
                threat_key, self.threat_ttl, json.dumps(threat_record.to_dict())
            )

            # Add to threat index for querying
            await self._add_to_threat_index(ip_address, threat_level, threat_score)

            logger.debug(
                f"Stored threat for IP {ip_address}: score={threat_score:.2f}, level={threat_level.value}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store threat for {ip_address}: {e}")
            context = create_error_context(
                "store_threat", "threat_storage", additional_data={"ip": ip_address}
            )
            handle_errors(e, context)
            return False

    async def get_threat(self, ip_address: str) -> Optional[ThreatRecord]:
        """Get threat information for an IP address"""
        try:
            if not self.redis_client:
                return None

            threat_key = f"threat:{ip_address}"
            data = await self.redis_client.get(threat_key)

            if data:
                return ThreatRecord.from_dict(json.loads(data))

            return None

        except Exception as e:
            logger.error(f"Failed to get threat for {ip_address}: {e}")
            return None

    async def get_all_threats(
        self, min_score: float = 0.0, limit: int = 1000
    ) -> List[ThreatRecord]:
        """Get all threats above minimum score"""
        try:
            if not self.redis_client:
                return []

            threats = []

            # Get all threat keys
            threat_keys = await self.redis_client.keys("threat:*")

            for key in threat_keys[:limit]:  # Limit for performance
                data = await self.redis_client.get(key)
                if data:
                    threat_record = ThreatRecord.from_dict(json.loads(data))
                    if threat_record.threat_score >= min_score:
                        threats.append(threat_record)

            # Sort by threat score descending
            threats.sort(key=lambda x: x.threat_score, reverse=True)
            return threats[:limit]

        except Exception as e:
            logger.error(f"Failed to get all threats: {e}")
            return []

    async def store_correlation(
        self,
        ip_address: str,
        events: List[StandardEvent],
        correlation_score: float,
        pattern: str = None,
    ) -> bool:
        """Store event correlation data"""
        try:
            if not self.redis_client:
                return False

            correlation_key = f"correlation:{ip_address}:{int(time.time())}"

            correlation_record = CorrelationRecord(
                ip_address=ip_address,
                events=[
                    {
                        "event_type": event.event_type,
                        "timestamp": event.timestamp,
                        "data": event.data,
                    }
                    for event in events
                ],
                correlation_score=correlation_score,
                pattern_detected=pattern,
                created_at=time.time(),
                expires_at=time.time() + self.correlation_ttl,
            )

            # Store correlation data
            await self.redis_client.setex(
                correlation_key,
                self.correlation_ttl,
                json.dumps(asdict(correlation_record)),
            )

            # Add to correlation index
            await self.redis_client.sadd(
                f"correlation_index:{ip_address}", correlation_key
            )

            logger.debug(
                f"Stored correlation for IP {ip_address}: score={correlation_score:.2f}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store correlation for {ip_address}: {e}")
            return False

    async def get_correlations(self, ip_address: str) -> List[CorrelationRecord]:
        """Get correlation data for an IP address"""
        try:
            if not self.redis_client:
                return []

            # Get correlation keys for this IP
            correlation_keys = await self.redis_client.smembers(
                f"correlation_index:{ip_address}"
            )

            correlations = []
            for key in correlation_keys:
                data = await self.redis_client.get(key)
                if data:
                    record_dict = json.loads(data)
                    correlations.append(CorrelationRecord(**record_dict))

            return correlations

        except Exception as e:
            logger.error(f"Failed to get correlations for {ip_address}: {e}")
            return []

    async def _add_to_threat_index(
        self, ip_address: str, threat_level: ThreatLevel, threat_score: float
    ):
        """Add threat to various indexes for querying"""
        try:
            if not self.redis_client:
                return

            # Add to threat level index
            await self.redis_client.sadd(
                f"threats_by_level:{threat_level.value}", ip_address
            )

            # Add to threat score sorted set
            await self.redis_client.zadd("threats_by_score", {ip_address: threat_score})

            # Add to recent threats
            await self.redis_client.zadd("recent_threats", {ip_address: time.time()})

        except Exception as e:
            logger.error(f"Failed to update threat index for {ip_address}: {e}")

    async def get_threat_statistics(self) -> Dict[str, Any]:
        """Get threat statistics"""
        try:
            if not self.redis_client:
                return {"error": "Redis not connected"}

            stats = {
                "total_threats": 0,
                "threats_by_level": {},
                "high_score_threats": 0,
                "recent_threats": 0,
            }

            # Count threats by level
            for level in ["low", "medium", "high", "critical"]:
                count = await self.redis_client.scard(f"threats_by_level:{level}")
                stats["threats_by_level"][level] = count
                stats["total_threats"] += count

            # Count high-score threats (>7.0)
            high_score_count = await self.redis_client.zcount(
                "threats_by_score", 7.0, "+inf"
            )
            stats["high_score_threats"] = high_score_count

            # Count recent threats (last hour)
            recent_count = await self.redis_client.zcount(
                "recent_threats", time.time() - 3600, time.time()
            )
            stats["recent_threats"] = recent_count

            return stats

        except Exception as e:
            logger.error(f"Failed to get threat statistics: {e}")
            return {"error": str(e)}

    async def cleanup_expired_data(self):
        """Clean up expired threat data"""
        try:
            if not self.redis_client:
                return

            # Note: Redis handles TTL automatically for individual keys
            # This method could be used for additional cleanup logic

            logger.info("Threat storage cleanup completed")

        except Exception as e:
            logger.error(f"Failed to cleanup threat data: {e}")


# Factory function
def create_threat_storage(
    redis_host: str = "redis",
    redis_port: int = 6379,
    redis_password: str = "",
    threat_ttl: int = 3600,
    correlation_ttl: int = 1800,
) -> ThreatStorage:
    """Create threat storage instance"""
    return ThreatStorage(
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        threat_ttl=threat_ttl,
        correlation_ttl=correlation_ttl,
    )
