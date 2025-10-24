"""
Unit tests for NetSentinel SDN integration
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from netsentinel.sdn_integration import (
    SDNManager,
    SDNController,
    SDNControllerType,
    FlowRule,
    QuarantinePolicy,
    get_sdn_manager,
    OpenDaylightController,
    ONOSController,
    RyuController,
)


class TestSDNController:
    """Test cases for SDNController class"""

    def test_controller_creation(self):
        """Test SDNController object creation"""
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="192.168.1.10",
            port=8181,
            username="admin",
            password="admin",
        )

        assert controller.name == "test_odl"
        assert controller.type == SDNControllerType.OPENDLIGHT
        assert controller.host == "192.168.1.10"
        assert controller.port == 8181
        assert controller.username == "admin"
        assert controller.password == "admin"
        assert controller.base_url == "http://192.168.1.10:8181"

    def test_https_url(self):
        """Test HTTPS URL generation"""
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="secure.example.com",
            port=443,
        )

        assert controller.base_url == "https://secure.example.com:443"


class TestFlowRule:
    """Test cases for FlowRule class"""

    def test_flow_rule_creation(self):
        """Test FlowRule object creation"""
        flow = FlowRule(
            switch_id="openflow:1",
            table_id=0,
            priority=100,
            idle_timeout=300,
            hard_timeout=0,
            cookie=12345,
        )

        assert flow.switch_id == "openflow:1"
        assert flow.table_id == 0
        assert flow.priority == 100
        assert flow.idle_timeout == 300
        assert flow.hard_timeout == 0
        assert flow.cookie == 12345
        assert flow.match == {}
        assert flow.actions == []

    def test_flow_rule_defaults(self):
        """Test FlowRule default values"""
        flow = FlowRule(switch_id="openflow:1", priority=200)

        assert flow.table_id == 0
        assert flow.idle_timeout == 300
        assert flow.hard_timeout == 0
        assert flow.cookie is None
        assert flow.match == {}
        assert flow.actions == []


class TestQuarantinePolicy:
    """Test cases for QuarantinePolicy class"""

    def test_quarantine_policy_creation(self):
        """Test QuarantinePolicy object creation"""
        policy = QuarantinePolicy(
            name="test_quarantine",
            target_ip="192.168.1.100",
            switch_id="openflow:1",
            quarantine_vlan=999,
            duration=3600,
        )

        assert policy.name == "test_quarantine"
        assert policy.target_ip == "192.168.1.100"
        assert policy.switch_id == "openflow:1"
        assert policy.quarantine_vlan == 999
        assert policy.duration == 3600
        assert policy.active is True
        assert isinstance(policy.created_at, float)

    def test_policy_expiration(self):
        """Test policy expiration logic"""
        # Create policy that expires immediately
        past_time = time.time() - 3601  # 1 hour ago
        policy = QuarantinePolicy(
            name="expired_policy",
            target_ip="192.168.1.100",
            switch_id="openflow:1",
            duration=3600,
        )
        policy.created_at = past_time

        assert policy.is_expired() is True

        # Create policy that hasn't expired
        policy.active_policy = QuarantinePolicy(
            name="active_policy",
            target_ip="192.168.1.100",
            switch_id="openflow:1",
            duration=3600,
        )

        assert policy.active_policy.is_expired() is False


class TestOpenDaylightController:
    """Test cases for OpenDaylight controller"""

    @pytest.fixture
    def odl_controller(self):
        """Create a test OpenDaylight controller"""
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
            username="admin",
            password="admin",
        )
        return OpenDaylightController(controller)

    @patch("netsentinel.sdn_integration.requests.Session.get")
    def test_get_topology(self, mock_get, odl_controller):
        """Test getting network topology"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "network-topology": {
                "topology": [
                    {"node": [{"node-id": "openflow:1"}, {"node-id": "openflow:2"}]}
                ]
            }
        }
        mock_get.return_value = mock_response

        topology = odl_controller.get_topology()
        assert "network-topology" in topology
        assert len(topology["network-topology"]["topology"][0]["node"]) == 2

    @patch("netsentinel.sdn_integration.requests.Session.post")
    def test_add_flow(self, mock_post, odl_controller):
        """Test adding a flow rule"""
        mock_response = Mock()
        mock_post.return_value = mock_response

        flow = FlowRule(
            switch_id="openflow:1",
            priority=100,
            match={"ipv4_src": "192.168.1.100"},
            actions=[{"drop-action": {}}],
        )

        result = odl_controller.add_flow("openflow:1", flow)
        assert result is True

        # Verify the request was made
        mock_post.assert_called_once()

    @patch("netsentinel.sdn_integration.requests.Session.delete")
    def test_delete_flow(self, mock_delete, odl_controller):
        """Test deleting a flow rule"""
        mock_response = Mock()
        mock_delete.return_value = mock_response

        result = odl_controller.delete_flow("openflow:1", "12345")
        assert result is True

        mock_delete.assert_called_once()


