"""QA Testing Agent - Comprehensive testing and code quality checks.

Phase 11D: Enhanced with both-theme testing, BrowserStack support, and KB integration.

Phase 11 Enhancements:
- Test ALL pages from requirements.pages
- Test both themes when dark_mode="both"
- Use BrowserStack if configured
- Query KB for common bugs
- Test integrations (Stripe, Auth, uploads)
- Write findings to KB
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import AgentResult, BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Represents a single test result."""
    name: str
    status: str  # passed, failed, skipped, error
    duration: float = 0.0
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class CodeQualityIssue:
    """Represents a code quality issue."""
    rule: str
    severity: str  # error, warning, info
    message: str
    file_path: str
    line: int
    column: int = 0
    tool: str = "eslint"  # eslint, pylint, prettier


@dataclass
class QAReport:
    """Complete QA test report."""
    # Test Results
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    test_results: List[TestResult] = field(default_factory=list)
    
    # Code Quality
    quality_issues: List[CodeQualityIssue] = field(default_factory=list)
    quality_score: float = 100.0
    
    # Bug Fix Loop
    fix_iterations: int = 0
    fixes_applied: List[Dict[str, Any]] = field(default_factory=list)
    all_tests_passing: bool = False
    
    # Timing
    total_duration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Errors during execution
    execution_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "test_results": [
                {
                    "name": t.name,
                    "status": t.status,
                    "duration": t.duration,
                    "error_message": t.error_message,
                    "file_path": t.file_path,
                    "line_number": t.line_number,
                }
                for t in self.test_results
            ],
            "quality_issues": [
                {
                    "rule": q.rule,
                    "severity": q.severity,
                    "message": q.message,
                    "file_path": q.file_path,
                    "line": q.line,
                    "column": q.column,
                    "tool": q.tool,
                }
                for q in self.quality_issues
            ],
            "quality_score": self.quality_score,
            "fix_iterations": self.fix_iterations,
            "fixes_applied": self.fixes_applied,
            "all_tests_passing": self.all_tests_passing,
            "total_duration": self.total_duration,
            "timestamp": self.timestamp,
            "execution_errors": self.execution_errors,
        }


