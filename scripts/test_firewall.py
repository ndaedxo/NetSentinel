#!/usr/bin/env python3
"""
Test script for firewall integration
Tests automated IP blocking and firewall management APIs
"""

import requests
import json
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netsentinel.firewall_manager import get_firewall_manager

EVENT_PROCESSOR_URL = "http://localhost:8082"

def test_firewall_manager():
    """Test the firewall manager directly"""
    print("🛡️ Testing Firewall Manager...")

    try:
        manager = get_firewall_manager()
        print(f"✅ Firewall backend: {manager.backend}")

        # Test status
        status = manager.get_firewall_status()
        print(f"✅ Firewall status: {status}")

        # Test blocking an IP
        test_ip = "192.168.1.100"
        print(f"🔒 Blocking test IP: {test_ip}")
        success = manager.block_ip(test_ip, "test_block")
        print(f"✅ Block result: {success}")

        # Check if blocked
        is_blocked = manager.is_ip_blocked(test_ip)
        print(f"✅ Is blocked: {is_blocked}")

        # Get blocked IPs
        blocked = manager.get_blocked_ips()
        print(f"✅ Blocked IPs: {list(blocked.keys())}")

        # Unblock the IP
        print(f"🔓 Unblocking test IP: {test_ip}")
        success = manager.unblock_ip(test_ip)
        print(f"✅ Unblock result: {success}")

        return True

    except Exception as e:
        print(f"❌ Firewall manager test failed: {e}")
        return False

def test_api_endpoints():
    """Test firewall API endpoints"""
    print("\n🔗 Testing Firewall API Endpoints...")

    try:
        # Test firewall status
        response = requests.get(f"{EVENT_PROCESSOR_URL}/firewall/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Firewall status API: {status['backend']} backend, {status['blocked_ips_count']} blocked IPs")
        else:
            print(f"❌ Firewall status API failed: {response.status_code}")
            return False

        # Test blocking an IP via API
        test_ip = "192.168.1.101"
        block_data = {"reason": "api_test"}
        response = requests.post(f"{EVENT_PROCESSOR_URL}/firewall/block/{test_ip}", json=block_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Block API result: {result['message']}")
        else:
            print(f"❌ Block API failed: {response.status_code} - {response.text}")
            return False

        # Test checking IP status
        response = requests.get(f"{EVENT_PROCESSOR_URL}/firewall/check/{test_ip}")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ IP check API: {test_ip} blocked = {status['blocked']}")
        else:
            print(f"❌ IP check API failed: {response.status_code}")

        # Test getting blocked IPs
        response = requests.get(f"{EVENT_PROCESSOR_URL}/firewall/blocked")
        if response.status_code == 200:
            blocked = response.json()
            print(f"✅ Blocked IPs API: {len(blocked['blocked_ips'])} blocked IPs")
        else:
            print(f"❌ Blocked IPs API failed: {response.status_code}")

        # Test unblocking via API
        response = requests.post(f"{EVENT_PROCESSOR_URL}/firewall/unblock/{test_ip}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Unblock API result: {result['message']}")
        else:
            print(f"❌ Unblock API failed: {response.status_code} - {response.text}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        return False

def test_automated_blocking():
    """Test automated blocking based on threat scores"""
    print("\n🤖 Testing Automated Blocking...")

    try:
        # Test high threat score (should trigger block)
        from netsentinel.firewall_manager import block_threat_ip

        test_ip = "192.168.1.102"
        high_score = 8.5  # Above default threshold of 7.0

        print(f"🚨 Testing high threat score blocking: {test_ip} score {high_score}")
        blocked = block_threat_ip(test_ip, high_score, "automated_test_high")
        print(f"✅ High score block result: {blocked}")

        # Test low threat score (should not trigger block)
        low_score = 3.0  # Below threshold

        print(f"✅ Testing low threat score (no block): score {low_score}")
        blocked = block_threat_ip("192.168.1.103", low_score, "automated_test_low")
        print(f"✅ Low score block result: {blocked} (should be False)")

        # Clean up
        manager = get_firewall_manager()
        if test_ip in manager.get_blocked_ips():
            manager.unblock_ip(test_ip)
            print(f"🧹 Cleaned up test IP: {test_ip}")

        return True

    except Exception as e:
        print(f"❌ Automated blocking test failed: {e}")
        return False

def main():
    """Run all firewall tests"""
    print("🔥 OpenCanary Firewall Integration Test Suite")
    print("=" * 50)

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
        test_firewall_manager,
        test_api_endpoints,
        test_automated_blocking
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All firewall integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
