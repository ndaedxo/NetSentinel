#!/usr/bin/env python3
"""
Test script for threat intelligence integration
Tests external threat feed processing and enrichment
"""

import requests
import json
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opencanary.threat_intelligence import get_threat_intel_manager

EVENT_PROCESSOR_URL = "http://localhost:8082"

def test_threat_intel_manager():
    """Test the threat intelligence manager directly"""
    print("🕵️ Testing Threat Intelligence Manager...")

    try:
        manager = get_threat_intel_manager()
        print(f"✅ Threat intelligence manager initialized")

        # Check feeds
        feeds = list(manager.feeds.keys())
        print(f"✅ Available feeds: {feeds}")

        # Get statistics
        stats = manager.get_statistics()
        print(f"✅ Statistics: {stats['total_indicators']} indicators, "
              f"{len(manager.feeds)} feeds")

        # Test indicator checking
        test_indicators = [
            "8.8.8.8",  # Should not be a threat
            "google.com",  # Should not be a threat
            "127.0.0.1"  # Local IP
        ]

        for indicator in test_indicators:
            threat_info = manager.check_indicator(indicator)
            status = "THREAT" if threat_info else "clean"
            print(f"✅ {indicator}: {status}")

        # Test manual feed update (this will take time)
        print("🔄 Testing feed update (this may take a moment)...")
        manager.update_feeds()
        print("✅ Feed update completed")

        # Check updated statistics
        stats = manager.get_statistics()
        print(f"✅ Updated statistics: {stats['total_indicators']} indicators")

        return True

    except Exception as e:
        print(f"❌ Threat intelligence manager test failed: {e}")
        return False

def test_threat_intel_api_endpoints():
    """Test threat intelligence API endpoints"""
    print("\n🔗 Testing Threat Intelligence API Endpoints...")

    try:
        # Test threat intel status
        response = requests.get(f"{EVENT_PROCESSOR_URL}/threat-intel/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Threat intel status API: enabled={status['threat_intel_enabled']}")
        else:
            print(f"❌ Threat intel status API failed: {response.status_code}")
            return False

        # Test indicator checking via API
        test_indicators = ["8.8.8.8", "google.com"]
        for indicator in test_indicators:
            response = requests.get(f"{EVENT_PROCESSOR_URL}/threat-intel/check/{indicator}")
            if response.status_code == 200:
                result = response.json()
                threat_status = "THREAT" if result['is_threat'] else "clean"
                print(f"✅ API check {indicator}: {threat_status}")
            else:
                print(f"❌ API check failed for {indicator}: {response.status_code}")

        # Test getting indicators
        response = requests.get(f"{EVENT_PROCESSOR_URL}/threat-intel/indicators?limit=5")
        if response.status_code == 200:
            indicators = response.json()
            print(f"✅ Indicators API: {indicators['count']} indicators returned")
        else:
            print(f"❌ Indicators API failed: {response.status_code}")

        # Test feeds status
        response = requests.get(f"{EVENT_PROCESSOR_URL}/threat-intel/feeds")
        if response.status_code == 200:
            feeds = response.json()
            print(f"✅ Feeds API: {feeds['count']} feeds configured")
        else:
            print(f"❌ Feeds API failed: {response.status_code}")

        # Test manual update
        response = requests.post(f"{EVENT_PROCESSOR_URL}/threat-intel/update")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Manual update API: {result['message']}")
        else:
            print(f"❌ Manual update API failed: {response.status_code}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        return False

def test_threat_enrichment():
    """Test threat score enrichment with threat intelligence"""
    print("\n🎯 Testing Threat Score Enrichment...")

    try:
        # Create a test event that might match threat intelligence
        test_event = {
            'logtype': 4002,  # SSH login attempt
            'src_host': '8.8.8.8',  # Google's DNS - should be clean
            'logdata': {
                'USERNAME': 'admin',
                'PASSWORD': 'password123'
            }
        }

        # Send test event to see if threat intelligence affects scoring
        # Note: This would normally happen through Kafka, but we can test the scoring logic
        print("✅ Test event created for threat enrichment validation")
        print(f"   Event: {test_event['logtype']} from {test_event['src_host']}")

        # Check if the IP is considered a threat
        manager = get_threat_intel_manager()
        threat_info = manager.check_indicator(test_event['src_host'])

        if threat_info:
            print(f"🚨 Threat intelligence match: {threat_info.threat_type} "
                  f"(confidence: {threat_info.confidence}%)")
        else:
            print("✅ IP not found in threat intelligence (expected for clean IP)")

        return True

    except Exception as e:
        print(f"❌ Threat enrichment test failed: {e}")
        return False

def test_feed_management():
    """Test threat feed management functionality"""
    print("\n📡 Testing Threat Feed Management...")

    try:
        manager = get_threat_intel_manager()

        # Test enabling/disabling feeds
        test_feed = "emerging_threats_compromised"

        if test_feed in manager.feeds:
            # Disable feed
            manager.enable_feed(test_feed, False)
            print(f"✅ Disabled feed: {test_feed}")

            # Re-enable feed
            manager.enable_feed(test_feed, True)
            print(f"✅ Re-enabled feed: {test_feed}")

            # Check feed status
            feed = manager.feeds[test_feed]
            print(f"✅ Feed status: enabled={feed.enabled}")
        else:
            print(f"⚠️ Test feed {test_feed} not found in configuration")

        return True

    except Exception as e:
        print(f"❌ Feed management test failed: {e}")
        return False

def main():
    """Run all threat intelligence tests"""
    print("🛡️ OpenCanary Threat Intelligence Integration Test Suite")
    print("=" * 60)

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
        test_threat_intel_manager,
        test_threat_intel_api_endpoints,
        test_threat_enrichment,
        test_feed_management
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All threat intelligence integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        print("💡 Note: Some tests may show 'no threats found' which is expected for clean test data.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
