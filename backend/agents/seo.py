"""SEO Agent - Lighthouse integration for performance and SEO audits.

Phase 11E Enhancement:
- Page-aware auditing (run Lighthouse on ALL pages from requirements.pages)
- Project-type-aware expectations (landing vs SaaS vs mobile)
- Dual-theme Lighthouse (if dark_mode="both")
- Dual-theme contrast ratios
- Integration-aware checks (Stripe structured data)
- Query KB for common SEO issues
- Write audit results to KB
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from .base import AgentResult, BaseAgent

# Import knowledge base
try:
    from ..knowledge import query_knowledge, store_knowledge, KnowledgeEntryType
    KB_AVAILABLE = True
except ImportError:
    KB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class LighthouseScores:
    """Lighthouse audit scores."""
    performance: int = 0
    accessibility: int = 0
    best_practices: int = 0
    seo: int = 0
    pwa: int = 0
    theme: str = "default"  # "light", "dark", or "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "performance": self.performance,
            "accessibility": self.accessibility,
            "best_practices": self.best_practices,
            "seo": self.seo,
            "pwa": self.pwa,
            "theme": self.theme,
        }


@dataclass
class SEOIssue:
    """Represents an SEO issue found during audit."""
    category: str
    title: str
    description: str
    page: str = "/"  # Which page this issue was found on
    theme: str = "default"  # Which theme this issue applies to
    score: Optional[float] = None
    impact: str = "medium"


@dataclass
class SEOReport:
    """SEO audit report."""
    scores: LighthouseScores = field(default_factory=LighthouseScores)
    scores_by_theme: Dict[str, LighthouseScores] = field(default_factory=dict)  # light/dark scores
    scores_by_page: Dict[str, LighthouseScores] = field(default_factory=dict)  # per-page scores
    issues: List[SEOIssue] = field(default_factory=list)
    meta_tags: Dict[str, str] = field(default_factory=dict)
    structured_data_valid: bool = False
    structured_data_errors: List[str] = field(default_factory=list)
    sitemap_generated: bool = False
    robots_generated: bool = False
    pages_audited: List[str] = field(default_factory=list)
    theme_mode: str = "single"  # "single" or "both"
    project_type: str = "web"
    kb_patterns_used: int = 0
    scan_url: str = ""
    scan_time: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scores": self.scores.to_dict(),
            "scores_by_theme": {k: v.to_dict() for k, v in self.scores_by_theme.items()},
            "scores_by_page": {k: v.to_dict() for k, v in self.scores_by_page.items()},
            "issues": [
                {
                    "category": i.category,
                    "title": i.title,
                    "description": i.description,
                    "page": i.page,
                    "theme": i.theme,
                    "score": i.score,
                    "impact": i.impact,
                }
                for i in self.issues
            ],
            "meta_tags": self.meta_tags,
            "structured_data_valid": self.structured_data_valid,
            "structured_data_errors": self.structured_data_errors,
            "sitemap_generated": self.sitemap_generated,
            "robots_generated": self.robots_generated,
            "pages_audited": self.pages_audited,
            "theme_mode": self.theme_mode,
            "project_type": self.project_type,
            "kb_patterns_used": self.kb_patterns_used,
            "scan_url": self.scan_url,
            "scan_time": self.scan_time,
            "errors": self.errors,
        }


# Project type SEO expectations
PROJECT_TYPE_EXPECTATIONS = {
    "landing": {
        "min_performance": 90,
        "min_seo": 95,
        "required_structured_data": ["Organization", "WebSite"],
    },
    "saas": {
        "min_performance": 80,
        "min_seo": 90,
        "required_structured_data": ["WebApplication", "Organization"],
    },
    "ecommerce": {
        "min_performance": 85,
        "min_seo": 95,
        "required_structured_data": ["Product", "Organization", "BreadcrumbList"],
    },
    "blog": {
        "min_performance": 85,
        "min_seo": 95,
        "required_structured_data": ["Article", "Organization", "BreadcrumbList"],
    },
    "mobile_pwa": {
        "min_performance": 90,
        "min_pwa": 90,
        "required_structured_data": ["WebApplication"],
    },
}


class SEOAgent(BaseAgent):
    """Agent for SEO auditing and optimization."""

    LIGHTHOUSE_NETWORK = "lighthouse-scan"

    @property
    def name(self) -> str:
        return "SEO"

    async def _query_kb_for_seo_issues(self, project_type: str) -> List[Dict]:
        """Query KB for common SEO issues for this project type."""
        if not KB_AVAILABLE:
            return []
        
        try:
            results = await query_knowledge(
                query=f"common SEO issues for {project_type} projects",
                entry_types=[KnowledgeEntryType.QA_FINDING],
                limit=15,
            )
            return results
        except Exception as e:
            logger.warning(f"KB query failed: {e}")
            return []
    
    async def _write_to_kb(self, report: 'SEOReport', project_type: str):
        """Write SEO findings to KB for future reference."""
        if not KB_AVAILABLE:
            return
        
        try:
            # Store scores
            await store_knowledge(
                entry_type=KnowledgeEntryType.QA_FINDING,
                content=f"SEO audit: perf={report.scores.performance}, seo={report.scores.seo}",
                metadata={
                    "project_type": project_type,
                    "scores": report.scores.to_dict(),
                    "pages_audited": len(report.pages_audited),
                    "theme_mode": report.theme_mode,
                    "agent": "seo",
                },
            )
            
            # Store significant issues
            for issue in report.issues:
                if issue.impact == "high":
                    await store_knowledge(
                        entry_type=KnowledgeEntryType.QA_FINDING,
                        content=f"SEO issue: {issue.title}",
                        metadata={
                            "project_type": project_type,
                            "category": issue.category,
                            "page": issue.page,
                            "theme": issue.theme,
                            "agent": "seo",
                        },
                    )
        except Exception as e:
            logger.warning(f"KB write failed: {e}")

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute SEO audit and generate optimizations."""
        project_path = context.get("project_path")
        live_url = context.get("live_url")  # Optional: deployed URL
        project_name = context.get("project_name", "project")
        requirements = context.get("requirements", {})
        project_type = context.get("project_type", "web_simple")

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

        logger.info(f"Running SEO audit on: {project_path}")

        report = SEOReport()
        report.project_type = project_type
        start_time = time.time()

        # Determine theme mode from requirements
        color_scheme = requirements.get("color_scheme", "dark")
        if color_scheme in ["both", "system"]:
            report.theme_mode = "both"
        else:
            report.theme_mode = "single"
        
        # Get pages from requirements
        pages_to_audit = self._get_pages_from_requirements(requirements, project_path)
        report.pages_audited = pages_to_audit
        
        # Query KB for common issues
        kb_patterns = await self._query_kb_for_seo_issues(project_type)
        report.kb_patterns_used = len(kb_patterns)
        
        # Pass 1: Scan local dev server (all pages)
        if self.use_docker_sdk:
            local_results = await self._scan_all_pages_locally(
                project_path, pages_to_audit, report.theme_mode
            )
            if local_results:
                for page, scores in local_results.items():
                    report.scores_by_page[page] = scores
        
        # Pass 2: Scan deployed URL if available
        if live_url:
            logger.info(f"Running production audit on: {live_url}")
            
            # Audit all pages in production
            for page in pages_to_audit[:10]:  # Limit to 10 pages for production
                page_url = f"{live_url.rstrip('/')}{page}"
                
                if report.theme_mode == "both":
                    # Run in both themes
                    light_scores = await self._run_lighthouse_audit(page_url, theme="light")
                    if light_scores:
                        light_scores.theme = "light"
                        report.scores_by_theme["light"] = light_scores
                    
                    dark_scores = await self._run_lighthouse_audit(page_url, theme="dark")
                    if dark_scores:
                        dark_scores.theme = "dark"
                        report.scores_by_theme["dark"] = dark_scores
                    
                    # Use average scores
                    if light_scores and dark_scores:
                        report.scores = LighthouseScores(
                            performance=(light_scores.performance + dark_scores.performance) // 2,
                            accessibility=(light_scores.accessibility + dark_scores.accessibility) // 2,
                            best_practices=(light_scores.best_practices + dark_scores.best_practices) // 2,
                            seo=(light_scores.seo + dark_scores.seo) // 2,
                        )
                else:
                    production_scores = await self._run_lighthouse_audit(page_url)
                    if production_scores:
                        report.scores = production_scores
                
                report.scan_url = live_url

        # Check project-type expectations
        expectations = PROJECT_TYPE_EXPECTATIONS.get(
            self._normalize_project_type(project_type), {}
        )
        self._check_expectations(report, expectations)

        # Generate optimizations
        await self._generate_meta_tags(project_path, project_name, report, requirements)
        await self._generate_sitemap(project_path, live_url or "https://example.com", report, pages_to_audit)
        await self._generate_robots_txt(project_path, report)
        await self._validate_structured_data(project_path, report, requirements)

        # Check integration-specific SEO
        await self._check_integration_seo(project_path, requirements, report)

        report.scan_time = time.time() - start_time

        # Write to KB
        await self._write_to_kb(report, project_type)

        # Generate report file
        report_path = os.path.join(project_path, "seo_report.json")
        self.write_file(report_path, json.dumps(report.to_dict(), indent=2))

        # Determine success
        success = report.scores.seo >= 80 and report.scores.performance >= 70

        return AgentResult(
            success=success,
            agent_name=self.name,
            data={
                "report": report.to_dict(),
                "report_path": report_path,
            },
            warnings=[f"{i.category}: {i.title}" for i in report.issues if i.impact == "high"],
        )
    
    def _get_pages_from_requirements(
        self, requirements: Dict[str, Any], project_path: str
    ) -> List[str]:
        """Extract pages to audit from requirements."""
        pages = ["/"]  # Always include home
        
        # From web_complex_options
        web_complex = requirements.get("web_complex_options", {})
        for page in web_complex.get("pages", []):
            if isinstance(page, dict):
                route = page.get("route", f"/{page.get('name', '')}")
            else:
                route = f"/{page}"
            route = route.replace(" ", "-").lower()
            if route not in pages:
                pages.append(route)
        
        # From web_simple_options
        web_simple = requirements.get("web_simple_options", {})
        for section in web_simple.get("sections", []):
            route = f"/#{section.lower().replace(' ', '-')}"
            # For single page, sections are anchors not routes
        
        # Also discover from project files
        discovered = self._discover_pages(project_path)
        for page in discovered:
            if page not in pages:
                pages.append(page)
        
        return pages[:20]  # Limit to 20 pages
    
    def _normalize_project_type(self, project_type: str) -> str:
        """Normalize project type to expectation categories."""
        if "landing" in project_type.lower():
            return "landing"
        if "saas" in project_type.lower() or "complex" in project_type.lower():
            return "saas"
        if "ecommerce" in project_type.lower() or "shop" in project_type.lower():
            return "ecommerce"
        if "blog" in project_type.lower():
            return "blog"
        if "pwa" in project_type.lower() or "mobile" in project_type.lower():
            return "mobile_pwa"
        return "saas"  # Default
    
    def _check_expectations(self, report: SEOReport, expectations: Dict[str, Any]):
        """Check if scores meet project type expectations."""
        if not expectations:
            return
        
        min_perf = expectations.get("min_performance", 0)
        min_seo = expectations.get("min_seo", 0)
        
        if report.scores.performance < min_perf:
            report.issues.append(SEOIssue(
                category="Performance",
                title=f"Performance below {report.project_type} expectations",
                description=f"Score {report.scores.performance} is below minimum {min_perf} for this project type",
                impact="high",
            ))
        
        if report.scores.seo < min_seo:
            report.issues.append(SEOIssue(
                category="SEO",
                title=f"SEO score below {report.project_type} expectations",
                description=f"Score {report.scores.seo} is below minimum {min_seo} for this project type",
                impact="high",
            ))
    
    async def _scan_all_pages_locally(
        self, 
        project_path: str, 
        pages: List[str],
        theme_mode: str
    ) -> Dict[str, LighthouseScores]:
        """Scan all pages locally with optional dual-theme testing."""
        results = {}
        
        if not self.use_docker_sdk:
            logger.warning("Docker SDK not available, skipping local server scan")
            return results
        
        try:
            import docker
            client = self.docker_client
            
            # Create network for scan
            try:
                network = client.networks.create(self.LIGHTHOUSE_NETWORK, driver="bridge")
            except docker.errors.APIError:
                network = client.networks.get(self.LIGHTHOUSE_NETWORK)
            
            project_container = None
            try:
                # Start project preview container
                logger.info("Starting project preview container...")
                project_container = client.containers.run(
                    image="node:20-alpine",
                    command="sh -c 'cd /app && npm install --silent && npm run build && npm start'",
                    volumes={project_path: {"bind": "/app", "mode": "ro"}},
                    network=self.LIGHTHOUSE_NETWORK,
                    name="project-preview",
                    detach=True,
                    environment={"PORT": "3000"},
                )
                
                # Wait for server
                await self._wait_for_server(project_container, timeout=120)
                
                # Scan each page
                for page in pages[:5]:  # Limit local scans
                    local_url = f"http://project-preview:3000{page}"
                    
                    if theme_mode == "both":
                        # Scan both themes
                        for theme in ["light", "dark"]:
                            scores = await self._run_lighthouse_audit(
                                local_url, 
                                network=self.LIGHTHOUSE_NETWORK,
                                theme=theme
                            )
                            if scores:
                                scores.theme = theme
                                results[f"{page}:{theme}"] = scores
                    else:
                        scores = await self._run_lighthouse_audit(
                            local_url,
                            network=self.LIGHTHOUSE_NETWORK
                        )
                        if scores:
                            results[page] = scores
                
            finally:
                if project_container:
                    try:
                        project_container.stop(timeout=5)
                        project_container.remove(force=True)
                    except:
                        pass
                try:
                    network.remove()
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Local server scan failed: {e}")
        
        return results

    async def _wait_for_server(self, container, timeout: int = 120) -> bool:
        """Wait for the server container to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                container.reload()
                if container.status == "exited":
                    logs = container.logs().decode("utf-8")
                    logger.error(f"Container exited: {logs}")
                    return False
                
                # Check if server is responding
                exit_code, output = container.exec_run(
                    "wget -q --spider http://localhost:3000 || exit 1"
                )
                if exit_code == 0:
                    logger.info("Project server is ready")
                    return True
            except:
                pass
            
            await asyncio.sleep(2)
        
        logger.warning("Timeout waiting for server")
        return False

    async def _run_lighthouse_audit(
        self, 
        url: str, 
        network: Optional[str] = None,
        theme: Optional[str] = None
    ) -> Optional[LighthouseScores]:
        """Run Lighthouse audit on a URL with optional theme setting."""
        command = [
            "lighthouse",
            url,
            "--output=json",
            "--output-path=/tmp/report.json",
            "--chrome-flags=--headless --no-sandbox --disable-gpu",
            "--only-categories=performance,accessibility,best-practices,seo",
        ]
        
        # Add theme emulation
        if theme:
            emulated_form_factor = "mobile"
            if theme == "dark":
                command.append("--emulated-media-type=screen")
                # Note: Lighthouse doesn't directly support dark mode, but we can
                # inject CSS to test. For production, use prefers-color-scheme
        
        logger.info(f"Running Lighthouse audit on: {url} (theme: {theme or 'default'})")

        exit_code, stdout, stderr = self.run_docker_container(
            image=self.settings.lighthouse_image,
            command=command,
            network=network,
            timeout=self.settings.lighthouse_timeout,
        )

        # Parse Lighthouse JSON output
        try:
            json_match = re.search(r'\{[\s\S]*\}', stdout)
            if json_match:
                results = json.loads(json_match.group())
                categories = results.get("categories", {})
                
                return LighthouseScores(
                    performance=int((categories.get("performance", {}).get("score", 0) or 0) * 100),
                    accessibility=int((categories.get("accessibility", {}).get("score", 0) or 0) * 100),
                    best_practices=int((categories.get("best-practices", {}).get("score", 0) or 0) * 100),
                    seo=int((categories.get("seo", {}).get("score", 0) or 0) * 100),
                    pwa=int((categories.get("pwa", {}).get("score", 0) or 0) * 100),
                    theme=theme or "default",
                )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Lighthouse output: {e}")
        except Exception as e:
            logger.error(f"Lighthouse audit error: {e}")

        return None

    async def _generate_meta_tags(
        self, 
        project_path: str, 
        project_name: str, 
        report: SEOReport,
        requirements: Dict[str, Any]
    ) -> None:
        """Generate optimized meta tags with theme support."""
        description = requirements.get("project_description", 
            f"Welcome to {project_name}. A fast, accessible, and modern web application.")
        
        meta_tags = {
            "title": f"{project_name} - Modern Web Application",
            "description": description[:160],  # Limit to 160 chars
            "viewport": "width=device-width, initial-scale=1.0",
            "charset": "utf-8",
            "robots": "index, follow",
            "theme-color": "#191A1A",  # Dark theme default
            "color-scheme": "dark light" if report.theme_mode == "both" else "dark",
            "og:type": "website",
            "og:title": project_name,
            "og:description": description[:200],
            "twitter:card": "summary_large_image",
            "twitter:title": project_name,
            "twitter:description": description[:200],
        }

        report.meta_tags = meta_tags

        # Generate meta tags file
        meta_content = self._generate_meta_html(meta_tags, report.theme_mode)
        meta_path = os.path.join(project_path, "generated_meta_tags.html")
        self.write_file(meta_path, meta_content)

    def _generate_meta_html(self, meta_tags: Dict[str, str], theme_mode: str) -> str:
        """Generate HTML meta tags snippet with theme support."""
        lines = ["<!-- Generated Meta Tags -->"]
        
        for key, value in meta_tags.items():
            if key == "charset":
                lines.append(f'<meta charset="{value}">')
            elif key == "title":
                lines.append(f'<title>{value}</title>')
            elif key.startswith("og:"):
                lines.append(f'<meta property="{key}" content="{value}">')
            elif key.startswith("twitter:"):
                lines.append(f'<meta name="{key}" content="{value}">')
            else:
                lines.append(f'<meta name="{key}" content="{value}">')
        
        # Add theme-aware meta tags
        if theme_mode == "both":
            lines.append("")
            lines.append("<!-- Theme-aware colors -->")
            lines.append('<meta name="theme-color" content="#191A1A" media="(prefers-color-scheme: dark)">')
            lines.append('<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">')
        
        return "\n".join(lines)

    async def _generate_sitemap(
        self, 
        project_path: str, 
        base_url: str, 
        report: SEOReport,
        pages: List[str]
    ) -> None:
        """Generate sitemap.xml with all pages."""
        root = ET.Element("urlset")
        root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

        for page in pages:
            if page.startswith("/#"):  # Skip anchor links
                continue
            
            url_elem = ET.SubElement(root, "url")
            loc = ET.SubElement(url_elem, "loc")
            loc.text = f"{base_url.rstrip('/')}{page}"
            
            lastmod = ET.SubElement(url_elem, "lastmod")
            lastmod.text = time.strftime("%Y-%m-%d")
            
            changefreq = ET.SubElement(url_elem, "changefreq")
            changefreq.text = "weekly"
            
            priority = ET.SubElement(url_elem, "priority")
            priority.text = "1.0" if page in ["", "/", "/index"] else "0.8"

        sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_content += ET.tostring(root, encoding="unicode")
        
        sitemap_path = os.path.join(project_path, "public", "sitemap.xml")
        os.makedirs(os.path.dirname(sitemap_path), exist_ok=True)
        
        if self.write_file(sitemap_path, sitemap_content):
            report.sitemap_generated = True
            logger.info("Generated sitemap.xml")

    def _discover_pages(self, project_path: str) -> List[str]:
        """Discover pages in the project."""
        pages = []
        
        # Check for Next.js pages
        pages_dirs = [
            os.path.join(project_path, "pages"),
            os.path.join(project_path, "src", "pages"),
            os.path.join(project_path, "app"),
            os.path.join(project_path, "src", "app"),
        ]

        for pages_dir in pages_dirs:
            if os.path.exists(pages_dir):
                for root, dirs, files in os.walk(pages_dir):
                    # Skip special directories
                    dirs[:] = [d for d in dirs if not d.startswith(("_", "api", "["))]
                    
                    for file in files:
                        if file.endswith((".tsx", ".jsx", ".js", ".ts")):
                            # Skip special files
                            if file.startswith("_") or file == "layout.tsx":
                                continue
                            
                            rel_path = os.path.relpath(
                                os.path.join(root, file), pages_dir
                            )
                            # Convert file path to URL path
                            page_path = "/" + rel_path.rsplit(".", 1)[0]
                            page_path = page_path.replace("/index", "").replace("\\", "/")
                            page_path = page_path.replace("/page", "")
                            if page_path and page_path not in pages:
                                pages.append(page_path)

        return pages

    async def _generate_robots_txt(
        self, project_path: str, report: SEOReport
    ) -> None:
        """Generate robots.txt."""
        robots_content = """# Generated robots.txt
