#!/usr/bin/env python3
"""
Enterprise Database Integration for NetSentinel
Provides Elasticsearch for document storage and InfluxDB for time-series metrics
"""

import time
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import threading
import queue

# Elasticsearch imports
try:
    from elasticsearch import Elasticsearch, helpers
    from elasticsearch.exceptions import ConnectionError, NotFoundError

    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False

# InfluxDB imports
try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS

    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False

logger = logging.getLogger(__name__)

# Log availability status
if not ELASTICSEARCH_AVAILABLE:
    logger.warning("Elasticsearch not available. Document storage disabled.")
if not INFLUXDB_AVAILABLE:
    logger.warning("InfluxDB not available. Time-series storage disabled.")


class ElasticsearchManager:
    """Manages Elasticsearch operations for document storage and search"""

    def __init__(
        self,
        hosts: List[str] = None,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        index_prefix: str = "netsentinel",
    ):
        if not ELASTICSEARCH_AVAILABLE:
            raise ImportError("Elasticsearch client not available")

        self.index_prefix = index_prefix
        self.indices = {
            "events": f"{index_prefix}-events",
            "threats": f"{index_prefix}-threats",
            "packets": f"{index_prefix}-packets",
            "anomalies": f"{index_prefix}-anomalies",
        }

        # Configure connection
        if hosts is None:
            hosts = ["http://elasticsearch:9200"]

        self.client = Elasticsearch(
            hosts=hosts,
            api_key=api_key,
            basic_auth=(username, password) if username and password else None,
            verify_certs=False,
            retry_on_timeout=True,
            max_retries=3,
        )

        # Queue for bulk operations
        self.bulk_queue = queue.Queue()
        self.bulk_thread = None
        self.running = False
        self._thread_lock = threading.Lock()

        logger.info(f"Initialized Elasticsearch manager with hosts: {hosts}")

    def start_bulk_processor(self):
        """Start background bulk processing"""
        with self._thread_lock:
            if self.running:
                return

            self.running = True
            self.bulk_thread = threading.Thread(
                target=self._process_bulk_queue, daemon=True, name="elasticsearch_bulk"
            )
            self.bulk_thread.start()
            logger.info("Elasticsearch bulk processor started")

    def stop_bulk_processor(self):
        """Stop background bulk processing"""
        with self._thread_lock:
            self.running = False
            if self.bulk_thread and self.bulk_thread.is_alive():
                self.bulk_thread.join(timeout=5)
            logger.info("Elasticsearch bulk processor stopped")

    def _process_bulk_queue(self):
        """Process bulk operations in background"""
        while self.running or not self.bulk_queue.empty():
            try:
                operations = []
                # Collect up to 100 operations
                while len(operations) < 100 and not self.bulk_queue.empty():
                    try:
                        operations.append(self.bulk_queue.get(timeout=1))
                    except queue.Empty:
                        break

                if operations:
                    success, failed = helpers.bulk(
                        self.client, operations, raise_on_error=False
                    )
                    if failed:
                        logger.error(f"Elasticsearch bulk operation failed: {failed}")
                    else:
                        logger.debug(
                            f"Elasticsearch bulk operation successful: {success} operations"
                        )

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in bulk processing: {e}")
                time.sleep(1)

    def ensure_indices(self):
        """Create indices with proper mappings if they don't exist"""
        for index_name, full_index in self.indices.items():
            try:
                if not self.client.indices.exists(index=full_index):
                    mapping = self._get_index_mapping(index_name)
                    self.client.indices.create(index=full_index, body=mapping)
                    logger.info(f"Created Elasticsearch index: {full_index}")
            except Exception as e:
                logger.error(f"Error creating index {full_index}: {e}")

    def _get_index_mapping(self, index_type: str) -> Dict:
        """Get index mapping for different data types"""
        base_mapping = self._get_base_mapping()
        type_specific_mapping = self._get_type_specific_mapping(index_type)

        if type_specific_mapping:
            base_mapping["mappings"]["properties"].update(type_specific_mapping)

        return base_mapping

    def _get_base_mapping(self) -> Dict:
        """Get base mapping configuration."""
        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "5s",
            },
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "event_type": {"type": "keyword"},
                    "src_ip": {"type": "ip"},
                    "dst_ip": {"type": "ip"},
                    "threat_score": {"type": "float"},
                    "logdata": {"type": "object"},
                    "tags": {"type": "keyword"},
                }
            },
        }

    def _get_type_specific_mapping(self, index_type: str) -> Dict:
        """Get type-specific mapping properties."""
        mappings = {
            "threats": {
                "rule_score": {"type": "float"},
                "ml_score": {"type": "float"},
                "hybrid_score": {"type": "float"},
                "threat_level": {"type": "keyword"},
                "blocked": {"type": "boolean"},
            },
            "packets": {
                "packet_size": {"type": "integer"},
                "protocol": {"type": "keyword"},
                "src_port": {"type": "integer"},
                "dst_port": {"type": "integer"},
                "flow_key": {"type": "keyword"},
            },
            "anomalies": {
                "anomaly_type": {"type": "keyword"},
                "severity": {"type": "keyword"},
                "confidence": {"type": "float"},
                "details": {"type": "text"},
            },
        }

        return mappings.get(index_type, {})

    def index_event(self, event_data: Dict, event_type: str = "events"):
        """Index an event document"""
        try:
            index_name = self.indices.get(event_type, self.indices["events"])

            # Prepare document
            doc = {"@timestamp": datetime.utcnow().isoformat(), **event_data}

            # Add to bulk queue for async processing
            operation = {"_index": index_name, "_source": doc}
            self.bulk_queue.put(operation)

        except Exception as e:
            logger.error(f"Error queuing event for indexing: {e}")

    def search_events(
        self,
        query: Dict,
        index_type: str = "events",
        size: int = 100,
        sort: List = None,
    ) -> Dict:
        """Search events in Elasticsearch"""
        try:
            index_name = self.indices.get(index_type, self.indices["events"])

            search_body = {"query": query, "size": size}

            if sort:
                search_body["sort"] = sort

            response = self.client.search(index=index_name, body=search_body)
            return response

        except Exception as e:
            logger.error(f"Error searching events: {e}")
            return {"error": str(e)}

    def get_statistics(self) -> Dict:
        """Get Elasticsearch statistics"""
        try:
            stats = {}
            for index_type, index_name in self.indices.items():
                try:
                    info = self.client.indices.stats(index=index_name)
                    total = info["indices"][index_name]["total"]
                    stats[index_type] = {
                        "docs_count": total["docs"]["count"],
                        "docs_deleted": total["docs"]["deleted"],
                        "store_size_bytes": total["store"]["size_in_bytes"],
                    }
                except NotFoundError:
                    stats[index_type] = {
                        "docs_count": 0,
                        "docs_deleted": 0,
                        "store_size_bytes": 0,
                    }
                except Exception as e:
                    stats[index_type] = {"error": str(e)}

            return stats

        except Exception as e:
            logger.error(f"Error getting Elasticsearch statistics: {e}")
            return {"error": str(e)}


