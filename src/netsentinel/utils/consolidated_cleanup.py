#!/usr/bin/env python3
"""
Consolidated cleanup utility for NetSentinel
Eliminates code debt and consolidates duplicate functionality
"""

import os
import re
import ast
import logging
import time
import threading
from typing import List, Dict, Any, Set, Optional, Callable
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict, deque
import json
import uuid

logger = logging.getLogger(__name__)


@dataclass
class CleanupIssue:
    """Represents a code cleanup issue"""

    file_path: str
    line_number: int
    issue_type: str
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    suggested_fix: str = ""
    auto_fixable: bool = False


class ConsolidatedCleanupUtility:
    """Comprehensive cleanup utility for NetSentinel"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.issues: List[CleanupIssue] = []
        self.fixed_issues: List[CleanupIssue] = []
        self._lock = threading.RLock()

    def scan_codebase(self) -> List[CleanupIssue]:
        """Scan the entire codebase for issues"""
        logger.info(f"Scanning codebase at: {self.base_path}")

        with self._lock:
            self.issues = []

            # Scan Python files
            for py_file in self.base_path.rglob("*.py"):
                if self._should_skip_file(py_file):
                    continue

                self._analyze_file(py_file)

        logger.info(f"Found {len(self.issues)} issues")
        return self.issues

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            "__pycache__",
            ".git",
            ".pytest_cache",
            "venv",
            ".venv",
            "node_modules",
            ".tox",
            "build",
            "dist",
            "egg-info",
        ]

        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=e.lineno or 0,
                        issue_type="syntax_error",
                        description=f"Syntax error: {e.msg}",
                        severity="critical",
                        suggested_fix="Fix syntax error",
                        auto_fixable=False,
                    )
                )
                return

            # Check for various issues
            self._check_imports(file_path, content, tree)
            self._check_error_handling(file_path, content, tree)
            self._check_code_quality(file_path, content, tree)
            self._check_security_issues(file_path, content, tree)
            self._check_performance_issues(file_path, content, tree)
            self._check_resource_management(file_path, content, tree)

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")

    def _check_imports(self, file_path: Path, content: str, tree: ast.AST):
        """Check for import-related issues"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # Check for wildcard imports
                if node.names and any(name.name == "*" for name in node.names):
                    self.issues.append(
                        CleanupIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            issue_type="wildcard_import",
                            description="Wildcard import detected",
                            severity="medium",
                            suggested_fix="Import specific items instead of using '*'",
                            auto_fixable=False,
                        )
                    )

                # Check for relative imports that could be absolute
                if node.level > 0 and node.module and not node.module.startswith("."):
                    self.issues.append(
                        CleanupIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            issue_type="relative_import",
                            description="Relative import that could be absolute",
                            severity="low",
                            suggested_fix="Consider using absolute imports",
                            auto_fixable=False,
                        )
                    )

    def _check_error_handling(self, file_path: Path, content: str, tree: ast.AST):
        """Check for error handling issues"""
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for bare except clauses
            if re.search(r"except:\s*$", line):
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="bare_except",
                        description="Bare except clause found",
                        severity="high",
                        suggested_fix="Specify exception type",
                        auto_fixable=True,
                    )
                )

            # Check for empty except blocks
            if re.search(r"except.*:\s*pass\s*$", line):
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="empty_except",
                        description="Empty except block found",
                        severity="medium",
                        suggested_fix="Add proper exception handling or logging",
                        auto_fixable=False,
                    )
                )

    def _check_code_quality(self, file_path: Path, content: str, tree: ast.AST):
        """Check for code quality issues"""
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for TODO/FIXME comments
            if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", line, re.IGNORECASE):
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="todo_comment",
                        description=f"TODO/FIXME comment found: {line.strip()}",
                        severity="low",
                        suggested_fix="Address the TODO/FIXME comment",
                        auto_fixable=False,
                    )
                )

            # Check for print statements
            if re.search(r"\bprint\s*\(", line):
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="print_statement",
                        description="Print statement detected",
                        severity="low",
                        suggested_fix="Use logging instead of print statements",
                        auto_fixable=True,
                    )
                )

            # Check for long lines
            if len(line) > 120:
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="long_line",
                        description=f"Line too long ({len(line)} characters)",
                        severity="low",
                        suggested_fix="Break long lines for better readability",
                        auto_fixable=False,
                    )
                )

    def _check_security_issues(self, file_path: Path, content: str, tree: ast.AST):
        """Check for security issues"""
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for hardcoded secrets
            secret_patterns = [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
            ]

            for pattern in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if it's a placeholder value
                    if not re.search(
                        r"(<not supplied>|Invalid|placeholder|example)",
                        line,
                        re.IGNORECASE,
                    ):
                        self.issues.append(
                            CleanupIssue(
                                file_path=str(file_path),
                                line_number=i,
                                issue_type="hardcoded_secret",
                                description="Potential hardcoded secret found",
                                severity="high",
                                suggested_fix="Use environment variables or secure configuration",
                                auto_fixable=False,
                            )
                        )

            # Check for eval usage
            if "eval(" in line:
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="eval_usage",
                        description="eval() usage found - security risk",
                        severity="critical",
                        suggested_fix="Use safer alternatives to eval()",
                        auto_fixable=False,
                    )
                )

    def _check_performance_issues(self, file_path: Path, content: str, tree: ast.AST):
        """Check for performance issues"""
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for inefficient string concatenation in loops
            if "for " in line and "+=" in line:
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="inefficient_string_concat",
                        description="Potential inefficient string concatenation in loop",
                        severity="low",
                        suggested_fix="Use join() or f-strings for better performance",
                        auto_fixable=False,
                    )
                )

            # Check for global variables
            if "global " in line:
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="global_variable",
                        description="Global variable usage found",
                        severity="medium",
                        suggested_fix="Consider using dependency injection or class attributes",
                        auto_fixable=False,
                    )
                )

    def _check_resource_management(self, file_path: Path, content: str, tree: ast.AST):
        """Check for resource management issues"""
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for file operations without context managers
            if (
                re.search(r"open\s*\(", line)
                and "with " not in lines[max(0, i - 3) : i]
            ):
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="file_without_context_manager",
                        description="File operation without context manager",
                        severity="medium",
                        suggested_fix="Use 'with' statement for automatic resource cleanup",
                        auto_fixable=False,
                    )
                )

            # Check for potential memory leaks
            if "deque(" in line and "maxlen" not in line:
                self.issues.append(
                    CleanupIssue(
                        file_path=str(file_path),
                        line_number=i,
                        issue_type="unbounded_deque",
                        description="Unbounded deque could cause memory leaks",
                        severity="medium",
                        suggested_fix="Add maxlen parameter to deque",
                        auto_fixable=True,
                    )
                )

    def fix_issues(self, auto_fix: bool = False) -> List[CleanupIssue]:
        """Fix identified issues"""
        logger.info(f"Fixing {len(self.issues)} issues")

        fixed_issues = []

        with self._lock:
            for issue in self.issues:
                if issue.severity in ["critical", "high"] or (
                    auto_fix and issue.auto_fixable
                ):
                    if self._apply_fix(issue):
                        fixed_issues.append(issue)
                        logger.info(
                            f"Fixed issue: {issue.issue_type} in {issue.file_path}:{issue.line_number}"
                        )
                    else:
                        logger.warning(
                            f"Manual fix required: {issue.issue_type} in "
                            f"{issue.file_path}:{issue.line_number}"
                        )

        self.fixed_issues.extend(fixed_issues)
        return fixed_issues

    def _apply_fix(self, issue: CleanupIssue) -> bool:
        """Apply a fix to an issue"""
        try:
            if issue.issue_type == "print_statement":
                return self._fix_print_statement(issue)
            elif issue.issue_type == "bare_except":
                return self._fix_bare_except(issue)
            elif issue.issue_type == "unbounded_deque":
                return self._fix_unbounded_deque(issue)
            else:
                return False
        except Exception as e:
            logger.error(f"Error applying fix for {issue.issue_type}: {e}")
            return False

    def _fix_print_statement(self, issue: CleanupIssue) -> bool:
        """Fix print statement by replacing with logging"""
        try:
            with open(issue.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            if issue.line_number <= len(lines):
                line = lines[issue.line_number - 1]
                # Replace print with logger.info (simplified)
                fixed_line = re.sub(r"\bprint\s*\(", "logger.info(", line)
                lines[issue.line_number - 1] = fixed_line

                with open(issue.file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                return True
        except Exception as e:
            logger.error(f"Error fixing print statement: {e}")
            return False

    def _fix_bare_except(self, issue: CleanupIssue) -> bool:
        """Fix bare except clause"""
        try:
            with open(issue.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace bare except with Exception
            fixed_content = re.sub(
                r"except:\s*$", "except Exception:", content, flags=re.MULTILINE
            )

            if fixed_content != content:
                with open(issue.file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)
                return True
        except Exception as e:
            logger.error(f"Error fixing bare except: {e}")
            return False

    def _fix_unbounded_deque(self, issue: CleanupIssue) -> bool:
        """Fix unbounded deque by adding maxlen"""
        try:
            with open(issue.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            if issue.line_number <= len(lines):
                line = lines[issue.line_number - 1]
                # Add maxlen parameter to deque
                fixed_line = re.sub(r"deque\s*\(", "deque(maxlen=1000, ", line)
                lines[issue.line_number - 1] = fixed_line

                with open(issue.file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                return True
        except Exception as e:
            logger.error(f"Error fixing unbounded deque: {e}")
            return False

    def generate_report(self) -> str:
        """Generate a comprehensive report of issues found"""
        report = []
        report.append("NetSentinel Consolidated Cleanup Report")
        report.append("=" * 50)
        report.append(f"Total issues found: {len(self.issues)}")
        report.append(f"Issues fixed: {len(self.fixed_issues)}")
        report.append("")

        # Group issues by severity
        by_severity = defaultdict(list)
        for issue in self.issues:
            by_severity[issue.severity].append(issue)

        for severity in ["critical", "high", "medium", "low"]:
            if severity in by_severity:
                report.append(
                    f"{severity.upper()} Issues ({len(by_severity[severity])}):"
                )
                for issue in by_severity[severity]:
                    report.append(
                        f"  {issue.file_path}:{issue.line_number} - {issue.description}"
                    )
                report.append("")

        return "\n".join(report)

    def consolidate_utilities(self) -> Dict[str, Any]:
        """Consolidate duplicate utility functions"""
        consolidation_report = {
            "duplicate_functions": [],
            "consolidation_opportunities": [],
            "recommendations": [],
        }

        # This would analyze the codebase for duplicate utility functions
        # and suggest consolidation opportunities

        return consolidation_report


def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(
        description="NetSentinel Consolidated Cleanup Utility"
    )
    parser.add_argument("path", help="Path to scan")
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix issues where possible"
    )
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument(
        "--consolidate", action="store_true", help="Analyze consolidation opportunities"
    )

    args = parser.parse_args()

    cleanup = ConsolidatedCleanupUtility(args.path)
    issues = cleanup.scan_codebase()

    if args.fix:
        cleanup.fix_issues(auto_fix=True)

    if args.report:
        logger.info(cleanup.generate_report())

    if args.consolidate:
        consolidation = cleanup.consolidate_utilities()
        logger.info(f"Consolidation analysis: {consolidation}")

    return len(issues)


if __name__ == "__main__":
    main()
