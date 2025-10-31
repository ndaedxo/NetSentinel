#!/usr/bin/env python3
"""
Authentication Performance Tests for NetSentinel
Tests latency, concurrency, scalability, and resource usage
"""

import pytest
import time
import threading
import statistics
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from src.netsentinel.security.auth_manager import AuthManager
from src.netsentinel.security.user_store import Role


class TestAuthenticationPerformance:
    """Performance tests for authentication system"""

    def setup_method(self):
        """Setup test fixtures with multiple users for performance testing"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"perf_test_{self.test_id}"
        self.storage_path = f"data/test_users_perf_{self.test_id}.json"
        self.auth_manager = AuthManager(self.secret_key, self.storage_path)

        # Create multiple test users for performance testing
        self.users = []
        for i in range(100):  # Create 100 users for load testing
            username = f"perfuser_{i}_{self.test_id}"
            password_hash = f"password_hash_{i}"
            email = f"perfuser_{i}_{self.test_id}@test.com"

            user = self.auth_manager.create_user(
                user_id=f"perf_user_{i}_{self.test_id}",
                username=username,
                email=email,
                password_hash=password_hash,
                roles=[Role.VIEWER],
            )
            self.users.append({
                'user': user,
                'username': username,
                'password_hash': password_hash,
                'token': None
            })

        # Pre-authenticate some users for token validation tests
        for user_data in self.users[:10]:  # Pre-auth 10 users
            token = self.auth_manager.authenticate_credentials(
                user_data['username'],
                user_data['password_hash']
            )
            user_data['token'] = token

    def teardown_method(self):
        """Cleanup after tests"""
        # Clean up any created files
        if os.path.exists(self.storage_path):
            try:
                os.remove(self.storage_path)
            except:
                pass


class TestLatencyPerformance:
    """Test authentication latency performance"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"latency_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

        # Create a test user
        self.username = f"latencyuser_{self.test_id}"
        self.password_hash = "latency_password_hash"

        self.auth_manager.create_user(
            user_id=f"latency_user_{self.test_id}",
            username=self.username,
            email=f"latency_{self.test_id}@test.com",
            password_hash=self.password_hash,
            roles=[Role.ANALYST],
        )

        # Get a valid token for validation tests
        self.valid_token = self.auth_manager.authenticate_credentials(
            self.username,
            self.password_hash
        )

    def test_authentication_latency(self):
        """Test authentication operation latency"""
        latencies = []

        # Perform multiple authentication operations
        for i in range(100):
            start_time = time.perf_counter()
            token = self.auth_manager.authenticate_credentials(
                self.username,
                self.password_hash
            )
            end_time = time.perf_counter()

            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency)
            assert token is not None

        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        max_latency = max(latencies)

        print(f"\nAuthentication Latency Statistics:")
        print(f"Average: {avg_latency:.2f}ms")
        print(f"Median: {median_latency:.2f}ms")
        print(f"95th percentile: {p95_latency:.2f}ms")
        print(f"Maximum: {max_latency:.2f}ms")

        # Performance requirements
        assert avg_latency < 50.0, f"Average latency {avg_latency:.2f}ms exceeds 50ms target"
        assert p95_latency < 100.0, f"P95 latency {p95_latency:.2f}ms too high"
        assert max_latency < 500.0, f"Maximum latency {max_latency:.2f}ms too high"

    def test_token_validation_latency(self):
        """Test token validation operation latency"""
        latencies = []

        # Perform multiple token validation operations
        for i in range(100):
            start_time = time.perf_counter()
            user = self.auth_manager.authenticate_token(self.valid_token)
            end_time = time.perf_counter()

            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency)
            assert user is not None

        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        max_latency = max(latencies)

        print(f"\nToken Validation Latency Statistics:")
        print(f"Average: {avg_latency:.2f}ms")
        print(f"Median: {median_latency:.2f}ms")
        print(f"95th percentile: {p95_latency:.2f}ms")
        print(f"Maximum: {max_latency:.2f}ms")

        # Token validation should be very fast
        assert avg_latency < 10.0, f"Average token validation latency {avg_latency:.2f}ms too high"
        assert p95_latency < 20.0, f"P95 token validation latency {p95_latency:.2f}ms too high"

    def test_user_lookup_latency(self):
        """Test user lookup operation latency"""
        latencies = []

        # Perform multiple user lookup operations
        for i in range(100):
            start_time = time.perf_counter()
            user = self.auth_manager.get_user_by_username(self.username)
            end_time = time.perf_counter()

            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency)
            assert user is not None

        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

        print(f"\nUser Lookup Latency Statistics:")
        print(f"Average: {avg_latency:.2f}ms")
        print(f"Median: {median_latency:.2f}ms")
        print(f"95th percentile: {p95_latency:.2f}ms")

        # User lookup should be fast
        assert avg_latency < 5.0, f"Average user lookup latency {avg_latency:.2f}ms too high"


