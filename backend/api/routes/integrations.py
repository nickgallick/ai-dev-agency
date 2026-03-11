"""Integration API routes.

Stores integration API keys (Stripe, Resend, Supabase, etc.)
in memory with fallback to environment variables.
Keys are read at runtime by agents — not hardcoded.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])

# All supported integrations with metadata
INTEGRATIONS: Dict[str, Dict[str, Any]] = {
    "stripe": {
        "name": "Stripe",
        "description": "Payment processing for generated SaaS projects",
        "category": "generated_project",
        "fields": [
            {"key": "STRIPE_SECRET_KEY", "label": "Secret Key", "placeholder": "sk_live_...", "secret": True},
            {"key": "STRIPE_PUBLISHABLE_KEY", "label": "Publishable Key", "placeholder": "pk_live_...", "secret": False},
        ],
        "test_url": "https://api.stripe.com/v1/charges?limit=1",
        "test_header": "Authorization",
        "test_header_prefix": "Bearer ",
        "test_field": "STRIPE_SECRET_KEY",
        "docs_url": "https://stripe.com/docs/keys",
    },
    "resend": {
        "name": "Resend",
        "description": "Transactional email for generated SaaS projects",
        "category": "generated_project",
        "fields": [
            {"key": "RESEND_API_KEY", "label": "API Key", "placeholder": "re_...", "secret": True},
        ],
        "test_url": "https://api.resend.com/domains",
        "test_header": "Authorization",
        "test_header_prefix": "Bearer ",
        "test_field": "RESEND_API_KEY",
        "docs_url": "https://resend.com/docs",
    },
    "r2": {
        "name": "Cloudflare R2",
        "description": "Object storage for generated projects",
        "category": "generated_project",
        "fields": [
            {"key": "R2_ACCESS_KEY_ID", "label": "Access Key ID", "placeholder": "...", "secret": False},
            {"key": "R2_SECRET_ACCESS_KEY", "label": "Secret Access Key", "placeholder": "...", "secret": True},
            {"key": "R2_BUCKET_NAME", "label": "Bucket Name", "placeholder": "my-bucket", "secret": False},
            {"key": "R2_ACCOUNT_ID", "label": "Account ID", "placeholder": "...", "secret": False},
        ],
        "test_url": None,
        "test_field": "R2_ACCESS_KEY_ID",
        "docs_url": "https://developers.cloudflare.com/r2/",
    },
    "supabase": {
        "name": "Supabase Auth",
        "description": "Authentication for generated SaaS projects",
        "category": "generated_project",
        "fields": [
            {"key": "SUPABASE_URL", "label": "Project URL", "placeholder": "https://xxx.supabase.co", "secret": False},
            {"key": "SUPABASE_ANON_KEY", "label": "Anon Key", "placeholder": "eyJ...", "secret": True},
            {"key": "SUPABASE_SERVICE_KEY", "label": "Service Role Key", "placeholder": "eyJ...", "secret": True},
        ],
        "test_url": None,  # Will test by hitting SUPABASE_URL/rest/v1/
        "test_field": "SUPABASE_URL",
        "docs_url": "https://supabase.com/docs/guides/api",
    },
    "openai_dalle": {
        "name": "OpenAI / DALL-E",
        "description": "AI image generation for project assets",
        "category": "agency_system",
        "fields": [
            {"key": "OPENAI_API_KEY", "label": "API Key", "placeholder": "sk-...", "secret": True},
        ],
        "test_url": "https://api.openai.com/v1/models",
        "test_header": "Authorization",
        "test_header_prefix": "Bearer ",
        "test_field": "OPENAI_API_KEY",
        "docs_url": "https://platform.openai.com/docs",
    },
    "openhands": {
        "name": "OpenHands",
        "description": "Autonomous coding agent for complex code generation",
        "category": "agency_system",
        "fields": [
            {"key": "OPENHANDS_API_URL", "label": "API URL", "placeholder": "http://localhost:3000", "secret": False},
        ],
        "test_url": None,
        "test_field": "OPENHANDS_API_URL",
        "is_url_field": True,
        "docs_url": "https://github.com/All-Hands-AI/OpenHands",
    },
    "slack": {
        "name": "Slack",
        "description": "Build notifications and project delivery alerts",
        "category": "agency_system",
        "fields": [
            {"key": "SLACK_WEBHOOK_URL", "label": "Webhook URL", "placeholder": "https://hooks.slack.com/services/...", "secret": True},
        ],
        "test_url": None,
        "test_field": "SLACK_WEBHOOK_URL",
        "is_url_field": True,
        "docs_url": "https://api.slack.com/messaging/webhooks",
    },
    "notion": {
        "name": "Notion",
        "description": "Project documentation and spec delivery",
        "category": "agency_system",
        "fields": [
            {"key": "NOTION_TOKEN", "label": "Integration Token", "placeholder": "secret_...", "secret": True},
        ],
        "test_url": "https://api.notion.com/v1/users/me",
        "test_header": "Authorization",
        "test_header_prefix": "Bearer ",
        "test_field": "NOTION_TOKEN",
        "extra_headers": {"Notion-Version": "2022-06-28"},
        "docs_url": "https://developers.notion.com",
    },
    "sentry": {
        "name": "Sentry",
        "description": "Error monitoring auto-configured in generated projects",
        "category": "generated_project",
        "fields": [
            {"key": "SENTRY_DSN", "label": "DSN", "placeholder": "https://...@sentry.io/...", "secret": False},
            {"key": "SENTRY_AUTH_TOKEN", "label": "Auth Token (for uploads)", "placeholder": "...", "secret": True},
        ],
        "test_url": None,
        "test_field": "SENTRY_DSN",
        "is_url_field": True,
        "docs_url": "https://docs.sentry.io",
    },
    "uptimerobot": {
        "name": "UptimeRobot",
        "description": "Uptime monitoring for deployed projects",
        "category": "generated_project",
        "fields": [
            {"key": "UPTIMEROBOT_API_KEY", "label": "API Key", "placeholder": "ur...", "secret": True},
        ],
        "test_url": "https://api.uptimerobot.com/v2/getAccountDetails",
        "test_method": "POST",
        "test_field": "UPTIMEROBOT_API_KEY",
        "docs_url": "https://uptimerobot.com/api/",
    },
    "plausible": {
        "name": "Plausible Analytics",
        "description": "Privacy-friendly analytics auto-added to generated projects",
        "category": "generated_project",
        "fields": [
            {"key": "PLAUSIBLE_DOMAIN", "label": "Site Domain", "placeholder": "mysite.com", "secret": False},
            {"key": "PLAUSIBLE_API_KEY", "label": "API Key", "placeholder": "...", "secret": True},
        ],
        "test_url": None,
        "test_field": "PLAUSIBLE_API_KEY",
        "docs_url": "https://plausible.io/docs",
    },
}

# In-memory key store (same pattern as api_keys.py)
_int_store: Dict[str, str] = {}


def _load_from_env() -> None:
    """Load integration keys from environment on first access."""
    for int_id, meta in INTEGRATIONS.items():
        for field in meta["fields"]:
            env_key = field["key"]
            env_val = os.environ.get(env_key, "")
            if env_val and env_key not in _int_store:
                _int_store[env_key] = env_val


def get_integration_value(env_key: str) -> Optional[str]:
    """Get an integration key value for use by agents at runtime."""
    _load_from_env()
    return _int_store.get(env_key) or os.environ.get(env_key) or None


def _mask(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


def _is_configured(int_id: str) -> bool:
    _load_from_env()
    meta = INTEGRATIONS[int_id]
    primary_field = meta["fields"][0]["key"]
    return bool(_int_store.get(primary_field) or os.environ.get(primary_field, ""))


# ── Models ────────────────────────────────────────────────────────────────────

class FieldStatus(BaseModel):
    key: str
    label: str
    placeholder: str
    secret: bool
    configured: bool
    masked_value: Optional[str] = None
    source: str  # "ui", "env", "none"


class IntegrationDetail(BaseModel):
    id: str
    name: str
    description: str
    category: str
    configured: bool
    docs_url: str
    fields: List[FieldStatus]


class SaveFieldRequest(BaseModel):
    env_key: str = Field(..., description="Environment variable name (e.g. STRIPE_SECRET_KEY)")
    value: str = Field(..., min_length=1)


class TestResult(BaseModel):
    success: bool
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[IntegrationDetail])
async def list_integrations():
    """List all integrations with field statuses."""
    _load_from_env()
    result = []
    for int_id, meta in INTEGRATIONS.items():
        field_statuses = []
        for f in meta["fields"]:
            env_key = f["key"]
            ui_val = _int_store.get(env_key)
            env_val = os.environ.get(env_key, "")
            configured = bool(ui_val or env_val)
            source = "ui" if ui_val else ("env" if env_val else "none")
            display = ui_val or env_val
            field_statuses.append(FieldStatus(
                key=env_key,
                label=f["label"],
                placeholder=f["placeholder"],
                secret=f["secret"],
                configured=configured,
                masked_value=_mask(display) if display else None,
                source=source,
            ))
        result.append(IntegrationDetail(
            id=int_id,
            name=meta["name"],
            description=meta["description"],
            category=meta["category"],
            configured=_is_configured(int_id),
            docs_url=meta.get("docs_url", ""),
            fields=field_statuses,
        ))
    return result


@router.put("/{int_id}/keys")
async def save_integration_key(int_id: str, body: SaveFieldRequest):
    """Save a single field value for an integration."""
    if int_id not in INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {int_id}")

    # Validate the env_key belongs to this integration
    valid_keys = {f["key"] for f in INTEGRATIONS[int_id]["fields"]}
    if body.env_key not in valid_keys:
        raise HTTPException(status_code=400, detail=f"Unknown field {body.env_key} for {int_id}")

    value = body.value.strip()
    _int_store[body.env_key] = value
    os.environ[body.env_key] = value

    # Reset settings singleton so agents pick up new values
    try:
        import config.settings as _cfg
        _cfg._settings = None
    except Exception:
        pass

    return {"success": True, "int_id": int_id, "env_key": body.env_key}


@router.delete("/{int_id}/keys/{env_key}")
async def delete_integration_key(int_id: str, env_key: str):
    """Remove a saved integration key."""
    if int_id not in INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {int_id}")
    _int_store.pop(env_key, None)
    return {"success": True, "int_id": int_id, "env_key": env_key}


@router.post("/{int_id}/test", response_model=TestResult)
async def test_integration(int_id: str):
    """Test whether an integration is reachable with the saved key."""
    if int_id not in INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {int_id}")

    meta = INTEGRATIONS[int_id]
    test_field = meta.get("test_field", "")
    value = get_integration_value(test_field) if test_field else None

    if not value:
        return TestResult(success=False, message="No key configured")

    # URL / webhook type — just validate format
    if meta.get("is_url_field"):
        valid = value.startswith("http://") or value.startswith("https://")
        return TestResult(
            success=valid,
            message="URL looks valid" if valid else "Must start with http:// or https://",
        )

    # Supabase — test by hitting the REST endpoint
    if int_id == "supabase":
        supabase_url = get_integration_value("SUPABASE_URL")
        if not supabase_url:
            return TestResult(success=False, message="SUPABASE_URL not configured")
        anon_key = get_integration_value("SUPABASE_ANON_KEY")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{supabase_url.rstrip('/')}/rest/v1/",
                    headers={"apikey": anon_key or "", "Authorization": f"Bearer {anon_key or ''}"},
                )
            if resp.status_code in (200, 201, 400):
                return TestResult(success=True, message=f"Supabase reachable (HTTP {resp.status_code})")
            return TestResult(success=False, message=f"Unexpected response: HTTP {resp.status_code}")
        except Exception as e:
            return TestResult(success=False, message=f"Connection error: {e}")

    # UptimeRobot — POST request
    if int_id == "uptimerobot":
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    "https://api.uptimerobot.com/v2/getAccountDetails",
                    data={"api_key": value, "format": "json"},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
            data = resp.json()
            if data.get("stat") == "ok":
                return TestResult(success=True, message="UptimeRobot account verified")
            return TestResult(success=False, message=data.get("error", {}).get("message", "Invalid key"))
        except Exception as e:
            return TestResult(success=False, message=f"Connection error: {e}")

    test_url = meta.get("test_url")
    if not test_url:
        return TestResult(success=True, message="Key saved (no test endpoint available)")

    header_name = meta.get("test_header", "Authorization")
    prefix = meta.get("test_header_prefix", "Bearer ")
    extra_headers = meta.get("extra_headers", {})

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                test_url,
                headers={header_name: f"{prefix}{value}", **extra_headers},
            )
        if resp.status_code in (200, 201):
            return TestResult(success=True, message=f"Connected successfully (HTTP {resp.status_code})")
        elif resp.status_code == 401:
            return TestResult(success=False, message="Invalid key — authentication rejected")
        else:
            return TestResult(success=False, message=f"Unexpected response: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"Integration test failed for {int_id}: {e}")
        return TestResult(success=False, message=f"Connection error: {str(e)}")


# ── Legacy endpoints for backwards compat ────────────────────────────────────

@router.get("/status")
async def get_integration_status():
    """Legacy status endpoint — returns configured state for all integrations."""
    _load_from_env()
    integrations_out = {}
    for int_id, meta in INTEGRATIONS.items():
        primary_key = meta["fields"][0]["key"]
        configured = bool(_int_store.get(primary_key) or os.environ.get(primary_key, ""))
        integrations_out[int_id] = {
            "name": meta["name"],
            "configured": configured,
            "description": meta["description"],
            "category": meta["category"],
            "required_vars": [f["key"] for f in meta["fields"]],
        }
    return {
        "integrations": integrations_out,
        "agency_system_count": sum(1 for k, v in integrations_out.items() if v["category"] == "agency_system" and v["configured"]),
        "generated_project_count": sum(1 for k, v in integrations_out.items() if v["category"] == "generated_project" and v["configured"]),
        "total_configured": sum(1 for v in integrations_out.values() if v["configured"]),
    }
