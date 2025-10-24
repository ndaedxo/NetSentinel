#!/usr/bin/env python3
"""
Startup script for the refactored NetSentinel event processor
"""

import asyncio
import os
from netsentinel.processors.refactored_event_processor import RefactoredEventProcessor, ProcessorConfig
from netsentinel.core.base import managed_component

async def main():
    """Main entry point for the event processor"""

    # Get configuration from environment variables
    config = ProcessorConfig(
        kafka_servers=os.getenv("NETSENTINEL_KAFKA_SERVERS", "kafka:29092"),
        kafka_topic=os.getenv("NETSENTINEL_KAFKA_TOPIC", "netsentinel-events"),
        consumer_group=os.getenv("NETSENTINEL_CONSUMER_GROUP", "netsentinel-processor"),
        ml_enabled=os.getenv("NETSENTINEL_ML_ENABLED", "true").lower() == "true",
        alerting_enabled=os.getenv("NETSENTINEL_ALERTING_ENABLED", "true").lower() == "true",
        siem_enabled=os.getenv("NETSENTINEL_SIEM_ENABLED", "true").lower() == "true",
        firewall_enabled=os.getenv("NETSENTINEL_FIREWALL_ENABLED", "true").lower() == "true",
        threat_storage_enabled=os.getenv("NETSENTINEL_THREAT_STORAGE_ENABLED", "true").lower() == "true",
        firewall_manager_enabled=os.getenv("NETSENTINEL_FIREWALL_MANAGER_ENABLED", "true").lower() == "true",
        api_enabled=os.getenv("NETSENTINEL_API_ENABLED", "true").lower() == "true",
        api_host=os.getenv("NETSENTINEL_API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("NETSENTINEL_API_PORT", "8082")),
    )

    print("Starting NetSentinel Refactored Event Processor...")
    print(f"Kafka Servers: {config.kafka_servers}")
    print(f"Topic: {config.kafka_topic}")
    print(f"Consumer Group: {config.consumer_group}")
    print(f"Redis Host: {os.getenv('NETSENTINEL_REDIS_HOST', 'redis')}")
    print(f"Threat Storage Enabled: {config.threat_storage_enabled}")
    print(f"Firewall Manager Enabled: {config.firewall_manager_enabled}")
    print(f"API Enabled: {config.api_enabled}")
    print(f"API Host: {config.api_host}:{config.api_port}" if config.api_enabled else "API Disabled")
    print(f"ML Enabled: {config.ml_enabled}")
    print(f"Alerting Enabled: {config.alerting_enabled}")
    print(f"SIEM Enabled: {config.siem_enabled}")
    print(f"Firewall Enabled: {config.firewall_enabled}")

    processor = RefactoredEventProcessor(config)

    try:
        async with managed_component(processor):
            print("Event processor started successfully. Press Ctrl+C to stop.")
            await asyncio.sleep(float('inf'))
    except KeyboardInterrupt:
        print("Shutting down event processor...")
    except Exception as e:
        print(f"Error running event processor: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
