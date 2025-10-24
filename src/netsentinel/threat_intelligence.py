#!/usr/bin/env python3
"""
Threat Intelligence Integration for NetSentinel
Fetches and processes external threat feeds for enhanced threat analysis
"""

import json
import time
import threading
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import hashlib
import requests
from urllib.parse import urljoin
import ipaddress

logger = logging.getLogger(__name__)


@dataclass
class ThreatIndicator:
    """Threat intelligence indicator"""

    indicator: str  # IP, domain, hash, etc.
    indicator_type: str  # 'ip', 'domain', 'hash', 'url'
    threat_type: str  # 'malware', 'phishing', 'botnet', etc.
    confidence: int  # 0-100
    source: str  # Feed source name
    description: str = ""
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    tags: List[str] = None
    raw_data: Dict = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.first_seen is None:
            self.first_seen = time.time()
        if self.last_seen is None:
            self.last_seen = time.time()
        if self.raw_data is None:
            self.raw_data = {}

    @property
    def indicator_hash(self) -> str:
        """Generate hash for indicator deduplication"""
        return hashlib.sha256(
            f"{self.indicator_type}:{self.indicator}".encode()
        ).hexdigest()

    def is_expired(self, max_age_days: int = 30) -> bool:
        """Check if indicator is expired"""
        if not self.last_seen:
            return True
        expiry_time = time.time() - (max_age_days * 24 * 3600)
        return self.last_seen < expiry_time

    def to_dict(self) -> Dict:
        return asdict(self)


class ThreatFeed:
    """Configuration for a threat intelligence feed"""

    def __init__(
        self,
        name: str,
        url: str,
        feed_type: str = "json",
        api_key: Optional[str] = None,
        update_interval: int = 3600,
        enabled: bool = True,
    ):
        self.name = name
        self.url = url
        self.feed_type = feed_type  # 'json', 'csv', 'stix', 'taxii'
        self.api_key = api_key
        self.update_interval = update_interval  # seconds
        self.enabled = enabled
        self.last_update = 0
        self.last_success = 0
        self.error_count = 0

    def needs_update(self) -> bool:
        """Check if feed needs updating"""
        return time.time() - self.last_update > self.update_interval

    def mark_success(self):
        """Mark successful update"""
        self.last_update = time.time()
        self.last_success = time.time()
        self.error_count = 0

    def mark_error(self):
        """Mark update error"""
        self.last_update = time.time()
        self.error_count += 1