class TestConcurrentPerformance:
    """Test concurrent authentication performance"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"concurrent_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

        # Create multiple test users for concurrent testing
        self.test_users = []
        for i in range(50):
            username = f"concurrent_user_{i}_{self.test_id}"
            password_hash = f"password_{i}"

            self.auth_manager.create_user(
                user_id=f"concurrent_user_{i}_{self.test_id}",
                username=username,
                email=f"concurrent_{i}_{self.test_id}@test.com",
                password_hash=password_hash,
                roles=[Role.VIEWER],
            )

            self.test_users.append((username, password_hash))

    def test_concurrent_authentication(self):
        """Test concurrent authentication requests"""
        results = []
        errors = []
        latencies = []

        def authenticate_worker(user_data):
            username, password_hash = user_data
            start_time = time.perf_counter()

            try:
                token = self.auth_manager.authenticate_credentials(username, password_hash)
                end_time = time.perf_counter()

                latency = (end_time - start_time) * 1000  # Convert to milliseconds
                latencies.append(latency)

                if token is not None:
                    results.append(token)
                else:
                    errors.append(f"Failed to authenticate {username}")

            except Exception as e:
                errors.append(f"Exception for {username}: {e}")

        # Test with different concurrency levels
        concurrency_levels = [10, 25, 50, 100]

        for num_threads in concurrency_levels:
            print(f"\nTesting with {num_threads} concurrent authentications...")

            results.clear()
            errors.clear()
            latencies.clear()

            # Create and start threads
            threads = []
            for i in range(num_threads):
                user_data = self.test_users[i % len(self.test_users)]
                thread = threading.Thread(target=authenticate_worker, args=(user_data,))
                threads.append(thread)

            start_time = time.time()
            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            total_time = time.time() - start_time

            # Analyze results
            success_rate = len(results) / num_threads * 100
            avg_latency = statistics.mean(latencies) if latencies else 0
            max_latency = max(latencies) if latencies else 0

            print(f"Concurrency {num_threads}: Success rate: {success_rate:.1f}%, "
                  f"Avg latency: {avg_latency:.2f}ms, Max latency: {max_latency:.2f}ms, "
                  f"Total time: {total_time:.2f}s")

            # Performance assertions
            assert success_rate >= 95.0, f"Success rate {success_rate:.1f}% too low for {num_threads} concurrent requests"

            # Adjust latency expectations based on concurrency level (realistic targets)
            max_expected_latency = 80.0 if num_threads <= 10 else 150.0 if num_threads <= 25 else 200.0
            assert avg_latency < max_expected_latency, f"Average latency {avg_latency:.2f}ms too high for {num_threads} concurrent requests (expected < {max_expected_latency}ms)"

            # For high concurrency, ensure reasonable performance
            if num_threads >= 50:
                assert max_latency < 1000.0, f"Maximum latency {max_latency:.2f}ms too high for high concurrency"

    def test_concurrent_token_validation(self):
        """Test concurrent token validation requests"""
        # First, get tokens for all users
        tokens = []
        for username, password_hash in self.test_users:
            token = self.auth_manager.authenticate_credentials(username, password_hash)
            tokens.append(token)

        results = []
        errors = []
        latencies = []

        def validate_token_worker(token):
            start_time = time.perf_counter()

            try:
                user = self.auth_manager.authenticate_token(token)
                end_time = time.perf_counter()

                latency = (end_time - start_time) * 1000  # Convert to milliseconds
                latencies.append(latency)

                if user is not None:
                    results.append(user)
                else:
                    errors.append(f"Failed to validate token")

            except Exception as e:
                errors.append(f"Exception validating token: {e}")

        # Test concurrent token validation
        for num_threads in [25, 50, 100]:
            print(f"\nTesting token validation with {num_threads} concurrent requests...")

            results.clear()
            errors.clear()
            latencies.clear()

            threads = []
            for i in range(num_threads):
                token = tokens[i % len(tokens)]
                thread = threading.Thread(target=validate_token_worker, args=(token,))
                threads.append(thread)

            start_time = time.time()
            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            total_time = time.time() - start_time

            success_rate = len(results) / num_threads * 100
            avg_latency = statistics.mean(latencies) if latencies else 0
            max_latency = max(latencies) if latencies else 0

            print(f"Token validation {num_threads}: Success rate: {success_rate:.1f}%, "
                  f"Avg latency: {avg_latency:.2f}ms, Max latency: {max_latency:.2f}ms")

            # Token validation should be very fast even under load
            assert success_rate >= 99.0, f"Token validation success rate {success_rate:.1f}% too low"
            assert avg_latency < 20.0, f"Average token validation latency {avg_latency:.2f}ms too high"


class TestScalabilityPerformance:
    """Test scalability with large numbers of users and operations"""

    def setup_method(self):
        """Setup test fixtures for scalability testing"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"scalability_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

        # Create a large number of users for scalability testing
        self.num_users = 500
        self.test_users = []

        print(f"Creating {self.num_users} users for scalability testing...")

        for i in range(self.num_users):
            username = f"scale_user_{i}_{self.test_id}"
            password_hash = f"scale_password_{i}"

            user = self.auth_manager.create_user(
                user_id=f"scale_user_{i}_{self.test_id}",
                username=username,
                email=f"scale_{i}_{self.test_id}@test.com",
                password_hash=password_hash,
                roles=[Role.VIEWER],
            )

            self.test_users.append((username, password_hash))

        print(f"Created {len(self.test_users)} users successfully")

    def test_large_scale_authentication(self):
        """Test authentication performance with many users"""
        # Test authentication operations across many users
        latencies = []

        # Sample a subset of users for performance testing
        test_sample = self.test_users[:100]  # Test 100 users

        print(f"Testing authentication performance with {len(test_sample)} users...")

        for username, password_hash in test_sample:
            start_time = time.perf_counter()
            token = self.auth_manager.authenticate_credentials(username, password_hash)
            end_time = time.perf_counter()

            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency)
            assert token is not None

        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]

        print(f"Large scale authentication - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")

        # Performance should still be good with many users
        assert avg_latency < 100.0, f"Average latency {avg_latency:.2f}ms too high with many users"
        assert p95_latency < 200.0, f"P95 latency {p95_latency:.2f}ms too high with many users"

    def test_user_lookup_scalability(self):
        """Test user lookup performance with large user base"""
        latencies = []

        # Test lookups for random users
        test_usernames = [user[0] for user in self.test_users[:50]]  # Test 50 lookups

        print(f"Testing user lookup scalability with {len(test_usernames)} lookups...")

        for username in test_usernames:
            start_time = time.perf_counter()
            user = self.auth_manager.get_user_by_username(username)
            end_time = time.perf_counter()

            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency)
            assert user is not None

        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)

        print(f"User lookup scalability - Avg: {avg_latency:.2f}ms, Max: {max_latency:.2f}ms")

        # User lookups should remain fast
        assert avg_latency < 10.0, f"Average user lookup latency {avg_latency:.2f}ms too high"
        assert max_latency < 50.0, f"Maximum user lookup latency {max_latency:.2f}ms too high"