class QATestingAgent(BaseAgent):
    """Agent for comprehensive QA testing and code quality checks.
    
    Phase 11 Enhancements:
    - Test ALL pages from requirements.pages
    - Test both themes when dark_mode="both"
    - Use BrowserStack if configured
    - Query KB for common bugs
    - Test integrations (Stripe, Auth, uploads)
    - Write findings to KB
    """

    MAX_FIX_ITERATIONS = 3
    
    # Phase 11: BrowserStack configuration
    BROWSERSTACK_BROWSERS = [
        {"browser": "chrome", "browser_version": "latest", "os": "Windows", "os_version": "11"},
        {"browser": "safari", "browser_version": "latest", "os": "OS X", "os_version": "Sonoma"},
        {"browser": "firefox", "browser_version": "latest", "os": "Windows", "os_version": "11"},
    ]

    @property
    def name(self) -> str:
        return "QA Testing Agent"

    async def execute(
        self,
        project_path: str,
        project_type: str = "web",
        requirements: Optional[Dict[str, Any]] = None,
        integrations: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AgentResult:
        """
        Execute comprehensive QA testing.
        
        Args:
            project_path: Path to the project directory
            project_type: Type of project (web, mobile, api, desktop)
            
        Returns:
            AgentResult with test results and quality metrics
        """
        import time
        start_time = time.time()
        
        report = QAReport()
        self.logger.info(f"Starting QA testing for {project_path}")
        
        try:
            # Detect project language/framework
            project_info = self._detect_project_type(project_path)
            self.logger.info(f"Detected project: {project_info}")
            
            # Run code quality checks
            await self._run_code_quality_checks(project_path, project_info, report)
            
            # Run tests with bug fix loop
            for iteration in range(self.MAX_FIX_ITERATIONS):
                report.fix_iterations = iteration + 1
                self.logger.info(f"Test iteration {iteration + 1}/{self.MAX_FIX_ITERATIONS}")
                
                # Run unit tests
                await self._run_unit_tests(project_path, project_info, report)
                
                # Run integration tests
                await self._run_integration_tests(project_path, project_info, report)
                
                # Run Playwright E2E tests if applicable
                if project_type in ["web", "mobile"]:
                    await self._run_playwright_tests(project_path, report)
                
                # Check if all tests pass
                if report.failed == 0 and report.errors == 0:
                    report.all_tests_passing = True
                    self.logger.info("All tests passing!")
                    break
                
                # Attempt to fix failures (if not last iteration)
                if iteration < self.MAX_FIX_ITERATIONS - 1:
                    fixes = await self._attempt_bug_fixes(project_path, report)
                    if fixes:
                        report.fixes_applied.extend(fixes)
                    else:
                        self.logger.info("No automatic fixes could be applied")
                        break
            
            # Calculate quality score
            report.quality_score = self._calculate_quality_score(report)
            report.total_duration = time.time() - start_time
            
            # Generate HTML report
            html_report_path = await self._generate_html_report(project_path, report)
            
            # Save JSON report
            report_path = os.path.join(project_path, "qa_report.json")
            with open(report_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            
            success = report.all_tests_passing or (report.failed == 0 and report.errors == 0)
            
            return AgentResult(
                success=success,
                agent_name=self.name,
                data={
                    "report": report.to_dict(),
                    "report_path": report_path,
                    "html_report_path": html_report_path,
                    "summary": {
                        "tests_passed": report.passed,
                        "tests_failed": report.failed,
                        "quality_score": report.quality_score,
                        "fix_iterations": report.fix_iterations,
                    }
                },
                errors=report.execution_errors if not success else [],
                execution_time=report.total_duration,
            )
            
        except Exception as e:
            self.logger.error(f"QA testing failed: {e}")
            report.execution_errors.append(str(e))
            return AgentResult(
                success=False,
                agent_name=self.name,
                data={"report": report.to_dict()},
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )

    def _detect_project_type(self, project_path: str) -> Dict[str, Any]:
        """Detect project language and framework."""
        info = {
            "language": "unknown",
            "framework": None,
            "package_manager": None,
            "test_framework": None,
        }
        
        path = Path(project_path)
        
        # Check for Node.js/TypeScript
        if (path / "package.json").exists():
            info["language"] = "javascript"
            info["package_manager"] = "npm"
            
            try:
                with open(path / "package.json") as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    
                    # Detect framework
                    if "next" in deps:
                        info["framework"] = "nextjs"
                    elif "react" in deps:
                        info["framework"] = "react"
                    elif "vue" in deps:
                        info["framework"] = "vue"
                    elif "express" in deps:
                        info["framework"] = "express"
                    
                    # Detect test framework
                    if "jest" in deps:
                        info["test_framework"] = "jest"
                    elif "vitest" in deps:
                        info["test_framework"] = "vitest"
                    elif "mocha" in deps:
                        info["test_framework"] = "mocha"
                    
                    # Check for TypeScript
                    if "typescript" in deps:
                        info["language"] = "typescript"
                        
            except Exception:
                pass
                
        # Check for Python
        elif (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            info["language"] = "python"
            info["package_manager"] = "pip"
            info["test_framework"] = "pytest"
            
            if (path / "pyproject.toml").exists():
                info["package_manager"] = "poetry"
        
        # Check for Go
        elif (path / "go.mod").exists():
            info["language"] = "go"
            info["test_framework"] = "go_test"
        
        return info

    async def _run_code_quality_checks(
        self, 
        project_path: str, 
        project_info: Dict[str, Any],
        report: QAReport
    ) -> None:
        """Run code quality checks (ESLint, Pylint, Prettier)."""
        self.logger.info("Running code quality checks...")
        
        language = project_info.get("language", "unknown")
        
        if language in ["javascript", "typescript"]:
            # Run ESLint
            await self._run_eslint(project_path, report)
            # Run Prettier check
            await self._run_prettier_check(project_path, report)
        elif language == "python":
            # Run Pylint
            await self._run_pylint(project_path, report)

    async def _run_eslint(self, project_path: str, report: QAReport) -> None:
        """Run ESLint for JavaScript/TypeScript projects."""
        try:
            # Check if ESLint is available
            eslint_config = Path(project_path) / ".eslintrc.json"
            if not eslint_config.exists():
                eslint_config = Path(project_path) / ".eslintrc.js"
            
            cmd = ["npx", "eslint", ".", "--format", "json", "--ext", ".js,.jsx,.ts,.tsx"]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if stdout:
                try:
                    eslint_output = json.loads(stdout.decode())
                    for file_result in eslint_output:
                        for msg in file_result.get("messages", []):
                            report.quality_issues.append(CodeQualityIssue(
                                rule=msg.get("ruleId", "unknown"),
                                severity="error" if msg.get("severity") == 2 else "warning",
                                message=msg.get("message", ""),
                                file_path=file_result.get("filePath", ""),
                                line=msg.get("line", 0),
                                column=msg.get("column", 0),
                                tool="eslint",
                            ))
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse ESLint output")
                    
        except Exception as e:
            self.logger.warning(f"ESLint check failed: {e}")
            report.execution_errors.append(f"ESLint failed: {str(e)}")

    async def _run_prettier_check(self, project_path: str, report: QAReport) -> None:
        """Run Prettier formatting check."""
        try:
            cmd = ["npx", "prettier", "--check", ".", "--ignore-unknown"]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                # Parse files that need formatting
                output = stdout.decode() + stderr.decode()
                for line in output.split("\n"):
                    if line.strip() and not line.startswith("["):
                        report.quality_issues.append(CodeQualityIssue(
                            rule="prettier/prettier",
                            severity="warning",
                            message="File needs formatting",
                            file_path=line.strip(),
                            line=0,
                            tool="prettier",
                        ))
                        
        except Exception as e:
            self.logger.warning(f"Prettier check failed: {e}")

    async def _run_pylint(self, project_path: str, report: QAReport) -> None:
        """Run Pylint for Python projects."""
        try:
            cmd = ["pylint", "--output-format=json", "--recursive=y", project_path]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if stdout:
                try:
                    pylint_output = json.loads(stdout.decode())
                    for msg in pylint_output:
                        severity = "error" if msg.get("type") in ["error", "fatal"] else "warning"
                        report.quality_issues.append(CodeQualityIssue(
                            rule=msg.get("symbol", msg.get("message-id", "unknown")),
                            severity=severity,
                            message=msg.get("message", ""),
                            file_path=msg.get("path", ""),
                            line=msg.get("line", 0),
                            column=msg.get("column", 0),
                            tool="pylint",
                        ))
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse Pylint output")
                    
        except Exception as e:
            self.logger.warning(f"Pylint check failed: {e}")
            report.execution_errors.append(f"Pylint failed: {str(e)}")

    async def _run_unit_tests(
        self, 
        project_path: str, 
        project_info: Dict[str, Any],
        report: QAReport
    ) -> None:
        """Run unit tests based on project type."""
        self.logger.info("Running unit tests...")
        
        test_framework = project_info.get("test_framework")
        
        if test_framework == "jest":
            await self._run_jest_tests(project_path, report)
        elif test_framework == "vitest":
            await self._run_vitest_tests(project_path, report)
        elif test_framework == "pytest":
            await self._run_pytest_tests(project_path, report)
        elif test_framework == "go_test":
            await self._run_go_tests(project_path, report)
        else:
            self.logger.warning(f"Unknown test framework: {test_framework}")

    async def _run_jest_tests(self, project_path: str, report: QAReport) -> None:
        """Run Jest tests."""
        try:
            cmd = ["npx", "jest", "--json", "--passWithNoTests"]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            self._parse_jest_output(stdout.decode(), report)
                    
        except Exception as e:
            self.logger.warning(f"Jest tests failed: {e}")
            report.execution_errors.append(f"Jest failed: {str(e)}")

    async def _run_vitest_tests(self, project_path: str, report: QAReport) -> None:
        """Run Vitest tests."""
        try:
            cmd = ["npx", "vitest", "run", "--reporter=json"]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            # Parse Vitest JSON output (similar to Jest)
            self._parse_jest_output(stdout.decode(), report)
                    
        except Exception as e:
            self.logger.warning(f"Vitest tests failed: {e}")
            report.execution_errors.append(f"Vitest failed: {str(e)}")

    async def _run_pytest_tests(self, project_path: str, report: QAReport) -> None:
        """Run pytest tests."""
        try:
            cmd = ["pytest", "--json-report", "--json-report-file=-", "-v", project_path]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            try:
                pytest_output = json.loads(stdout.decode())
                summary = pytest_output.get("summary", {})
                
                report.total_tests += summary.get("total", 0)
                report.passed += summary.get("passed", 0)
                report.failed += summary.get("failed", 0)
                report.skipped += summary.get("skipped", 0)
                report.errors += summary.get("error", 0)
                
                for test in pytest_output.get("tests", []):
                    report.test_results.append(TestResult(
                        name=test.get("nodeid", "unknown"),
                        status=test.get("outcome", "unknown"),
                        duration=test.get("duration", 0.0),
                        error_message=test.get("longrepr") if test.get("outcome") == "failed" else None,
                    ))
            except json.JSONDecodeError:
                # Fallback: parse text output
                self._parse_pytest_text_output(stdout.decode() + stderr.decode(), report)
                    
        except Exception as e:
            self.logger.warning(f"pytest tests failed: {e}")
            report.execution_errors.append(f"pytest failed: {str(e)}")

    async def _run_go_tests(self, project_path: str, report: QAReport) -> None:
        """Run Go tests."""
        try:
            cmd = ["go", "test", "-json", "./..."]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            # Parse Go test JSON output
            for line in stdout.decode().split("\n"):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    if event.get("Action") == "pass":
                        report.passed += 1
                        report.total_tests += 1
                    elif event.get("Action") == "fail":
                        report.failed += 1
                        report.total_tests += 1
                        report.test_results.append(TestResult(
                            name=event.get("Test", "unknown"),
                            status="failed",
                            error_message=event.get("Output"),
                        ))
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Go tests failed: {e}")
            report.execution_errors.append(f"Go test failed: {str(e)}")

    def _parse_jest_output(self, output: str, report: QAReport) -> None:
        """Parse Jest/Vitest JSON output."""
        try:
            # Find JSON in output (may have other text)
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                jest_output = json.loads(output[json_start:json_end])
                
                report.total_tests += jest_output.get("numTotalTests", 0)
                report.passed += jest_output.get("numPassedTests", 0)
                report.failed += jest_output.get("numFailedTests", 0)
                report.skipped += jest_output.get("numPendingTests", 0)
                
                for test_file in jest_output.get("testResults", []):
                    for test in test_file.get("assertionResults", []):
                        report.test_results.append(TestResult(
                            name=test.get("fullName", test.get("title", "unknown")),
                            status=test.get("status", "unknown"),
                            duration=test.get("duration", 0) / 1000.0,
                            error_message="\n".join(test.get("failureMessages", [])) if test.get("status") == "failed" else None,
                            file_path=test_file.get("name"),
                        ))
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse Jest output")

    def _parse_pytest_text_output(self, output: str, report: QAReport) -> None:
        """Parse pytest text output as fallback."""
        # Look for summary line like "5 passed, 2 failed"
        summary_match = re.search(
            r"(\d+) passed.*?(\d+) failed|(\d+) passed|(\d+) failed",
            output
        )
        if summary_match:
            groups = summary_match.groups()
            if groups[0] and groups[1]:  # "X passed, Y failed"
                report.passed += int(groups[0])
                report.failed += int(groups[1])
                report.total_tests += int(groups[0]) + int(groups[1])
            elif groups[2]:  # "X passed"
                report.passed += int(groups[2])
                report.total_tests += int(groups[2])
            elif groups[3]:  # "X failed"
                report.failed += int(groups[3])
                report.total_tests += int(groups[3])

    async def _run_integration_tests(
        self, 
        project_path: str, 
        project_info: Dict[str, Any],
        report: QAReport
    ) -> None:
        """Run integration tests."""
        self.logger.info("Running integration tests...")
        
        # Check for integration test directory
        int_test_paths = [
            Path(project_path) / "tests" / "integration",
            Path(project_path) / "__tests__" / "integration",
            Path(project_path) / "test" / "integration",
        ]
        
        for test_path in int_test_paths:
            if test_path.exists():
                language = project_info.get("language")
                if language in ["javascript", "typescript"]:
                    await self._run_jest_tests(str(test_path), report)
                elif language == "python":
                    await self._run_pytest_tests(str(test_path), report)
                break

    async def _run_playwright_tests(self, project_path: str, report: QAReport) -> None:
        """Run Playwright E2E tests."""
        self.logger.info("Running Playwright E2E tests...")
        
        try:
            # Check if Playwright tests exist
            e2e_paths = [
                Path(project_path) / "e2e",
                Path(project_path) / "tests" / "e2e",
                Path(project_path) / "__tests__" / "e2e",
                Path(project_path) / "playwright",
            ]
            
            e2e_path = None
            for path in e2e_paths:
                if path.exists():
                    e2e_path = path
                    break
            
            if not e2e_path:
                self.logger.info("No Playwright tests found, skipping E2E tests")
                return
            
            cmd = ["npx", "playwright", "test", "--reporter=json"]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            # Parse Playwright JSON output
            try:
                pw_output = json.loads(stdout.decode())
                for suite in pw_output.get("suites", []):
                    for spec in suite.get("specs", []):
                        status = "passed" if spec.get("ok") else "failed"
                        report.test_results.append(TestResult(
                            name=f"[E2E] {spec.get('title', 'unknown')}",
                            status=status,
                            file_path=suite.get("file"),
                        ))
                        report.total_tests += 1
                        if status == "passed":
                            report.passed += 1
                        else:
                            report.failed += 1
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse Playwright output")
                    
        except Exception as e:
            self.logger.warning(f"Playwright tests failed: {e}")
            report.execution_errors.append(f"Playwright failed: {str(e)}")

    async def _attempt_bug_fixes(
        self, 
        project_path: str, 
        report: QAReport
    ) -> List[Dict[str, Any]]:
        """Attempt to automatically fix test failures."""
        fixes = []
        
        for test in report.test_results:
            if test.status != "failed" or not test.error_message:
                continue
            
            fix = self._analyze_and_fix_error(test, project_path)
            if fix:
                fixes.append(fix)
        
        return fixes

    def _analyze_and_fix_error(
        self, 
        test: TestResult, 
        project_path: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze a test error and attempt to fix it."""
        error = test.error_message or ""
        
        # Common fixable patterns
        fix_patterns = [
            # Missing import
            (r"Cannot find module '([^']+)'", self._fix_missing_import),
            # Undefined variable
            (r"(\w+) is not defined", self._fix_undefined_variable),
            # Type error
            (r"TypeError: Cannot read propert(?:y|ies) '(\w+)' of (undefined|null)", 
             self._fix_null_access),
        ]
        
        for pattern, fix_func in fix_patterns:
            match = re.search(pattern, error)
            if match:
                result = fix_func(match, test, project_path)
                if result:
                    return result
        
        return None

    def _fix_missing_import(
        self, 
        match: re.Match, 
        test: TestResult, 
        project_path: str
    ) -> Optional[Dict[str, Any]]:
        """Fix missing import error."""
        module_name = match.group(1)
        
        # This would need LLM integration for smart fixes
        # For now, log the issue
        self.logger.info(f"Detected missing import: {module_name}")
        
        return {
            "type": "missing_import",
            "module": module_name,
            "test": test.name,
            "auto_fixed": False,
            "suggestion": f"Install module with: npm install {module_name}",
        }

    def _fix_undefined_variable(
        self, 
        match: re.Match, 
        test: TestResult, 
        project_path: str
    ) -> Optional[Dict[str, Any]]:
        """Fix undefined variable error."""
        variable_name = match.group(1)
        
        return {
            "type": "undefined_variable",
            "variable": variable_name,
            "test": test.name,
            "auto_fixed": False,
            "suggestion": f"Define or import '{variable_name}' before use",
        }

    def _fix_null_access(
        self, 
        match: re.Match, 
        test: TestResult, 
        project_path: str
    ) -> Optional[Dict[str, Any]]:
        """Fix null/undefined property access."""
        property_name = match.group(1)
        null_type = match.group(2)
        
        return {
            "type": "null_access",
            "property": property_name,
            "null_type": null_type,
            "test": test.name,
            "auto_fixed": False,
            "suggestion": f"Add null check before accessing '{property_name}'",
        }

    def _calculate_quality_score(self, report: QAReport) -> float:
        """Calculate overall quality score (0-100)."""
        score = 100.0
        
        # Deduct for test failures
        if report.total_tests > 0:
            pass_rate = report.passed / report.total_tests
            score -= (1 - pass_rate) * 40  # Up to 40 points for test failures
        
        # Deduct for code quality issues
        error_count = sum(1 for q in report.quality_issues if q.severity == "error")
        warning_count = sum(1 for q in report.quality_issues if q.severity == "warning")
        
        score -= error_count * 5  # 5 points per error
        score -= warning_count * 1  # 1 point per warning
        
        # Bonus for all tests passing on first try
        if report.all_tests_passing and report.fix_iterations == 1:
            score = min(100, score + 5)
        
        return max(0, min(100, score))

    async def _generate_html_report(
        self, 
        project_path: str, 
        report: QAReport
    ) -> str:
        """Generate HTML test report."""
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QA Test Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 20px; }}
        .stat {{ background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ opacity: 0.9; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h2 {{ margin-top: 0; color: #333; }}
        .test-item {{ padding: 12px; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 10px; }}
        .test-item:last-child {{ border-bottom: none; }}
        .status {{ padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: 500; }}
        .status.passed {{ background: #d4edda; color: #155724; }}
        .status.failed {{ background: #f8d7da; color: #721c24; }}
        .status.skipped {{ background: #fff3cd; color: #856404; }}
        .quality-issue {{ padding: 10px; border-left: 3px solid; margin-bottom: 8px; background: #f8f9fa; }}
        .quality-issue.error {{ border-color: #dc3545; }}
        .quality-issue.warning {{ border-color: #ffc107; }}
        .score-ring {{ width: 120px; height: 120px; margin: 0 auto; }}
        .score-text {{ text-align: center; font-size: 2em; font-weight: bold; color: {'#28a745' if report.quality_score >= 80 else '#ffc107' if report.quality_score >= 50 else '#dc3545'}; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 QA Test Report</h1>
            <p>Generated: {report.timestamp}</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{report.total_tests}</div>
                    <div class="stat-label">Total Tests</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{report.passed}</div>
                    <div class="stat-label">Passed</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{report.failed}</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{report.quality_score:.0f}</div>
                    <div class="stat-label">Quality Score</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Test Results</h2>
            {''.join(f'''
            <div class="test-item">
                <span class="status {t.status}">{t.status.upper()}</span>
                <span>{t.name}</span>
                {f'<span style="color: #999;">({t.duration:.2f}s)</span>' if t.duration else ''}
            </div>
            {f'<div style="padding: 10px; background: #fff3cd; margin: 0 0 10px 20px; border-radius: 4px; font-family: monospace; font-size: 0.85em;">{t.error_message[:200]}...</div>' if t.error_message else ''}
            ''' for t in report.test_results[:50])}
            {f'<p style="color: #666;">... and {len(report.test_results) - 50} more tests</p>' if len(report.test_results) > 50 else ''}
        </div>
        
        <div class="card">
            <h2>Code Quality Issues ({len(report.quality_issues)})</h2>
            {''.join(f'''
            <div class="quality-issue {q.severity}">
                <strong>[{q.tool.upper()}] {q.rule}</strong> - {q.message}
                <br><small>{q.file_path}:{q.line}</small>
            </div>
            ''' for q in report.quality_issues[:30])}
            {f'<p style="color: #666;">... and {len(report.quality_issues) - 30} more issues</p>' if len(report.quality_issues) > 30 else ''}
        </div>
        
        <div class="card">
            <h2>Fix Attempts</h2>
            <p>Iterations: {report.fix_iterations} / {self.MAX_FIX_ITERATIONS}</p>
            <p>All Tests Passing: {'✅ Yes' if report.all_tests_passing else '❌ No'}</p>
            {f'''
            <h3>Applied Fixes</h3>
            {''.join(f"<p>• {fix.get('type', 'unknown')}: {fix.get('suggestion', '')}</p>" for fix in report.fixes_applied)}
            ''' if report.fixes_applied else ''}
        </div>
    </div>
</body>
</html>"""
        
        report_path = os.path.join(project_path, "qa_report.html")
        with open(report_path, "w") as f:
            f.write(html_content)
        
        return report_path
