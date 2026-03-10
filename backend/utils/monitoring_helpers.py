"""Monitoring helper functions for analytics and monitoring API integrations."""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


# =============================================================================
# Credentials Management
# =============================================================================

@dataclass
class MonitoringCredentials:
    """Container for monitoring service credentials."""
    plausible_api_key: Optional[str] = None
    ga4_measurement_id: Optional[str] = None
    sentry_dsn: Optional[str] = None
    uptimerobot_api_key: Optional[str] = None
    lighthouse_ci_token: Optional[str] = None
    
    def validate(self, services: List[str]) -> Dict[str, bool]:
        """Validate credentials for specified services."""
        credential_map = {
            "plausible": self.plausible_api_key,
            "ga4": self.ga4_measurement_id,
            "sentry": self.sentry_dsn,
            "uptimerobot": self.uptimerobot_api_key,
            "lighthouse": self.lighthouse_ci_token,
        }
        return {svc: bool(credential_map.get(svc)) for svc in services}
    
    def get_configured_services(self) -> List[str]:
        """Get list of services with configured credentials."""
        services = []
        if self.plausible_api_key:
            services.append("plausible")
        if self.ga4_measurement_id:
            services.append("ga4")
        if self.sentry_dsn:
            services.append("sentry")
        if self.uptimerobot_api_key:
            services.append("uptimerobot")
        if self.lighthouse_ci_token:
            services.append("lighthouse")
        return services


def get_monitoring_credentials() -> MonitoringCredentials:
    """Load monitoring credentials from environment variables."""
    return MonitoringCredentials(
        plausible_api_key=os.environ.get("PLAUSIBLE_API_KEY"),
        ga4_measurement_id=os.environ.get("GA4_MEASUREMENT_ID"),
        sentry_dsn=os.environ.get("SENTRY_DSN"),
        uptimerobot_api_key=os.environ.get("UPTIMEROBOT_API_KEY"),
        lighthouse_ci_token=os.environ.get("LIGHTHOUSE_CI_TOKEN"),
    )


# =============================================================================
# Plausible Analytics API Helpers
# =============================================================================

PLAUSIBLE_API_BASE = "https://plausible.io/api/v1"


async def plausible_create_site(
    api_key: str,
    domain: str,
    timezone: str = "UTC",
) -> Optional[Dict[str, Any]]:
    """Create a new site in Plausible Analytics."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f"{PLAUSIBLE_API_BASE}/sites",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "domain": domain,
                    "timezone": timezone,
                },
                timeout=30,
            )
            if response.status_code in [200, 201]:
                return response.json()
            elif response.status_code == 400:
                # Site might already exist
                return {"existing": True, "domain": domain}
        except Exception:
            pass
    return None


async def plausible_get_site_stats(
    api_key: str,
    domain: str,
    period: str = "30d",
) -> Optional[Dict[str, Any]]:
    """Get site statistics from Plausible."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{PLAUSIBLE_API_BASE}/stats/aggregate",
                headers={"Authorization": f"Bearer {api_key}"},
                params={
                    "site_id": domain,
                    "period": period,
                    "metrics": "visitors,pageviews,bounce_rate,visit_duration",
                },
                timeout=30,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
    return None


def generate_plausible_tracking_code(domain: str) -> str:
    """Generate Plausible tracking code snippet."""
    return f'''<!-- Plausible Analytics -->
<script defer data-domain="{domain}" src="https://plausible.io/js/script.js"></script>'''


# =============================================================================
# UptimeRobot API Helpers
# =============================================================================

UPTIMEROBOT_API_BASE = "https://api.uptimerobot.com/v2"


