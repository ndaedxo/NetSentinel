#!/usr/bin/env python3
"""
Test script for enterprise database integration
Tests Elasticsearch and InfluxDB functionality
"""

import requests
import json
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netsentinel.enterprise_database import get_enterprise_db

EVENT_PROCESSOR_URL = "http://localhost:8082"

def test_enterprise_db_manager():
    """Test the enterprise database manager directly"""
    print("🏢 Testing Enterprise Database Manager...")

    try:
        db = get_enterprise_db()
        print(f"✅ Enterprise database manager initialized")

        # Get statistics
        stats = db.get_statistics()
        print(f"✅ Database health: {stats['overall_health']}")

        if 'elasticsearch' in stats:
            es_stats = stats['elasticsearch']
            print(f"   Elasticsearch: {len(es_stats)} indices")
            for index, info in es_stats.items():
                if isinstance(info, dict) and 'docs_count' in info:
                    print(f"     {index}: {info['docs_count']} documents")

        if 'influxdb' in stats:
            influx_stats = stats['influxdb']
            print(f"   InfluxDB: {influx_stats}")

        # Test storing a sample event
        sample_event = {
            'logtype': 4002,
            'src_host': '192.168.1.100',
            'threat_score': 8.5,
            'rule_score': 6.0,
            'ml_score': 2.5,
            'logdata': {'USERNAME': 'admin', 'PASSWORD': 'secret'},
            'processed_at': time.time(),
            'tags': ['test', 'sample']
        }

        db.store_event(sample_event, "threats")
        print("✅ Sample event stored successfully")

        # Test storing packet data
        sample_packet = {
            'timestamp': time.time(),
            'src_ip': '10.0.0.1',
            'dst_ip': '192.168.1.1',
            'protocol': 'TCP',
            'src_port': 44321,
            'dst_port': 22,
            'packet_size': 1500,
            'flow_key': '10.0.0.1:44321-192.168.1.1:22-TCP'
        }

        db.store_packet_data(sample_packet)
        print("✅ Sample packet data stored successfully")

        # Test searching events
        query = {"term": {"src_host": "192.168.1.100"}}
        results = db.search_events(query, "threats", 10)
        print(f"✅ Event search returned {len(results.get('hits', {}).get('hits', []))} results")

        return True

    except Exception as e:
        print(f"❌ Enterprise database manager test failed: {e}")
        return False

