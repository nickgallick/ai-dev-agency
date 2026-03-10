"""Security Agent - Semgrep integration for vulnerability scanning and auto-fixing."""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .base import AgentResult, BaseAgent


@dataclass
class SecurityFinding:
    """Represents a security finding from Semgrep."""
    rule_id: str
    severity: str
    message: str
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    fix_suggestion: Optional[str] = None
    auto_fixed: bool = False
    fix_verified: bool = False


@dataclass
class SecurityReport:
    """Security scan report."""
    total_findings: int = 0
    auto_fixed: int = 0
    fix_verified: int = 0
    suggestions_only: int = 0
    findings: List[SecurityFinding] = field(default_factory=list)
    by_severity: Dict[str, Dict[str, int]] = field(default_factory=dict)
    scan_time: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "total_findings": self.total_findings,
            "auto_fixed": self.auto_fixed,
            "fix_verified": self.fix_verified,
            "suggestions_only": self.suggestions_only,
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "message": f.message,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                    "line_end": f.line_end,
                    "code_snippet": f.code_snippet,
                    "fix_suggestion": f.fix_suggestion,
                    "auto_fixed": f.auto_fixed,
                    "fix_verified": f.fix_verified,
                }
                for f in self.findings
            ],
            "by_severity": self.by_severity,
            "scan_time": self.scan_time,
            "errors": self.errors,
        }