async def uptimerobot_create_monitor(
    api_key: str,
    friendly_name: str,
    url: str,
    monitor_type: int = 1,  # 1 = HTTP(s)
    interval: int = 300,  # 5 minutes
) -> Optional[Dict[str, Any]]:
    """Create a new monitor in UptimeRobot."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{UPTIMEROBOT_API_BASE}/newMonitor",
                data={
                    "api_key": api_key,
                    "friendly_name": friendly_name,
                    "url": url,
                    "type": monitor_type,
                    "interval": interval,
                },
                timeout=30,
            )
            data = response.json()
            if data.get("stat") == "ok":
                return data.get("monitor")
        except Exception:
            pass
    return None


async def uptimerobot_get_monitors(
    api_key: str,
) -> List[Dict[str, Any]]:
    """Get all monitors from UptimeRobot."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{UPTIMEROBOT_API_BASE}/getMonitors",
                data={"api_key": api_key},
                timeout=30,
            )
            data = response.json()
            if data.get("stat") == "ok":
                return data.get("monitors", [])
        except Exception:
            pass
    return []


async def uptimerobot_get_monitor_status(
    api_key: str,
    monitor_id: int,
) -> Optional[Dict[str, Any]]:
    """Get status of a specific monitor."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{UPTIMEROBOT_API_BASE}/getMonitors",
                data={
                    "api_key": api_key,
                    "monitors": str(monitor_id),
                    "response_times": "1",
                    "logs": "1",
                },
                timeout=30,
            )
            data = response.json()
            if data.get("stat") == "ok" and data.get("monitors"):
                return data["monitors"][0]
        except Exception:
            pass
    return None


# =============================================================================
# Sentry API Helpers
# =============================================================================

SENTRY_API_BASE = "https://sentry.io/api/0"


async def sentry_get_projects(
    auth_token: str,
    organization_slug: str,
) -> List[Dict[str, Any]]:
    """Get projects from Sentry organization."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SENTRY_API_BASE}/organizations/{organization_slug}/projects/",
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=30,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
    return []


async def sentry_create_project(
    auth_token: str,
    organization_slug: str,
    team_slug: str,
    project_name: str,
    platform: str = "javascript",
) -> Optional[Dict[str, Any]]:
    """Create a new project in Sentry."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SENTRY_API_BASE}/teams/{organization_slug}/{team_slug}/projects/",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "name": project_name,
                    "platform": platform,
                },
                timeout=30,
            )
            if response.status_code in [200, 201]:
                return response.json()
        except Exception:
            pass
    return None


def parse_sentry_dsn(dsn: str) -> Dict[str, Any]:
    """Parse Sentry DSN to extract components."""
    try:
        # DSN format: https://key@org.ingest.sentry.io/project_id
        from urllib.parse import urlparse
        parsed = urlparse(dsn)
        
        key = parsed.username
        host = parsed.hostname
        project_id = parsed.path.strip("/")
        
        # Extract org from host (e.g., o123.ingest.sentry.io -> o123)
        org_id = host.split(".")[0] if host else None
        
        return {
            "key": key,
            "host": host,
            "project_id": project_id,
            "org_id": org_id,
            "valid": bool(key and project_id),
        }
    except Exception:
        return {"valid": False}


def generate_sentry_init_code(dsn: str, platform: str = "javascript") -> str:
    """Generate Sentry initialization code for different platforms."""
    if platform in ["javascript", "react", "nextjs"]:
        return f'''import * as Sentry from "@sentry/nextjs";

Sentry.init({{
  dsn: "{dsn}",
  tracesSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
}});'''
    
    elif platform == "python":
        return f'''import sentry_sdk

sentry_sdk.init(
    dsn="{dsn}",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)'''
    
    elif platform == "react-native":
        return f'''import * as Sentry from "@sentry/react-native";

Sentry.init({{
  dsn: "{dsn}",
  tracesSampleRate: 1.0,
}});'''
    
    return f'// Configure Sentry with DSN: {dsn}'


# =============================================================================
# Lighthouse CI Helpers
# =============================================================================

def generate_lighthouse_config(
    urls: List[str],
    performance_threshold: float = 0.9,
    accessibility_threshold: float = 0.9,
    best_practices_threshold: float = 0.9,
    seo_threshold: float = 0.9,
    upload_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate Lighthouse CI configuration."""
    config = {
        "ci": {
            "collect": {
                "url": urls,
                "numberOfRuns": 3,
            },
            "assert": {
                "assertions": {
                    "categories:performance": ["warn", {"minScore": performance_threshold}],
                    "categories:accessibility": ["error", {"minScore": accessibility_threshold}],
                    "categories:best-practices": ["warn", {"minScore": best_practices_threshold}],
                    "categories:seo": ["warn", {"minScore": seo_threshold}],
                },
            },
            "upload": {
                "target": "temporary-public-storage",
            },
        },
    }
    
    if upload_token:
        config["ci"]["upload"]["target"] = "lhci"
        config["ci"]["upload"]["token"] = upload_token
    
    return config