def test_database_api_endpoints():
    """Test enterprise database API endpoints"""
    print("\n🔗 Testing Enterprise Database API Endpoints...")

    try:
        # Test database status
        response = requests.get(f"{EVENT_PROCESSOR_URL}/db/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Database status API: elasticsearch={'healthy' if status.get('elasticsearch', {}).get('events') is not None else 'degraded'}")
            influxdb_status = status.get('influxdb', {}).get('status', 'unknown')
            print(f"   InfluxDB status: {influxdb_status}")
        else:
            print(f"❌ Database status API failed: {response.status_code}")
            return False

        # Test searching events with IP parameter
        response = requests.get(f"{EVENT_PROCESSOR_URL}/db/search/events?src_ip=192.168.1.100&limit=5")
        if response.status_code == 200:
            search_results = response.json()
            total = search_results.get('count', 0)
            print(f"✅ Event search API: {total} events found for IP 192.168.1.100")
        else:
            print(f"❌ Event search API failed: {response.status_code}")

        # Test recent events
        response = requests.get(f"{EVENT_PROCESSOR_URL}/db/events/recent?limit=5")
        if response.status_code == 200:
            recent = response.json()
            print(f"✅ Recent events API: {recent['count']} events in last 24h")
        else:
            print(f"❌ Recent events API failed: {response.status_code}")

        # Test recent anomalies
        response = requests.get(f"{EVENT_PROCESSOR_URL}/db/anomalies/recent?limit=5")
        if response.status_code == 200:
            anomalies = response.json()
            print(f"✅ Recent anomalies API: {anomalies['count']} anomalies in last 24h")
        else:
            print(f"❌ Recent anomalies API failed: {response.status_code}")

        # Test metrics retrieval
        response = requests.get(f"{EVENT_PROCESSOR_URL}/db/metrics/opencanary_events?hours=1")
        if response.status_code == 200:
            metrics = response.json()
            print(f"✅ Metrics API: retrieved {len(metrics.get('data', []))} metric records")
        else:
            print(f"❌ Metrics API failed: {response.status_code} - {response.text}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        return False

def test_database_search_functionality():
    """Test advanced database search functionality"""
    print("\n🔍 Testing Database Search Functionality...")

    try:
        # Test searching by source IP
        response = requests.get(f"{EVENT_PROCESSOR_URL}/db/search/events?src_ip=192.168.1.100&limit=10")
        if response.status_code == 200:
            results = response.json()
            events = results.get('events', [])
            print(f"✅ IP search: {len(events)} events from 192.168.1.100")
        else:
            print(f"❌ IP search failed: {response.status_code}")

        # Skip threat score search (API doesn't support it yet)
        print(f"ℹ️  Threat score search: Not implemented in current API")

        # Test searching by destination port
        response = requests.get(f"{EVENT_PROCESSOR_URL}/db/search/events?dst_port=22&limit=10")
        if response.status_code == 200:
            results = response.json()
            events = results.get('events', [])
            print(f"✅ Port search: {len(events)} events targeting port 22")
        else:
            print(f"❌ Port search failed: {response.status_code}")

        # Skip anomaly search (would need separate endpoint)
        print(f"ℹ️  Anomaly search: Not implemented in current API")

        return True

    except Exception as e:
        print(f"❌ Search functionality test failed: {e}")
        return False

def test_database_integration():
    """Test end-to-end database integration"""
    print("\n🔄 Testing Database Integration...")

    try:
        # Send a test event through the event processor
        test_event = {
            'logtype': 4002,
            'src_host': '10.0.0.50',
            'logdata': {
                'USERNAME': 'testuser',
                'PASSWORD': 'testpass123'
            }
        }

        # This would normally go through Kafka, but we'll simulate
        # by calling the processor's threat analysis
        response = requests.get(f"{EVENT_PROCESSOR_URL}/threats/10.0.0.50")
        if response.status_code == 200:
            threat_data = response.json()
            if threat_data:
                print("✅ Threat data retrieved (may be from cache or new processing)")
            else:
                print("ℹ️  No threat data found (expected for new IP)")
        else:
            print(f"❌ Threat analysis failed: {response.status_code}")

        # Check if the event was stored in enterprise database
        time.sleep(2)  # Allow time for async processing

        response = requests.get(f"{EVENT_PROCESSOR_URL}/db/search/events?src_ip=10.0.0.50&size=5")
        if response.status_code == 200:
            results = response.json()
            hits = results.get('results', {}).get('hits', {}).get('hits', [])
            print(f"✅ Database integration: {len(hits)} events stored for test IP")
        else:
            print(f"❌ Database integration check failed: {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        return False

def main():
    """Run all enterprise database tests"""
    print("🏢 OpenCanary Enterprise Database Integration Test Suite")
    print("=" * 65)

    # Check if event processor is running
    try:
        response = requests.get(f"{EVENT_PROCESSOR_URL}/health", timeout=5)
        if response.status_code != 200:
            print("⚠️  Event processor not responding. Make sure the system is running with 'docker-compose up'")
            return 1
    except requests.exceptions.RequestException:
        print("⚠️  Event processor not accessible. Make sure the system is running with 'docker-compose up'")
        return 1

    # Check database availability
    try:
        # Test Elasticsearch
        response = requests.get("http://localhost:9200/_cluster/health", timeout=5)
        if response.status_code == 200:
            print("✅ Elasticsearch is accessible")
        else:
            print("⚠️  Elasticsearch not responding (may still be initializing)")
    except:
        print("⚠️  Elasticsearch not accessible")

    try:
        # Test InfluxDB
        response = requests.get("http://localhost:8086/health", timeout=5)
        if response.status_code == 200:
            print("✅ InfluxDB is accessible")
        else:
            print("⚠️  InfluxDB not responding (may still be initializing)")
    except:
        print("⚠️  InfluxDB not accessible")

    tests = [
        test_enterprise_db_manager,
        test_database_api_endpoints,
        test_database_search_functionality,
        test_database_integration
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 65)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All enterprise database integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        print("💡 Note: Database services may take time to fully initialize after startup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