class TestONOSController:
    """Test cases for ONOS controller"""

    @pytest.fixture
    def onos_controller(self):
        """Create a test ONOS controller"""
        controller = SDNController(
            name="test_onos",
            type=SDNControllerType.ONOS,
            host="localhost",
            port=8181,
            username="onos",
            password="rocks",
        )
        return ONOSController(controller)

    @patch("netsentinel.sdn_integration.requests.Session.get")
    def test_get_devices(self, mock_get, onos_controller):
        """Test getting network devices"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "devices": [{"id": "of:0000000000000001"}, {"id": "of:0000000000000002"}]
        }
        mock_get.return_value = mock_response

        devices = onos_controller.get_devices()
        assert len(devices) == 2
        assert devices[0]["id"] == "of:0000000000000001"

    @patch("netsentinel.sdn_integration.requests.Session.post")
    def test_add_flow(self, mock_post, onos_controller):
        """Test adding a flow rule"""
        mock_response = Mock()
        mock_post.return_value = mock_response

        flow_data = {
            "flows": [
                {
                    "deviceId": "of:0000000000000001",
                    "priority": 100,
                    "matches": [{"type": "IPV4_SRC", "ip": "192.168.1.100"}],
                    "instructions": [{"type": "OUTPUT", "port": "DROP"}],
                }
            ]
        }

        result = onos_controller.add_flow("of:0000000000000001", flow_data)
        assert result is True
        mock_post.assert_called_once()


class TestRyuController:
    """Test cases for Ryu controller"""

    @pytest.fixture
    def ryu_controller(self):
        """Create a test Ryu controller"""
        controller = SDNController(
            name="test_ryu", type=SDNControllerType.RYU, host="localhost", port=8080
        )
        return RyuController(controller)

    @patch("netsentinel.sdn_integration.requests.Session.get")
    def test_get_switches(self, mock_get, ryu_controller):
        """Test getting connected switches"""
        mock_response = Mock()
        mock_response.json.return_value = ["0000000000000001", "0000000000000002"]
        mock_get.return_value = mock_response

        switches = ryu_controller.get_switches()
        assert len(switches) == 2
        assert "0000000000000001" in switches

    @patch("netsentinel.sdn_integration.requests.Session.post")
    def test_add_flow(self, mock_post, ryu_controller):
        """Test adding a flow rule"""
        mock_response = Mock()
        mock_post.return_value = mock_response

        flow_data = {
            "dpid": 1,
            "priority": 100,
            "match": {"ipv4_src": "192.168.1.100"},
            "actions": [{"type": "DROP"}],
        }

        result = ryu_controller.add_flow("0000000000000001", flow_data)
        assert result is True
        mock_post.assert_called_once()


class TestSDNManager:
    """Test cases for SDNManager class"""

    @pytest.fixture
    def sdn_manager(self):
        """Create a test SDN manager instance"""
        manager = SDNManager()
        yield manager
        # Clean up
        manager.controllers.clear()
        manager.quarantine_policies.clear()
        manager.active_flows.clear()

    def test_singleton_pattern(self):
        """Test that SDN manager follows singleton pattern"""
        manager1 = get_sdn_manager()
        manager2 = get_sdn_manager()
        assert manager1 is manager2

    def test_add_controller(self, sdn_manager):
        """Test adding SDN controllers"""
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )

        sdn_manager.add_controller(controller)
        assert "test_odl" in sdn_manager.controllers

    def test_get_controller_interface(self, sdn_manager):
        """Test getting controller interface instances"""
        # Add OpenDaylight controller
        odl_controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )
        sdn_manager.add_controller(odl_controller)

        interface = sdn_manager.get_controller_interface("test_odl")
        assert isinstance(interface, OpenDaylightController)

        # Test unknown controller type
        unknown_controller = SDNController(
            name="test_unknown",
            type=SDNControllerType.FLOODLIGHT,  # Not implemented
            host="localhost",
            port=8080,
        )
        sdn_manager.add_controller(unknown_controller)

        interface = sdn_manager.get_controller_interface("test_unknown")
        assert interface is None

    @patch("src.netsentinel.sdn_integration.OpenDaylightController")
    def test_quarantine_ip(self, mock_odl_class, sdn_manager):
        """Test IP quarantine functionality"""
        # Setup mock controller
        mock_controller = Mock()
        mock_odl_class.return_value = mock_controller
        mock_controller.add_flow.return_value = True

        # Add controller
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )
        sdn_manager.add_controller(controller)

        # Test quarantine
        result = sdn_manager.quarantine_ip(
            controller_name="test_odl",
            switch_id="openflow:1",
            target_ip="192.168.1.100",
            duration=3600,
        )

        assert result is True
        mock_controller.add_flow.assert_called()

        # Verify policy was created
        assert len(sdn_manager.quarantine_policies) == 1
        policy = list(sdn_manager.quarantine_policies.values())[0]
        assert policy.target_ip == "192.168.1.100"
        assert policy.active is True

    @patch("src.netsentinel.sdn_integration.OpenDaylightController")
    def test_release_quarantine(self, mock_odl_class, sdn_manager):
        """Test quarantine release functionality"""
        # Setup mock controller
        mock_controller = Mock()
        mock_odl_class.return_value = mock_controller
        mock_controller.delete_flow.return_value = True

        # Add controller and create quarantine
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )
        sdn_manager.add_controller(controller)

        # Create a quarantine policy
        policy = QuarantinePolicy(
            name="test_policy",
            target_ip="192.168.1.100",
            switch_id="openflow:1",
            controller_name="test_odl",
            duration=3600,
        )
        sdn_manager.quarantine_policies["test_policy"] = policy
        
        # Add a mock flow entry to simulate what would be created during quarantine
        sdn_manager.active_flows["openflow:1_test_flow"] = {
            "policy": "test_policy",
            "controller": "test_odl",
            "switch_id": "openflow:1",
            "installed_at": time.time(),
        }

        # Release quarantine
        result = sdn_manager.release_quarantine("test_policy")
        assert result is True

        # Verify policy was deactivated
        assert policy.active is False

    @patch("src.netsentinel.sdn_integration.OpenDaylightController")
    def test_traffic_redirection(self, mock_odl_class, sdn_manager):
        """Test traffic redirection functionality"""
        # Setup mock controller
        mock_controller = Mock()
        mock_odl_class.return_value = mock_controller
        mock_controller.add_flow.return_value = True

        # Add controller
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )
        sdn_manager.add_controller(controller)

        # Test redirection
        result = sdn_manager.redirect_traffic(
            controller_name="test_odl",
            switch_id="openflow:1",
            source_ip="192.168.1.100",
            destination_port="2",
            duration=300,
        )

        assert result is True
        mock_controller.add_flow.assert_called_once()

        # Verify flow was tracked
        assert len(sdn_manager.active_flows) == 1

    @patch("src.netsentinel.sdn_integration.OpenDaylightController")
    def test_traffic_mirroring(self, mock_odl_class, sdn_manager):
        """Test traffic mirroring functionality"""
        # Setup mock controller
        mock_controller = Mock()
        mock_odl_class.return_value = mock_controller
        mock_controller.add_flow.return_value = True

        # Add controller
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )
        sdn_manager.add_controller(controller)

        # Test mirroring
        result = sdn_manager.mirror_traffic(
            controller_name="test_odl",
            switch_id="openflow:1",
            source_ip="192.168.1.100",
            mirror_port="3",
            duration=300,
        )

        assert result is True
        mock_controller.add_flow.assert_called_once()

        # Verify flow was tracked
        assert len(sdn_manager.active_flows) == 1

    def test_create_quarantine_flows(self, sdn_manager):
        """Test quarantine flow creation"""
        policy = QuarantinePolicy(
            name="test_quarantine",
            target_ip="192.168.1.100",
            switch_id="openflow:1",
            quarantine_vlan=999,
            duration=3600,
        )

        flows = sdn_manager._create_quarantine_flows(policy)
        assert len(flows) == 1

        flow = flows[0]
        assert flow.switch_id == "openflow:1"
        assert flow.priority == 300
        assert flow.match["ipv4_src"] == "192.168.1.100"
        assert len(flow.actions) > 0  # Should have VLAN actions

    def test_monitoring_loop(self, sdn_manager):
        """Test the monitoring loop functionality"""
        # Add an expired policy
        expired_policy = QuarantinePolicy(
            name="expired_policy",
            target_ip="192.168.1.100",
            switch_id="openflow:1",
            duration=1,  # Very short duration
        )
        expired_policy.created_at = time.time() - 2  # Already expired

        sdn_manager.quarantine_policies["expired_policy"] = expired_policy

        # Run monitoring (should clean up expired policy)
        sdn_manager._monitoring_loop()

        # Policy should still be there (just marked inactive)
        # In real scenario, release_quarantine would be called
        assert "expired_policy" in sdn_manager.quarantine_policies

    def test_get_status(self, sdn_manager):
        """Test status reporting"""
        # Add a controller
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )
        sdn_manager.add_controller(controller)

        # Add a quarantine policy
        policy = QuarantinePolicy(
            name="test_policy", target_ip="192.168.1.100", switch_id="openflow:1"
        )
        sdn_manager.quarantine_policies["test_policy"] = policy

        status = sdn_manager.get_status()
        assert len(status["controllers"]) == 1
        assert status["active_quarantines"] == 1
        assert status["active_flows"] == 0
        assert status["monitoring_active"] is False

    def test_error_handling(self, sdn_manager):
        """Test error handling in SDN operations"""
        # Test with non-existent controller
        result = sdn_manager.quarantine_ip(
            controller_name="non_existent",
            switch_id="openflow:1",
            target_ip="192.168.1.100",
        )
        assert result is False

        # Test with invalid IP
        result = sdn_manager.quarantine_ip(
            controller_name="test_odl",
            switch_id="openflow:1",
            target_ip="invalid.ip.address",
        )
        assert result is False

    def test_concurrent_operations(self, sdn_manager):
        """Test concurrent SDN operations"""
        import threading

        # Add controller
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )
        sdn_manager.add_controller(controller)

        results = []
        errors = []

        def quarantine_worker(ip):
            try:
                result = sdn_manager.quarantine_ip(
                    controller_name="test_odl",
                    switch_id="openflow:1",
                    target_ip=ip,
                    duration=300,
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(3):
            ip = f"192.168.1.{100 + i}"
            thread = threading.Thread(target=quarantine_worker, args=(ip,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 3


class TestSDNManagerIntegration:
    """Integration tests for SDN manager"""

    @pytest.mark.integration
    def test_full_sdn_workflow(self, sdn_manager):
        """Test complete SDN workflow"""
        # This would require actual SDN controllers running
        # For now, test with mocked components

        with patch(
            "src.netsentinel.sdn_integration.OpenDaylightController"
        ) as mock_odl_class:
            mock_controller = Mock()
            mock_odl_class.return_value = mock_controller
            mock_controller.add_flow.return_value = True
            mock_controller.delete_flow.return_value = True

            # Add controller
            controller = SDNController(
                name="test_odl",
                type=SDNControllerType.OPENDLIGHT,
                host="localhost",
                port=8181,
            )
            sdn_manager.add_controller(controller)

            # Test quarantine workflow
            quarantine_result = sdn_manager.quarantine_ip(
                "test_odl", "openflow:1", "192.168.1.100", 3600
            )
            assert quarantine_result is True

            # Test traffic redirection
            redirect_result = sdn_manager.redirect_traffic(
                "test_odl", "openflow:1", "192.168.1.200", "2", 300
            )
            assert redirect_result is True

            # Test quarantine release
            policies = sdn_manager.get_quarantine_policies()
            if policies:
                policy_name = policies[0]["name"]
                release_result = sdn_manager.release_quarantine(policy_name)
                assert release_result is True

    @pytest.mark.performance
    def test_performance_under_load(self, sdn_manager):
        """Test SDN manager performance under load"""

        # Add controller
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )
        sdn_manager.add_controller(controller)

        with patch.object(
            sdn_manager, "get_controller_interface"
        ) as mock_get_interface:
            mock_controller = Mock()
            mock_controller.add_flow.return_value = True
            mock_get_interface.return_value = mock_controller

            # Test multiple quarantine operations
            ips = [f"192.168.1.{i}" for i in range(50, 60)]  # 10 IPs

            start_time = time.time()

            for ip in ips:
                sdn_manager.quarantine_ip("test_odl", "openflow:1", ip, 300)

            end_time = time.time()
            quarantine_time = end_time - start_time

            # Should complete in reasonable time
            assert quarantine_time < 10.0  # Less than 10 seconds for 10 operations

            operations_per_second = len(ips) / quarantine_time
            assert operations_per_second > 1  # At least 1 operation per second

    @pytest.mark.security
    def test_security_validations(self, sdn_manager):
        """Test security validations in SDN operations"""
        # Add controller
        controller = SDNController(
            name="test_odl",
            type=SDNControllerType.OPENDLIGHT,
            host="localhost",
            port=8181,
        )
        sdn_manager.add_controller(controller)

        # Test with malicious switch ID
        malicious_switch = "openflow:1; DROP TABLE switches; --"
        result = sdn_manager.quarantine_ip(
            "test_odl", malicious_switch, "192.168.1.100"
        )
        assert result is False  # Should reject malicious input

        # Test with invalid IP
        result = sdn_manager.quarantine_ip("test_odl", "openflow:1", "invalid.ip")
        assert result is False
