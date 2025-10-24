#!/usr/bin/env python3
"""
Complete Data Flow Test for NetSentinel
Tests the entire pipeline: OpenCanary → Kafka → Event Processor → Redis
"""

import asyncio
import json
import time
import requests
from typing import Dict, Any
import sys
import os

# Add the netsentinel package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from netsentinel.core.models import StandardEvent, EventType, EventSeverity


class DataFlowTester:
    """Comprehensive data flow testing"""

    def __init__(self):
        self.kafka_servers = os.getenv("NETSENTINEL_KAFKA_SERVERS", "localhost:9092")
        self.redis_host = os.getenv("NETSENTINEL_REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("NETSENTINEL_REDIS_PORT", "6379"))
        self.api_base = os.getenv("NETSENTINEL_API_BASE", "http://localhost:8082")

        self.test_results = []
        self.test_ip = "192.168.1.100"

    def log_test(self, test_name: str, success: bool, message: str, details: Dict = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")

        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        })

    async def test_kafka_connectivity(self):
        """Test Kafka connectivity and topic creation"""
        try:
            import kafka
            from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
            from kafka.admin import NewTopic

            # Test producer
            producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )

            # Test admin client for topic creation
            admin_client = KafkaAdminClient(bootstrap_servers=self.kafka_servers.split(','))

            # Create topic if it doesn't exist
            topic_name = "netsentinel-events"
            try:
                # Check if topic exists
                topics = admin_client.list_topics()
                if topic_name not in topics:
                    # Create topic
                    topic = NewTopic(
                        name=topic_name,
                        num_partitions=3,
                        replication_factor=1
                    )
                    admin_client.create_topics([topic])
                    self.log_test("Kafka Topic Creation", True, f"Created topic '{topic_name}'")
                else:
                    self.log_test("Kafka Topic Check", True, f"Topic '{topic_name}' already exists")
            except Exception as e:
                self.log_test("Kafka Topic Management", False, f"Failed to manage topic: {e}")
                return False

            # Test sending a message
            test_message = {"test": "connectivity", "timestamp": time.time()}
            producer.send(topic_name, value=test_message, key="test")
            producer.flush()

            # Test consumer
            consumer = KafkaConsumer(
                topic_name,
                bootstrap_servers=self.kafka_servers.split(','),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='test-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                consumer_timeout_ms=5000
            )

            # Try to consume the test message
            messages_received = 0
            for message in consumer:
                if message.value.get("test") == "connectivity":
                    messages_received += 1
                    break

            consumer.close()
            producer.close()
            admin_client.close()

            if messages_received > 0:
                self.log_test("Kafka Connectivity", True, "Successfully sent and received test message")
                return True
            else:
                self.log_test("Kafka Connectivity", False, "Sent message but couldn't consume it")
                return False

        except ImportError:
            self.log_test("Kafka Dependencies", False, "kafka-python not installed")
            return False
        except Exception as e:
            self.log_test("Kafka Connectivity", False, f"Kafka test failed: {e}")
            return False

    async def test_redis_connectivity(self):
        """Test Redis connectivity"""
        try:
            import redis.asyncio as redis

            redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=os.getenv("NETSENTINEL_REDIS_PASSWORD", ""),
                decode_responses=True
            )

            # Test connection
            await redis_client.ping()

            # Test basic operations
            test_key = "netsentinel:test:connectivity"
            test_value = {"status": "ok", "timestamp": time.time()}

            await redis_client.set(test_key, json.dumps(test_value))
            retrieved = await redis_client.get(test_key)
            await redis_client.delete(test_key)

            if retrieved:
                retrieved_data = json.loads(retrieved)
                if retrieved_data["status"] == "ok":
                    self.log_test("Redis Connectivity", True, "Successfully connected and performed operations")
                    await redis_client.close()
                    return True

            await redis_client.close()
            self.log_test("Redis Connectivity", False, "Connected but operations failed")
            return False

        except ImportError:
            self.log_test("Redis Dependencies", False, "redis not installed")
            return False
        except Exception as e:
            self.log_test("Redis Connectivity", False, f"Redis test failed: {e}")
            return False

    async def send_test_event_to_kafka(self):
        """Send a test security event to Kafka"""
        try:
            import kafka
            from kafka import KafkaProducer

            producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )

            # Create a realistic test event (simulating NetSentinel SSH login attempt)
            test_event = {
                "node_id": "netsentinel-test-1",
                "logtype": 4002,  # SSH login attempt
                "logdata": {
                    "USERNAME": "admin",
                    "PASSWORD": "secret123",
                    "REMOTE_ADDRESS": self.test_ip,
                    "REMOTE_PORT": 12345
                },
                "dst_host": "192.168.1.1",
                "dst_port": 22,
                "local_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "local_time_adjusted": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "timestamp": time.time()
            }

            # Send to Kafka
            producer.send("netsentinel-events", value=test_event, key=self.test_ip)
            producer.flush()
            producer.close()

            self.log_test("Test Event Sent", True, f"Sent test SSH event from {self.test_ip} to Kafka")
            return True

        except Exception as e:
            self.log_test("Test Event Sent", False, f"Failed to send test event: {e}")
            return False

    async def test_api_endpoints(self):
        """Test REST API endpoints"""
        try:
            # Test health endpoint
            response = requests.get(f"{self.api_base}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") == "healthy":
                    self.log_test("API Health Endpoint", True, "Health check passed")
                else:
                    self.log_test("API Health Endpoint", False, f"Health check returned unhealthy: {health_data}")
            else:
                self.log_test("API Health Endpoint", False, f"Health check failed with status {response.status_code}")

            # Test threats endpoint
            response = requests.get(f"{self.api_base}/threats", timeout=5)
            if response.status_code == 200:
                threats_data = response.json()
                self.log_test("API Threats Endpoint", True, f"Retrieved threat data: {len(threats_data.get('threats', []))} threats")
            else:
                self.log_test("API Threats Endpoint", False, f"Threats endpoint failed with status {response.status_code}")

            # Test metrics endpoint
            response = requests.get(f"{self.api_base}/metrics", timeout=5)
            if response.status_code == 200:
                metrics_data = response.text
                if "netsentinel_api_uptime_seconds" in metrics_data:
                    self.log_test("API Metrics Endpoint", True, "Metrics endpoint returned Prometheus data")
                else:
                    self.log_test("API Metrics Endpoint", False, "Metrics endpoint returned data but missing expected metrics")
            else:
                self.log_test("API Metrics Endpoint", False, f"Metrics endpoint failed with status {response.status_code}")

            return True

        except requests.exceptions.RequestException as e:
            self.log_test("API Endpoints", False, f"API request failed: {e}")
            return False

    async def check_redis_threat_storage(self):
        """Check if threat data is stored in Redis"""
        try:
            import redis.asyncio as redis

            redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=os.getenv("NETSENTINEL_REDIS_PASSWORD", ""),
                decode_responses=True
            )

            # Check for threat data
            threat_key = f"threat:{self.test_ip}"
            threat_data = await redis_client.get(threat_key)

            if threat_data:
                threat_record = json.loads(threat_data)
                threat_score = threat_record.get("threat_score", 0)
                self.log_test("Redis Threat Storage", True, f"Found threat record for {self.test_ip} with score {threat_score}")
                await redis_client.close()
                return True
            else:
                # Wait a bit and try again (processing might be async)
                await asyncio.sleep(2)
                threat_data = await redis_client.get(threat_key)
                if threat_data:
                    threat_record = json.loads(threat_data)
                    threat_score = threat_record.get("threat_score", 0)
                    self.log_test("Redis Threat Storage", True, f"Found threat record for {self.test_ip} with score {threat_score} (after delay)")
                    await redis_client.close()
                    return True
                else:
                    self.log_test("Redis Threat Storage", False, f"No threat record found for {self.test_ip}")
                    await redis_client.close()
                    return False

        except Exception as e:
            self.log_test("Redis Threat Storage", False, f"Failed to check Redis threat storage: {e}")
            return False

    async def run_complete_test(self):
        """Run the complete data flow test"""
        print("🚀 Starting NetSentinel Complete Data Flow Test")
        print("=" * 60)

        # Test infrastructure connectivity
        print("\n📡 Testing Infrastructure Connectivity...")
        kafka_ok = await self.test_kafka_connectivity()
        redis_ok = await self.test_redis_connectivity()

        if not kafka_ok or not redis_ok:
            print("\n❌ Infrastructure tests failed. Cannot proceed with data flow test.")
            return False

        # Send test event
        print("\n📨 Sending Test Security Event...")
        event_sent = await self.send_test_event_to_kafka()

        if not event_sent:
            print("\n❌ Failed to send test event. Cannot proceed with data flow test.")
            return False

        # Wait for processing
        print("\n⏳ Waiting for event processing (10 seconds)...")
        await asyncio.sleep(10)

        # Test API endpoints
        print("\n🔗 Testing REST API Endpoints...")
        api_ok = await self.test_api_endpoints()

        # Check Redis threat storage
        print("\n💾 Checking Redis Threat Storage...")
        storage_ok = await self.check_redis_threat_storage()

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for test in self.test_results if test["success"])
        total = len(self.test_results)

        print(f"Tests Passed: {passed}/{total}")

        if passed == total:
            print("🎉 ALL TESTS PASSED! Complete data flow is working.")
            return True
        else:
            print("⚠️  Some tests failed. Check the details above.")
            return False


async def main():
    """Main test function"""
    tester = DataFlowTester()

    # Run the complete test
    success = await tester.run_complete_test()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