def generate_lighthouse_github_action() -> str:
    """Generate GitHub Action workflow for Lighthouse CI."""
    return '''name: Lighthouse CI

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
          cache: 'npm'
          
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
          
      - name: Upload Lighthouse Report
        uses: actions/upload-artifact@v4
        with:
          name: lighthouse-report
          path: .lighthouseci/
          retention-days: 30
'''


# =============================================================================
# Monitoring Dashboard Helpers
# =============================================================================

def generate_monitoring_dashboard_url(
    service: str,
    **kwargs,
) -> Optional[str]:
    """Generate dashboard URL for a monitoring service."""
    if service == "plausible":
        domain = kwargs.get("domain")
        return f"https://plausible.io/{domain}" if domain else None
    
    elif service == "ga4":
        measurement_id = kwargs.get("measurement_id")
        return f"https://analytics.google.com/analytics/web/#/?measurementId={measurement_id}" if measurement_id else None
    
    elif service == "sentry":
        org = kwargs.get("org")
        project = kwargs.get("project")
        if org and project:
            return f"https://sentry.io/organizations/{org}/issues/?project={project}"
        return "https://sentry.io"
    
    elif service == "uptimerobot":
        monitor_id = kwargs.get("monitor_id")
        return f"https://uptimerobot.com/dashboard#{monitor_id}" if monitor_id else "https://uptimerobot.com/dashboard"
    
    return None


def generate_monitoring_summary(
    services: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a summary of monitoring configuration."""
    summary = {
        "total_services": len(services),
        "configured": 0,
        "not_configured": 0,
        "services": {},
        "generated_at": datetime.utcnow().isoformat(),
    }
    
    for service in services:
        name = service.get("name", "Unknown")
        configured = service.get("configured", False)
        
        summary["services"][name] = {
            "configured": configured,
            "dashboard_url": service.get("dashboard_url"),
            "api_key_provided": service.get("api_key_provided", False),
        }
        
        if configured:
            summary["configured"] += 1
        else:
            summary["not_configured"] += 1
    
    return summary


# =============================================================================
# Tracking Code Generators
# =============================================================================

def generate_analytics_head_snippet(
    plausible_domain: Optional[str] = None,
    ga4_measurement_id: Optional[str] = None,
) -> str:
    """Generate combined analytics tracking code for HTML head."""
    snippets = []
    
    if plausible_domain:
        snippets.append(generate_plausible_tracking_code(plausible_domain))
    
    if ga4_measurement_id:
        snippets.append(f'''<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id={ga4_measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{ga4_measurement_id}');
</script>''')
    
    return "\n\n".join(snippets)


def generate_error_tracking_snippet(
    sentry_dsn: Optional[str] = None,
) -> str:
    """Generate error tracking initialization code."""
    if not sentry_dsn:
        return "// Error tracking not configured"
    
    return f'''<!-- Sentry Error Tracking -->
<script
  src="https://browser.sentry-cdn.com/7.98.0/bundle.min.js"
  integrity="sha384-xxx"
  crossorigin="anonymous"
></script>
<script>
  Sentry.init({{
    dsn: "{sentry_dsn}",
    tracesSampleRate: 1.0,
  }});
</script>'''
