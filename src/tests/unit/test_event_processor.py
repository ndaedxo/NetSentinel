"""
Unit tests for NetSentinel refactored event processor
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Skip all tests in this file if kafka is not available
kafka = pytest.importorskip("kafka")

try:
    from src.netsentinel.processors.refactored_event_processor import (
        RefactoredEventProcessor,
        ProcessorConfig,
    )
    FASTAPI_AVAILABLE = True
except ImportError as e:
    FASTAPI_AVAILABLE = False
    pytest.skip(f"Event processor not available: {e}", allow_module_level=True)


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI/Uvicorn not available")
class TestRefactoredEventProcessor:
    """Test cases for RefactoredEventProcessor class"""

    @pytest.fixture
    def processor(self):
        """Create a test refactored event processor instance"""
        config = ProcessorConfig(
            kafka_servers=["localhost:9092"],
            kafka_topic="test-events",
            consumer_group="test-processor",
            ml_enabled=False,
            alerting_enabled=False,
            siem_enabled=False,
            firewall_enabled=False,
        )
        processor = RefactoredEventProcessor(config)
        yield processor
        # Cleanup if needed

    def test_initialization(self, processor):
        """Test event processor initialization"""
        assert processor is not None
        assert hasattr(processor, "config")
        assert processor.config.kafka_servers == ["localhost:9092"]
        assert processor.config.ml_enabled is False
        assert processor.config.alerting_enabled is False

    @pytest.mark.asyncio
    async def test_processor_initialization(self, processor):
        """Test processor initialization"""
        assert processor.config is not None
        assert processor.consumer is None  # Not started yet
        assert processor.analyzer is None  # Not started yet
        assert processor.router is None  # Not started yet

    @pytest.mark.asyncio
    async def test_processor_metrics(self, processor):
        """Test processor metrics collection"""
        metrics = await processor.get_processor_metrics()
        assert isinstance(metrics, dict)
        assert "events_processed" in metrics
        assert "events_failed" in metrics

    @pytest.mark.asyncio
    async def test_processor_health_check(self, processor):
        """Test processor health check"""
        health = await processor.health_check()
        assert isinstance(health, dict)
        assert "status" in health


class TestProcessorConfig:
    """Test processor configuration"""

    def test_config_creation(self):
        """Test ProcessorConfig creation"""
        config = ProcessorConfig(
            kafka_servers=["localhost:9092"], ml_enabled=True, alerting_enabled=True
        )
        assert config.kafka_servers == ["localhost:9092"]
        assert config.ml_enabled is True
        assert config.alerting_enabled is True

    def test_config_defaults(self):
        """Test ProcessorConfig defaults"""
        config = ProcessorConfig(kafka_servers=["localhost:9092"])
        assert config.max_workers == 3
        assert config.queue_size == 1000
        assert config.ml_enabled is True  # Default is True
