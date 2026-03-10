"""Analytics & Monitoring Setup Agent - Comprehensive monitoring and analytics configuration."""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .base import AgentResult, BaseAgent


@dataclass
class MonitoringService:
    """Represents a monitoring service configuration."""
    name: str
    enabled: bool
    configured: bool = False
    tracking_code: Optional[str] = None
    dashboard_url: Optional[str] = None
    api_key_provided: bool = False
    error_message: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringReport:
    """Complete monitoring setup report."""
    project_name: str
    services: List[MonitoringService] = field(default_factory=list)
    lighthouse_ci_configured: bool = False
    lighthouse_config_path: Optional[str] = None
    github_action_path: Optional[str] = None
    monitoring_docs_path: Optional[str] = None
    dashboard_config_path: Optional[str] = None
    total_configured: int = 0
    total_available: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "project_name": self.project_name,
            "services": [
                {
                    "name": s.name,
                    "enabled": s.enabled,
                    "configured": s.configured,
                    "tracking_code": s.tracking_code,
                    "dashboard_url": s.dashboard_url,
                    "api_key_provided": s.api_key_provided,
                    "error_message": s.error_message,
                    "config": s.config,
                }
                for s in self.services
            ],
            "lighthouse_ci_configured": self.lighthouse_ci_configured,
            "lighthouse_config_path": self.lighthouse_config_path,
            "github_action_path": self.github_action_path,
            "monitoring_docs_path": self.monitoring_docs_path,
            "dashboard_config_path": self.dashboard_config_path,
            "total_configured": self.total_configured,
            "total_available": self.total_available,
            "timestamp": self.timestamp,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class AnalyticsMonitoringAgent(BaseAgent):
    """Agent for setting up analytics and monitoring services."""

    # API endpoints
    PLAUSIBLE_API = "https://plausible.io/api/v1"
    SENTRY_API = "https://sentry.io/api/0"
    UPTIMEROBOT_API = "https://api.uptimerobot.com/v2"

    @property
    def name(self) -> str:
        return "Analytics & Monitoring Agent"

    async def execute(
        self,
        project_path: str,
        project_name: str,
        site_url: Optional[str] = None,
        project_type: str = "web",
        **kwargs
    ) -> AgentResult:
        """
        Set up analytics and monitoring for the project.
        
        Args:
            project_path: Path to the project directory
            project_name: Name of the project
            site_url: URL of the deployed site (for monitoring)
            project_type: Type of project (web, mobile, api, desktop)
            
        Returns:
            AgentResult with monitoring configuration
        """
        import time
        start_time = time.time()
        
        report = MonitoringReport(project_name=project_name)
        self.logger.info(f"Setting up monitoring for {project_name}")
        
        # Get API keys from environment
        plausible_key = os.environ.get("PLAUSIBLE_API_KEY")
        sentry_dsn = os.environ.get("SENTRY_DSN")
        uptimerobot_key = os.environ.get("UPTIMEROBOT_API_KEY")
        lighthouse_token = os.environ.get("LIGHTHOUSE_CI_TOKEN")
        ga4_id = os.environ.get("GA4_MEASUREMENT_ID")
        
        try:
            # Setup Plausible Analytics
            plausible_service = await self._setup_plausible(
                project_name, site_url, plausible_key
            )
            report.services.append(plausible_service)
            
            # Setup Google Analytics 4 (if ID provided)
            ga4_service = await self._setup_ga4(project_path, ga4_id, project_type)
            report.services.append(ga4_service)
            
            # Setup Sentry Error Tracking
            sentry_service = await self._setup_sentry(
                project_path, project_name, sentry_dsn, project_type
            )
            report.services.append(sentry_service)
            
            # Setup UptimeRobot Monitoring
            uptimerobot_service = await self._setup_uptimerobot(
                project_name, site_url, uptimerobot_key
            )
            report.services.append(uptimerobot_service)
            
            # Setup Lighthouse CI
            lighthouse_configured = await self._setup_lighthouse_ci(
                project_path, site_url, lighthouse_token
            )
            report.lighthouse_ci_configured = lighthouse_configured
            if lighthouse_configured:
                report.lighthouse_config_path = str(Path(project_path) / "lighthouserc.json")
                report.github_action_path = str(Path(project_path) / ".github" / "workflows" / "lighthouse.yml")
            
            # Generate monitoring dashboard configuration
            dashboard_path = await self._generate_dashboard_config(
                project_path, project_name, report.services, site_url
            )
            report.dashboard_config_path = dashboard_path
            
            # Generate monitoring documentation
            docs_path = await self._generate_monitoring_docs(
                project_path, project_name, report
            )
            report.monitoring_docs_path = docs_path
            
            # Calculate totals
            report.total_available = len(report.services)
            report.total_configured = sum(1 for s in report.services if s.configured)
            
            # Save report to file
            report_path = Path(project_path) / "monitoring_report.json"
            self.write_file(str(report_path), json.dumps(report.to_dict(), indent=2))
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                success=True,
                agent_name=self.name,
                data={
                    "report": report.to_dict(),
                    "summary": {
                        "configured": report.total_configured,
                        "available": report.total_available,
                        "lighthouse_ci": report.lighthouse_ci_configured,
                    },
                },
                warnings=report.warnings,
                execution_time=execution_time,
            )
            
        except Exception as e:
            self.logger.error(f"Monitoring setup failed: {e}")
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )

    async def _setup_plausible(
        self,
        project_name: str,
        site_url: Optional[str],
        api_key: Optional[str],
    ) -> MonitoringService:
        """Setup Plausible Analytics."""
        service = MonitoringService(
            name="Plausible Analytics",
            enabled=True,
            api_key_provided=bool(api_key),
        )
        
        if not api_key:
            service.configured = False
            service.error_message = "PLAUSIBLE_API_KEY not configured"
            service.config = {
                "setup_instructions": [
                    "1. Sign up at https://plausible.io",
                    "2. Add your site domain in dashboard",
                    "3. Get API key from Settings > API Keys",
                    "4. Set PLAUSIBLE_API_KEY environment variable",
                ],
            }
            return service
        
        if not site_url:
            service.configured = False
            service.error_message = "No site URL provided for monitoring"
            return service
        
        try:
            # Extract domain from URL
            from urllib.parse import urlparse
            domain = urlparse(site_url).netloc or site_url
            
            async with httpx.AsyncClient() as client:
                # Create site in Plausible
                response = await client.put(
                    f"{self.PLAUSIBLE_API}/sites",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"domain": domain},
                    timeout=30,
                )
                
                if response.status_code in [200, 201]:
                    service.configured = True
                    service.dashboard_url = f"https://plausible.io/{domain}"
                    service.tracking_code = self._generate_plausible_snippet(domain)
                    service.config = {
                        "domain": domain,
                        "script_url": "https://plausible.io/js/script.js",
                    }
                elif response.status_code == 400 and "already exists" in response.text.lower():
                    # Site already exists, that's fine
                    service.configured = True
                    service.dashboard_url = f"https://plausible.io/{domain}"
                    service.tracking_code = self._generate_plausible_snippet(domain)
                    service.config = {"domain": domain, "existing": True}
                else:
                    service.error_message = f"API error: {response.status_code}"
                    
        except Exception as e:
            service.error_message = str(e)
            self.logger.warning(f"Plausible setup failed: {e}")
        
        return service

    def _generate_plausible_snippet(self, domain: str) -> str:
        """Generate Plausible tracking code snippet."""
        return f'''<!-- Plausible Analytics -->
<script defer data-domain="{domain}" src="https://plausible.io/js/script.js"></script>'''

    async def _setup_ga4(
        self,
        project_path: str,
        measurement_id: Optional[str],
        project_type: str,
    ) -> MonitoringService:
        """Setup Google Analytics 4."""
        service = MonitoringService(
            name="Google Analytics 4",
            enabled=True,
            api_key_provided=bool(measurement_id),
        )
        
        if not measurement_id:
            service.configured = False
            service.error_message = "GA4_MEASUREMENT_ID not configured"
            service.config = {
                "setup_instructions": [
                    "1. Go to Google Analytics: https://analytics.google.com",
                    "2. Create a GA4 property",
                    "3. Get your Measurement ID (G-XXXXXXXXXX)",
                    "4. Set GA4_MEASUREMENT_ID environment variable",
                ],
            }
            return service
        
        # Generate tracking code based on project type
        if project_type in ["web", "website"]:
            service.tracking_code = self._generate_ga4_snippet(measurement_id)
        elif project_type == "mobile":
            service.config["firebase_setup"] = True
            service.tracking_code = "// Use Firebase Analytics for mobile apps"
        
        service.configured = True
        service.dashboard_url = f"https://analytics.google.com/analytics/web/#/?measurementId={measurement_id}"
        service.config["measurement_id"] = measurement_id
        
        # Write gtag config file for web projects
        if project_type in ["web", "website"]:
            gtag_path = Path(project_path) / "public" / "gtag.js"
            gtag_path.parent.mkdir(parents=True, exist_ok=True)
            self.write_file(str(gtag_path), self._generate_gtag_file(measurement_id))
        
        return service

    def _generate_ga4_snippet(self, measurement_id: str) -> str:
        """Generate GA4 tracking code snippet."""
        return f'''<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{measurement_id}');
</script>'''

    def _generate_gtag_file(self, measurement_id: str) -> str:
        """Generate gtag.js helper file."""
        return f'''// Google Analytics 4 Helper
export const GA_MEASUREMENT_ID = '{measurement_id}';

export const pageview = (url) => {{
  window.gtag('config', GA_MEASUREMENT_ID, {{
    page_path: url,
  }});
}};

export const event = ({{ action, category, label, value }}) => {{
  window.gtag('event', action, {{
    event_category: category,
    event_label: label,
    value: value,
  }});
}};
'''

    async def _setup_sentry(
        self,
        project_path: str,
        project_name: str,
        dsn: Optional[str],
        project_type: str,
    ) -> MonitoringService:
        """Setup Sentry error tracking."""
        service = MonitoringService(
            name="Sentry",
            enabled=True,
            api_key_provided=bool(dsn),
        )
        
        if not dsn:
            service.configured = False
            service.error_message = "SENTRY_DSN not configured"
            service.config = {
                "setup_instructions": [
                    "1. Sign up at https://sentry.io",
                    "2. Create a new project",
                    "3. Copy the DSN from project settings",
                    "4. Set SENTRY_DSN environment variable",
                ],
            }
            return service
        
        service.configured = True
        service.tracking_code = dsn
        
        # Extract org/project from DSN for dashboard URL
        try:
            # DSN format: https://key@o123.ingest.sentry.io/456
            parts = dsn.split("@")
            if len(parts) > 1:
                org_project = parts[1].split("/")[-1]
                service.dashboard_url = f"https://sentry.io/issues/?project={org_project}"
        except:
            service.dashboard_url = "https://sentry.io"
        
        # Generate Sentry config based on project type
        await self._generate_sentry_config(project_path, dsn, project_type)
        service.config["dsn"] = dsn
        service.config["project_type"] = project_type
        
        return service

    async def _generate_sentry_config(
        self,
        project_path: str,
        dsn: str,
        project_type: str,
    ) -> None:
        """Generate Sentry configuration files."""
        path = Path(project_path)
        
        if project_type in ["web", "website"]:
            # Generate sentry.client.config.js for Next.js/React
            sentry_config = f'''import * as Sentry from "@sentry/nextjs";

Sentry.init({{
  dsn: "{dsn}",
  tracesSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  integrations: [
    Sentry.replayIntegration(),
  ],
}});
'''
            self.write_file(str(path / "sentry.client.config.js"), sentry_config)
            
        elif project_type == "api":
            # Generate sentry config for Python/Node API
            sentry_py_config = f'''import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="{dsn}",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    integrations=[FastApiIntegration()],
)
'''
            self.write_file(str(path / "sentry_config.py"), sentry_py_config)
            
        elif project_type == "mobile":
            # Generate React Native Sentry config
            sentry_mobile_config = f'''import * as Sentry from "@sentry/react-native";

Sentry.init({{
  dsn: "{dsn}",
  tracesSampleRate: 1.0,
}});

export {{ Sentry }};
'''
            self.write_file(str(path / "src" / "sentry.js"), sentry_mobile_config)

    async def _setup_uptimerobot(
        self,
        project_name: str,
        site_url: Optional[str],
        api_key: Optional[str],
    ) -> MonitoringService:
        """Setup UptimeRobot monitoring."""
        service = MonitoringService(
            name="UptimeRobot",
            enabled=True,
            api_key_provided=bool(api_key),
        )
        
        if not api_key:
            service.configured = False
            service.error_message = "UPTIMEROBOT_API_KEY not configured"
            service.config = {
                "setup_instructions": [
                    "1. Sign up at https://uptimerobot.com",
                    "2. Go to My Settings > API Settings",
                    "3. Create Main API Key",
                    "4. Set UPTIMEROBOT_API_KEY environment variable",
                ],
            }
            return service
        
        if not site_url:
            service.configured = False
            service.error_message = "No site URL provided for uptime monitoring"
            return service
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.UPTIMEROBOT_API}/newMonitor",
                    data={
                        "api_key": api_key,
                        "friendly_name": f"{project_name} Uptime",
                        "url": site_url,
                        "type": 1,  # HTTP(s) monitor
                        "interval": 300,  # 5 minutes
                    },
                    timeout=30,
                )
                
                data = response.json()
                if data.get("stat") == "ok":
                    monitor = data.get("monitor", {})
                    service.configured = True
                    service.config = {
                        "monitor_id": monitor.get("id"),
                        "interval": 300,
                        "type": "HTTP(s)",
                    }
                    service.dashboard_url = f"https://uptimerobot.com/dashboard#{monitor.get('id', '')}"
                else:
                    error = data.get("error", {}).get("message", "Unknown error")
                    if "already exists" in error.lower():
                        service.configured = True
                        service.config = {"existing": True}
                        service.dashboard_url = "https://uptimerobot.com/dashboard"
                    else:
                        service.error_message = error
                        
        except Exception as e:
            service.error_message = str(e)
            self.logger.warning(f"UptimeRobot setup failed: {e}")
        
        return service

    async def _setup_lighthouse_ci(
        self,
        project_path: str,
        site_url: Optional[str],
        token: Optional[str],
    ) -> bool:
        """Setup Lighthouse CI for performance monitoring."""
        path = Path(project_path)
        
        # Generate lighthouserc.json
        lighthouse_config = {
            "ci": {
                "collect": {
                    "url": [site_url or "http://localhost:3000"],
                    "numberOfRuns": 3,
                },
                "assert": {
                    "assertions": {
                        "categories:performance": ["warn", {"minScore": 0.9}],
                        "categories:accessibility": ["error", {"minScore": 0.9}],
                        "categories:best-practices": ["warn", {"minScore": 0.9}],
                        "categories:seo": ["warn", {"minScore": 0.9}],
                    },
                },
                "upload": {
                    "target": "temporary-public-storage" if not token else "lhci",
                },
            },
        }
        
        if token:
            lighthouse_config["ci"]["upload"]["serverBaseUrl"] = "https://lhci.example.com"
            lighthouse_config["ci"]["upload"]["token"] = token
        
        self.write_file(
            str(path / "lighthouserc.json"),
            json.dumps(lighthouse_config, indent=2),
        )
        
        # Generate GitHub Action for Lighthouse CI
        github_actions_path = path / ".github" / "workflows"
        github_actions_path.mkdir(parents=True, exist_ok=True)
        
        lighthouse_action = '''name: Lighthouse CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Build
        run: npm run build
        
      - name: Run Lighthouse CI
        uses: treosh/lighthouse-ci-action@v11
        with:
          configPath: './lighthouserc.json'
          uploadArtifacts: true
          temporaryPublicStorage: true
'''
        
        self.write_file(str(github_actions_path / "lighthouse.yml"), lighthouse_action)
        
        return True

    async def _generate_dashboard_config(
        self,
        project_path: str,
        project_name: str,
        services: List[MonitoringService],
        site_url: Optional[str],
    ) -> str:
        """Generate monitoring dashboard configuration."""
        path = Path(project_path)
        
        dashboard_config = {
            "project": project_name,
            "url": site_url,
            "generated_at": datetime.utcnow().isoformat(),
            "services": {},
        }
        
        for service in services:
            if service.configured:
                dashboard_config["services"][service.name] = {
                    "enabled": True,
                    "dashboard_url": service.dashboard_url,
                    "tracking_configured": bool(service.tracking_code),
                }
            else:
                dashboard_config["services"][service.name] = {
                    "enabled": False,
                    "reason": service.error_message,
                }
        
        config_path = str(path / "monitoring_dashboard.json")
        self.write_file(config_path, json.dumps(dashboard_config, indent=2))
        
        return config_path

    async def _generate_monitoring_docs(
        self,
        project_path: str,
        project_name: str,
        report: MonitoringReport,
    ) -> str:
        """Generate monitoring documentation."""
        path = Path(project_path)
        
        doc = f"""# Monitoring Documentation - {project_name}

Generated: {report.timestamp}

## Overview

This document provides details on the monitoring and analytics services configured for this project.

## Configured Services

"""
        
        for service in report.services:
            status = "✅ Configured" if service.configured else "❌ Not Configured"
            doc += f"### {service.name}\n\n"
            doc += f"**Status:** {status}\n\n"
            
            if service.configured:
                if service.dashboard_url:
                    doc += f"**Dashboard:** [{service.dashboard_url}]({service.dashboard_url})\n\n"
                if service.tracking_code and "script" in service.tracking_code.lower():
                    doc += f"**Tracking Code:**\n```html\n{service.tracking_code}\n```\n\n"
            else:
                doc += f"**Issue:** {service.error_message}\n\n"
                if service.config.get("setup_instructions"):
                    doc += "**Setup Instructions:**\n"
                    for instruction in service.config["setup_instructions"]:
                        doc += f"- {instruction}\n"
                    doc += "\n"
        
        # Lighthouse CI section
        if report.lighthouse_ci_configured:
            doc += """### Lighthouse CI

**Status:** ✅ Configured

Lighthouse CI is set up to run on every push and pull request. Results are uploaded to temporary public storage.

**Configuration Files:**
- `lighthouserc.json` - Lighthouse CI configuration
- `.github/workflows/lighthouse.yml` - GitHub Actions workflow

**Performance Thresholds:**
- Performance: 90%
- Accessibility: 90%
- Best Practices: 90%
- SEO: 90%

"""
        
        # Environment Variables section
        doc += """## Environment Variables

The following environment variables are used for monitoring:

| Variable | Description | Required |
|----------|-------------|----------|
| `PLAUSIBLE_API_KEY` | Plausible Analytics API key | Optional |
| `GA4_MEASUREMENT_ID` | Google Analytics 4 Measurement ID | Optional |
| `SENTRY_DSN` | Sentry DSN for error tracking | Optional |
| `UPTIMEROBOT_API_KEY` | UptimeRobot API key | Optional |
| `LIGHTHOUSE_CI_TOKEN` | Lighthouse CI server token | Optional |

## Quick Access Links

"""
        
        for service in report.services:
            if service.configured and service.dashboard_url:
                doc += f"- [{service.name}]({service.dashboard_url})\n"
        
        doc += "\n---\n*Generated by AI Dev Agency Analytics & Monitoring Agent*\n"
        
        docs_path = str(path / "docs" / "MONITORING.md")
        Path(path / "docs").mkdir(parents=True, exist_ok=True)
        self.write_file(docs_path, doc)
        
        return docs_path