class TestMemoryPerformance:
    """Test memory usage during authentication operations"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"memory_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

        # Create test users
        self.test_users = []
        for i in range(100):
            username = f"memory_user_{i}_{self.test_id}"
            password_hash = f"memory_password_{i}"

            self.auth_manager.create_user(
                user_id=f"memory_user_{i}_{self.test_id}",
                username=username,
                email=f"memory_{i}_{self.test_id}@test.com",
                password_hash=password_hash,
                roles=[Role.ANALYST],
            )

            self.test_users.append((username, password_hash))

    def test_memory_usage_during_operations(self):
        """Test memory usage during authentication operations"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_readings = []

        # Perform many authentication operations and monitor memory
        for i in range(100):
            # Record memory before operation
            mem_before = process.memory_info().rss / 1024 / 1024

            # Perform authentication
            username, password_hash = self.test_users[i % len(self.test_users)]
            token = self.auth_manager.authenticate_credentials(username, password_hash)

            # Record memory after operation
            mem_after = process.memory_info().rss / 1024 / 1024

            memory_readings.append(mem_after)
            assert token is not None

        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        max_memory = max(memory_readings)
        avg_memory = statistics.mean(memory_readings)

        print(f"\nMemory Usage Statistics:")
        print(f"Initial memory: {initial_memory:.1f} MB")
        print(f"Final memory: {final_memory:.1f} MB")
        print(f"Memory increase: {memory_increase:.1f} MB")
        print(f"Average memory: {avg_memory:.1f} MB")
        print(f"Maximum memory: {max_memory:.1f} MB")

        # Memory usage should be reasonable
        assert memory_increase < 50.0, f"Memory increase {memory_increase:.1f} MB too high"
        assert max_memory < 200.0, f"Peak memory usage {max_memory:.1f} MB too high"


