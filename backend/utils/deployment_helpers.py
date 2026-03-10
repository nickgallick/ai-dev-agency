"""Deployment helper functions for cloud API calls and build management."""

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class APICredentials:
    """Container for API credentials."""
    vercel_token: Optional[str] = None
    railway_token: Optional[str] = None
    expo_token: Optional[str] = None
    github_token: Optional[str] = None
    
    def validate(self, required: List[str]) -> List[str]:
        """Validate that required credentials are present."""
        missing = []
        credential_map = {
            "vercel": self.vercel_token,
            "railway": self.railway_token,
            "expo": self.expo_token,
            "github": self.github_token,
        }
        for cred in required:
            if cred in credential_map and not credential_map[cred]:
                missing.append(cred.upper() + "_TOKEN")
        return missing


def get_credentials() -> APICredentials:
    """Load API credentials from environment variables."""
    return APICredentials(
        vercel_token=os.environ.get("VERCEL_TOKEN"),
        railway_token=os.environ.get("RAILWAY_TOKEN"),
        expo_token=os.environ.get("EXPO_TOKEN"),
        github_token=os.environ.get("GITHUB_TOKEN"),
    )


def validate_credentials(platforms: List[str]) -> Dict[str, bool]:
    """Validate credentials for specified platforms."""
    creds = get_credentials()
    result = {}
    
    for platform in platforms:
        if platform == "vercel":
            result["vercel"] = bool(creds.vercel_token)
        elif platform == "railway":
            result["railway"] = bool(creds.railway_token)
        elif platform == "expo":
            result["expo"] = bool(creds.expo_token)
        elif platform == "github":
            result["github"] = bool(creds.github_token)
    
    return result


# =============================================================================
# Vercel API Helpers
# =============================================================================

async def vercel_get_user(token: str) -> Optional[Dict[str, Any]]:
    """Get Vercel user info."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.vercel.com/v2/user",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 200:
            return response.json().get("user")
    return None


async def vercel_list_projects(token: str) -> List[Dict[str, Any]]:
    """List Vercel projects."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.vercel.com/v9/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 200:
            return response.json().get("projects", [])
    return []


