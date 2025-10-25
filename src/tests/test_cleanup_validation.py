#!/usr/bin/env python3
"""
Tests to validate that the cleanup didn't break functionality
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports_after_cleanup():
    """Test that all cleaned up modules can still be imported"""
    # Test core imports
    from netsentinel.core.base import BaseComponent, ComponentState
    from netsentinel.core.models import StandardEvent, StandardAlert, create_event
    from netsentinel.core.error_handler import NetSentinelErrorHandler
    from netsentinel.core.container import ServiceContainer

    # Test config import (should work with lazy loading)
    from netsentinel.config import get_config

    # Test utility imports
    from netsentinel.utils.centralized import create_logger, handle_errors_simple

    print("✅ All core imports successful after cleanup")


def test_config_lazy_loading():
    """Test that config lazy loading works"""
    from netsentinel.config import get_config

    # This should not fail even without config file
    # because of lazy loading
    config = get_config()
    assert config is not None
    print("✅ Config lazy loading works")


def test_core_functionality():
    """Test that core functionality still works"""
    from netsentinel.core.models import create_event

    # Test event creation
    event = create_event(event_type="test", source="test_source", data={"key": "value"})
    assert event.event_type == "test"
    assert event.source == "test_source"

    print("✅ Core functionality works after cleanup")


@pytest.mark.asyncio
async def test_error_handling():
    """Test that error handling still works"""
    from netsentinel.core.error_handler import NetSentinelErrorHandler, ErrorContext

    handler = NetSentinelErrorHandler()
    context = ErrorContext("test", "test_operation")

    # Test error handling
    result = await handler.handle_error(ValueError("test"), context)
    assert "status" in result

    print("✅ Error handling works after cleanup")


def test_cleanup_utilities():
    """Test that cleanup utilities still work"""
    from netsentinel.utils.centralized import create_logger, handle_errors_simple

    # Test that utilities can be used
    logger = create_logger("test")
    assert logger is not None

    # Test error handling utility
    try:
        handle_errors_simple(ValueError("test"), "test_context")
    except Exception:
        pass  # Expected to handle the error

    print("✅ Cleanup utilities work after cleanup")


def test_no_print_statements():
    """Test that print statements were properly replaced"""
    import os
    import glob

    # Search for print statements only in netsentinel Python files
    python_files = glob.glob("netsentinel/**/*.py", recursive=True)
    print_statements_found = []

    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line_num, line in enumerate(lines, 1):
                    if "print(" in line and not line.strip().startswith("#"):
                        print_statements_found.append(f"{file_path}:{line_num}")
        except Exception:
            continue

    if print_statements_found:
        print(f"❌ Found print statements: {print_statements_found}")
        assert False, "Found print statements in codebase"
    else:
        print("✅ No print statements found")


def test_long_lines_fixed():
    """Test that long lines were properly broken"""
    import os
    import glob

    # Search for lines longer than 120 characters only in netsentinel files
    python_files = glob.glob("netsentinel/**/*.py", recursive=True)
    long_lines_found = []

    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line_num, line in enumerate(lines, 1):
                    if len(line.rstrip()) > 120:
                        long_lines_found.append(f"{file_path}:{line_num}")
        except Exception:
            continue

    if long_lines_found:
        print(f"❌ Found long lines: {long_lines_found}")
        assert False, "Found long lines in codebase"
    else:
        print("✅ No long lines found")


def run_all_tests():
    """Run all validation tests"""
    tests = [
        test_imports_after_cleanup,
        test_config_lazy_loading,
        test_core_functionality,
        test_error_handling,
        test_cleanup_utilities,
        test_no_print_statements,
        test_long_lines_fixed,
    ]

    passed = 0
    total = len(tests)

    print("🧪 Running cleanup validation tests...")
    print("=" * 50)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All cleanup validation tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