class TestThroughputPerformance:
    """Test authentication system throughput"""

    def setup_method(self):
        """Setup test fixtures"""
        import uuid
        self.test_id = str(uuid.uuid4())[:8]
        self.secret_key = f"throughput_test_{self.test_id}"
        self.auth_manager = AuthManager(self.secret_key)

        # Create test users
        self.test_users = []
        for i in range(20):
            username = f"throughput_user_{i}_{self.test_id}"
            password_hash = f"throughput_password_{i}"

            self.auth_manager.create_user(
                user_id=f"throughput_user_{i}_{self.test_id}",
                username=username,
                email=f"throughput_{i}_{self.test_id}@test.com",
                password_hash=password_hash,
                roles=[Role.VIEWER],
            )

            self.test_users.append((username, password_hash))

    def test_authentication_throughput(self):
        """Test authentication throughput (operations per second)"""
        def auth_operation(user_data):
            username, password_hash = user_data
            token = self.auth_manager.authenticate_credentials(username, password_hash)
            return token is not None

        # Test throughput with different loads
        test_durations = [5, 10]  # seconds
        target_throughput = 100  # operations per second target

        for duration in test_durations:
            print(f"\nTesting throughput for {duration} seconds...")

            operations_completed = 0
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []

                while time.time() - start_time < duration:
                    # Submit authentication operations
                    for _ in range(10):  # Batch submit 10 operations
                        user_data = self.test_users[operations_completed % len(self.test_users)]
                        future = executor.submit(auth_operation, user_data)
                        futures.append(future)
                        operations_completed += 1

                        if time.time() - start_time >= duration:
                            break

                    # Wait for some completions to avoid queue buildup
                    if len(futures) > 50:
                        for future in as_completed(futures[:20]):
                            assert future.result() == True
                        futures = futures[20:]

                # Wait for remaining operations
                for future in as_completed(futures):
                    assert future.result() == True

            actual_duration = time.time() - start_time
            throughput = operations_completed / actual_duration

            print(f"Completed {operations_completed} operations in {actual_duration:.2f}s")
            print(f"Throughput: {throughput:.1f} operations/second")

            # Should achieve reasonable throughput
            assert throughput >= target_throughput * 0.5, f"Throughput {throughput:.1f} ops/sec below minimum target"