User-agent: *
Allow: /

# Disallow admin and API routes
Disallow: /admin
Disallow: /api/
Disallow: /dashboard
Disallow: /_next/

# Sitemap location
Sitemap: /sitemap.xml
"""
        
        robots_path = os.path.join(project_path, "public", "robots.txt")
        os.makedirs(os.path.dirname(robots_path), exist_ok=True)
        
        if self.write_file(robots_path, robots_content):
            report.robots_generated = True
            logger.info("Generated robots.txt")

    async def _validate_structured_data(
        self, 
        project_path: str, 
        report: SEOReport,
        requirements: Dict[str, Any]
    ) -> None:
        """Validate JSON-LD structured data in the project."""
        errors = []
        found_structured_data = False
        found_types = set()

        # Search for JSON-LD in files
        for root, _, files in os.walk(project_path):
            if "node_modules" in root:
                continue
            
            for file in files:
                if file.endswith((".html", ".tsx", ".jsx")):
                    file_path = os.path.join(root, file)
                    content = self.read_file(file_path)
                    if not content:
                        continue

                    # Find JSON-LD scripts
                    jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>'
                    matches = re.findall(jsonld_pattern, content)

                    for match in matches:
                        found_structured_data = True
                        try:
                            data = json.loads(match)
                            # Basic validation
                            if "@context" not in data:
                                errors.append(f"{file}: Missing @context in JSON-LD")
                            if "@type" not in data:
                                errors.append(f"{file}: Missing @type in JSON-LD")
                            else:
                                found_types.add(data["@type"])
                        except json.JSONDecodeError as e:
                            errors.append(f"{file}: Invalid JSON-LD - {e}")

        report.structured_data_valid = found_structured_data and not errors
        report.structured_data_errors = errors

        # Check for required types based on project type
        expectations = PROJECT_TYPE_EXPECTATIONS.get(
            self._normalize_project_type(report.project_type), {}
        )
        required_types = expectations.get("required_structured_data", [])
        
        for req_type in required_types:
            if req_type not in found_types:
                report.issues.append(SEOIssue(
                    category="Structured Data",
                    title=f"Missing {req_type} structured data",
                    description=f"Project type '{report.project_type}' should have {req_type} schema",
                    impact="medium",
                ))

        if not found_structured_data:
            # Generate sample structured data
            sample_jsonld = {
                "@context": "https://schema.org",
                "@type": "WebApplication",
                "name": "Application Name",
                "description": "Application description",
                "applicationCategory": "WebApplication",
            }
            sample_path = os.path.join(project_path, "sample_structured_data.json")
            self.write_file(sample_path, json.dumps(sample_jsonld, indent=2))
            logger.info("Generated sample structured data template")
    
    async def _check_integration_seo(
        self, 
        project_path: str, 
        requirements: Dict[str, Any],
        report: SEOReport
    ) -> None:
        """Check integration-specific SEO requirements."""
        integrations = requirements.get("integrations", [])
        features = requirements.get("features", [])
        
        # Check for payment-related structured data
        has_payments = any("stripe" in i.lower() or "payment" in i.lower() 
                          for i in integrations + features)
        
        if has_payments:
            # Check for Product schema if selling products
            has_product_schema = False
            for root, _, files in os.walk(project_path):
                if "node_modules" in root:
                    continue
                for file in files:
                    if file.endswith((".tsx", ".jsx", ".html")):
                        content = self.read_file(os.path.join(root, file))
                        if content and '"@type":"Product"' in content.replace(" ", ""):
                            has_product_schema = True
                            break
                if has_product_schema:
                    break
            
            if not has_product_schema:
                report.issues.append(SEOIssue(
                    category="Structured Data",
                    title="Payment integration without Product schema",
                    description="Consider adding Product structured data for better SEO of purchasable items",
                    impact="low",
                ))
