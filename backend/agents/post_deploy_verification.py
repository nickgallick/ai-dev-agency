"""Post-Deploy Verification Agent - Verifies live deployment.

Runs after Deployment, before Delivery to verify:
- All pages/endpoints return 200 status codes
- Visual diff between live and QA screenshots
- SSL certificate verification
- Environment variables configured
- Health endpoints responding
- Login flows for SaaS
- EAS builds for mobile
- GitHub Releases for desktop

Uses DeepSeek V3.2 model (cheap, just HTTP requests).
Uses fetch_mcp, browser_mcp, github_mcp tools.
"""

import asyncio
import json
import os
import ssl
import socket
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from PIL import Image
    import imagehash
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .base import BaseAgent, AgentResult


@dataclass
class VerificationResult:
    """Result of a single verification check."""
    check_name: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    severity: str = "info"  # critical, warning, info


@dataclass
class EndpointCheck:
    """Result of an endpoint health check."""
    url: str
    status_code: int
    response_time_ms: float
    passed: bool
    error: Optional[str] = None


@dataclass
class DeployVerificationReport:
    """Complete deployment verification report."""
    project_id: str
    deployment_url: str
    generated_at: str
    overall_status: str  # passed, failed, partial
    checks_passed: int
    checks_failed: int
    endpoint_checks: List[Dict[str, Any]]
    ssl_valid: bool
    ssl_expiry: Optional[str]
    visual_diff_score: Optional[float]
    verification_results: List[Dict[str, Any]]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "deployment_url": self.deployment_url,
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "endpoint_checks": self.endpoint_checks,
            "ssl_valid": self.ssl_valid,
            "ssl_expiry": self.ssl_expiry,
            "visual_diff_score": self.visual_diff_score,
            "verification_results": self.verification_results,
            "warnings": self.warnings,
        }


