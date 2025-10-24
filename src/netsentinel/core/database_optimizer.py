#!/usr/bin/env python3
"""
Database Query Optimizer for NetSentinel
Implements query optimization for Elasticsearch and InfluxDB
Designed for maintainability and preventing code debt
"""

import asyncio
import time
import threading
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque
import re

from .exceptions import NetSentinelException, ProcessingError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("database_optimizer", level="INFO")
structured_logger = get_structured_logger("database_optimizer")


class DatabaseType(Enum):
    """Database type enumeration"""

    ELASTICSEARCH = "elasticsearch"
    INFLUXDB = "influxdb"
    REDIS = "redis"


class QueryType(Enum):
    """Query type enumeration"""

    SEARCH = "search"
    AGGREGATION = "aggregation"
    TIME_SERIES = "time_series"
    COUNT = "count"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class QueryOptimizationConfig:
    """Query optimization configuration"""

    max_query_time: int = 30  # seconds
    max_results: int = 10000
    enable_caching: bool = True
    cache_ttl: int = 300  # 5 minutes
    enable_indexing: bool = True
    batch_size: int = 1000
    connection_pool_size: int = 10


@dataclass
class QueryMetrics:
    """Query performance metrics"""

    query_id: str
    database: DatabaseType
    query_type: QueryType
    execution_time: float
    result_count: int
    cache_hit: bool = False
    index_used: bool = False
    optimization_applied: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query_id": self.query_id,
            "database": self.database.value,
            "query_type": self.query_type.value,
            "execution_time": self.execution_time,
            "result_count": self.result_count,
            "cache_hit": self.cache_hit,
            "index_used": self.index_used,
            "optimization_applied": self.optimization_applied,
        }


