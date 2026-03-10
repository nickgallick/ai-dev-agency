"""SEO Agent - Lighthouse integration for performance and SEO audits."""

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from .base import AgentResult, BaseAgent


@dataclass
class LighthouseScores:
    """Lighthouse audit scores."""
    performance: int = 0
    accessibility: int = 0
    best_practices: int = 0
    seo: int = 0
    pwa: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "performance": self.performance,
            "accessibility": self.accessibility,
            "best_practices": self.best_practices,
            "seo": self.seo,
            "pwa": self.pwa,
        }


@dataclass
class SEOIssue:
    """Represents an SEO issue found during audit."""
    category: str
    title: str
    description: str
    score: Optional[float] = None
    impact: str = "medium"


@dataclass
class SEOReport:
    """SEO audit report."""
    scores: LighthouseScores = field(default_factory=LighthouseScores)
    issues: List[SEOIssue] = field(default_factory=list)
    meta_tags: Dict[str, str] = field(default_factory=dict)
    structured_data_valid: bool = False
    structured_data_errors: List[str] = field(default_factory=list)
    sitemap_generated: bool = False
    robots_generated: bool = False
    scan_url: str = ""
    scan_time: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scores": self.scores.to_dict(),
            "issues": [
                {
                    "category": i.category,
                    "title": i.title,
                    "description": i.description,
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
            "scan_url": self.scan_url,
            "scan_time": self.scan_time,
            "errors": self.errors,
        }


class SEOAgent(BaseAgent):
    """Agent for SEO auditing and optimization."""

    LIGHTHOUSE_NETWORK = "lighthouse-scan"

    @property
    def name(self) -> str:
        return "SEO"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute SEO audit and generate optimizations."""
        project_path = context.get("project_path")
        live_url = context.get("live_url")  # Optional: deployed URL for Phase 5
        project_name = context.get("project_name", "project")

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

        self.logger.info(f"Running SEO audit on: {project_path}")

        report = SEOReport()
        start_time = time.time()

        # Pass 1: Scan local dev server
        local_report = await self._scan_local_server(project_path)
        if local_report:
            report = local_report

        # Pass 2: Scan deployed URL if available (Phase 5)
        if live_url:
            self.logger.info(f"Running production audit on: {live_url}")
            production_report = await self._run_lighthouse_audit(live_url)
            if production_report:
                # Store both reports, prioritize production scores
                report.scores = production_report.scores
                report.scan_url = live_url

        # Generate optimizations
        await self._generate_meta_tags(project_path, project_name, report)
        await self._generate_sitemap(project_path, live_url or "https://example.com", report)
        await self._generate_robots_txt(project_path, report)
        await self._validate_structured_data(project_path, report)

        report.scan_time = time.time() - start_time

        # Generate report file
        report_path = os.path.join(project_path, "seo_report.json")
        self.write_file(report_path, json.dumps(report.to_dict(), indent=2))

        return AgentResult(
            success=True,
            agent_name=self.name,
            data={
                "report": report.to_dict(),
                "report_path": report_path,
            },
        )

    async def _scan_local_server(self, project_path: str) -> Optional[SEOReport]:
        """Build project and scan local dev server."""
        if not self.use_docker_sdk:
            self.logger.warning("Docker SDK not available, skipping local server scan")
            return None

        try:
            import docker
            client = self.docker_client

            # Create network for scan
            try:
                network = client.networks.create(
                    self.LIGHTHOUSE_NETWORK, driver="bridge"
                )
            except docker.errors.APIError:
                # Network might already exist
                network = client.networks.get(self.LIGHTHOUSE_NETWORK)

            project_container = None
            try:
                # Start project preview container
                self.logger.info("Starting project preview container...")
                project_container = client.containers.run(
                    image="node:20-alpine",
                    command="sh -c 'cd /app && npm install --silent && npm run build && npm start'",
                    volumes={project_path: {"bind": "/app", "mode": "ro"}},
                    network=self.LIGHTHOUSE_NETWORK,
                    name="project-preview",
                    detach=True,
                    environment={"PORT": "3000"},
                )

                # Wait for server to be ready
                await self._wait_for_server(project_container, timeout=120)

                # Run Lighthouse against local server
                local_url = "http://project-preview:3000"
                report = await self._run_lighthouse_audit(
                    local_url, network=self.LIGHTHOUSE_NETWORK
                )
                if report:
                    report.scan_url = "local-dev-server"
                return report

            finally:
                # Cleanup
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
            self.logger.error(f"Local server scan failed: {e}")
            return None

    async def _wait_for_server(self, container, timeout: int = 120) -> bool:
        """Wait for the server container to be ready."""
        import asyncio
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                container.reload()
                if container.status == "exited":
                    logs = container.logs().decode("utf-8")
                    self.logger.error(f"Container exited: {logs}")
                    return False
                
                # Check if server is responding
                exit_code, output = container.exec_run(
                    "wget -q --spider http://localhost:3000 || exit 1"
                )
                if exit_code == 0:
                    self.logger.info("Project server is ready")
                    return True
            except:
                pass
            
            await asyncio.sleep(2)
        
        self.logger.warning("Timeout waiting for server")
        return False

    async def _run_lighthouse_audit(
        self, url: str, network: Optional[str] = None
    ) -> Optional[SEOReport]:
        """Run Lighthouse audit on a URL."""
        report = SEOReport()
        
        command = [
            "lighthouse",
            url,
            "--output=json",
            "--output-path=/tmp/report.json",
            "--chrome-flags=--headless --no-sandbox --disable-gpu",
            "--only-categories=performance,accessibility,best-practices,seo",
        ]

        self.logger.info(f"Running Lighthouse audit on: {url}")

        exit_code, stdout, stderr = self.run_docker_container(
            image=self.settings.lighthouse_image,
            command=command,
            network=network,
            timeout=self.settings.lighthouse_timeout,
        )

        # Parse Lighthouse JSON output
        try:
            # Try to find JSON in stdout
            json_match = re.search(r'\{[\s\S]*\}', stdout)
            if json_match:
                results = json.loads(json_match.group())
                categories = results.get("categories", {})
                
                report.scores = LighthouseScores(
                    performance=int((categories.get("performance", {}).get("score", 0) or 0) * 100),
                    accessibility=int((categories.get("accessibility", {}).get("score", 0) or 0) * 100),
                    best_practices=int((categories.get("best-practices", {}).get("score", 0) or 0) * 100),
                    seo=int((categories.get("seo", {}).get("score", 0) or 0) * 100),
                )

                # Extract issues from audits
                audits = results.get("audits", {})
                for audit_id, audit in audits.items():
                    score = audit.get("score")
                    if score is not None and score < 1:
                        report.issues.append(SEOIssue(
                            category=self._get_audit_category(audit_id),
                            title=audit.get("title", audit_id),
                            description=audit.get("description", ""),
                            score=score,
                            impact=self._score_to_impact(score),
                        ))

                return report
        except json.JSONDecodeError as e:
            report.errors.append(f"Failed to parse Lighthouse output: {e}")
        except Exception as e:
            report.errors.append(f"Lighthouse audit error: {e}")

        return report if not report.errors else None

    def _get_audit_category(self, audit_id: str) -> str:
        """Map audit ID to category."""
        performance_audits = ["first-contentful-paint", "speed-index", "largest-contentful-paint", 
                            "total-blocking-time", "cumulative-layout-shift"]
        seo_audits = ["meta-description", "document-title", "link-text", "robots-txt", "canonical"]
        
        if any(a in audit_id for a in performance_audits):
            return "Performance"
        if any(a in audit_id for a in seo_audits):
            return "SEO"
        return "Best Practices"

    def _score_to_impact(self, score: Optional[float]) -> str:
        """Convert score to impact level."""
        if score is None:
            return "medium"
        if score < 0.5:
            return "high"
        if score < 0.9:
            return "medium"
        return "low"

    async def _generate_meta_tags(
        self, project_path: str, project_name: str, report: SEOReport
    ) -> None:
        """Generate optimized meta tags."""
        meta_tags = {
            "title": f"{project_name} - Modern Web Application",
            "description": f"Welcome to {project_name}. A fast, accessible, and modern web application.",
            "viewport": "width=device-width, initial-scale=1.0",
            "charset": "utf-8",
            "robots": "index, follow",
            "og:type": "website",
            "og:title": f"{project_name}",
            "og:description": f"Welcome to {project_name}. A fast, accessible, and modern web application.",
            "twitter:card": "summary_large_image",
            "twitter:title": f"{project_name}",
            "twitter:description": f"Welcome to {project_name}. A fast, accessible, and modern web application.",
        }

        report.meta_tags = meta_tags

        # Generate meta tags file
        meta_content = self._generate_meta_html(meta_tags)
        meta_path = os.path.join(project_path, "generated_meta_tags.html")
        self.write_file(meta_path, meta_content)

    def _generate_meta_html(self, meta_tags: Dict[str, str]) -> str:
        """Generate HTML meta tags snippet."""
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
        
        return "\n".join(lines)

    async def _generate_sitemap(
        self, project_path: str, base_url: str, report: SEOReport
    ) -> None:
        """Generate sitemap.xml."""
        # Discover pages in the project
        pages = self._discover_pages(project_path)
        
        root = ET.Element("urlset")
        root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

        for page in pages:
            url_elem = ET.SubElement(root, "url")
            loc = ET.SubElement(url_elem, "loc")
            loc.text = f"{base_url.rstrip('/')}/{page.lstrip('/')}"
            
            lastmod = ET.SubElement(url_elem, "lastmod")
            lastmod.text = time.strftime("%Y-%m-%d")
            
            changefreq = ET.SubElement(url_elem, "changefreq")
            changefreq.text = "weekly"
            
            priority = ET.SubElement(url_elem, "priority")
            priority.text = "1.0" if page in ["", "/", "index"] else "0.8"

        sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_content += ET.tostring(root, encoding="unicode")
        
        sitemap_path = os.path.join(project_path, "public", "sitemap.xml")
        os.makedirs(os.path.dirname(sitemap_path), exist_ok=True)
        
        if self.write_file(sitemap_path, sitemap_content):
            report.sitemap_generated = True
            self.logger.info("Generated sitemap.xml")

    def _discover_pages(self, project_path: str) -> List[str]:
        """Discover pages in the project."""
        pages = ["/"]
        
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

# Sitemap location
Sitemap: /sitemap.xml
"""
        
        robots_path = os.path.join(project_path, "public", "robots.txt")
        os.makedirs(os.path.dirname(robots_path), exist_ok=True)
        
        if self.write_file(robots_path, robots_content):
            report.robots_generated = True
            self.logger.info("Generated robots.txt")

    async def _validate_structured_data(
        self, project_path: str, report: SEOReport
    ) -> None:
        """Validate JSON-LD structured data in the project."""
        errors = []
        found_structured_data = False

        # Search for JSON-LD in HTML files
        for root, _, files in os.walk(project_path):
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
                        except json.JSONDecodeError as e:
                            errors.append(f"{file}: Invalid JSON-LD - {e}")

        report.structured_data_valid = found_structured_data and not errors
        report.structured_data_errors = errors

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
            self.logger.info("Generated sample structured data template")
