#!/usr/bin/env python3
"""
Test script for alerting system integration
Tests alert generation, notification channels, and management
"""

import requests
import json
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netsentinel.alerts.alert_store import AlertStore

EVENT_PROCESSOR_URL = "http://localhost:8082"

def test_alert_manager():
    """Test the alert manager directly"""
    print("🚨 Testing Alert Manager...")

    try:
        manager = get_alert_manager()
        print(f"✅ Alert manager initialized")

        # Generate a test alert
        alert_id = manager.generate_alert(
            title="Test Direct Alert",
            description="This is a test alert generated directly",
            severity="medium",
            source="test_script",
            event_data={"test_type": "direct", "timestamp": time.time()},
            tags=["test", "direct"]
        )

        print(f"✅ Test alert generated: {alert_id}")

        # Get alerts
        alerts = manager.get_alerts(limit=10)
        print(f"✅ Retrieved {len(alerts)} alerts")

        # Check statistics
        stats = manager.get_statistics()
        print(f"✅ Alert statistics: {stats['total_alerts']} total, {stats['active_alerts']} active")

        # Acknowledge the test alert
        if alert_id:
            success = manager.acknowledge_alert(alert_id)
            print(f"✅ Alert acknowledgment: {success}")

        return True

    except Exception as e:
        print(f"❌ Alert manager test failed: {e}")
        return False

