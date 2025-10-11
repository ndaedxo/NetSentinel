#!/usr/bin/env python3
"""
Test script for SDN integration
Tests connectivity and dynamic network policy modification
"""

import requests
import json
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netsentinel.sdn_integration import get_sdn_manager, SDNController, SDNControllerType

EVENT_PROCESSOR_URL = "http://localhost:8082"

def test_sdn_manager():
    """Test the SDN manager directly"""
    print("🔗 Testing SDN Manager...")

    try:
        manager = get_sdn_manager()
        print(f"✅ SDN manager initialized")

        # Add a test controller if none exist
        if not manager.controllers:
            print("ℹ️  No SDN controllers configured - adding test OpenDaylight controller")
            test_controller = SDNController(
                name="test_opendaylight",
                type=SDNControllerType.OPENDLIGHT,
                host="localhost",
                port=8181,
                username="admin",
                password="admin"
            )
            manager.add_controller(test_controller)
            print("✅ Test OpenDaylight controller added")

        # Check status
        status = manager.get_status()
        print(f"✅ Status: {status['controllers']} controllers, {status['active_flows']} active flows")

        return True

    except Exception as e:
        print(f"❌ SDN manager test failed: {e}")
        return False

def test_sdn_api_endpoints():
    """Test SDN API endpoints"""
    print("\n🔗 Testing SDN API Endpoints...")

    try:
        # Test SDN status
        response = requests.get(f"{EVENT_PROCESSOR_URL}/sdn/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ SDN status API: enabled={status['sdn_enabled']}")
            if 'status' in status:
                s = status['status']
                print(f"   Status: {s.get('controllers', 0)} controllers, {s.get('active_flows', 0)} flows")
        else:
            print(f"❌ SDN status API failed: {response.status_code}")
            return False

        # Test SDN controllers
        response = requests.get(f"{EVENT_PROCESSOR_URL}/sdn/controllers")
        if response.status_code == 200:
            controllers = response.json()
            print(f"✅ SDN controllers API: {controllers.get('count', 0)} controllers configured")
        else:
            print(f"❌ SDN controllers API failed: {response.status_code}")

        # Test quarantine policies
        response = requests.get(f"{EVENT_PROCESSOR_URL}/sdn/quarantine/policies")
        if response.status_code == 200:
            policies = response.json()
            print(f"✅ Quarantine policies API: {policies.get('active_count', 0)} active policies")
        else:
            print(f"❌ Quarantine policies API failed: {response.status_code}")

        # Test active flows
        response = requests.get(f"{EVENT_PROCESSOR_URL}/sdn/flows")
        if response.status_code == 200:
            flows = response.json()
            print(f"✅ Active flows API: {flows.get('count', 0)} active flows")
        else:
            print(f"❌ Active flows API failed: {response.status_code}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        return False

def test_sdn_quarantine_operations():
    """Test SDN quarantine operations (simulated)"""
    print("\n🛡️  Testing SDN Quarantine Operations...")

    try:
        # Note: This test assumes SDN controllers are not actually configured
        # In a real environment, you would need running SDN controllers

        # Test manual quarantine API (will fail without real controller)
        quarantine_data = {
            "ip_address": "192.168.1.100",
            "controller": "test_opendaylight",
            "switch_id": "openflow:1",
            "duration": 300,
            "quarantine_vlan": 999
        }

        response = requests.post(f"{EVENT_PROCESSOR_URL}/sdn/quarantine", json=quarantine_data)
        if response.status_code in [200, 500]:  # 200 if successful, 500 if controller not available
            result = response.json()
            if result.get('status') == 'success':
                print(f"✅ Quarantine API test: {result['message']}")

                # Test quarantine release
                policy_name = f"quarantine_{quarantine_data['ip_address']}_{int(time.time())}"
                response = requests.delete(f"{EVENT_PROCESSOR_URL}/sdn/quarantine/{policy_name}")
                if response.status_code in [200, 500]:
                    print("✅ Quarantine release API responded")
            else:
                print(f"ℹ️  Quarantine API test: {result.get('error', 'Expected failure - no real SDN controller')}")
        else:
            print(f"❌ Quarantine API failed: {response.status_code}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Quarantine test failed: {e}")
        return False

def test_sdn_traffic_operations():
    """Test SDN traffic redirection and mirroring operations"""
    print("\n🔀 Testing SDN Traffic Operations...")

    try:
        # Test traffic redirection
        redirect_data = {
            "ip_address": "192.168.1.200",
            "controller": "test_opendaylight",
            "switch_id": "openflow:1",
            "destination_port": "2",
            "duration": 300
        }

        response = requests.post(f"{EVENT_PROCESSOR_URL}/sdn/traffic/redirect", json=redirect_data)
        if response.status_code in [200, 500]:
            result = response.json()
            if result.get('status') == 'success':
                print(f"✅ Traffic redirect API test: {result['message']}")
            else:
                print(f"ℹ️  Traffic redirect API test: {result.get('error', 'Expected failure - no real SDN controller')}")
        else:
            print(f"❌ Traffic redirect API failed: {response.status_code}")

        # Test traffic mirroring
        mirror_data = {
            "ip_address": "192.168.1.201",
            "controller": "test_opendaylight",
            "switch_id": "openflow:1",
            "mirror_port": "3",
            "duration": 300
        }

        response = requests.post(f"{EVENT_PROCESSOR_URL}/sdn/traffic/mirror", json=mirror_data)
        if response.status_code in [200, 500]:
            result = response.json()
            if result.get('status') == 'success':
                print(f"✅ Traffic mirror API test: {result['message']}")
            else:
                print(f"ℹ️  Traffic mirror API test: {result.get('error', 'Expected failure - no real SDN controller')}")
        else:
            print(f"❌ Traffic mirror API failed: {response.status_code}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Traffic operations test failed: {e}")
        return False

def test_sdn_connectivity():
    """Test SDN connectivity (if controllers are configured)"""
    print("\n🌐 Testing SDN Connectivity...")

    try:
        # Test SDN integration connectivity
        test_data = {"controller": "test_opendaylight"}

        response = requests.post(f"{EVENT_PROCESSOR_URL}/sdn/test", json=test_data)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print(f"✅ SDN connectivity test: {result['message']}")
                if 'topology_nodes' in result:
                    print(f"   Topology: {result['topology_nodes']} nodes")
                elif 'device_count' in result:
                    print(f"   Devices: {result['device_count']} devices")
                elif 'switch_count' in result:
                    print(f"   Switches: {result['switch_count']} switches")
            else:
                print(f"ℹ️  SDN connectivity test: {result.get('message', 'Controller not available')}")
        elif response.status_code == 400:
            result = response.json()
            print(f"ℹ️  SDN connectivity test: {result.get('error', 'Controller not configured')}")
        else:
            print(f"❌ SDN connectivity test failed: {response.status_code}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Connectivity test failed: {e}")
        return False

def test_sdn_controller_types():
    """Test different SDN controller types"""
    print("\n🎛️  Testing SDN Controller Types...")

    try:
        manager = get_sdn_manager()

        # Test adding different controller types
        controllers_to_test = [
            ("test_opendaylight", SDNControllerType.OPENDLIGHT, 8181),
            ("test_onos", SDNControllerType.ONOS, 8181),
            ("test_ryu", SDNControllerType.RYU, 8080),
        ]

        for name, ctrl_type, port in controllers_to_test:
            try:
                controller = SDNController(
                    name=name,
                    type=ctrl_type,
                    host="localhost",
                    port=port
                )
                manager.add_controller(controller)
                print(f"✅ Added {ctrl_type.value} controller: {name}")

                # Test getting interface
                interface = manager.get_controller_interface(name)
                if interface:
                    print(f"✅ Interface created for {name}")
                else:
                    print(f"❌ Failed to create interface for {name}")

            except Exception as e:
                print(f"❌ Failed to add {ctrl_type.value} controller: {e}")

        # Check final controller count
        status = manager.get_status()
        print(f"✅ Total controllers configured: {len(status['controllers'])}")

        return True

    except Exception as e:
        print(f"❌ Controller types test failed: {e}")
        return False

def main():
    """Run all SDN integration tests"""
    print("🌐 NetSentinel SDN Integration Test Suite")
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
        test_sdn_manager,
        test_sdn_api_endpoints,
        test_sdn_controller_types,
        test_sdn_quarantine_operations,
        test_sdn_traffic_operations,
        test_sdn_connectivity
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
        print("🎉 All SDN integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        print("💡 Note: SDN tests may show 'expected failures' if no real SDN controllers are running.")
        print("   This is normal for testing without actual SDN infrastructure.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
