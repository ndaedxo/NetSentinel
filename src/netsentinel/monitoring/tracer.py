#!/usr/bin/env python3
"""
Distributed Tracing Implementation for NetSentinel
Uses OpenTelemetry for request tracking across services
"""

import time
import uuid
import threading
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from contextvars import ContextVar

# OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.context import Context
    from opentelemetry.propagate import extract, inject
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.kafka import KafkaInstrumentor

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

    # Fallback implementations
    class Status:
        OK = "OK"
        ERROR = "ERROR"

    class StatusCode:
        OK = 1
        ERROR = 2


from ..core.exceptions import NetSentinelException
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("tracer", level="INFO")
structured_logger = get_structured_logger("tracer")


class TraceContext:
    """Trace context for request correlation"""

    def __init__(
        self, trace_id: str, span_id: str, parent_span_id: Optional[str] = None
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.baggage: Dict[str, str] = {}

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for serialization"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id or "",
            "baggage": json.dumps(self.baggage),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "TraceContext":
        """Create from dictionary"""
        context = cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id") or None,
        )
        if data.get("baggage"):
            context.baggage = json.loads(data["baggage"])
        return context


class SpanKind(Enum):
    """Span kind enumeration"""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class Span:
    """Span representation"""

    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    kind: SpanKind
    start_time: float
    end_time: Optional[float] = None
    status: str = Status.OK
    status_code: int = StatusCode.OK
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Get span duration in seconds"""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def add_attribute(self, key: str, value: Any) -> None:
        """Add attribute to span"""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to span"""
        event = {"name": name, "timestamp": time.time(), "attributes": attributes or {}}
        self.events.append(event)

    def set_status(self, status: str, status_code: int) -> None:
        """Set span status"""
        self.status = status
        self.status_code = status_code

    def finish(self) -> None:
        """Finish span"""
        self.end_time = time.time()


class TraceExporter:
    """Base trace exporter"""

    def export(self, spans: List[Span]) -> None:
        """Export spans"""
        pass


class ConsoleTraceExporter(TraceExporter):
    """Console trace exporter for development"""

    def export(self, spans: List[Span]) -> None:
        """Export spans to console"""
        import logging

        logger = logging.getLogger(__name__)
        for span in spans:
            logger.debug(f"Span: {span.name}")
            logger.debug(f"  Trace ID: {span.trace_id}")
            logger.debug(f"  Span ID: {span.span_id}")
            logger.debug(f"  Duration: {span.duration:.3f}s")
            logger.debug(f"  Status: {span.status}")
            if span.attributes:
                logger.debug(f"  Attributes: {span.attributes}")
            logger.debug("")


class FileTraceExporter(TraceExporter):
    """File trace exporter"""

    def __init__(self, filename: str = "traces.json"):
        self.filename = filename

    def export(self, spans: List[Span]) -> None:
        """Export spans to file"""
        with open(self.filename, "a") as f:
            for span in spans:
                trace_data = {
                    "name": span.name,
                    "trace_id": span.trace_id,
                    "span_id": span.span_id,
                    "parent_span_id": span.parent_span_id,
                    "kind": span.kind.value,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "duration": span.duration,
                    "status": span.status,
                    "status_code": span.status_code,
                    "attributes": span.attributes,
                    "events": span.events,
                }
                f.write(json.dumps(trace_data) + "\n")


class JaegerTraceExporter(TraceExporter):
    """Jaeger trace exporter"""

    def __init__(self, endpoint: str = "http://localhost:14268/api/traces"):
        self.endpoint = endpoint
        if OPENTELEMETRY_AVAILABLE:
            self.exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
                collector_endpoint=endpoint,
            )
        else:
            self.exporter = None

    def export(self, spans: List[Span]) -> None:
        """Export spans to Jaeger"""
        if self.exporter:
            # Convert spans to OpenTelemetry format
            # This is a simplified implementation
            pass