class SecurityAgent(BaseAgent):
    """Agent for security scanning and auto-fixing vulnerabilities."""

    # Auto-fix patterns for critical/high severity issues
    AUTO_FIX_PATTERNS = {
        # Hardcoded secrets
        "hardcoded-secret": {
            "pattern": r'(api_key|apikey|api-key|secret|password|token)\s*[=:]\s*["\']([^"\']+)["\']',
            "replacement": r'\1 = os.environ.get("\1_VALUE", "")',
            "import_needed": "import os",
        },
        # Missing rel="noopener noreferrer" on target="_blank"
        "missing-noopener": {
            "pattern": r'<a\s+([^>]*?)target=["\']_blank["\']([^>]*?)>',
            "replacement": r'<a \1target="_blank" rel="noopener noreferrer"\2>',
        },
        # innerHTML XSS risk
        "innerHTML-xss": {
            "pattern": r'\.innerHTML\s*=\s*([^;]+);',
            "replacement": r'.textContent = \1;',
        },
        # Missing CSRF token
        "missing-csrf": {
            "suggestion": "Add CSRF middleware to your application configuration",
        },
        # Missing CSP headers
        "missing-csp": {
            "suggestion": "Add Content-Security-Policy header to server configuration",
        },
        # Unsafe input handling
        "unsafe-input": {
            "pattern": r'document\.(getElementById|querySelector)\(["\']([^"\']+)["\']\)\.value',
            "replacement": r'DOMPurify.sanitize(document.\1("\2").value)',
            "import_needed": "import DOMPurify from 'dompurify';",
        },
    }

    @property
    def name(self) -> str:
        return "Security"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute security scanning and auto-fixing."""
        project_path = context.get("project_path")
        if not project_path:
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=["No project path provided"],
            )

        if not os.path.exists(project_path):
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=[f"Project path does not exist: {project_path}"],
            )

        self.logger.info(f"Running security scan on: {project_path}")

        # Run initial Semgrep scan
        report = await self._run_semgrep_scan(project_path)

        if report.errors and not report.findings:
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=report.errors,
            )

        # Process findings and apply auto-fixes
        modified_files: Set[str] = set()
        
        for finding in report.findings:
            if finding.severity.lower() in self.settings.auto_fix_severities:
                if await self._auto_fix_finding(finding, project_path):
                    finding.auto_fixed = True
                    report.auto_fixed += 1
                    modified_files.add(finding.file_path)
            else:
                finding.fix_suggestion = self._get_fix_suggestion(finding)
                report.suggestions_only += 1

        # Re-run Semgrep on modified files to verify fixes
        if modified_files:
            verification_report = await self._verify_fixes(project_path, modified_files)
            
            # Mark verified fixes
            fixed_rules = {f.rule_id for f in report.findings if f.auto_fixed}
            still_present = {f.rule_id for f in verification_report.findings}
            
            for finding in report.findings:
                if finding.auto_fixed and finding.rule_id not in still_present:
                    finding.fix_verified = True
                    report.fix_verified += 1

        # Update severity breakdown
        report.by_severity = self._calculate_severity_breakdown(report.findings)
        report.total_findings = len(report.findings)

        # Generate report file
        report_path = os.path.join(project_path, "security_report.json")
        self.write_file(report_path, json.dumps(report.to_dict(), indent=2))

        return AgentResult(
            success=True,
            agent_name=self.name,
            data={
                "report": report.to_dict(),
                "report_path": report_path,
            },
        )

    async def _run_semgrep_scan(
        self, project_path: str, files: Optional[Set[str]] = None
    ) -> SecurityReport:
        """Run Semgrep scan on the project or specific files."""
        report = SecurityReport()

        # Build command
        if files:
            files_arg = " ".join(files)
            command = ["semgrep", "scan", "--json", "--config", "auto"] + list(files)
        else:
            command = ["semgrep", "scan", "--json", "--config", "auto", "/project"]

        volumes = {
            project_path: {"bind": "/project", "mode": "rw"},
        }

        environment = {}
        if self.settings.semgrep_api_token:
            environment["SEMGREP_API_TOKEN"] = self.settings.semgrep_api_token

        self.logger.info("Running Semgrep scan...")

        exit_code, stdout, stderr = self.run_docker_container(
            image=self.settings.semgrep_image,
            command=command,
            volumes=volumes,
            environment=environment,
            timeout=self.settings.semgrep_timeout,
        )

        # Parse Semgrep JSON output
        try:
            if stdout:
                results = json.loads(stdout)
                for result in results.get("results", []):
                    finding = SecurityFinding(
                        rule_id=result.get("check_id", "unknown"),
                        severity=self._map_severity(
                            result.get("extra", {}).get("severity", "INFO")
                        ),
                        message=result.get("extra", {}).get("message", ""),
                        file_path=result.get("path", ""),
                        line_start=result.get("start", {}).get("line", 0),
                        line_end=result.get("end", {}).get("line", 0),
                        code_snippet=result.get("extra", {}).get("lines", ""),
                    )
                    report.findings.append(finding)
        except json.JSONDecodeError as e:
            report.errors.append(f"Failed to parse Semgrep output: {e}")
            if stderr:
                report.errors.append(stderr)

        return report

    def _map_severity(self, semgrep_severity: str) -> str:
        """Map Semgrep severity to standardized levels."""
        severity_map = {
            "ERROR": "critical",
            "WARNING": "high",
            "INFO": "medium",
        }
        return severity_map.get(semgrep_severity.upper(), "low")

    async def _auto_fix_finding(
        self, finding: SecurityFinding, project_path: str
    ) -> bool:
        """Attempt to auto-fix a security finding."""
        if not self.settings.auto_fix_enabled:
            return False

        file_path = os.path.join(project_path, finding.file_path)
        if not os.path.exists(file_path):
            return False

        content = self.read_file(file_path)
        if not content:
            return False

        # Find matching fix pattern
        fix_config = self._find_fix_pattern(finding.rule_id)
        if not fix_config:
            return False

        if "pattern" not in fix_config:
            # No automated fix available, only suggestion
            finding.fix_suggestion = fix_config.get("suggestion", "Manual fix required")
            return False

        # Apply the fix
        lines = content.split("\n")
        modified = False

        # Get the lines to fix
        start_idx = max(0, finding.line_start - 1)
        end_idx = min(len(lines), finding.line_end)

        for i in range(start_idx, end_idx):
            original_line = lines[i]
            fixed_line = re.sub(
                fix_config["pattern"],
                fix_config["replacement"],
                original_line,
            )
            if fixed_line != original_line:
                lines[i] = fixed_line
                modified = True

        if modified:
            # Add import if needed
            if "import_needed" in fix_config:
                import_statement = fix_config["import_needed"]
                if import_statement not in content:
                    lines.insert(0, import_statement)

            # Write the fixed content
            new_content = "\n".join(lines)
            if self.write_file(file_path, new_content):
                self.logger.info(f"Auto-fixed {finding.rule_id} in {finding.file_path}")
                return True

        return False

    def _find_fix_pattern(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Find a fix pattern matching the rule ID."""
        rule_id_lower = rule_id.lower()
        
        for pattern_key, fix_config in self.AUTO_FIX_PATTERNS.items():
            if pattern_key in rule_id_lower:
                return fix_config
        
        # Generic pattern matching
        if any(kw in rule_id_lower for kw in ["secret", "password", "key", "token"]):
            return self.AUTO_FIX_PATTERNS["hardcoded-secret"]
        if "noopener" in rule_id_lower or "target-blank" in rule_id_lower:
            return self.AUTO_FIX_PATTERNS["missing-noopener"]
        if "innerhtml" in rule_id_lower or "xss" in rule_id_lower:
            return self.AUTO_FIX_PATTERNS["innerHTML-xss"]
        if "csrf" in rule_id_lower:
            return self.AUTO_FIX_PATTERNS["missing-csrf"]
        if "csp" in rule_id_lower or "content-security" in rule_id_lower:
            return self.AUTO_FIX_PATTERNS["missing-csp"]
        
        return None

    def _get_fix_suggestion(self, finding: SecurityFinding) -> str:
        """Generate fix suggestion for a finding."""
        fix_config = self._find_fix_pattern(finding.rule_id)
        
        if fix_config and "suggestion" in fix_config:
            return fix_config["suggestion"]
        
        # Generic suggestions based on severity
        suggestions = {
            "critical": "This is a critical security issue. Immediate manual review and fix required.",
            "high": "High severity issue detected. Please review and fix as soon as possible.",
            "medium": "Medium severity issue. Consider fixing in the next sprint.",
            "low": "Low severity issue. Address when convenient.",
        }
        
        return suggestions.get(finding.severity.lower(), "Review and fix as appropriate.")

    async def _verify_fixes(
        self, project_path: str, modified_files: Set[str]
    ) -> SecurityReport:
        """Re-run Semgrep on modified files to verify fixes."""
        self.logger.info(f"Verifying fixes for {len(modified_files)} modified files")
        return await self._run_semgrep_scan(project_path, modified_files)

    def _calculate_severity_breakdown(
        self, findings: List[SecurityFinding]
    ) -> Dict[str, Dict[str, int]]:
        """Calculate breakdown of findings by severity."""
        breakdown = {
            "critical": {"found": 0, "auto_fixed": 0},
            "high": {"found": 0, "auto_fixed": 0},
            "medium": {"found": 0, "auto_fixed": 0},
            "low": {"found": 0, "auto_fixed": 0},
        }

        for finding in findings:
            severity = finding.severity.lower()
            if severity in breakdown:
                breakdown[severity]["found"] += 1
                if finding.auto_fixed:
                    breakdown[severity]["auto_fixed"] += 1

        return breakdown
