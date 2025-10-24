#!/usr/bin/env python3
"""
Simulate NetSentinel Events for Testing
Sends realistic NetSentinel security events to Kafka
"""

import json
import time
import sys
import os
from typing import Dict, Any

# Add the netsentinel package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def create_ssh_login_event(ip_address: str, username: str = "admin", password: str = "password123") -> Dict[str, Any]:
    """Create a realistic SSH login attempt event"""
    return {
        "node_id": "netsentinel-simulator-1",
        "logtype": 4002,  # SSH login attempt
        "logdata": {
            "USERNAME": username,
            "PASSWORD": password,
            "REMOTE_ADDRESS": ip_address,
            "REMOTE_PORT": 54321
        },
        "dst_host": "192.168.1.1",
        "dst_port": 22,
        "local_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "local_time_adjusted": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "timestamp": time.time()
    }


def create_http_request_event(ip_address: str, path: str = "/admin", method: str = "GET") -> Dict[str, Any]:
    """Create a realistic HTTP request event"""
    return {
        "node_id": "netsentinel-simulator-1",
        "logtype": 3001,  # HTTP request
        "logdata": {
            "HOST": "example.com",
            "PATH": path,
            "METHOD": method,
            "USERAGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "REMOTE_ADDRESS": ip_address,
            "REMOTE_PORT": 12345
        },
        "dst_host": "192.168.1.1",
        "dst_port": 80,
        "local_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "local_time_adjusted": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "timestamp": time.time()
    }


def create_mysql_login_event(ip_address: str, username: str = "root", password: str = "secret") -> Dict[str, Any]:
    """Create a realistic MySQL login attempt event"""
    return {
        "node_id": "netsentinel-simulator-1",
        "logtype": 5001,  # MySQL login attempt
        "logdata": {
            "USERNAME": username,
            "PASSWORD": password,
            "REMOTE_ADDRESS": ip_address,
            "REMOTE_PORT": 3306
        },
        "dst_host": "192.168.1.1",
        "dst_port": 3307,  # OpenCanary MySQL port
        "local_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "local_time_adjusted": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "timestamp": time.time()
    }


def send_event_to_kafka(event: Dict[str, Any], kafka_servers: str = "localhost:9092", topic: str = "netsentinel-events"):
    """Send event to Kafka"""
    try:
        from kafka import KafkaProducer

        producer = KafkaProducer(
            bootstrap_servers=kafka_servers.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )

        # Extract IP for key
        ip_address = event.get("logdata", {}).get("REMOTE_ADDRESS", "unknown")

        producer.send(topic, value=event, key=ip_address)
        producer.flush()
        producer.close()

        print(f"✅ Sent {event.get('logtype')} event from {ip_address} to Kafka topic '{topic}'")
        return True

    except ImportError:
        print("❌ kafka-python not installed. Install with: pip install kafka-python")
        return False
    except Exception as e:
        print(f"❌ Failed to send event to Kafka: {e}")
        return False


def main():
    """Main simulation function"""
    import argparse

    parser = argparse.ArgumentParser(description="Simulate OpenCanary security events")
    parser.add_argument("--kafka", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--topic", default="netsentinel-events", help="Kafka topic name")
    parser.add_argument("--ip", default="192.168.1.100", help="Source IP address")
    parser.add_argument("--count", type=int, default=1, help="Number of events to send")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between events (seconds)")
    parser.add_argument("--type", choices=["ssh", "http", "mysql", "mixed"], default="ssh",
                       help="Type of events to simulate")

    args = parser.parse_args()

    print(f"🎭 Simulating OpenCanary Events")
    print(f"   Kafka: {args.kafka}")
    print(f"   Topic: {args.topic}")
    print(f"   Events: {args.count}")
    print(f"   Type: {args.type}")
    print("-" * 50)

    success_count = 0

    for i in range(args.count):
        # Generate different IPs for testing
        ip = f"192.168.1.{100 + (i % 20)}" if args.count > 1 else args.ip

        if args.type == "ssh" or (args.type == "mixed" and i % 3 == 0):
            event = create_ssh_login_event(ip, username=f"user{i%5}", password=f"pass{i%10}")
        elif args.type == "http" or (args.type == "mixed" and i % 3 == 1):
            paths = ["/admin", "/wp-admin", "/phpmyadmin", "/login"]
            event = create_http_request_event(ip, path=paths[i % len(paths)])
        elif args.type == "mysql" or (args.type == "mixed" and i % 3 == 2):
            event = create_mysql_login_event(ip, username=f"root{i%3}", password=f"secret{i%5}")

        if send_event_to_kafka(event, args.kafka, args.topic):
            success_count += 1

        if i < args.count - 1 and args.delay > 0:
            time.sleep(args.delay)

    print("-" * 50)
    print(f"📊 Sent {success_count}/{args.count} events successfully")


if __name__ == "__main__":
    main()