class ElasticsearchOptimizer:
    """Elasticsearch query optimizer"""

    def __init__(self, config: QueryOptimizationConfig):
        self.config = config
        self._lock = threading.RLock()
        self.query_cache: Dict[str, Any] = {}
        self.index_stats: Dict[str, Dict[str, Any]] = {}

        # Statistics
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_execution_time": 0.0,
            "optimizations_applied": 0,
        }

    def optimize_search_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize Elasticsearch search query"""
        try:
            optimized_query = query.copy()
            optimizations = []

            # Add size limit if not present
            if "size" not in optimized_query:
                optimized_query["size"] = min(self.config.max_results, 1000)
                optimizations.append("added_size_limit")

            # Optimize bool queries
            if "query" in optimized_query and "bool" in optimized_query["query"]:
                optimized_query["query"]["bool"] = self._optimize_bool_query(
                    optimized_query["query"]["bool"]
                )
                optimizations.append("optimized_bool_query")

            # Add timeout
            if "timeout" not in optimized_query:
                optimized_query["timeout"] = f"{self.config.max_query_time}s"
                optimizations.append("added_timeout")

            # Optimize aggregations
            if "aggs" in optimized_query:
                optimized_query["aggs"] = self._optimize_aggregations(
                    optimized_query["aggs"]
                )
                optimizations.append("optimized_aggregations")

            # Add source filtering
            if "source" not in optimized_query:
                optimized_query["source"] = True
                optimizations.append("added_source_filtering")

            logger.info(
                f"Optimized Elasticsearch query with {len(optimizations)} optimizations"
            )
            return optimized_query

        except Exception as e:
            logger.error(f"Elasticsearch query optimization failed: {e}")
            return query

    def _optimize_bool_query(self, bool_query: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize bool query"""
        optimized = bool_query.copy()

        # Optimize must clauses
        if "must" in optimized:
            optimized["must"] = self._optimize_clauses(optimized["must"])

        # Optimize should clauses
        if "should" in optimized:
            optimized["should"] = self._optimize_clauses(optimized["should"])

        # Optimize filter clauses
        if "filter" in optimized:
            optimized["filter"] = self._optimize_clauses(optimized["filter"])

        return optimized

    def _optimize_clauses(self, clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize query clauses"""
        optimized_clauses = []

        for clause in clauses:
            if "term" in clause:
                # Optimize term queries
                optimized_clauses.append(self._optimize_term_query(clause))
            elif "range" in clause:
                # Optimize range queries
                optimized_clauses.append(self._optimize_range_query(clause))
            elif "match" in clause:
                # Optimize match queries
                optimized_clauses.append(self._optimize_match_query(clause))
            else:
                optimized_clauses.append(clause)

        return optimized_clauses

    def _optimize_term_query(self, clause: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize term query"""
        optimized = clause.copy()

        # Add case_insensitive if not present
        if "case_insensitive" not in optimized["term"]:
            optimized["term"][list(optimized["term"].keys())[0]][
                "case_insensitive"
            ] = True

        return optimized

    def _optimize_range_query(self, clause: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize range query"""
        optimized = clause.copy()

        # Add format for date ranges
        field_name = list(optimized["range"].keys())[0]
        field_config = optimized["range"][field_name]

        if "gte" in field_config or "lte" in field_config:
            if "format" not in field_config:
                field_config["format"] = "strict_date_optional_time"

        return optimized

    def _optimize_match_query(self, clause: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize match query"""
        optimized = clause.copy()

        # Add fuzziness for better matching
        if "fuzziness" not in optimized["match"]:
            optimized["match"][list(optimized["match"].keys())[0]]["fuzziness"] = "AUTO"

        return optimized

    def _optimize_aggregations(self, aggs: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize aggregations"""
        optimized = aggs.copy()

        for agg_name, agg_config in optimized.items():
            if "terms" in agg_config:
                # Optimize terms aggregation
                if "size" not in agg_config["terms"]:
                    agg_config["terms"]["size"] = 100
                if "min_doc_count" not in agg_config["terms"]:
                    agg_config["terms"]["min_doc_count"] = 1

            elif "date_histogram" in agg_config:
                # Optimize date histogram
                if "min_doc_count" not in agg_config["date_histogram"]:
                    agg_config["date_histogram"]["min_doc_count"] = 1

            elif "cardinality" in agg_config:
                # Optimize cardinality aggregation
                if "precision_threshold" not in agg_config["cardinality"]:
                    agg_config["cardinality"]["precision_threshold"] = 1000

        return optimized

    def create_index_optimization(
        self, index_name: str, mapping: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create optimized index mapping"""
        try:
            optimized_mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "refresh_interval": "30s",
                    "index": {
                        "max_result_window": self.config.max_results,
                        "query": {"default_field": "content"},
                    },
                },
                "mappings": mapping,
            }

            # Add field mappings for common fields
            if "properties" in mapping:
                for field_name, field_config in mapping["properties"].items():
                    if field_name in ["timestamp", "created_at", "updated_at"]:
                        field_config["type"] = "date"
                        field_config["format"] = "strict_date_optional_time"
                    elif field_name in ["ip_address", "source_ip", "dest_ip"]:
                        field_config["type"] = "ip"
                    elif field_name in ["severity", "level"]:
                        field_config["type"] = "keyword"
                    elif field_name in ["message", "description"]:
                        field_config["type"] = "text"
                        field_config["analyzer"] = "standard"

            logger.info(f"Created optimized index mapping for {index_name}")
            return optimized_mapping

        except Exception as e:
            logger.error(f"Index optimization failed: {e}")
            return mapping

    def get_query_statistics(self) -> Dict[str, Any]:
        """Get query statistics"""
        with self._lock:
            cache_hit_rate = 0
            if self.stats["total_queries"] > 0:
                cache_hit_rate = self.stats["cache_hits"] / self.stats["total_queries"]

            return {
                "database": "elasticsearch",
                "total_queries": self.stats["total_queries"],
                "cache_hit_rate": cache_hit_rate,
                "average_execution_time": self.stats["average_execution_time"],
                "optimizations_applied": self.stats["optimizations_applied"],
            }


class InfluxDBOptimizer:
    """InfluxDB query optimizer"""

    def __init__(self, config: QueryOptimizationConfig):
        self.config = config
        self._lock = threading.RLock()
        self.query_cache: Dict[str, Any] = {}

        # Statistics
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_execution_time": 0.0,
            "optimizations_applied": 0,
        }

    def optimize_query(self, query: str) -> str:
        """Optimize InfluxDB query"""
        try:
            optimized_query = query.strip()
            optimizations = []

            # Add LIMIT if not present
            if "LIMIT" not in optimized_query.upper():
                optimized_query += f" LIMIT {self.config.max_results}"
                optimizations.append("added_limit")

            # Optimize time range queries
            if "WHERE" in optimized_query.upper():
                optimized_query = self._optimize_time_range(optimized_query)
                optimizations.append("optimized_time_range")

            # Optimize GROUP BY clauses
            if "GROUP BY" in optimized_query.upper():
                optimized_query = self._optimize_group_by(optimized_query)
                optimizations.append("optimized_group_by")

            # Add timezone if not present
            if "tz(" not in optimized_query.lower():
                optimized_query = self._add_timezone(optimized_query)
                optimizations.append("added_timezone")

            logger.info(
                f"Optimized InfluxDB query with {len(optimizations)} optimizations"
            )
            return optimized_query

        except Exception as e:
            logger.error(f"InfluxDB query optimization failed: {e}")
            return query

    def _optimize_time_range(self, query: str) -> str:
        """Optimize time range in query"""
        # Add time range optimization
        if "time >=" in query.lower():
            # Already has time range
            return query

        # Add default time range if none exists
        if "WHERE" in query.upper():
            query = query.replace("WHERE", "WHERE time >= now() - 1h AND")
        else:
            query += " WHERE time >= now() - 1h"

        return query

    def _optimize_group_by(self, query: str) -> str:
        """Optimize GROUP BY clause"""
        # Add time() function to GROUP BY if not present
        if "GROUP BY" in query.upper() and "time(" not in query.lower():
            group_by_match = re.search(r"GROUP BY\s+([^,\s]+)", query, re.IGNORECASE)
            if group_by_match:
                group_by_field = group_by_match.group(1)
                query = query.replace(
                    f"GROUP BY {group_by_field}", f"GROUP BY time(1m), {group_by_field}"
                )

        return query

    def _add_timezone(self, query: str) -> str:
        """Add timezone to query"""
        # Add timezone function if not present
        if "tz(" not in query.lower():
            query = query.replace("time", "tz(time, 'UTC')")

        return query

    def create_retention_policy(self, database: str, duration: str = "30d") -> str:
        """Create retention policy"""
        return f"""
        CREATE RETENTION POLICY "default" ON "{database}" 
        DURATION {duration} 
        REPLICATION 1 
        DEFAULT
        """

    def create_continuous_query(self, name: str, database: str, query: str) -> str:
        """Create continuous query"""
        return f"""
        CREATE CONTINUOUS QUERY "{name}" ON "{database}" 
        BEGIN 
            {query} 
        END
        """

    def get_query_statistics(self) -> Dict[str, Any]:
        """Get query statistics"""
        with self._lock:
            cache_hit_rate = 0
            if self.stats["total_queries"] > 0:
                cache_hit_rate = self.stats["cache_hits"] / self.stats["total_queries"]

            return {
                "database": "influxdb",
                "total_queries": self.stats["total_queries"],
                "cache_hit_rate": cache_hit_rate,
                "average_execution_time": self.stats["average_execution_time"],
                "optimizations_applied": self.stats["optimizations_applied"],
            }