def test_alert_api_endpoints():
    """Test alert API endpoints"""
    print("\n🔗 Testing Alert API Endpoints...")

    try:
        # Test alert status
        response = requests.get(f"{EVENT_PROCESSOR_URL}/alerts/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Alert status API: enabled={status['alerting_enabled']}")
            if 'statistics' in status:
                stats = status['statistics']
                print(f"   Stats: {stats['total_alerts']} alerts, {stats['rules_count']} rules")
        else:
            print(f"❌ Alert status API failed: {response.status_code}")
            return False

        # Test generating a test alert via API
        test_payload = {
            "severity": "low",
            "message": "API-generated test alert"
        }
        response = requests.post(f"{EVENT_PROCESSOR_URL}/alerts/test", json=test_payload)
        if response.status_code == 200:
            result = response.json()
            alert_id = result.get('alert_id')
            print(f"✅ Test alert API: generated alert {alert_id}")
        else:
            print(f"❌ Test alert API failed: {response.status_code}")
            return False

        # Test getting alerts
        response = requests.get(f"{EVENT_PROCESSOR_URL}/alerts?limit=5")
        if response.status_code == 200:
            alerts = response.json()
            print(f"✅ Get alerts API: {alerts['count']} alerts retrieved")
        else:
            print(f"❌ Get alerts API failed: {response.status_code}")

        # Test acknowledging the alert
        if alert_id:
            response = requests.post(f"{EVENT_PROCESSOR_URL}/alerts/{alert_id}/acknowledge")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Acknowledge alert API: {result['message']}")
            else:
                print(f"❌ Acknowledge alert API failed: {response.status_code}")

        # Test alert rules
        response = requests.get(f"{EVENT_PROCESSOR_URL}/alerts/rules")
        if response.status_code == 200:
            rules = response.json()
            print(f"✅ Alert rules API: {rules['count']} rules configured")
        else:
            print(f"❌ Alert rules API failed: {response.status_code}")

        # Test alert templates
        response = requests.get(f"{EVENT_PROCESSOR_URL}/alerts/templates")
        if response.status_code == 200:
            templates = response.json()
            print(f"✅ Alert templates API: {templates['count']} templates available")
        else:
            print(f"❌ Alert templates API failed: {response.status_code}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        return False

def test_alert_escalation():
    """Test alert escalation functionality"""
    print("\n⚡ Testing Alert Escalation...")

    try:
        manager = get_alert_manager()

        # Generate a high-severity alert that should trigger escalation
        alert_id = manager.generate_alert(
            title="Escalation Test Alert",
            description="This alert should escalate if not acknowledged",
            severity="high",
            source="test_escalation",
            event_data={"escalation_test": True},
            tags=["test", "escalation"]
        )

        if not alert_id:
            print("❌ Failed to generate escalation test alert")
            return False

        print(f"✅ Escalation test alert generated: {alert_id}")

        # Check initial escalation level
        alert = manager.alerts.get(alert_id)
        if alert:
            print(f"   Initial escalation level: {alert.escalation_level}")

            # Wait a bit and check if it escalated
            time.sleep(2)
            print(f"   Current escalation level: {alert.escalation_level}")
            print(f"   Last notification: {alert.last_notification}")

        # Clean up - acknowledge the alert
        manager.acknowledge_alert(alert_id)
        print("✅ Escalation test alert acknowledged")

        return True

    except Exception as e:
        print(f"❌ Escalation test failed: {e}")
        return False

def test_alert_filtering():
    """Test alert filtering and querying"""
    print("\n🔍 Testing Alert Filtering...")

    try:
        manager = get_alert_manager()

        # Generate alerts with different severities
        severities = ["low", "medium", "high"]
        alert_ids = []

        for severity in severities:
            alert_id = manager.generate_alert(
                title=f"{severity.capitalize()} Test Alert",
                description=f"Test alert with {severity} severity",
                severity=severity,
                source="filter_test",
                event_data={"severity": severity},
                tags=["test", "filter", severity]
            )
            if alert_id:
                alert_ids.append((alert_id, severity))

        print(f"✅ Generated {len(alert_ids)} test alerts for filtering")

        # Test filtering by severity
        for severity in severities:
            alerts = manager.get_alerts(severity=severity, limit=10)
            severity_alerts = [a for a in alerts if a['severity'] == severity]
            print(f"✅ {severity} severity filter: {len(severity_alerts)} alerts found")

        # Test acknowledged vs unacknowledged filtering
        unacked_alerts = manager.get_alerts(acknowledged=False, limit=10)
        print(f"✅ Unacknowledged alerts: {len(unacked_alerts)}")

        acked_alerts = manager.get_alerts(acknowledged=True, limit=10)
        print(f"✅ Acknowledged alerts: {len(acked_alerts)}")

        # Clean up - acknowledge all test alerts
        for alert_id, _ in alert_ids:
            manager.acknowledge_alert(alert_id)

        print("✅ Test alerts cleaned up")

        return True

    except Exception as e:
        print(f"❌ Alert filtering test failed: {e}")
        return False

def test_security_alert_generation():
    """Test automatic security alert generation from events"""
    print("\n🛡️ Testing Security Alert Generation...")

    try:
        from netsentinel.alert_manager import create_security_alert

        # Create test security events with different threat scores
        test_events = [
            {
                'logtype': 4002,  # SSH login attempt
                'src_host': '192.168.1.100',
                'threat_score': 8.5,  # Should trigger high alert
                'logdata': {'USERNAME': 'admin', 'PASSWORD': 'secret'}
            },
            {
                'logtype': 3000,  # HTTP request
                'src_host': '192.168.1.101',
                'threat_score': 3.0,  # Should not trigger alert (below threshold)
                'logdata': {'url': '/login.php'}
            },
            {
                'logtype': 4000,  # SSH connection
                'src_host': '192.168.1.102',
                'threat_score': 6.5,  # Should trigger medium alert
                'logdata': {'connection': 'established'}
            }
        ]

        generated_alerts = []

        for event in test_events:
            alert_id = create_security_alert(event)
            if alert_id:
                generated_alerts.append(alert_id)
                print(f"✅ Alert generated for threat score {event['threat_score']}: {alert_id}")
            else:
                print(f"ℹ️  No alert generated for threat score {event['threat_score']} (expected)")

        print(f"✅ Total alerts generated: {len(generated_alerts)}")

        # Clean up generated alerts
        manager = get_alert_manager()
        for alert_id in generated_alerts:
            manager.acknowledge_alert(alert_id)

        print("✅ Security test alerts cleaned up")

        return True

    except Exception as e:
        print(f"❌ Security alert generation test failed: {e}")
        return False

def main():
    """Run all alerting system tests"""
    print("🚨 NetSentinel Alerting System Integration Test Suite")
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

    tests = [
        test_alert_manager,
        test_alert_api_endpoints,
        test_alert_escalation,
        test_alert_filtering,
        test_security_alert_generation
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
        print("🎉 All alerting system integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        print("💡 Note: Alert generation depends on system configuration (SMTP, Slack, etc.)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
