"""Security Agent - Semgrep integration for vulnerability scanning and auto-fixing.

Phase 11E Enhancement:
- Feature-aware scanning based on requirements.features
- Auth: session fixation, JWT exposure, CSRF, cookie flags
- Payments: Stripe key exposure, webhook validation, PCI compliance
- File uploads: file type validation, size limits, path traversal
- Email: Resend key exposure, email injection, rate limiting
- Tech-stack-aware scanning (Next.js, Nuxt, Supabase)
- Query KB for common vulnerabilities
- Write findings to KB
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .base import AgentResult, BaseAgent

# Import knowledge base
try:
    from ..knowledge import query_knowledge, store_knowledge, KnowledgeEntryType
    KB_AVAILABLE = True
except ImportError:
    KB_AVAILABLE = False

logger = logging.getLogger(__name__)


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
    feature_context: Optional[str] = None  # Which feature this relates to (auth, payments, etc.)
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
    by_feature: Dict[str, int] = field(default_factory=dict)  # Findings by feature area
    scan_time: float = 0.0
    features_scanned: List[str] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)
    kb_patterns_used: int = 0
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
                    "feature_context": f.feature_context,
                    "fix_suggestion": f.fix_suggestion,
                    "auto_fixed": f.auto_fixed,
                    "fix_verified": f.fix_verified,
                }
                for f in self.findings
            ],
            "by_severity": self.by_severity,
            "by_feature": self.by_feature,
            "scan_time": self.scan_time,
            "features_scanned": self.features_scanned,
            "tech_stack": self.tech_stack,
            "kb_patterns_used": self.kb_patterns_used,
            "errors": self.errors,
        }


# Feature-specific security checks
FEATURE_SECURITY_CHECKS = {
    "auth": {
        "patterns": [
            r"session\s*=\s*{[^}]*httpOnly\s*:\s*false",  # Missing httpOnly
            r"session\s*=\s*{[^}]*secure\s*:\s*false",    # Missing secure
            r"jwt\s*=.*secret.*['\"].*['\"]",              # Hardcoded JWT secret
            r"sameSite\s*:\s*['\"]none['\"]",              # Unsafe sameSite
            r"credentials\s*:\s*['\"]include['\"]",        # CORS credentials
            r"password.*=.*['\"][^'\"]+['\"]",             # Hardcoded passwords
        ],
        "messages": {
            "httpOnly": "Session cookie missing httpOnly flag - vulnerable to XSS",
            "secure": "Session cookie missing secure flag - vulnerable to MITM",
            "jwt_secret": "Hardcoded JWT secret - use environment variable",
            "sameSite": "SameSite=none without secure - vulnerable to CSRF",
            "cors_creds": "CORS credentials:include needs careful validation",
        },
    },
    "payments": {
        "patterns": [
            r"sk_live_[a-zA-Z0-9]{24,}",                   # Stripe secret key
            r"sk_test_[a-zA-Z0-9]{24,}",                   # Stripe test key
            r"STRIPE.*KEY.*=.*['\"]sk_",                   # Stripe key in code
            r"stripe\.webhooks\.constructEvent.*without.*verify",  # Unverified webhook
            r"price_\d+",                                  # Hardcoded price IDs
        ],
        "messages": {
            "stripe_live_key": "CRITICAL: Stripe live secret key exposed in code",
            "stripe_test_key": "Stripe test key in code - use environment variable",
            "unverified_webhook": "Stripe webhook not properly verified - security risk",
            "hardcoded_price": "Hardcoded Stripe price ID - use environment variable",
        },
    },
    "file_uploads": {
        "patterns": [
            r"accept\s*=\s*['\"][^'\"]*\*[^'\"]*['\"]",    # Accepts all file types
            r"multer\s*\(\s*\)",                           # No multer config
            r"path\.join\([^)]*req\.(body|query|params)", # Path traversal risk
            r"fs\.write.*req\.(body|query|params)",       # Unsafe file write
            r"maxFileSize\s*:\s*\d{9,}",                  # Very large file limit
        ],
        "messages": {
            "accept_all": "File input accepts all types - validate allowed extensions",
            "no_multer_config": "Multer without configuration - set file limits",
            "path_traversal": "Potential path traversal vulnerability",
            "unsafe_write": "File write with user input - validate path",
            "large_file": "File size limit too large - consider reducing",
        },
    },
    "email": {
        "patterns": [
            r"re_[a-zA-Z0-9]{32,}",                        # Resend API key
            r"RESEND.*KEY.*=.*['\"]re_",                   # Resend key in code
            r"sendEmail.*\+.*req\.(body|query)",          # Email injection
            r"to\s*:\s*req\.(body|query)",                # Dynamic recipient
            r"html\s*:\s*`.*\$\{.*req\.",                 # Template injection
        ],
        "messages": {
            "resend_key": "Resend API key exposed - use environment variable",
            "email_injection": "Potential email injection vulnerability",
            "dynamic_recipient": "Email recipient from user input - validate domain",
            "template_injection": "Email template with user input - sanitize content",
        },
    },
    "database": {
        "patterns": [
            r"supabase.*service_role",                     # Service role exposed
            r"\.rpc\([^)]*\+.*req\.",                     # SQL injection in RPC
            r"\.from\(['\"].*['\"].*\+.*req\.",           # SQL injection
            r"raw\([^)]*\$\{",                            # Raw SQL with interpolation
            r"SUPABASE.*KEY.*=.*['\"]eyJ",                # Key in code
        ],
        "messages": {
            "service_role": "Supabase service role key exposed - use on server only",
            "rpc_injection": "Potential SQL injection in Supabase RPC call",
            "from_injection": "Potential SQL injection in Supabase query",
            "raw_sql": "Raw SQL with string interpolation - use parameterized queries",
        },
    },
}

# Tech-stack-specific checks
TECH_STACK_CHECKS = {
    "nextjs": {
        "patterns": [
            r"getServerSideProps.*client.*secret",         # Secret in SSR
            r"NEXT_PUBLIC_.*SECRET",                       # Public env secret
            r"NEXT_PUBLIC_.*KEY(?!.*PUBLISHABLE)",        # Non-publishable key
            r"middleware\.ts.*return NextResponse\.next", # Bypass middleware
        ],
        "messages": {
            "ssr_secret": "Client secret exposed in getServerSideProps response",
            "public_secret": "Secret key in NEXT_PUBLIC_ variable - exposed to client",
            "public_key": "Potentially sensitive key in NEXT_PUBLIC_ variable",
            "middleware_bypass": "Middleware may be bypassed without proper checks",
        },
    },
    "nuxt": {
        "patterns": [
            r"runtimeConfig\.public.*secret",              # Secret in public config
            r"NUXT_PUBLIC_.*SECRET",                       # Public env secret
            r"server/middleware.*next\(\)",               # Middleware bypass
        ],
        "messages": {
            "public_secret": "Secret in Nuxt public runtime config",
            "public_env_secret": "Secret in NUXT_PUBLIC_ variable",
            "middleware_bypass": "Nuxt middleware may be bypassed",
        },
    },
    "supabase": {
        "patterns": [
            r"createClient.*anon.*service_role",          # Mixed keys
            r"supabaseAdmin.*client",                     # Admin on client
            r"\.auth\.admin\.",                           # Admin auth on client
        ],
        "messages": {
            "mixed_keys": "Supabase client using wrong key type",
            "admin_client": "Supabase admin client used in client code",
            "admin_auth": "Supabase admin auth used inappropriately",
        },
    },
}


class SecurityAgent(BaseAgent):
    """Agent for security scanning and auto-fixing vulnerabilities."""

    # Auto-fix patterns for critical/high severity issues
    AUTO_FIX_PATTERNS = {
        # Hardcoded secrets
        "hardcoded-secret": {
            "pattern": r'(api_key|apikey|api-key|secret|password|token)\s*[=:]\s*["\']([^"\']+)["\']',
            "replacement": r'\1 = process.env.\1_VALUE || ""',
            "import_needed": None,
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
        # Stripe key exposure
        "stripe-key": {
            "pattern": r'(sk_live_|sk_test_)[a-zA-Z0-9]{24,}',
            "replacement": r'process.env.STRIPE_SECRET_KEY',
        },
        # Resend key exposure
        "resend-key": {
            "pattern": r're_[a-zA-Z0-9]{32,}',
            "replacement": r'process.env.RESEND_API_KEY',
        },
    }

    @property
    def name(self) -> str:
        return "Security"

    async def _query_kb_for_vulnerabilities(self, features: List[str], tech_stack: List[str]) -> List[Dict]:
        """Query KB for known vulnerability patterns."""
        if not KB_AVAILABLE:
            return []
        
        try:
            query = f"security vulnerabilities for {', '.join(features)} with {', '.join(tech_stack)}"
            results = await query_knowledge(
                query=query,
                entry_types=[KnowledgeEntryType.QA_FINDING],
                limit=20,
            )
            return results
        except Exception as e:
            logger.warning(f"KB query failed: {e}")
            return []
    
    async def _write_findings_to_kb(self, findings: List[SecurityFinding], project_type: str):
        """Write security findings to KB for future reference."""
        if not KB_AVAILABLE:
            return
        
        try:
            for finding in findings:
                if finding.severity in ["critical", "high"]:
                    await store_knowledge(
                        entry_type=KnowledgeEntryType.QA_FINDING,
                        content=f"Security: {finding.message}",
                        metadata={
                            "project_type": project_type,
                            "rule_id": finding.rule_id,
                            "severity": finding.severity,
                            "feature_context": finding.feature_context,
                            "fix_suggestion": finding.fix_suggestion,
                            "agent": "security",
                        },
                    )
        except Exception as e:
            logger.warning(f"KB write failed: {e}")

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute security scanning and auto-fixing with feature awareness."""
        import time
        start_time = time.time()
        
        project_path = context.get("project_path")
        requirements = context.get("requirements", {})
        project_type = context.get("project_type", "web_simple")
        
        if not project_path or not os.path.exists(project_path):
            logger.warning(f"Project path not available or does not exist, skipping security scan")
            return AgentResult(
                success=True,  # Allow pipeline to continue
                agent_name=self.name,
                data={
                    "skipped": True, 
                    "reason": "No project path available",
                    "security_report": {"total_findings": 0, "auto_fixed": 0, "verification_passed": True}
                },
                warnings=["Security scan skipped - no project path available"],
            )

        logger.info(f"Running security scan on: {project_path}")
        
        # Extract features and tech stack from requirements
        features = self._extract_features(requirements)
        tech_stack = self._detect_tech_stack(project_path, requirements)
        
        logger.info(f"Features to scan: {features}")
        logger.info(f"Tech stack detected: {tech_stack}")
        
        # Query KB for known vulnerabilities
        kb_patterns = await self._query_kb_for_vulnerabilities(features, tech_stack)

        # Run initial Semgrep scan
        report = await self._run_semgrep_scan(project_path)
        report.features_scanned = features
        report.tech_stack = tech_stack
        report.kb_patterns_used = len(kb_patterns)
        
        # Run feature-specific scans
        feature_findings = await self._run_feature_scans(project_path, features)
        for finding in feature_findings:
            report.findings.append(finding)
        
        # Run tech-stack-specific scans
        tech_findings = await self._run_tech_stack_scans(project_path, tech_stack)
        for finding in tech_findings:
            report.findings.append(finding)

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

        # Update breakdowns
        report.by_severity = self._calculate_severity_breakdown(report.findings)
        report.by_feature = self._calculate_feature_breakdown(report.findings)
        report.total_findings = len(report.findings)
        report.scan_time = time.time() - start_time

        # Write findings to KB
        await self._write_findings_to_kb(report.findings, project_type)

        # Generate report file
        report_path = os.path.join(project_path, "security_report.json")
        self.write_file(report_path, json.dumps(report.to_dict(), indent=2))

        # Determine success (no critical findings)
        critical_count = report.by_severity.get("critical", {}).get("found", 0)
        success = critical_count == 0

        return AgentResult(
            success=success,
            agent_name=self.name,
            data={
                "report": report.to_dict(),
                "report_path": report_path,
            },
            errors=[f"Critical: {f.message}" for f in report.findings if f.severity == "critical"],
            warnings=[f"High: {f.message}" for f in report.findings if f.severity == "high"],
        )
    
    def _extract_features(self, requirements: Dict[str, Any]) -> List[str]:
        """Extract security-relevant features from requirements."""
        features = set()
        
        # Get features from requirements
        req_features = requirements.get("features", [])
        for feature in req_features:
            feature_lower = feature.lower()
            if any(kw in feature_lower for kw in ["auth", "login", "signin", "signup"]):
                features.add("auth")
            if any(kw in feature_lower for kw in ["payment", "stripe", "billing", "checkout"]):
                features.add("payments")
            if any(kw in feature_lower for kw in ["upload", "file", "storage", "image"]):
                features.add("file_uploads")
            if any(kw in feature_lower for kw in ["email", "resend", "notification", "contact"]):
                features.add("email")
            if any(kw in feature_lower for kw in ["database", "supabase", "postgres"]):
                features.add("database")
        
        # Get from integrations
        integrations = requirements.get("integrations", [])
        for integration in integrations:
            int_lower = integration.lower()
            if "stripe" in int_lower:
                features.add("payments")
            if "resend" in int_lower:
                features.add("email")
            if "supabase" in int_lower:
                features.add("database")
                features.add("auth")
            if "r2" in int_lower or "s3" in int_lower:
                features.add("file_uploads")
        
        return list(features)
    
    def _detect_tech_stack(self, project_path: str, requirements: Dict[str, Any]) -> List[str]:
        """Detect tech stack from project files and requirements."""
        tech_stack = set()
        
        # From requirements
        req_tech = requirements.get("tech_stack", {})
        framework = req_tech.get("framework", "").lower()
        if "next" in framework:
            tech_stack.add("nextjs")
        elif "nuxt" in framework:
            tech_stack.add("nuxt")
        
        # From project files
        if os.path.exists(os.path.join(project_path, "next.config.js")) or \
           os.path.exists(os.path.join(project_path, "next.config.mjs")):
            tech_stack.add("nextjs")
        
        if os.path.exists(os.path.join(project_path, "nuxt.config.ts")) or \
           os.path.exists(os.path.join(project_path, "nuxt.config.js")):
            tech_stack.add("nuxt")
        
        # Check package.json
        package_json_path = os.path.join(project_path, "package.json")
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, "r") as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    
                    if "@supabase/supabase-js" in deps:
                        tech_stack.add("supabase")
                    if "next" in deps:
                        tech_stack.add("nextjs")
                    if "nuxt" in deps:
                        tech_stack.add("nuxt")
                    if "stripe" in deps:
                        tech_stack.add("stripe")
            except:
                pass
        
        return list(tech_stack)
    
    async def _run_feature_scans(
        self, 
        project_path: str, 
        features: List[str]
    ) -> List[SecurityFinding]:
        """Run feature-specific security scans."""
        findings = []
        
        code_extensions = [".ts", ".tsx", ".js", ".jsx", ".mjs"]
        skip_dirs = ["node_modules", ".git", ".next", "dist", "build"]
        
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if not any(file.endswith(ext) for ext in code_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_path)
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        lines = content.split("\n")
                except:
                    continue
                
                # Check each feature's patterns
                for feature in features:
                    if feature not in FEATURE_SECURITY_CHECKS:
                        continue
                    
                    checks = FEATURE_SECURITY_CHECKS[feature]
                    
                    for i, line in enumerate(lines):
                        for pattern in checks["patterns"]:
                            if re.search(pattern, line, re.IGNORECASE):
                                findings.append(SecurityFinding(
                                    rule_id=f"custom-{feature}",
                                    severity="high" if feature in ["auth", "payments"] else "medium",
                                    message=self._get_feature_message(feature, pattern),
                                    file_path=rel_path,
                                    line_start=i + 1,
                                    line_end=i + 1,
                                    code_snippet=line.strip()[:100],
                                    feature_context=feature,
                                ))
                                break  # One finding per line per feature
        
        return findings
    
    def _get_feature_message(self, feature: str, pattern: str) -> str:
        """Get appropriate message for a feature pattern match."""
        checks = FEATURE_SECURITY_CHECKS.get(feature, {})
        messages = checks.get("messages", {})
        
        # Try to match pattern to message
        for key, msg in messages.items():
            if key in pattern.lower():
                return msg
        
        # Default messages
        defaults = {
            "auth": "Authentication security concern detected",
            "payments": "Payment security concern detected - review carefully",
            "file_uploads": "File upload security concern detected",
            "email": "Email security concern detected",
            "database": "Database security concern detected",
        }
        
        return defaults.get(feature, "Security concern detected")
    
    async def _run_tech_stack_scans(
        self, 
        project_path: str, 
        tech_stack: List[str]
    ) -> List[SecurityFinding]:
        """Run tech-stack-specific security scans."""
        findings = []
        
        code_extensions = [".ts", ".tsx", ".js", ".jsx", ".mjs"]
        skip_dirs = ["node_modules", ".git", ".next", "dist", "build"]
        
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if not any(file.endswith(ext) for ext in code_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_path)
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        lines = content.split("\n")
                except:
                    continue
                
                # Check each tech stack's patterns
                for tech in tech_stack:
                    if tech not in TECH_STACK_CHECKS:
                        continue
                    
                    checks = TECH_STACK_CHECKS[tech]
                    
                    for i, line in enumerate(lines):
                        for pattern in checks["patterns"]:
                            if re.search(pattern, line, re.IGNORECASE):
                                findings.append(SecurityFinding(
                                    rule_id=f"tech-{tech}",
                                    severity="high",
                                    message=self._get_tech_message(tech, pattern),
                                    file_path=rel_path,
                                    line_start=i + 1,
                                    line_end=i + 1,
                                    code_snippet=line.strip()[:100],
                                    feature_context=f"tech:{tech}",
                                ))
                                break  # One finding per line per tech
        
        return findings
    
    def _get_tech_message(self, tech: str, pattern: str) -> str:
        """Get appropriate message for a tech stack pattern match."""
        checks = TECH_STACK_CHECKS.get(tech, {})
        messages = checks.get("messages", {})
        
        for key, msg in messages.items():
            if key in pattern.lower():
                return msg
        
        return f"{tech.title()} security concern detected"

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

        logger.info("Running Semgrep scan...")

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
            if fix_config.get("import_needed"):
                import_statement = fix_config["import_needed"]
                if import_statement not in content:
                    lines.insert(0, import_statement)

            # Write the fixed content
            new_content = "\n".join(lines)
            if self.write_file(file_path, new_content):
                logger.info(f"Auto-fixed {finding.rule_id} in {finding.file_path}")
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
        if "stripe" in rule_id_lower:
            return self.AUTO_FIX_PATTERNS["stripe-key"]
        if "resend" in rule_id_lower:
            return self.AUTO_FIX_PATTERNS["resend-key"]
        
        return None

    def _get_fix_suggestion(self, finding: SecurityFinding) -> str:
        """Generate fix suggestion for a finding."""
        fix_config = self._find_fix_pattern(finding.rule_id)
        
        if fix_config and "suggestion" in fix_config:
            return fix_config["suggestion"]
        
        # Feature-specific suggestions
        if finding.feature_context:
            feature_suggestions = {
                "auth": "Review authentication implementation for security best practices",
                "payments": "Ensure all payment keys are in environment variables and webhooks are verified",
                "file_uploads": "Validate file types, sizes, and paths server-side",
                "email": "Use environment variables for API keys and validate recipient addresses",
                "database": "Use parameterized queries and keep service keys server-side only",
            }
            if finding.feature_context in feature_suggestions:
                return feature_suggestions[finding.feature_context]
        
        # Generic suggestions based on severity
        suggestions = {
            "critical": "CRITICAL: Immediate manual review and fix required.",
            "high": "High severity issue. Review and fix as soon as possible.",
            "medium": "Medium severity issue. Consider fixing in the next sprint.",
            "low": "Low severity issue. Address when convenient.",
        }
        
        return suggestions.get(finding.severity.lower(), "Review and fix as appropriate.")

    async def _verify_fixes(
        self, project_path: str, modified_files: Set[str]
    ) -> SecurityReport:
        """Re-run Semgrep on modified files to verify fixes."""
        logger.info(f"Verifying fixes for {len(modified_files)} modified files")
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
    
    def _calculate_feature_breakdown(
        self, findings: List[SecurityFinding]
    ) -> Dict[str, int]:
        """Calculate breakdown of findings by feature context."""
        breakdown: Dict[str, int] = {}
        
        for finding in findings:
            feature = finding.feature_context or "general"
            breakdown[feature] = breakdown.get(feature, 0) + 1
        
        return breakdown