class QueryCache:
    """Query result cache"""

    def __init__(self, config: QueryOptimizationConfig):
        self.config = config
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None

    def get_cached_result(self, query_hash: str) -> Optional[Any]:
        """Get cached query result"""
        with self._lock:
            if query_hash in self.cache:
                cached_data = self.cache[query_hash]
                if time.time() - cached_data["timestamp"] < self.config.cache_ttl:
                    return cached_data["result"]
                else:
                    # Remove expired cache entry
                    del self.cache[query_hash]
            return None

    def cache_result(self, query_hash: str, result: Any) -> None:
        """Cache query result"""
        with self._lock:
            self.cache[query_hash] = {"result": result, "timestamp": time.time()}

    def clear_cache(self) -> None:
        """Clear query cache"""
        with self._lock:
            self.cache.clear()

    async def cleanup_expired_cache(self) -> None:
        """Cleanup expired cache entries"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, data in self.cache.items()
                if current_time - data["timestamp"] > self.config.cache_ttl
            ]

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

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
                await asyncio.sleep(300)  # 5 minutes
                await self.cleanup_expired_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "cache_size": len(self.cache),
                "cache_ttl": self.config.cache_ttl,
                "cache_enabled": self.config.enable_caching,
            }


class DatabaseOptimizer:
    """Main database optimizer"""

    def __init__(self, config: Optional[QueryOptimizationConfig] = None):
        self.config = config or QueryOptimizationConfig()
        self.elasticsearch_optimizer = ElasticsearchOptimizer(self.config)
        self.influxdb_optimizer = InfluxDBOptimizer(self.config)
        self.query_cache = QueryCache(self.config)
        self._lock = threading.RLock()

    def optimize_query(
        self,
        database: DatabaseType,
        query: Union[str, Dict[str, Any]],
        query_type: QueryType = QueryType.SEARCH,
    ) -> Union[str, Dict[str, Any]]:
        """Optimize database query"""
        try:
            if database == DatabaseType.ELASTICSEARCH:
                if isinstance(query, dict):
                    return self.elasticsearch_optimizer.optimize_search_query(query)
                else:
                    raise ValueError("Elasticsearch queries must be dictionaries")

            elif database == DatabaseType.INFLUXDB:
                if isinstance(query, str):
                    return self.influxdb_optimizer.optimize_query(query)
                else:
                    raise ValueError("InfluxDB queries must be strings")

            else:
                raise ValueError(f"Unsupported database type: {database}")

        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            return query

    def create_optimized_index(
        self,
        database: DatabaseType,
        index_name: str,
        mapping: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create optimized database index"""
        try:
            if database == DatabaseType.ELASTICSEARCH:
                return self.elasticsearch_optimizer.create_index_optimization(
                    index_name, mapping or {}
                )
            else:
                raise ValueError(f"Index creation not supported for {database}")

        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            return {}

    async def start(self) -> None:
        """Start database optimizer"""
        if self.config.enable_caching:
            await self.query_cache.start_cleanup_task()
        logger.info("Started database optimizer")

    async def stop(self) -> None:
        """Stop database optimizer"""
        if self.config.enable_caching:
            await self.query_cache.stop_cleanup_task()
        logger.info("Stopped database optimizer")

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        return {
            "config": {
                "max_query_time": self.config.max_query_time,
                "max_results": self.config.max_results,
                "enable_caching": self.config.enable_caching,
                "cache_ttl": self.config.cache_ttl,
            },
            "elasticsearch": self.elasticsearch_optimizer.get_query_statistics(),
            "influxdb": self.influxdb_optimizer.get_query_statistics(),
            "cache": self.query_cache.get_cache_statistics(),
        }


# Global database optimizer
_database_optimizer: Optional[DatabaseOptimizer] = None


def get_database_optimizer() -> DatabaseOptimizer:
    """Get global database optimizer"""
    global _database_optimizer
    if _database_optimizer is None:
        _database_optimizer = DatabaseOptimizer()
    return _database_optimizer
