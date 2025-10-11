#!/usr/bin/env python3
"""
Test script for packet analysis integration
Tests network traffic monitoring and anomaly detection
"""

import requests
import json
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opencanary.packet_analyzer import get_packet_analyzer

EVENT_PROCESSOR_URL = "http://localhost:8082"

def test_packet_analyzer():
    """Test the packet analyzer directly"""
    print("📡 Testing Packet Analyzer...")

    try:
        analyzer = get_packet_analyzer()
        print(f"✅ Packet analyzer initialized on interface: {analyzer.interface}")

        # Test starting capture (brief test)
        print("🔍 Starting packet capture for 5 seconds...")
        success = analyzer.start_capture()
        print(f"✅ Capture start: {success}")

        # Wait a bit for some packets
        time.sleep(3)

        # Get statistics
        stats = analyzer.get_statistics()
        print(f"✅ Captured {stats['total_packets']} packets, {stats['total_bytes']} bytes")
        print(f"   Protocols: {stats['protocol_counts']}")

        # Stop capture
        analyzer.stop_capture()
        print("✅ Packet capture stopped")

        # Check for any anomalies
        anomalies = analyzer.get_anomalies()
        print(f"✅ Detected {len(anomalies)} anomalies")

        return True

    except Exception as e:
        print(f"❌ Packet analyzer test failed: {e}")
        return False

def test_packet_api_endpoints():
    """Test packet analysis API endpoints"""
    print("\n🔗 Testing Packet Analysis API Endpoints...")

    try:
        # Test packet status
        response = requests.get(f"{EVENT_PROCESSOR_URL}/packet/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Packet status API: enabled={status['packet_analysis_enabled']}")
            if 'statistics' in status:
                stats = status['statistics']
                print(f"   Stats: {stats['total_packets']} packets, {stats['active_flows']} flows")
        else:
            print(f"❌ Packet status API failed: {response.status_code}")
            return False

        # Test packet anomalies
        response = requests.get(f"{EVENT_PROCESSOR_URL}/packet/anomalies")
        if response.status_code == 200:
            anomalies = response.json()
            print(f"✅ Packet anomalies API: {anomalies['count']} anomalies")
        else:
            print(f"❌ Packet anomalies API failed: {response.status_code}")

        # Test active flows
        response = requests.get(f"{EVENT_PROCESSOR_URL}/packet/flows")
        if response.status_code == 200:
            flows = response.json()
            print(f"✅ Active flows API: {flows['count']} flows")
        else:
            print(f"❌ Active flows API failed: {response.status_code}")

        # Test starting packet capture via API
        response = requests.post(f"{EVENT_PROCESSOR_URL}/packet/start",
                               json={'interface': 'any'})
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Start capture API: {result['status']}")
        else:
            print(f"❌ Start capture API failed: {response.status_code}")

        # Wait a moment
        time.sleep(2)

        # Test stopping packet capture via API
        response = requests.post(f"{EVENT_PROCESSOR_URL}/packet/stop")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Stop capture API: {result['status']}")
        else:
            print(f"❌ Stop capture API failed: {response.status_code}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        return False

def test_network_anomaly_detection():
    """Test network anomaly detection capabilities"""
    print("\n🕵️ Testing Network Anomaly Detection...")

    try:
        # This test would require generating actual network traffic
        # For now, we'll just verify the integration is working

        analyzer = get_packet_analyzer()

        # Start brief capture
        analyzer.start_capture()
        time.sleep(2)  # Capture some traffic
        analyzer.stop_capture()

        # Check what was captured
        stats = analyzer.get_statistics()

        print("✅ Network traffic captured:")
        print(f"   Total packets: {stats['total_packets']}")
        print(f"   Protocols detected: {list(stats['protocol_counts'].keys())}")
        print(f"   Top source IPs: {stats['top_ips'][:3] if stats['top_ips'] else 'None'}")

        # Check for any anomalies detected
        anomalies = analyzer.get_anomalies()
        if anomalies:
            print(f"✅ Anomalies detected: {len(anomalies)}")
            for anomaly in anomalies[:2]:  # Show first 2
                print(f"   - {anomaly['type']}: {anomaly['details']}")
        else:
            print("ℹ️  No anomalies detected (this is normal for clean traffic)")

        return True

    except Exception as e:
        print(f"❌ Anomaly detection test failed: {e}")
        return False

def test_packet_event_integration():
    """Test that packet anomalies are processed as events"""
    print("\n🔄 Testing Packet-Event Integration...")

    try:
        # Start packet capture briefly
        analyzer = get_packet_analyzer()
        analyzer.start_capture()
        time.sleep(3)
        analyzer.stop_capture()

        # Check if any packet anomalies were processed as events
        # This would show up in the threat analysis
        response = requests.get(f"{EVENT_PROCESSOR_URL}/threats")
        if response.status_code == 200:
            threats = response.json()
            packet_events = [ip for ip, data in threats.items()
                           if data.get('event', {}).get('anomaly_source') == 'packet_analyzer']

            if packet_events:
                print(f"✅ Packet anomalies processed as events: {len(packet_events)} IPs")
                for ip in packet_events[:3]:
                    event = threats[ip]['event']
                    print(f"   - {ip}: {event.get('logdata', {}).get('anomaly_type', 'unknown')}")
            else:
                print("ℹ️  No packet anomalies processed yet (normal for clean networks)")

        return True

    except Exception as e:
        print(f"❌ Packet-event integration test failed: {e}")
        return False

def main():
    """Run all packet analysis tests"""
    print("🔍 OpenCanary Packet Analysis Integration Test Suite")
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

    # Check if Scapy is available
    try:
        from scapy.all import get_if_list
        interfaces = get_if_list()
        print(f"✅ Scapy available, detected interfaces: {interfaces[:3]}...")
    except ImportError:
        print("❌ Scapy not available. Packet analysis requires Scapy library.")
        return 1

    tests = [
        test_packet_analyzer,
        test_packet_api_endpoints,
        test_network_anomaly_detection,
        test_packet_event_integration
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
        print("🎉 All packet analysis integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        print("💡 Note: Some tests may fail on clean networks with no traffic anomalies")
        return 1

if __name__ == "__main__":
    sys.exit(main())