class InfluxDBManager:
    """Manages InfluxDB operations for time-series metrics"""

    def __init__(
        self,
        url: str = "http://influxdb:8086",
        token: str = "",
        org: str = "netsentinel",
        bucket: str = "netsentinel-metrics",
    ):
        if not INFLUXDB_AVAILABLE:
            raise ImportError("InfluxDB client not available")

        self.url = url
        self.token = token or "netsentinel-token-2024"
        self.org = org
        self.bucket = bucket

        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)

        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()

        # Ensure bucket exists
        self._ensure_bucket()

        logger.info(f"Initialized InfluxDB manager with URL: {url}")

    def _ensure_bucket(self):
        """Ensure the bucket exists"""
        try:
            buckets_api = self.client.buckets_api()
            bucket = buckets_api.find_bucket_by_name(self.bucket)
            if not bucket:
                buckets_api.create_bucket(bucket_name=self.bucket, org=self.org)
                logger.info(f"Created InfluxDB bucket: {self.bucket}")
        except Exception as e:
            logger.error(f"Error ensuring InfluxDB bucket: {e}")

    def write_metric(
        self,
        measurement: str,
        fields: Dict[str, Union[int, float, str, bool]],
        tags: Dict[str, str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Write a metric to InfluxDB"""
        try:
            point = Point(measurement)

            if tags:
                for tag_key, tag_value in tags.items():
                    point.tag(tag_key, str(tag_value))

            for field_key, field_value in fields.items():
                if isinstance(field_value, (int, float)):
                    point.field(field_key, field_value)
                else:
                    point.field(field_key, str(field_value))

            if timestamp:
                point.time(timestamp, WritePrecision.NS)
            else:
                point.time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)

        except Exception as e:
            logger.error(f"Error writing metric to InfluxDB: {e}")

    def write_event_metrics(self, event_data: Dict):
        """Write event-related metrics"""
        try:
            event_type = event_data.get("logtype", 0)
            src_ip = event_data.get("src_host", "unknown")
            threat_score = event_data.get("threat_score", 0)

            # Event count metric
            self.write_metric(
                measurement="netsentinel_events",
                fields={"count": 1, "threat_score": float(threat_score)},
                tags={
                    "event_type": str(event_type),
                    "src_ip": src_ip,
                    "severity": (
                        "high"
                        if threat_score >= 7.0
                        else "medium" if threat_score >= 4.0 else "low"
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Error writing event metrics: {e}")

    def write_packet_metrics(self, packet_stats: Dict):
        """Write packet analysis metrics"""
        try:
            self.write_metric(
                measurement="netsentinel_packet_analysis",
                fields={
                    "total_packets": packet_stats.get("total_packets", 0),
                    "total_bytes": packet_stats.get("total_bytes", 0),
                    "packets_per_second": packet_stats.get("packets_per_second", 0),
                    "active_flows": packet_stats.get("active_flows", 0),
                    "anomalies_detected": packet_stats.get("anomalies_detected", 0),
                },
                tags={"analyzer": "scapy"},
            )

            # Protocol breakdown
            for protocol, count in packet_stats.get("protocol_counts", {}).items():
                self.write_metric(
                    measurement="netsentinel_packet_protocols",
                    fields={"count": count},
                    tags={"protocol": protocol},
                )

        except Exception as e:
            logger.error(f"Error writing packet metrics: {e}")

    def write_threat_intel_metrics(self, threat_stats: Dict):
        """Write threat intelligence metrics"""
        try:
            self.write_metric(
                measurement="netsentinel_threat_intelligence",
                fields={
                    "total_indicators": threat_stats.get("total_indicators", 0),
                    "indicators_processed": threat_stats.get("indicators_processed", 0),
                    "feeds_active": threat_stats.get("feeds_active", 0),
                },
                tags={"source": "multiple_feeds"},
            )

        except Exception as e:
            logger.error(f"Error writing threat intel metrics: {e}")

    def query_metrics(self, flux_query: str) -> List[Dict]:
        """Query metrics using Flux"""
        try:
            result = self.query_api.query(flux_query, org=self.org)
            return result
        except Exception as e:
            logger.error(f"Error querying InfluxDB: {e}")
            return []

    def get_recent_metrics(self, measurement: str, hours: int = 24) -> List[Dict]:
        """Get recent metrics for a measurement"""
        try:
            flux_query = f"""
            from(bucket: "{self.bucket}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "{measurement}")
            |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
            |> yield(name: "mean")
            """

            return self.query_api.query(flux_query, org=self.org)

        except Exception as e:
            logger.error(f"Error getting recent metrics: {e}")
            return []


class EnterpriseDatabaseManager:
    """
    Unified manager for enterprise databases (Elasticsearch + InfluxDB)
    Provides comprehensive data storage and analytics capabilities
    """

    def __init__(self, elasticsearch_config: Dict = None, influxdb_config: Dict = None):
        self.elasticsearch_config = elasticsearch_config or {}
        self.influxdb_config = influxdb_config or {}

        # Initialize database managers
        self.elasticsearch = None
        self.influxdb = None

        # WebSocket integration
        self.event_bus = get_event_bus() if get_event_bus else None

        self._init_databases()

        logger.info("Initialized enterprise database manager")

    def _publish_database_event(self, event_type: str, data: Dict[str, Any]):
        """
        Publish database event via WebSocket

        Args:
            event_type: Type of database event
            data: Event data
        """
        if not self.event_bus:
            return

        try:
            event_data = {
                "type": f"db.{event_type}",
                "data": {
                    "event_type": event_type,
                    "timestamp": time.time(),
                    **data
                }
            }

            event = create_event(f"db.{event_type}", event_data)
            self.event_bus.publish(event)

            logger.debug(f"Published database event: {event_type}")

        except Exception as e:
            logger.warning(f"Failed to publish database event {event_type}: {e}")

    def store_event(self, event_data: Dict[str, Any], event_type: str = "events") -> bool:
        """
        Store an event and publish WebSocket notification

        Args:
            event_data: Event data to store
            event_type: Type of event

        Returns:
            bool: Success status
        """
        try:
            # Store in Elasticsearch
            if self.elasticsearch:
                self.elasticsearch.index_event(event_data, event_type)

            # Store in InfluxDB if it's a metric
            if self.influxdb and event_type == "metrics":
                self.influxdb.write_metric(event_data)

            # Publish WebSocket event
            self._publish_database_event("event_stored", {
                "event_type": event_type,
                "event_data": event_data
            })

            return True

        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            return False

    def _init_databases(self):
        """Initialize database connections"""
        # Initialize Elasticsearch
        if ELASTICSEARCH_AVAILABLE:
            try:
                self.elasticsearch = ElasticsearchManager(**self.elasticsearch_config)
                self.elasticsearch.ensure_indices()
                self.elasticsearch.start_bulk_processor()
                logger.info("Elasticsearch initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Elasticsearch: {e}")
                self.elasticsearch = None

        # Initialize InfluxDB
        if INFLUXDB_AVAILABLE:
            try:
                self.influxdb = InfluxDBManager(**self.influxdb_config)
                logger.info("InfluxDB initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize InfluxDB: {e}")
                self.influxdb = None

    def store_event(self, event_data: Dict, event_type: str = "events"):
        """Store event in appropriate databases"""
        try:
            # Store in Elasticsearch for document search
            if self.elasticsearch:
                self.elasticsearch.index_event(event_data, event_type)

            # Store metrics in InfluxDB
            if self.influxdb:
                self.influxdb.write_event_metrics(event_data)

        except Exception as e:
            logger.error(f"Error storing event: {e}")

    def store_packet_data(self, packet_info: Dict):
        """Store packet analysis data"""
        try:
            # Store packet details in Elasticsearch
            if self.elasticsearch:
                self.elasticsearch.index_event(packet_info, "packets")

        except Exception as e:
            logger.error(f"Error storing packet data: {e}")

    def store_anomaly(self, anomaly_data: Dict):
        """Store anomaly detection results"""
        try:
            # Store anomaly in Elasticsearch
            if self.elasticsearch:
                self.elasticsearch.index_event(anomaly_data, "anomalies")

        except Exception as e:
            logger.error(f"Error storing anomaly: {e}")

    def update_packet_metrics(self, packet_stats: Dict):
        """Update packet analysis metrics"""
        try:
            if self.influxdb:
                self.influxdb.write_packet_metrics(packet_stats)

        except Exception as e:
            logger.error(f"Error updating packet metrics: {e}")

    def update_threat_intel_metrics(self, threat_stats: Dict):
        """Update threat intelligence metrics"""
        try:
            if self.influxdb:
                self.influxdb.write_threat_intel_metrics(threat_stats)

        except Exception as e:
            logger.error(f"Error updating threat intel metrics: {e}")

    def search_events(
        self, query: Dict, index_type: str = "events", size: int = 100
    ) -> Dict:
        """Search events in Elasticsearch"""
        if self.elasticsearch:
            return self.elasticsearch.search_events(query, index_type, size)
        return {"error": "Elasticsearch not available"}

    def get_metrics(self, measurement: str, hours: int = 24) -> List[Dict]:
        """Get metrics from InfluxDB"""
        if self.influxdb:
            return self.influxdb.get_recent_metrics(measurement, hours)
        return []

    def get_statistics(self) -> Dict:
        """Get comprehensive database statistics"""
        stats = {"elasticsearch": {}, "influxdb": {}, "overall_health": "degraded"}

        # Elasticsearch stats
        if self.elasticsearch:
            try:
                stats["elasticsearch"] = self.elasticsearch.get_statistics()
            except Exception as e:
                stats["elasticsearch"] = {"error": str(e)}

        # InfluxDB health check
        if self.influxdb:
            try:
                # Simple health check - try to query recent data
                result = self.influxdb.query_metrics(
                    f"""
                from(bucket: "{self.influxdb.bucket}")
                |> range(start: -1h)
                |> limit(n: 1)
                """
                )
                stats["influxdb"] = {
                    "status": "healthy",
                    "bucket": self.influxdb.bucket,
                    "recent_records": len(result) if result else 0,
                }
            except Exception as e:
                stats["influxdb"] = {"status": "error", "error": str(e)}

        # Overall health assessment
        es_healthy = bool(
            self.elasticsearch and not stats["elasticsearch"].get("error")
        )
        influx_healthy = bool(
            self.influxdb and stats["influxdb"].get("status") == "healthy"
        )

        if es_healthy and influx_healthy:
            stats["overall_health"] = "healthy"
        elif es_healthy or influx_healthy:
            stats["overall_health"] = "partial"

        return stats

    def shutdown(self):
        """Shutdown database connections"""
        if self.elasticsearch:
            self.elasticsearch.stop_bulk_processor()

        if self.influxdb:
            self.influxdb.client.close()

        logger.info("Enterprise database manager shutdown complete")


# Global enterprise database manager instance
enterprise_db = None
_enterprise_db_lock = threading.Lock()


def get_enterprise_db() -> EnterpriseDatabaseManager:
    """Get or create global enterprise database manager instance"""
    global enterprise_db
    if enterprise_db is None:
        with _enterprise_db_lock:
            if enterprise_db is None:  # Double-check locking
                enterprise_db = EnterpriseDatabaseManager()
    return enterprise_db


def store_security_event(event_data: Dict, event_type: str = "events"):
    """Convenience function to store security events"""
    db = get_enterprise_db()
    db.store_event(event_data, event_type)


def search_security_events(
    query: Dict, event_type: str = "events", size: int = 100
) -> Dict:
    """Convenience function to search security events"""
    db = get_enterprise_db()
    return db.search_events(query, event_type, size)
