#!/usr/bin/env python3
"""
REST API Server for NetSentinel Event Processor
Provides HTTP endpoints for health checks, threat intelligence, and metrics
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

try:
    from ..core.base import BaseComponent
    from ..core.models import StandardEvent, ThreatLevel
    from ..core.error_handler import handle_errors, create_error_context
    from ..monitoring.metrics import MetricsCollector, get_metrics_collector
    from ..monitoring.logger import create_logger
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from core.models import StandardEvent, ThreatLevel
    from core.error_handler import handle_errors, create_error_context
    from monitoring.metrics import MetricsCollector, get_metrics_collector
    from monitoring.logger import create_logger

logger = create_logger("api_server", level="INFO")


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = Field(..., description="Service health status")
    timestamp: float = Field(..., description="Current timestamp")
    uptime: float = Field(..., description="Service uptime in seconds")
    version: str = Field(default="1.0.0", description="API version")


class ThreatInfo(BaseModel):
    """Threat information model"""

    source_ip: str = Field(..., description="Source IP address")
    threat_score: float = Field(..., description="Calculated threat score")
    threat_level: str = Field(..., description="Threat level classification")
    event_count: int = Field(..., description="Number of related events")
    last_seen: float = Field(..., description="Last event timestamp")
    indicators: List[str] = Field(default_factory=list, description="Threat indicators")


class ThreatResponse(BaseModel):
    """Threat intelligence response model"""

    total_threats: int = Field(..., description="Total number of tracked threats")
    threats: Dict[str, ThreatInfo] = Field(
        default_factory=dict, description="Threat details by IP"
    )


class APIServer(BaseComponent):
    """
    REST API server for the NetSentinel event processor
    Provides HTTP endpoints for monitoring and threat intelligence
    """

    def __init__(
        self,
        name: str = "api_server",
        host: str = "0.0.0.0",
        port: int = 8082,
        processor=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, config, logger)

        self.host = host
        self.port = port
        self.processor = processor
        self.start_time = time.time()

        # Initialize FastAPI app
        self.app = FastAPI(
            title="NetSentinel Event Processor API",
            description="REST API for NetSentinel threat detection and monitoring",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        # Use processor's metrics collector if available, otherwise create our own
        if processor and hasattr(processor, "metrics_collector"):
            self.metrics_collector = processor.metrics_collector
        else:
            self.metrics_collector = get_metrics_collector()

        # Setup routes
        self._setup_routes()

        # Server instance (will be set during startup)
        self.server = None

    def _setup_routes(self):
        """Setup FastAPI routes"""

        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint"""
            try:
                # Check component health
                is_healthy = self.is_healthy()
                if not is_healthy:
                    raise HTTPException(status_code=503, detail="Service unhealthy")

                # Check processor health if available
                processor_healthy = True
                if self.processor and hasattr(self.processor, "is_healthy"):
                    processor_healthy = self.processor.is_healthy()

                if not processor_healthy:
                    raise HTTPException(
                        status_code=503, detail="Event processor unhealthy"
                    )

                return HealthResponse(
                    status="healthy",
                    timestamp=time.time(),
                    uptime=time.time() - self.start_time,
                    version="1.0.0",
                )

            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(
                    status_code=503, detail=f"Health check failed: {str(e)}"
                )

        @self.app.get("/threats", response_model=ThreatResponse)
        async def get_threats(
            min_score: float = Query(
                0.0, description="Minimum threat score to include"
            ),
            limit: int = Query(100, description="Maximum number of threats to return"),
        ):
            """Get threat intelligence data"""
            try:
                if not self.processor:
                    raise HTTPException(
                        status_code=503, detail="Event processor not available"
                    )

                # Get threat data from processor
                threat_data = await self._get_threat_intelligence(min_score, limit)

                return ThreatResponse(
                    total_threats=len(threat_data), threats=threat_data
                )

            except Exception as e:
                logger.error(f"Failed to get threat data: {e}")
                context = create_error_context("get_threats", "api_server")
                handle_errors(e, context)
                raise HTTPException(
                    status_code=500, detail=f"Failed to get threat data: {str(e)}"
                )

        @self.app.get("/threats/{ip_address}", response_model=ThreatInfo)
        async def get_threat_by_ip(ip_address: str):
            """Get threat information for specific IP address"""
            try:
                if not self.processor:
                    raise HTTPException(
                        status_code=503, detail="Event processor not available"
                    )

                threat_info = await self._get_threat_by_ip(ip_address)
                if not threat_info:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No threat data found for IP: {ip_address}",
                    )

                return threat_info

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get threat data for IP {ip_address}: {e}")
                context = create_error_context(
                    "get_threat_by_ip", "api_server", additional_data={"ip": ip_address}
                )
                handle_errors(e, context)
                raise HTTPException(
                    status_code=500, detail=f"Failed to get threat data: {str(e)}"
                )

        @self.app.get("/metrics")
        async def get_metrics():
            """Get Prometheus-compatible metrics"""
            try:
                # Get metrics from collector
                metrics_data = self.metrics_collector.get_prometheus_metrics()

                # Add custom API metrics
                custom_metrics = f"""# NetSentinel API Server Metrics
netsentinel_api_uptime_seconds{{service="api_server"}} {time.time() - self.start_time}
netsentinel_api_requests_total{{service="api_server", endpoint="health"}} 1
netsentinel_api_requests_total{{service="api_server", endpoint="threats"}} 1
"""

                return JSONResponse(
                    content={"metrics": metrics_data + custom_metrics},
                    media_type="text/plain",
                )

            except Exception as e:
                logger.error(f"Failed to get metrics: {e}")
                context = create_error_context("get_metrics", "api_server")
                handle_errors(e, context)
                raise HTTPException(
                    status_code=500, detail=f"Failed to get metrics: {str(e)}"
                )

        @self.app.get("/status")
        async def get_status():
            """Get detailed system status"""
            try:
                status = {
                    "api_server": {
                        "status": "healthy" if self.is_healthy() else "unhealthy",
                        "uptime": time.time() - self.start_time,
                        "host": self.host,
                        "port": self.port,
                    },
                    "event_processor": {"status": "unknown"},
                    "components": {},
                }

                # Add processor status if available
                if self.processor:
                    if hasattr(self.processor, "is_healthy"):
                        status["event_processor"]["status"] = (
                            "healthy" if self.processor.is_healthy() else "unhealthy"
                        )

                    if hasattr(self.processor, "get_metrics"):
                        status["event_processor"][
                            "metrics"
                        ] = self.processor.get_metrics()

                # Add component information
                if hasattr(self, "_dependencies"):
                    for dep in self._dependencies:
                        status["components"][dep.name] = {
                            "status": "healthy" if dep.is_healthy() else "unhealthy"
                        }

                return status

            except Exception as e:
                logger.error(f"Failed to get status: {e}")
                context = create_error_context("get_status", "api_server")
                handle_errors(e, context)
                raise HTTPException(
                    status_code=500, detail=f"Failed to get status: {str(e)}"
                )

    async def _get_threat_intelligence(
        self, min_score: float = 0.0, limit: int = 100
    ) -> Dict[str, ThreatInfo]:
        """Get threat intelligence data from processor"""
        try:
            if (
                not self.processor
                or not hasattr(self.processor, "threat_storage")
                or not self.processor.threat_storage
            ):
                return {}

            # Get threats from storage
            threat_records = await self.processor.threat_storage.get_all_threats(
                min_score, limit
            )

            # Convert to API format
            threats = {}
            for record in threat_records:
                threats[record.ip_address] = ThreatInfo(
                    source_ip=record.ip_address,
                    threat_score=record.threat_score,
                    threat_level=record.threat_level.value,
                    event_count=record.event_count,
                    last_seen=record.last_seen,
                    indicators=record.indicators,
                )

            return threats

        except Exception as e:
            logger.error(f"Error getting threat intelligence: {e}")
            return {}

    async def _get_threat_by_ip(self, ip_address: str) -> Optional[ThreatInfo]:
        """Get threat information for specific IP"""
        try:
            if (
                not self.processor
                or not hasattr(self.processor, "threat_storage")
                or not self.processor.threat_storage
            ):
                return None

            # Get threat record from storage
            threat_record = await self.processor.threat_storage.get_threat(ip_address)

            if not threat_record:
                return None

            # Convert to API format
            return ThreatInfo(
                source_ip=threat_record.ip_address,
                threat_score=threat_record.threat_score,
                threat_level=threat_record.threat_level.value,
                event_count=threat_record.event_count,
                last_seen=threat_record.last_seen,
                indicators=threat_record.indicators,
            )

        except Exception as e:
            logger.error(f"Error getting threat for IP {ip_address}: {e}")
            return None

        @self.app.get("/correlations/{ip_address}")
        async def get_correlations_by_ip(
            ip_address: str,
            limit: int = Query(
                10, description="Maximum number of correlations to return"
            ),
        ):
            """Get correlation data for specific IP address"""
            try:
                if (
                    not self.processor
                    or not hasattr(self.processor, "threat_storage")
                    or not self.processor.threat_storage
                ):
                    raise HTTPException(
                        status_code=503, detail="Threat storage not available"
                    )

                # Get correlation data
                correlations = await self.processor.threat_storage.get_correlations(
                    ip_address
                )

                # Convert to API format
                correlation_data = []
                for corr in correlations[-limit:]:  # Limit results
                    correlation_data.append(
                        {
                            "correlation_score": corr.correlation_score,
                            "pattern_detected": corr.pattern_detected,
                            "created_at": corr.created_at,
                            "expires_at": corr.expires_at,
                            "event_count": len(corr.events),
                            "events": corr.events[-5:],  # Last 5 events for brevity
                        }
                    )

                return {"ip_address": ip_address, "correlations": correlation_data}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting correlations for IP {ip_address}: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to get correlations: {str(e)}"
                )

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize API server resources"""
        logger.info(f"Initializing API server on {self.host}:{self.port}")
        # Already done in __init__

    async def _start_internal(self):
        """Start the API server"""
        try:
            # Create server configuration
            config = uvicorn.Config(
                app=self.app, host=self.host, port=self.port, log_level="info"
            )

            # Create and start server
            self.server = uvicorn.Server(config)

            # Start server in background task
            asyncio.create_task(self.server.serve())

            logger.info(f"API server started on http://{self.host}:{self.port}")
            logger.info(
                f"API documentation available at http://{self.host}:{self.port}/docs"
            )

        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            context = create_error_context("start_api_server", "api_server")
            handle_errors(e, context)
            raise

    async def _stop_internal(self):
        """Stop the API server"""
        try:
            if self.server:
                await self.server.shutdown()
                logger.info("API server stopped")
        except Exception as e:
            logger.error(f"Error stopping API server: {e}")
            context = create_error_context("stop_api_server", "api_server")
            handle_errors(e, context)

    async def _cleanup(self):
        """Cleanup API server resources"""
        # Server shutdown is handled in _stop_internal
        pass


# Factory function for creating API server
def create_api_server(
    processor=None, host: str = "0.0.0.0", port: int = 8082
) -> APIServer:
    """Create and configure API server instance"""
    return APIServer(name="api_server", host=host, port=port, processor=processor)