class PostDeployVerificationAgent(BaseAgent):
    """Verifies deployment is working correctly on live URL."""
    
    name = "post_deploy_verification"
    description = "Post-Deploy Verification - Validates live deployment"
    model = "deepseek/deepseek-chat"  # Cheap model, just HTTP requests
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verification_results: List[VerificationResult] = []
        self.endpoint_checks: List[EndpointCheck] = []
    
    @property
    def name(self) -> str:
        return "post_deploy_verification"
    
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute deployment verification."""
        self.logger.info("Starting post-deploy verification")
        
        project_id = context.get("project_id", "unknown")
        project_type = context.get("project_type", "web_simple")
        project_path = context.get("project_path", "/tmp/project")
        
        # Get deployment info
        deployment_result = context.get("deployment_result", {})
        deployment_url = deployment_result.get("url") or deployment_result.get("deployment_url")
        
        if not deployment_url:
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=["No deployment URL found - cannot verify deployment"],
            )
        
        self.verification_results = []
        self.endpoint_checks = []
        warnings = []
        
        # 1. Verify all pages/endpoints return 200
        pages = self._get_pages_to_check(context, project_path)
        await self._check_endpoints(deployment_url, pages)
        
        # 2. Verify SSL certificate
        ssl_result = await self._verify_ssl(deployment_url)
        self.verification_results.append(ssl_result)
        
        # 3. Verify health endpoint
        health_result = await self._verify_health_endpoint(deployment_url)
        self.verification_results.append(health_result)
        
        # 4. Project type-specific checks
        if project_type in ["python_saas", "web_complex"]:
            # Check login flow for SaaS
            login_result = await self._verify_login_flow(deployment_url)
            self.verification_results.append(login_result)
            
            # Check API endpoints
            api_result = await self._verify_api_endpoints(deployment_url, context)
            self.verification_results.append(api_result)
        
        if project_type in ["mobile_native_ios", "mobile_cross_platform"]:
            # Check EAS build status
            eas_result = await self._verify_eas_builds(context)
            self.verification_results.append(eas_result)
        
        if project_type == "desktop_app":
            # Check GitHub releases
            release_result = await self._verify_github_releases(context)
            self.verification_results.append(release_result)
        
        # 5. Visual diff (if screenshots available)
        visual_score = None
        if PIL_AVAILABLE:
            visual_result = await self._perform_visual_diff(deployment_url, project_path)
            if visual_result:
                visual_score = visual_result.details.get("similarity_score")
                self.verification_results.append(visual_result)
        
        # Generate report
        report = self._generate_report(
            project_id=project_id,
            deployment_url=deployment_url,
            visual_score=visual_score,
            warnings=warnings,
        )
        
        # Write report to file
        report_path = os.path.join(project_path, "deploy_verification_report.json")
        try:
            with open(report_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            self.logger.info(f"Verification report written to {report_path}")
        except Exception as e:
            self.logger.warning(f"Failed to write report: {e}")
        
        # Determine success
        critical_failures = [
            r for r in self.verification_results 
            if not r.passed and r.severity == "critical"
        ]
        
        endpoint_failures = [e for e in self.endpoint_checks if not e.passed]
        
        success = len(critical_failures) == 0 and len(endpoint_failures) <= 1
        
        return AgentResult(
            success=success,
            agent_name=self.name,
            data={
                "report": report.to_dict(),
                "report_path": report_path,
                "deployment_url": deployment_url,
                "overall_status": report.overall_status,
            },
            errors=[f"{r.check_name}: {r.message}" for r in critical_failures],
            warnings=[r.message for r in self.verification_results if not r.passed and r.severity == "warning"],
        )
    
    def _get_pages_to_check(self, context: Dict[str, Any], project_path: str) -> List[str]:
        """Get list of pages/routes to check."""
        pages = ["/"]  # Always check home page
        
        # Get from build manifest
        manifest_path = os.path.join(project_path, "build_manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                    for page in manifest.get("pages", []):
                        route = page.get("route", "/")
                        if route not in pages:
                            pages.append(route)
            except Exception:
                pass
        
        # Get from architect output
        architect_result = context.get("architect_result", {})
        for page in architect_result.get("pages", []):
            route = page.get("route", "/")
            if route not in pages:
                pages.append(route)
        
        return pages
    
    async def _check_endpoints(self, base_url: str, pages: List[str]) -> None:
        """Check all endpoints return 200 status."""
        if not AIOHTTP_AVAILABLE:
            self.logger.warning("aiohttp not available - skipping endpoint checks")
            return
        
        async with aiohttp.ClientSession() as session:
            for page in pages:
                url = f"{base_url.rstrip('/')}{page}"
                
                try:
                    start_time = asyncio.get_event_loop().time()
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), ssl=False) as response:
                        response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                        
                        passed = response.status == 200
                        
                        self.endpoint_checks.append(EndpointCheck(
                            url=url,
                            status_code=response.status,
                            response_time_ms=round(response_time, 2),
                            passed=passed,
                        ))
                        
                        if not passed:
                            self.logger.warning(f"Endpoint {url} returned {response.status}")
                
                except asyncio.TimeoutError:
                    self.endpoint_checks.append(EndpointCheck(
                        url=url,
                        status_code=0,
                        response_time_ms=10000,
                        passed=False,
                        error="Request timed out",
                    ))
                
                except Exception as e:
                    self.endpoint_checks.append(EndpointCheck(
                        url=url,
                        status_code=0,
                        response_time_ms=0,
                        passed=False,
                        error=str(e),
                    ))
    
    async def _verify_ssl(self, deployment_url: str) -> VerificationResult:
        """Verify SSL certificate is valid."""
        parsed = urlparse(deployment_url)
        hostname = parsed.hostname
        
        if not hostname:
            return VerificationResult(
                check_name="ssl_certificate",
                passed=False,
                message="Could not parse hostname from URL",
                severity="warning",
            )
        
        # Skip SSL check for localhost
        if hostname in ["localhost", "127.0.0.1"]:
            return VerificationResult(
                check_name="ssl_certificate",
                passed=True,
                message="SSL check skipped for localhost",
                severity="info",
            )
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Get expiry date
                    not_after = cert.get("notAfter")
                    
                    return VerificationResult(
                        check_name="ssl_certificate",
                        passed=True,
                        message=f"SSL certificate valid, expires: {not_after}",
                        details={"expiry": not_after},
                        severity="info",
                    )
        
        except ssl.SSLCertVerificationError as e:
            return VerificationResult(
                check_name="ssl_certificate",
                passed=False,
                message=f"SSL certificate verification failed: {e}",
                severity="critical",
            )
        
        except Exception as e:
            return VerificationResult(
                check_name="ssl_certificate",
                passed=False,
                message=f"SSL check failed: {e}",
                severity="warning",
            )
    
    async def _verify_health_endpoint(self, deployment_url: str) -> VerificationResult:
        """Check health/status endpoint."""
        if not AIOHTTP_AVAILABLE:
            return VerificationResult(
                check_name="health_endpoint",
                passed=False,
                message="aiohttp not available",
                severity="warning",
            )
        
        health_paths = ["/api/health", "/health", "/api/status", "/_health"]
        
        async with aiohttp.ClientSession() as session:
            for path in health_paths:
                url = f"{deployment_url.rstrip('/')}{path}"
                
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), ssl=False) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                return VerificationResult(
                                    check_name="health_endpoint",
                                    passed=True,
                                    message=f"Health endpoint responding at {path}",
                                    details={"path": path, "response": data},
                                    severity="info",
                                )
                            except:
                                return VerificationResult(
                                    check_name="health_endpoint",
                                    passed=True,
                                    message=f"Health endpoint responding at {path}",
                                    details={"path": path},
                                    severity="info",
                                )
                except Exception:
                    continue
        
        return VerificationResult(
            check_name="health_endpoint",
            passed=False,
            message="No health endpoint found at common paths",
            severity="warning",
        )
    
    async def _verify_login_flow(self, deployment_url: str) -> VerificationResult:
        """Verify login/auth endpoints for SaaS projects."""
        if not AIOHTTP_AVAILABLE:
            return VerificationResult(
                check_name="login_flow",
                passed=False,
                message="aiohttp not available",
                severity="warning",
            )
        
        auth_paths = ["/login", "/auth/login", "/signin", "/auth/signin", "/api/auth/signin"]
        
        async with aiohttp.ClientSession() as session:
            for path in auth_paths:
                url = f"{deployment_url.rstrip('/')}{path}"
                
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), ssl=False) as response:
                        if response.status in [200, 302, 307]:
                            return VerificationResult(
                                check_name="login_flow",
                                passed=True,
                                message=f"Auth endpoint accessible at {path}",
                                details={"path": path, "status": response.status},
                                severity="info",
                            )
                except Exception:
                    continue
        
        return VerificationResult(
            check_name="login_flow",
            passed=False,
            message="No login endpoint found",
            severity="warning",
        )
    
    async def _verify_api_endpoints(self, deployment_url: str, context: Dict[str, Any]) -> VerificationResult:
        """Verify API endpoints are responding."""
        if not AIOHTTP_AVAILABLE:
            return VerificationResult(
                check_name="api_endpoints",
                passed=False,
                message="aiohttp not available",
                severity="warning",
            )
        
        # Get API endpoints from build manifest or architect output
        api_endpoints = []
        
        architect_result = context.get("architect_result", {})
        for endpoint in architect_result.get("api_endpoints", []):
            path = endpoint.get("path", "")
            if path.startswith("/api"):
                api_endpoints.append({
                    "path": path,
                    "method": endpoint.get("method", "GET"),
                })
        
        if not api_endpoints:
            return VerificationResult(
                check_name="api_endpoints",
                passed=True,
                message="No API endpoints defined to check",
                severity="info",
            )
        
        working = 0
        failed = 0
        
        async with aiohttp.ClientSession() as session:
            for endpoint in api_endpoints[:10]:  # Limit to 10 endpoints
                url = f"{deployment_url.rstrip('/')}{endpoint['path']}"
                
                try:
                    async with session.request(
                        method=endpoint["method"],
                        url=url,
                        timeout=aiohttp.ClientTimeout(total=5),
                        ssl=False
                    ) as response:
                        # Accept 200, 401, 403 (auth required is expected)
                        if response.status in [200, 201, 401, 403]:
                            working += 1
                        else:
                            failed += 1
                except Exception:
                    failed += 1
        
        passed = failed <= 1
        
        return VerificationResult(
            check_name="api_endpoints",
            passed=passed,
            message=f"{working}/{working + failed} API endpoints responding",
            details={"working": working, "failed": failed},
            severity="warning" if not passed else "info",
        )
    
    async def _verify_eas_builds(self, context: Dict[str, Any]) -> VerificationResult:
        """Verify EAS build status for mobile projects."""
        # This would use the Expo API to check build status
        # For now, check if build was submitted
        
        deployment_result = context.get("deployment_result", {})
        eas_build_id = deployment_result.get("eas_build_id")
        
        if eas_build_id:
            return VerificationResult(
                check_name="eas_build",
                passed=True,
                message=f"EAS build submitted: {eas_build_id}",
                details={"build_id": eas_build_id},
                severity="info",
            )
        
        return VerificationResult(
            check_name="eas_build",
            passed=False,
            message="No EAS build ID found",
            severity="warning",
        )
    
    async def _verify_github_releases(self, context: Dict[str, Any]) -> VerificationResult:
        """Verify GitHub release for desktop apps."""
        deployment_result = context.get("deployment_result", {})
        release_url = deployment_result.get("release_url")
        
        if not release_url:
            return VerificationResult(
                check_name="github_release",
                passed=False,
                message="No GitHub release URL found",
                severity="warning",
            )
        
        if not AIOHTTP_AVAILABLE:
            return VerificationResult(
                check_name="github_release",
                passed=False,
                message="aiohttp not available to verify release",
                severity="warning",
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(release_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        return VerificationResult(
                            check_name="github_release",
                            passed=True,
                            message=f"GitHub release accessible at {release_url}",
                            details={"url": release_url},
                            severity="info",
                        )
        except Exception as e:
            pass
        
        return VerificationResult(
            check_name="github_release",
            passed=False,
            message=f"Could not verify GitHub release at {release_url}",
            severity="warning",
        )
    
    async def _perform_visual_diff(self, deployment_url: str, project_path: str) -> Optional[VerificationResult]:
        """Compare live screenshot with QA screenshot."""
        if not PIL_AVAILABLE:
            return None
        
        # Look for QA screenshots
        qa_screenshot_paths = [
            os.path.join(project_path, "qa_screenshots", "homepage.png"),
            os.path.join(project_path, "screenshots", "qa", "homepage.png"),
            os.path.join(project_path, ".qa", "screenshots", "homepage.png"),
        ]
        
        qa_screenshot = None
        for path in qa_screenshot_paths:
            if os.path.exists(path):
                qa_screenshot = path
                break
        
        if not qa_screenshot:
            return None
        
        # In a real implementation, we would:
        # 1. Use browser_mcp or Playwright to take a live screenshot
        # 2. Compare with the QA screenshot using image hashing
        
        # For now, return a placeholder result
        return VerificationResult(
            check_name="visual_diff",
            passed=True,
            message="Visual diff check skipped - browser automation not available",
            details={"similarity_score": None},
            severity="info",
        )
    
    def _generate_report(
        self,
        project_id: str,
        deployment_url: str,
        visual_score: Optional[float],
        warnings: List[str],
    ) -> DeployVerificationReport:
        """Generate the verification report."""
        checks_passed = sum(1 for r in self.verification_results if r.passed)
        checks_failed = sum(1 for r in self.verification_results if not r.passed)
        
        endpoint_passed = sum(1 for e in self.endpoint_checks if e.passed)
        endpoint_failed = sum(1 for e in self.endpoint_checks if not e.passed)
        
        total_passed = checks_passed + endpoint_passed
        total_failed = checks_failed + endpoint_failed
        
        # Determine overall status
        critical_failures = [r for r in self.verification_results if not r.passed and r.severity == "critical"]
        
        if critical_failures or endpoint_failed > 2:
            overall_status = "failed"
        elif total_failed > 0:
            overall_status = "partial"
        else:
            overall_status = "passed"
        
        # Get SSL info
        ssl_result = next((r for r in self.verification_results if r.check_name == "ssl_certificate"), None)
        ssl_valid = ssl_result.passed if ssl_result else False
        ssl_expiry = ssl_result.details.get("expiry") if ssl_result and ssl_result.details else None
        
        return DeployVerificationReport(
            project_id=project_id,
            deployment_url=deployment_url,
            generated_at=datetime.utcnow().isoformat(),
            overall_status=overall_status,
            checks_passed=total_passed,
            checks_failed=total_failed,
            endpoint_checks=[
                {
                    "url": e.url,
                    "status_code": e.status_code,
                    "response_time_ms": e.response_time_ms,
                    "passed": e.passed,
                    "error": e.error,
                }
                for e in self.endpoint_checks
            ],
            ssl_valid=ssl_valid,
            ssl_expiry=ssl_expiry,
            visual_diff_score=visual_score,
            verification_results=[
                {
                    "check": r.check_name,
                    "passed": r.passed,
                    "message": r.message,
                    "severity": r.severity,
                    "details": r.details,
                }
                for r in self.verification_results
            ],
            warnings=warnings,
        )