class ThreatIntelligenceManager:
    """
    Manages threat intelligence feeds and indicator processing
    Integrates with event processor for enhanced threat analysis
    """

    def __init__(
        self,
        cache_file: str = "/tmp/netsentinel_threat_intel.json",
        max_indicators: int = 100000,
    ):
        self.cache_file = cache_file
        self.max_indicators = max_indicators

        # Threat indicators storage
        self.indicators = {}  # hash -> ThreatIndicator
        self.indicators_by_type = {"ip": {}, "domain": {}, "hash": {}, "url": {}}

        # Feed configurations
        self.feeds = self._setup_default_feeds()

        # Threading
        self.running = False
        self.update_thread = None

        # Statistics
        self.stats = {
            "total_indicators": 0,
            "indicators_by_type": {},
            "indicators_by_source": {},
            "last_update": 0,
            "feeds_status": {},
        }

        # Load cached indicators
        self._load_cache()

        logger.info(
            f"Initialized threat intelligence manager with {len(self.indicators)} cached indicators"
        )

    def _setup_default_feeds(self) -> Dict[str, ThreatFeed]:
        """Setup default threat intelligence feeds"""
        feeds = {}

        # AbuseIPDB (requires API key)
        feeds["abuseipdb"] = ThreatFeed(
            name="abuseipdb",
            url="https://api.abuseipdb.com/api/v2/blacklist",
            feed_type="json",
            api_key=None,  # Requires configuration
            update_interval=3600,  # 1 hour
            enabled=False,  # Disabled by default (needs API key)
        )

        # Emerging Threats - Compromised IPs
        feeds["emerging_threats_compromised"] = ThreatFeed(
            name="emerging_threats_compromised",
            url="https://rules.emergingthreats.net/blockrules/compromised-ips.txt",
            feed_type="text",
            update_interval=3600,
            enabled=True,
        )

        # OpenPhish (phishing domains)
        feeds["openphish"] = ThreatFeed(
            name="openphish",
            url="https://openphish.com/feed.txt",
            feed_type="text",
            update_interval=1800,  # 30 minutes
            enabled=True,
        )

        # Malware Domain List
        feeds["malware_domain_list"] = ThreatFeed(
            name="malware_domain_list",
            url="https://www.malwaredomainlist.com/hostslist/ip.txt",
            feed_type="text",
            update_interval=3600,
            enabled=True,
        )

        # Feodo Tracker (botnet C2 servers)
        feeds["feodo_tracker"] = ThreatFeed(
            name="feodo_tracker",
            url="https://feodotracker.abuse.ch/downloads/ipblocklist.txt",
            feed_type="text",
            update_interval=3600,
            enabled=True,
        )

        return feeds

    def start_updates(self):
        """Start background feed updates"""
        if self.running:
            logger.warning("Threat intelligence updates already running")
            return

        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

        logger.info("Threat intelligence updates started")

    def stop_updates(self):
        """Stop background feed updates"""
        self.running = False

        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)

        logger.info("Threat intelligence updates stopped")

    def _update_loop(self):
        """Main update loop"""
        while self.running:
            try:
                self.update_feeds()
                self._cleanup_expired_indicators()

                # Save cache periodically
                self._save_cache()

                # Update stats
                self._update_stats()

            except Exception as e:
                logger.error(f"Error in threat intelligence update loop: {e}")

            # Sleep for update interval
            time.sleep(300)  # Check every 5 minutes

    def update_feeds(self):
        """Update all enabled feeds"""
        logger.info("Updating threat intelligence feeds...")

        for feed_name, feed in self.feeds.items():
            if not feed.enabled or not feed.needs_update():
                continue

            try:
                logger.debug(f"Updating feed: {feed_name}")
                indicators = self._fetch_feed(feed)

                if indicators:
                    self._process_indicators(indicators, feed)
                    feed.mark_success()
                    logger.info(
                        f"Successfully updated feed {feed_name}: {len(indicators)} indicators"
                    )
                else:
                    logger.warning(f"No indicators received from feed {feed_name}")
                    feed.mark_error()

            except Exception as e:
                logger.error(f"Error updating feed {feed_name}: {e}")
                feed.mark_error()

    def _fetch_feed(self, feed: ThreatFeed) -> List[ThreatIndicator]:
        """Fetch indicators from a threat feed"""
        headers = {}
        if feed.api_key:
            headers["Key"] = feed.api_key

        try:
            response = requests.get(feed.url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Feed {feed.name} returned status {response.status_code}")
                return []

            content = response.text

            # Parse based on feed type
            if feed.feed_type == "json":
                return self._parse_json_feed(content, feed)
            elif feed.feed_type == "text":
                return self._parse_text_feed(content, feed)
            elif feed.feed_type == "csv":
                return self._parse_csv_feed(content, feed)
            else:
                logger.warning(f"Unsupported feed type: {feed.feed_type}")
                return []

        except requests.RequestException as e:
            logger.error(f"Error fetching feed {feed.name}: {e}")
            return []

    def _parse_json_feed(self, content: str, feed: ThreatFeed) -> List[ThreatIndicator]:
        """Parse JSON format threat feed"""
        try:
            data = json.loads(content)
            indicators = []

            # Handle different JSON structures
            if "data" in data:
                items = data["data"]
            elif isinstance(data, list):
                items = data
            else:
                items = [data]

            for item in items:
                if isinstance(item, dict):
                    # Extract indicator information
                    indicator = (
                        item.get("ipAddress")
                        or item.get("domain")
                        or item.get("url")
                        or item.get("hash")
                    )
                    if not indicator:
                        continue

                    # Determine indicator type
                    indicator_type = self._classify_indicator(indicator)

                    threat_indicator = ThreatIndicator(
                        indicator=indicator,
                        indicator_type=indicator_type,
                        threat_type=item.get("threatType", "unknown"),
                        confidence=int(item.get("confidence", 50)),
                        source=feed.name,
                        description=item.get("description", ""),
                        first_seen=item.get("firstSeen"),
                        last_seen=item.get("lastSeen"),
                        tags=item.get("tags", []),
                        raw_data=item,
                    )
                    indicators.append(threat_indicator)

            return indicators

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON feed {feed.name}: {e}")
            return []

    def _parse_text_feed(self, content: str, feed: ThreatFeed) -> List[ThreatIndicator]:
        """Parse text format threat feed (one indicator per line)"""
        indicators = []

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Extract IP or domain
            parts = line.split()
            indicator = parts[0]

            # Skip invalid indicators
            if not self._is_valid_indicator(indicator):
                continue

            indicator_type = self._classify_indicator(indicator)

            threat_indicator = ThreatIndicator(
                indicator=indicator,
                indicator_type=indicator_type,
                threat_type="malicious",
                confidence=80,  # Default confidence for text feeds
                source=feed.name,
                description=f"Listed in {feed.name}",
                raw_data={"line": line},
            )
            indicators.append(threat_indicator)

        return indicators

    def _parse_csv_feed(self, content: str, feed: ThreatFeed) -> List[ThreatIndicator]:
        """Parse CSV format threat feed"""
        # Basic CSV parsing (could be enhanced with csv module)
        indicators = []
        lines = content.splitlines()

        if not lines:
            return indicators

        # Assume first line is header
        headers = lines[0].split(",")
        data_lines = lines[1:]

        for line in data_lines:
            parts = line.split(",")
            if len(parts) != len(headers):
                continue

            item = dict(zip(headers, parts))
            indicator = item.get("ip") or item.get("domain") or item.get("url")
            if not indicator:
                continue

            indicator_type = self._classify_indicator(indicator)

            threat_indicator = ThreatIndicator(
                indicator=indicator,
                indicator_type=indicator_type,
                threat_type=item.get("type", "unknown"),
                confidence=int(item.get("confidence", 50)),
                source=feed.name,
                description=item.get("description", ""),
                raw_data=item,
            )
            indicators.append(threat_indicator)

        return indicators

    def _classify_indicator(self, indicator: str) -> str:
        """Classify indicator type"""
        try:
            # Check if it's an IP address
            ipaddress.ip_address(indicator)
            return "ip"
        except ValueError:
            pass

        # Check if it's a domain (contains dots, not URL)
        if "." in indicator and "://" not in indicator:
            return "domain"

        # Check if it's a URL
        if "://" in indicator:
            return "url"

        # Default to hash (MD5, SHA1, SHA256)
        if len(indicator) in [32, 40, 64] and all(
            c in "0123456789abcdefABCDEF" for c in indicator
        ):
            return "hash"

        return "unknown"

    def _is_valid_indicator(self, indicator: str) -> bool:
        """Validate indicator format"""
        if not indicator or len(indicator) < 4:
            return False

        # Basic validation
        try:
            if self._classify_indicator(indicator) in ["ip", "domain"]:
                return True
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"Indicator validation failed for {indicator}: {e}")
            pass

        return False

    def _process_indicators(self, indicators: List[ThreatIndicator], feed: ThreatFeed):
        """Process and store threat indicators"""
        for indicator in indicators:
            indicator_hash = indicator.indicator_hash

            # Check for duplicates and updates
            if indicator_hash in self.indicators:
                existing = self.indicators[indicator_hash]
                # Update last seen and merge data
                existing.last_seen = max(existing.last_seen, indicator.last_seen)
                existing.confidence = max(existing.confidence, indicator.confidence)
                existing.tags.extend(indicator.tags)
                existing.tags = list(set(existing.tags))  # Remove duplicates
            else:
                # Add new indicator
                self.indicators[indicator_hash] = indicator

                # Add to type index
                if indicator.indicator_type in self.indicators_by_type:
                    self.indicators_by_type[indicator.indicator_type][
                        indicator.indicator
                    ] = indicator

        # Enforce max indicators limit
        if len(self.indicators) > self.max_indicators:
            # Remove oldest indicators
            sorted_indicators = sorted(
                self.indicators.items(), key=lambda x: x[1].last_seen
            )
            to_remove = len(self.indicators) - self.max_indicators

            for i in range(to_remove):
                hash_key, indicator = sorted_indicators[i]
                del self.indicators[hash_key]
                if (
                    indicator.indicator
                    in self.indicators_by_type[indicator.indicator_type]
                ):
                    del self.indicators_by_type[indicator.indicator_type][
                        indicator.indicator
                    ]

    def _cleanup_expired_indicators(self, max_age_days: int = 30):
        """Remove expired indicators"""
        expired_hashes = []

        for hash_key, indicator in self.indicators.items():
            if indicator.is_expired(max_age_days):
                expired_hashes.append(hash_key)
                if (
                    indicator.indicator
                    in self.indicators_by_type[indicator.indicator_type]
                ):
                    del self.indicators_by_type[indicator.indicator_type][
                        indicator.indicator
                    ]

        for hash_key in expired_hashes:
            del self.indicators[hash_key]

        if expired_hashes:
            logger.info(f"Cleaned up {len(expired_hashes)} expired threat indicators")

    def _load_cache(self):
        """Load indicators from cache file"""
        try:
            with open(self.cache_file, "r") as f:
                cache_data = json.load(f)

            for item in cache_data.get("indicators", []):
                indicator = ThreatIndicator(**item)
                if not indicator.is_expired():
                    self.indicators[indicator.indicator_hash] = indicator

                    # Rebuild type index
                    if indicator.indicator_type in self.indicators_by_type:
                        self.indicators_by_type[indicator.indicator_type][
                            indicator.indicator
                        ] = indicator

            logger.info(f"Loaded {len(self.indicators)} indicators from cache")

        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            logger.info("No valid cache file found, starting fresh")

    def _save_cache(self):
        """Save indicators to cache file"""
        try:
            cache_data = {
                "indicators": [
                    indicator.to_dict() for indicator in self.indicators.values()
                ],
                "timestamp": time.time(),
            }

            with open(self.cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def _update_stats(self):
        """Update statistics"""
        self.stats["total_indicators"] = len(self.indicators)
        self.stats["indicators_by_type"] = {
            indicator_type: len(indicators)
            for indicator_type, indicators in self.indicators_by_type.items()
        }

        # Count by source
        source_counts = {}
        for indicator in self.indicators.values():
            source_counts[indicator.source] = source_counts.get(indicator.source, 0) + 1
        self.stats["indicators_by_source"] = source_counts

        # Feed status
        self.stats["feeds_status"] = {
            name: {
                "enabled": feed.enabled,
                "last_update": feed.last_update,
                "last_success": feed.last_success,
                "error_count": feed.error_count,
            }
            for name, feed in self.feeds.items()
        }

        self.stats["last_update"] = time.time()

    def check_indicator(
        self, indicator: str, indicator_type: Optional[str] = None
    ) -> Optional[ThreatIndicator]:
        """
        Check if an indicator is in threat intelligence

        Args:
            indicator: Indicator to check
            indicator_type: Type of indicator ('ip', 'domain', etc.)

        Returns:
            ThreatIndicator if found, None otherwise
        """
        if not indicator_type:
            indicator_type = self._classify_indicator(indicator)

        if indicator_type in self.indicators_by_type:
            return self.indicators_by_type[indicator_type].get(indicator)

        return None

    def get_indicators(
        self,
        indicator_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[ThreatIndicator]:
        """
        Get threat indicators with optional filtering

        Args:
            indicator_type: Filter by type ('ip', 'domain', etc.)
            source: Filter by source feed
            limit: Maximum number of indicators to return

        Returns:
            List of matching ThreatIndicator objects
        """
        indicators = list(self.indicators.values())

        # Apply filters
        if indicator_type:
            indicators = [i for i in indicators if i.indicator_type == indicator_type]

        if source:
            indicators = [i for i in indicators if i.source == source]

        # Sort by last seen (most recent first)
        indicators.sort(key=lambda x: x.last_seen or 0, reverse=True)

        return indicators[:limit]

    def get_statistics(self) -> Dict:
        """Get threat intelligence statistics"""
        self._update_stats()
        return self.stats.copy()

    def add_feed(self, feed: ThreatFeed):
        """Add a new threat feed"""
        self.feeds[feed.name] = feed
        logger.info(f"Added threat feed: {feed.name}")

    def remove_feed(self, feed_name: str):
        """Remove a threat feed"""
        if feed_name in self.feeds:
            del self.feeds[feed_name]
            logger.info(f"Removed threat feed: {feed_name}")

    def enable_feed(self, feed_name: str, enabled: bool = True):
        """Enable or disable a threat feed"""
        if feed_name in self.feeds:
            self.feeds[feed_name].enabled = enabled
            status = "enabled" if enabled else "disabled"
            logger.info(f"{status.capitalize()} threat feed: {feed_name}")


# Global threat intelligence manager instance
threat_intel_manager = None


def get_threat_intel_manager() -> ThreatIntelligenceManager:
    """Get or create global threat intelligence manager instance"""
    global threat_intel_manager
    if threat_intel_manager is None:
        threat_intel_manager = ThreatIntelligenceManager()
    return threat_intel_manager


def check_threat_indicator(indicator: str) -> Optional[ThreatIndicator]:
    """Convenience function to check if indicator is a threat"""
    manager = get_threat_intel_manager()
    return manager.check_indicator(indicator)


def start_threat_intel_updates():
    """Convenience function to start threat intelligence updates"""
    manager = get_threat_intel_manager()
    manager.start_updates()


def stop_threat_intel_updates():
    """Convenience function to stop threat intelligence updates"""
    manager = get_threat_intel_manager()
    manager.stop_updates()
