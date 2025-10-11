#!/usr/bin/env python3
"""
Test script for SIEM integration
Tests connectivity and event forwarding to SIEM systems
"""

import requests
import json
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netsentinel.siem_integration import get_siem_manager

EVENT_PROCESSOR_URL = "http://localhost:8082"

def test_siem_manager():
    """Test the SIEM manager directly"""
    print("🔗 Testing SIEM Manager...")

    try:
        manager = get_siem_manager()
        print(f"✅ SIEM manager initialized")

        # Check statistics
        stats = manager.get_statistics()
        print(f"✅ Statistics: {stats['events_sent']} sent, {stats['connectors_active']} active connectors")

        # Add a test connector if none exist
        if not manager.enabled_systems:
            print("ℹ️  No SIEM connectors configured - adding test webhook connector")
            manager.add_webhook_connector("test_webhook", "http://httpbin.org/post")
            manager.enable_system("webhook_test_webhook")
            print("✅ Test webhook connector added")

        # Send a test event
        test_event = {
            'logtype': '4002',
            'src_host': '192.168.1.100',
            'threat_score': 8.5,
            'rule_score': 6.0,
            'ml_score': 2.5,
            'event_details': {'test': True, 'message': 'SIEM manager test'},
            'processed_at': time.time(),
            'tags': ['test', 'siem_manager']
        }

        success = manager.send_event(test_event)
        print(f"✅ Test event sent: {success}")

        return True

    except Exception as e:
        print(f"❌ SIEM manager test failed: {e}")
        return False

