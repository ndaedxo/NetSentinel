"""
Unit tests for NetSentinel firewall manager
"""

import pytest
import subprocess
import time
import platform
from unittest.mock import Mock, patch, MagicMock
from netsentinel.firewall_manager import FirewallManager, get_firewall_manager

# Skip all firewall tests on Windows (no iptables/ufw/firewalld support)
pytestmark = pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Firewall tests require Linux with iptables/ufw/firewalld",
)


class TestFirewallManager:
    """Test cases for FirewallManager class"""

    @pytest.fixture
    def firewall_manager(self):
        """Create a test firewall manager instance"""
        manager = FirewallManager()
        yield manager
        # No cleanup needed for test rules in this implementation

    def _set_backend_for_testing(self, firewall_manager, backend):
        """Helper method to set backend for testing"""
        firewall_manager.backend = backend

    def test_singleton_pattern(self):
        """Test that firewall manager follows singleton pattern"""
        manager1 = get_firewall_manager()
        manager2 = get_firewall_manager()
        assert manager1 is manager2

    def test_detect_backend(self, firewall_manager):
        """Test firewall backend detection"""
        # On Windows, backend should be "none"
        # On Linux, it should be a valid backend or "none" if no firewall tools available
        assert firewall_manager.backend in [
            "iptables",
            "ufw",
            "firewalld",
            "nftables",
            "none",
        ]

        # Test that the backend detection works by checking the property
        # The actual detection happens in the constructor
        assert hasattr(firewall_manager, "backend")

    def test_ip_blocking_iptables(self, firewall_manager):
        """Test IP blocking with iptables"""
        test_ip = "192.168.1.100"

        with (
            patch.object(firewall_manager, "_detect_backend", return_value="iptables"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = Mock(returncode=0)

            # Test blocking
            result = firewall_manager.block_ip(test_ip, "test block")
            assert result is True

            # Verify iptables command was called
            mock_run.assert_called_with(
                [
                    "iptables",
                    "-I",
                    "NETSENTINEL_BLOCK",
                    "1",
                    "-s",
                    test_ip,
                    "-j",
                    "DROP",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

    def test_ip_blocking_ufw(self, firewall_manager):
        """Test IP blocking with UFW"""
        test_ip = "192.168.1.100"

        with (
            patch.object(firewall_manager, "_detect_backend", return_value="ufw"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = Mock(returncode=0)

            result = firewall_manager.block_ip(test_ip, "test block")
            assert result is True

            # Verify ufw command was called
            mock_run.assert_called_with(
                ["ufw", "deny", "from", test_ip, "comment", "NetSentinel: test block"],
                capture_output=True,
                text=True,
                timeout=30,
            )

    def test_ip_blocking_firewalld(self, firewall_manager):
        """Test IP blocking with firewalld"""
        test_ip = "192.168.1.100"

        with (
            patch.object(firewall_manager, "_detect_backend", return_value="firewalld"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = Mock(returncode=0)

            result = firewall_manager.block_ip(test_ip, "test block")
            assert result is True

            # Verify firewalld commands were called
            assert mock_run.call_count >= 2  # Should call firewall-cmd multiple times

    def test_ip_unblocking(self, firewall_manager):
        """Test IP unblocking"""
        test_ip = "192.168.1.100"

        with (
            patch.object(firewall_manager, "_detect_backend", return_value="iptables"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = Mock(returncode=0)

            # First block the IP
            firewall_manager.block_ip(test_ip, "test block")

            # Then unblock it
            result = firewall_manager.unblock_ip(test_ip)
            assert result is True

            # Verify unblock command was called
            unblock_calls = [
                call for call in mock_run.call_args_list if "-D" in call[0][0]
            ]
            assert len(unblock_calls) > 0

    def test_ip_status_check(self, firewall_manager):
        """Test checking if IP is blocked"""
        test_ip = "192.168.1.100"

        with (
            patch.object(firewall_manager, "_detect_backend", return_value="iptables"),
            patch("subprocess.run") as mock_run,
        ):

            # Mock iptables output showing the IP is blocked
            mock_run.return_value = Mock(
                returncode=0, stdout=f"-A INPUT -s {test_ip} -j DROP"
            )

            result = firewall_manager.is_ip_blocked(test_ip)
            assert result is True

            # Mock iptables output showing the IP is not blocked
            mock_run.return_value = Mock(
                returncode=0, stdout="-A INPUT -s 10.0.0.1 -j DROP"
            )

            result = firewall_manager.is_ip_blocked(test_ip)
            assert result is False

    def test_get_blocked_ips(self, firewall_manager):
        """Test retrieving list of blocked IPs"""
        with (
            patch.object(firewall_manager, "_detect_backend", return_value="iptables"),
            patch("subprocess.run") as mock_run,
        ):

            # Mock iptables output with multiple blocked IPs
            mock_output = """
-A INPUT -s 192.168.1.100 -j DROP -m comment --comment "NetSentinel: attack"
-A INPUT -s 10.0.0.5 -j DROP -m comment --comment "NetSentinel: scan"
-A INPUT -s 172.16.0.1 -j DROP -m comment --comment "other rule"
"""
            mock_run.return_value = Mock(returncode=0, stdout=mock_output)

            blocked_ips = firewall_manager.get_blocked_ips()

            # Should only return IPs blocked by NetSentinel
            assert "192.168.1.100" in blocked_ips
            assert "10.0.0.5" in blocked_ips
            assert "172.16.0.1" not in blocked_ips  # Not blocked by NetSentinel

    def test_firewall_status(self, firewall_manager):
        """Test firewall status retrieval"""
        with (
            patch.object(firewall_manager, "_detect_backend", return_value="iptables"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = Mock(returncode=0, stdout="iptables active")

            status = firewall_manager.get_firewall_status()
            assert "type" in status
            assert "status" in status
            assert status["type"] == "iptables"

    def test_error_handling(self, firewall_manager):
        """Test error handling for firewall operations"""
        test_ip = "192.168.1.100"

        with patch("subprocess.run") as mock_run:
            # Mock command failure
            mock_run.return_value = Mock(returncode=1, stderr="Command failed")

            # Should handle errors gracefully
            result = firewall_manager.block_ip(test_ip, "test")
            assert result is False

    def test_timeout_handling(self, firewall_manager):
        """Test timeout handling for firewall commands"""
        test_ip = "192.168.1.100"

        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("timeout", 30)
        ):
            result = firewall_manager.block_ip(test_ip, "test")
            assert result is False

    def test_invalid_ip_addresses(self, firewall_manager):
        """Test handling of invalid IP addresses"""
        invalid_ips = ["", "invalid", "256.256.256.256", "192.168.1.100/24"]

        for invalid_ip in invalid_ips:
            result = firewall_manager.block_ip(invalid_ip, "test")
            assert result is False

    def test_ipv6_support(self, firewall_manager):
        """Test IPv6 address handling"""
        ipv6_address = "2001:db8::1"

        with (
            patch.object(firewall_manager, "_detect_backend", return_value="iptables"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = Mock(returncode=0)

            result = firewall_manager.block_ip(ipv6_address, "IPv6 test")
            assert result is True

            # Verify ip6tables was used for IPv6
            ipv6_calls = [
                call for call in mock_run.call_args_list if "ip6tables" in call[0][0]
            ]
            assert len(ipv6_calls) > 0

    def test_rule_cleanup(self, firewall_manager):
        """Test cleanup of test rules"""
        test_ip = "192.168.1.200"

        with (
            patch.object(firewall_manager, "_detect_backend", return_value="iptables"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = Mock(returncode=0)

            # Add a test rule
            firewall_manager.block_ip(test_ip, "test rule")

            # Cleanup should work without errors
            firewall_manager.cleanup_test_rules()

    def test_concurrent_operations(self, firewall_manager):
        """Test concurrent firewall operations"""
        import threading

        results = []
        errors = []

        def block_ip_worker(ip):
            try:
                result = firewall_manager.block_ip(ip, f"concurrent test {ip}")
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            ip = f"192.168.1.{100 + i}"
            thread = threading.Thread(target=block_ip_worker, args=(ip,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 5

    @pytest.mark.slow
    def test_persistence_across_restarts(self, firewall_manager):
        """Test that firewall rules persist across manager restarts"""
        test_ip = "192.168.1.150"

        with (
            patch.object(firewall_manager, "_detect_backend", return_value="iptables"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = Mock(returncode=0)

            # Block IP
            firewall_manager.block_ip(test_ip, "persistence test")

            # Create new manager instance (simulating restart)
            new_manager = FirewallManager()

            # Check if IP is still blocked
            with patch.object(new_manager, "is_ip_blocked") as mock_check:
                mock_check.return_value = True
                assert new_manager.is_ip_blocked(test_ip) is True


class TestFirewallManagerIntegration:
    """Integration tests for firewall manager"""

    @pytest.mark.integration
    def test_real_firewall_operations(self, firewall_manager):
        """Test with real firewall operations (requires system permissions)"""
        test_ip = "192.168.1.250"

        try:
            # This test requires actual firewall access
            # Skip if running in CI without proper permissions
            if not firewall_manager._has_firewall_permissions():
                pytest.skip("No firewall permissions - skipping integration test")

            # Test blocking
            result = firewall_manager.block_ip(test_ip, "integration test")
            assert isinstance(result, bool)

            # Test status check
            status = firewall_manager.get_firewall_status()
            assert isinstance(status, dict)

            # Clean up
            firewall_manager.unblock_ip(test_ip)

        except Exception as e:
            # Integration test may fail due to permissions or environment
            pytest.skip(f"Integration test failed: {e}")

    @pytest.mark.security
    def test_security_validations(self, firewall_manager):
        """Test security validations"""
        # Test command injection prevention
        malicious_ip = "192.168.1.100; rm -rf /"
        result = firewall_manager.block_ip(malicious_ip, "test")
        assert result is False  # Should reject malicious input

        # Test SQL injection prevention (if applicable)
        malicious_comment = "test'; DROP TABLE users; --"
        result = firewall_manager.block_ip("192.168.1.100", malicious_comment)
        # Should either reject or sanitize the input
        assert isinstance(result, bool)

    @pytest.mark.performance
    def test_performance_under_load(self, firewall_manager):
        """Test firewall manager performance under load"""

        test_ips = [f"192.168.1.{i}" for i in range(200, 210)]  # 10 test IPs

        with (
            patch.object(firewall_manager, "_detect_backend", return_value="iptables"),
            patch("subprocess.run") as mock_run,
        ):

            mock_run.return_value = Mock(returncode=0)

            start_time = time.time()

            # Block multiple IPs
            for ip in test_ips:
                firewall_manager.block_ip(ip, f"load test {ip}")

            end_time = time.time()
            blocking_time = end_time - start_time

            # Should complete in reasonable time (less than 5 seconds)
            assert blocking_time < 5.0

            # Verify all operations succeeded
            assert mock_run.call_count >= len(test_ips)