async def vercel_create_project(
    token: str, 
    name: str, 
    framework: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Create a new Vercel project."""
    async with httpx.AsyncClient() as client:
        payload = {"name": name}
        if framework:
            payload["framework"] = framework
        
        response = await client.post(
            "https://api.vercel.com/v10/projects",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if response.status_code in [200, 201]:
            return response.json()
    return None


async def vercel_get_deployment(
    token: str, 
    deployment_id: str
) -> Optional[Dict[str, Any]]:
    """Get deployment status."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.vercel.com/v13/deployments/{deployment_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 200:
            return response.json()
    return None


async def vercel_list_deployments(
    token: str, 
    project_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """List deployments for a project."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.vercel.com/v6/deployments",
            headers={"Authorization": f"Bearer {token}"},
            params={"projectId": project_id, "limit": limit},
        )
        if response.status_code == 200:
            return response.json().get("deployments", [])
    return []


# =============================================================================
# Railway API Helpers
# =============================================================================

async def railway_graphql(
    token: str, 
    query: str, 
    variables: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Execute Railway GraphQL query."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://backboard.railway.app/graphql/v2",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables or {}},
        )
        if response.status_code == 200:
            return response.json()
    return None


async def railway_get_user(token: str) -> Optional[Dict[str, Any]]:
    """Get Railway user info."""
    query = """
    query {
        me {
            id
            email
            name
        }
    }
    """
    result = await railway_graphql(token, query)
    if result:
        return result.get("data", {}).get("me")
    return None


async def railway_list_projects(token: str) -> List[Dict[str, Any]]:
    """List Railway projects."""
    query = """
    query {
        projects {
            edges {
                node {
                    id
                    name
                    createdAt
                    updatedAt
                }
            }
        }
    }
    """
    result = await railway_graphql(token, query)
    if result:
        edges = result.get("data", {}).get("projects", {}).get("edges", [])
        return [edge.get("node") for edge in edges]
    return []


async def railway_create_project(token: str, name: str) -> Optional[Dict[str, Any]]:
    """Create a new Railway project."""
    mutation = """
    mutation CreateProject($name: String!) {
        projectCreate(input: { name: $name }) {
            id
            name
        }
    }
    """
    result = await railway_graphql(token, mutation, {"name": name})
    if result:
        return result.get("data", {}).get("projectCreate")
    return None


async def railway_get_deployment(
    token: str, 
    deployment_id: str
) -> Optional[Dict[str, Any]]:
    """Get Railway deployment status."""
    query = """
    query GetDeployment($id: String!) {
        deployment(id: $id) {
            id
            status
            createdAt
            staticUrl
        }
    }
    """
    result = await railway_graphql(token, query, {"id": deployment_id})
    if result:
        return result.get("data", {}).get("deployment")
    return None


# =============================================================================
# Expo EAS API Helpers
# =============================================================================

async def expo_get_user(token: str) -> Optional[Dict[str, Any]]:
    """Get Expo user info."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.expo.dev/v2/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 200:
            return response.json().get("data")
    return None


async def expo_list_builds(
    token: str, 
    project_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """List EAS builds for a project."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.expo.dev/v2/projects/{project_id}/builds",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": limit},
        )
        if response.status_code == 200:
            return response.json().get("data", [])
    return []


async def expo_get_build(token: str, build_id: str) -> Optional[Dict[str, Any]]:
    """Get EAS build status."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.expo.dev/v2/builds/{build_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 200:
            return response.json().get("data")
    return None


# =============================================================================
# Build Status Polling
# =============================================================================

async def poll_build_status(
    platform: str,
    build_id: str,
    token: str,
    max_attempts: int = 60,
    interval: int = 10,
    callback: Optional[callable] = None,
) -> Dict[str, Any]:
    """
    Poll build status until completion.
    
    Args:
        platform: vercel, railway, or expo
        build_id: Build/deployment ID
        token: API token
        max_attempts: Maximum polling attempts
        interval: Seconds between polls
        callback: Optional callback function(status_dict)
    
    Returns:
        Final status dictionary
    """
    status = {"platform": platform, "build_id": build_id, "status": "polling"}
    
    for attempt in range(max_attempts):
        try:
            if platform == "vercel":
                data = await vercel_get_deployment(token, build_id)
                if data:
                    state = data.get("readyState")
                    if state == "READY":
                        status["status"] = "deployed"
                        status["url"] = f"https://{data.get('url')}"
                        break
                    elif state in ["ERROR", "CANCELED"]:
                        status["status"] = "failed"
                        status["error"] = data.get("errorMessage")
                        break
            
            elif platform == "railway":
                data = await railway_get_deployment(token, build_id)
                if data:
                    state = data.get("status")
                    if state == "SUCCESS":
                        status["status"] = "deployed"
                        status["url"] = data.get("staticUrl")
                        break
                    elif state in ["FAILED", "CRASHED"]:
                        status["status"] = "failed"
                        break
            
            elif platform == "expo":
                data = await expo_get_build(token, build_id)
                if data:
                    state = data.get("status")
                    if state == "finished":
                        status["status"] = "deployed"
                        status["url"] = data.get("artifacts", {}).get("buildUrl")
                        break
                    elif state in ["errored", "canceled"]:
                        status["status"] = "failed"
                        status["error"] = data.get("error", {}).get("message")
                        break
            
            status["attempt"] = attempt + 1
            if callback:
                callback(status)
            
            await asyncio.sleep(interval)
            
        except Exception as e:
            status["error"] = str(e)
    
    if status["status"] == "polling":
        status["status"] = "timeout"
    
    return status


# =============================================================================
# GitHub Actions Workflow Templates
# =============================================================================

WORKFLOW_TEMPLATES = {
    "ci": """name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
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
      - name: Run tests
        run: npm test --if-present
      - name: Run build
        run: npm run build --if-present
""",

    "vercel": """name: Deploy to Vercel

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
""",

    "railway": """name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      - name: Deploy
        run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
""",

    "expo-eas": """name: EAS Build

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - name: Setup Expo
        uses: expo/expo-github-action@v8
        with:
          eas-version: latest
          token: ${{ secrets.EXPO_TOKEN }}
      - name: Install dependencies
        run: npm ci
      - name: Build
        run: eas build --platform all --profile production --non-interactive
      - name: Submit (on tag)
        if: startsWith(github.ref, 'refs/tags/v')
        run: eas submit --platform all --latest --non-interactive
""",

    "electron": """name: Electron Build

on:
  push:
    tags: ['v*']

jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
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
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.os }}-build
          path: dist/*
""",
}


def get_workflow_template(name: str) -> Optional[str]:
    """Get a GitHub Actions workflow template by name."""
    return WORKFLOW_TEMPLATES.get(name)


def generate_workflow_file(
    template_name: str,
    output_path: str,
    variables: Optional[Dict[str, str]] = None,
) -> bool:
    """
    Generate a GitHub Actions workflow file from template.
    
    Args:
        template_name: Name of the template
        output_path: Path to write the workflow file
        variables: Optional variables to substitute in template
    
    Returns:
        True if successful
    """
    template = get_workflow_template(template_name)
    if not template:
        return False
    
    content = template
    if variables:
        for key, value in variables.items():
            content = content.replace(f"${{{key}}}", value)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)
    
    return True


# =============================================================================
# Deployment Configuration Helpers
# =============================================================================

def detect_project_type(project_path: str) -> str:
    """Detect project type from files."""
    from pathlib import Path
    path = Path(project_path)
    
    # Check for mobile (Expo/React Native)
    if (path / "app.json").exists() or (path / "app.config.js").exists():
        return "mobile"
    
    # Check for desktop (Electron)
    pkg_path = path / "package.json"
    if pkg_path.exists():
        try:
            with open(pkg_path) as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "electron" in deps:
                    return "desktop"
        except Exception:
            pass
    
    # Check for API (Python/FastAPI/Express)
    if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        return "api"
    
    # Default to web
    return "web"


def get_recommended_platforms(project_type: str) -> List[str]:
    """Get recommended deployment platforms for project type."""
    recommendations = {
        "web": ["vercel"],
        "api": ["railway"],
        "mobile": ["expo"],
        "desktop": ["github-releases"],
        "fullstack": ["vercel", "railway"],
    }
    return recommendations.get(project_type, ["vercel"])


def generate_deployment_checklist(project_type: str) -> List[Dict[str, Any]]:
    """Generate a deployment checklist for project type."""
    checklist = []
    
    # Common items
    checklist.append({
        "task": "Verify all tests pass",
        "required": True,
        "completed": False,
    })
    checklist.append({
        "task": "Review and update environment variables",
        "required": True,
        "completed": False,
    })
    
    if project_type == "web":
        checklist.extend([
            {"task": "Create Vercel account", "required": True, "completed": False},
            {"task": "Connect GitHub repository", "required": False, "completed": False},
            {"task": "Configure custom domain", "required": False, "completed": False},
            {"task": "Set up SSL certificate", "required": False, "completed": False},
        ])
    
    elif project_type == "mobile":
        checklist.extend([
            {"task": "Create Expo account", "required": True, "completed": False},
            {"task": "Configure app.json/app.config.js", "required": True, "completed": False},
            {"task": "Enroll in Apple Developer Program", "required": False, "completed": False},
            {"task": "Create Google Play Console account", "required": False, "completed": False},
            {"task": "Generate app icons and splash screens", "required": True, "completed": False},
            {"task": "Configure EAS build profiles", "required": True, "completed": False},
        ])
    
    elif project_type == "desktop":
        checklist.extend([
            {"task": "Configure electron-builder", "required": True, "completed": False},
            {"task": "Generate app icons for all platforms", "required": True, "completed": False},
            {"task": "Set up code signing (macOS/Windows)", "required": False, "completed": False},
            {"task": "Configure auto-update mechanism", "required": False, "completed": False},
        ])
    
    elif project_type == "api":
        checklist.extend([
            {"task": "Create Railway account", "required": True, "completed": False},
            {"task": "Configure database connection", "required": True, "completed": False},
            {"task": "Set up health check endpoint", "required": True, "completed": False},
            {"task": "Configure logging and monitoring", "required": False, "completed": False},
        ])
    
    return checklist