def test_siem_api_endpoints():
    """Test SIEM API endpoints"""
    print("\n🔗 Testing SIEM API Endpoints...")

    try:
        # Test SIEM status
        response = requests.get(f"{EVENT_PROCESSOR_URL}/siem/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ SIEM status API: enabled={status['siem_enabled']}")
            if 'statistics' in status:
                stats = status['statistics']
                print(f"   Stats: {stats.get('events_sent', 0)} sent, {stats.get('connectors_active', 0)} active")
        else:
            print(f"❌ SIEM status API failed: {response.status_code}")
            return False

        # Test SIEM connectors
        response = requests.get(f"{EVENT_PROCESSOR_URL}/siem/connectors")
        if response.status_code == 200:
            connectors = response.json()
            print(f"✅ SIEM connectors API: {len(connectors.get('enabled_systems', []))} enabled")
        else:
            print(f"❌ SIEM connectors API failed: {response.status_code}")

        # Test sending a test event via API
        test_payload = {
            "severity": "high",
            "threat_score": 9.0
        }
        response = requests.post(f"{EVENT_PROCESSOR_URL}/siem/test", json=test_payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SIEM test API: {result['message']}")
        else:
            print(f"❌ SIEM test API failed: {response.status_code}")

        # Test connector enable/disable
        response = requests.post(f"{EVENT_PROCESSOR_URL}/siem/connectors/webhook_test_webhook/enable",
                               json={"enable": False})
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Connector disable API: {result['status']}")
        else:
            print(f"❌ Connector disable API failed: {response.status_code}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        return False

def test_siem_connector_types():
    """Test different SIEM connector types"""
    print("\n🔧 Testing SIEM Connector Types...")

    try:
        manager = get_siem_manager()

        # Test webhook connector
        print("📡 Testing webhook connector...")
        manager.add_webhook_connector("test_webhook", "http://httpbin.org/post")
        manager.enable_system("webhook_test_webhook")

        test_event = {
            'logtype': '4002',
            'src_host': '10.0.0.1',
            'threat_score': 7.5,
            'event_details': {'connector_test': 'webhook'},
            'processed_at': time.time()
        }

        success = manager.send_event(test_event)
        print(f"✅ Webhook connector test: {success}")

        # Disable test connector
        manager.disable_system("webhook_test_webhook")

        # Test Splunk connector (if configured)
        splunk_url = os.getenv('SPLUNK_HEC_URL')
        splunk_token = os.getenv('SPLUNK_HEC_TOKEN')

        if splunk_url and splunk_token:
            print("🎯 Testing Splunk connector...")
            manager.add_splunk_connector("test_splunk", splunk_url, splunk_token)
            manager.enable_system("splunk_test_splunk")

            success = manager.send_event(test_event)
            print(f"✅ Splunk connector test: {success}")

            manager.disable_system("splunk_test_splunk")
        else:
            print("ℹ️  Splunk not configured - skipping Splunk connector test")

        # Test syslog connector (if configured)
        syslog_host = os.getenv('SYSLOG_HOST')
        if syslog_host:
            print("📝 Testing syslog connector...")
            manager.add_syslog_connector("test_syslog", syslog_host)
            manager.enable_system("syslog_test_syslog")

            success = manager.send_event(test_event)
            print(f"✅ Syslog connector test: {success}")

            manager.disable_system("syslog_test_syslog")
        else:
            print("ℹ️  Syslog not configured - skipping syslog connector test")

        return True

    except Exception as e:
        print(f"❌ Connector types test failed: {e}")
        return False

def test_siem_filtering():
    """Test SIEM event filtering"""
    print("\n🔍 Testing SIEM Event Filtering...")

    try:
        manager = get_siem_manager()

        # Add a test connector
        manager.add_webhook_connector("filter_test", "http://httpbin.org/post")
        manager.enable_system("webhook_filter_test")

        # Set filtering rules
        manager.set_event_filter(
            "webhook_filter_test",
            event_types=["4002", "4000"],  # Only SSH events
            severities=["high", "critical"],  # Only high severity
            min_score=7.0  # Minimum threat score
        )
        print("✅ Filter rules set for test connector")

        # Test events that should pass filter
        high_score_event = {
            'logtype': '4002',  # SSH event
            'src_host': '192.168.1.1',
            'threat_score': 8.0,  # Above threshold
            'event_details': {'filter_test': 'should_pass'},
            'processed_at': time.time()
        }

        # Test events that should be filtered out
        low_score_event = {
            'logtype': '4002',  # SSH event
            'src_host': '192.168.1.2',
            'threat_score': 5.0,  # Below threshold
            'event_details': {'filter_test': 'should_filter'},
            'processed_at': time.time()
        }

        wrong_type_event = {
            'logtype': '3000',  # HTTP event (not in filter)
            'src_host': '192.168.1.3',
            'threat_score': 8.0,  # High score
            'event_details': {'filter_test': 'wrong_type'},
            'processed_at': time.time()
        }

        # Send test events
        print("📤 Sending test events through filter...")
        results = []
        for i, event in enumerate([high_score_event, low_score_event, wrong_type_event], 1):
            success = manager.send_event(event)
            results.append(success)
            print(f"   Event {i}: {'✅ Sent' if success else '❌ Filtered'} (score: {event['threat_score']}, type: {event['logtype']})")

        # Clean up
        manager.disable_system("webhook_filter_test")
        print("🧹 Test connector cleaned up")

        return True

    except Exception as e:
        print(f"❌ SIEM filtering test failed: {e}")
        return False

def main():
    """Run all SIEM integration tests"""
    print("🏢 NetSentinel SIEM Integration Test Suite")
    print("=" * 55)

    # Check if event processor is running
    try:
        response = requests.get(f"{EVENT_PROCESSOR_URL}/health", timeout=5)
        if response.status_code != 200:
            print("⚠️  Event processor not responding. Make sure the system is running with 'docker-compose up'")
            return 1
    except requests.exceptions.RequestException:
        print("⚠️  Event processor not accessible. Make sure the system is running with 'docker-compose up'")
        return 1

    tests = [
        test_siem_manager,
        test_siem_api_endpoints,
        test_siem_connector_types,
        test_siem_filtering
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 55)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All SIEM integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        print("💡 Note: SIEM tests may show partial results if external systems are not configured.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