class TraceManager:
    """Main trace manager"""

    def __init__(
        self,
        service_name: str = "netsentinel",
        exporter: Optional[TraceExporter] = None,
    ):
        self.service_name = service_name
        self.exporter = exporter or ConsoleTraceExporter()
        self.spans: Dict[str, Span] = {}
        self._lock = threading.RLock()

        # Initialize OpenTelemetry if available
        if OPENTELEMETRY_AVAILABLE:
            self._setup_opentelemetry()
        else:
            logger.warning("OpenTelemetry not available, using fallback tracing")

    def _setup_opentelemetry(self):
        """Setup OpenTelemetry"""
        try:
            # Create resource
            resource = Resource.create(
                {"service.name": self.service_name, "service.version": "1.0.0"}
            )

            # Create tracer provider
            tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(tracer_provider)

            # Add span processor
            span_processor = BatchSpanProcessor(self.exporter)
            tracer_provider.add_span_processor(span_processor)

            # Instrument libraries
            RequestsInstrumentor().instrument()
            FlaskInstrumentor().instrument()
            RedisInstrumentor().instrument()
            KafkaInstrumentor().instrument()

            logger.info("OpenTelemetry setup complete")
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry: {e}")

    def start_span(
        self,
        name: str,
        parent_span_id: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span"""
        with self._lock:
            span_id = str(uuid.uuid4())
            trace_id = parent_span_id or str(uuid.uuid4())

            span = Span(
                name=name,
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                kind=kind,
                start_time=time.time(),
                attributes=attributes or {},
            )

            self.spans[span_id] = span
            return span

    def finish_span(
        self, span_id: str, status: str = Status.OK, status_code: int = StatusCode.OK
    ) -> None:
        """Finish a span"""
        with self._lock:
            if span_id in self.spans:
                span = self.spans[span_id]
                span.finish()
                span.set_status(status, status_code)

                # Export span
                self.exporter.export([span])

                # Remove from active spans
                del self.spans[span_id]

    def add_span_attribute(self, span_id: str, key: str, value: Any) -> None:
        """Add attribute to span"""
        with self._lock:
            if span_id in self.spans:
                self.spans[span_id].add_attribute(key, value)

    def add_span_event(
        self, span_id: str, name: str, attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add event to span"""
        with self._lock:
            if span_id in self.spans:
                self.spans[span_id].add_event(name, attributes)

    def get_trace_context(self, span_id: str) -> Optional[TraceContext]:
        """Get trace context for span"""
        with self._lock:
            if span_id in self.spans:
                span = self.spans[span_id]
                return TraceContext(
                    trace_id=span.trace_id,
                    span_id=span.span_id,
                    parent_span_id=span.parent_span_id,
                )
            return None

    def get_active_spans(self) -> List[Span]:
        """Get all active spans"""
        with self._lock:
            return list(self.spans.values())

    def get_trace_statistics(self) -> Dict[str, Any]:
        """Get trace statistics"""
        with self._lock:
            active_spans = len(self.spans)
            total_duration = sum(span.duration for span in self.spans.values())

            return {
                "active_spans": active_spans,
                "total_duration": total_duration,
                "average_duration": total_duration / max(1, active_spans),
                "service_name": self.service_name,
            }


# Global trace manager
_trace_manager: Optional[TraceManager] = None


def get_tracer(service_name: str = "netsentinel") -> TraceManager:
    """Get global trace manager"""
    global _trace_manager
    if _trace_manager is None:
        _trace_manager = TraceManager(service_name)
    return _trace_manager


def start_span(
    name: str,
    parent_span_id: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
) -> Span:
    """Start a new span"""
    return get_tracer().start_span(name, parent_span_id, kind, attributes)


def finish_span(
    span_id: str, status: str = Status.OK, status_code: int = StatusCode.OK
) -> None:
    """Finish a span"""
    get_tracer().finish_span(span_id, status, status_code)


def add_span_attribute(span_id: str, key: str, value: Any) -> None:
    """Add attribute to span"""
    get_tracer().add_span_attribute(span_id, key, value)


def add_span_event(
    span_id: str, name: str, attributes: Optional[Dict[str, Any]] = None
) -> None:
    """Add event to span"""
    get_tracer().add_span_event(span_id, name, attributes)


# Context variable for current span
_current_span: ContextVar[Optional[str]] = ContextVar("current_span", default=None)


def set_current_span(span_id: str) -> None:
    """Set current span in context"""
    _current_span.set(span_id)


def get_current_span() -> Optional[str]:
    """Get current span from context"""
    return _current_span.get()


def clear_current_span() -> None:
    """Clear current span from context"""
    _current_span.set(None)


# Decorator for automatic tracing
def trace_function(
    name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None
):
    """Decorator for automatic function tracing"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            span_name = name or f"{func.__module__}.{func.__name__}"
            span = start_span(span_name, attributes=attributes)

            try:
                result = func(*args, **kwargs)
                finish_span(span.span_id, Status.OK, StatusCode.OK)
                return result
            except Exception as e:
                finish_span(span.span_id, Status.ERROR, StatusCode.ERROR)
                raise

        return wrapper

    return decorator


# Async decorator for automatic tracing
def trace_async_function(
    name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None
):
    """Decorator for automatic async function tracing"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            span_name = name or f"{func.__module__}.{func.__name__}"
            span = start_span(span_name, attributes=attributes)

            try:
                result = await func(*args, **kwargs)
                finish_span(span.span_id, Status.OK, StatusCode.OK)
                return result
            except Exception as e:
                finish_span(span.span_id, Status.ERROR, StatusCode.ERROR)
                raise

        return wrapper

    return decorator
