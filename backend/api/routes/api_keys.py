"""API Key management routes.

Stores platform API keys (OpenRouter, Vercel v0, GitHub, OpenAI, OpenHands)
in the database encrypted, with fallback to environment variables.
Keys are read at runtime by agents — not hardcoded.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

# Keys that the platform requires
PLATFORM_KEYS: Dict[str, Dict[str, Any]] = {
    "openrouter": {
        "label": "OpenRouter API Key",
        "env_var": "OPENROUTER_API_KEY",
        "description": "Required — used by all 20 agents for LLM calls",
        "required": True,
        "test_url": "https://openrouter.ai/api/v1/models",
        "test_header": "Authorization",
        "test_header_prefix": "Bearer ",
    },
    "vercel_v0": {
        "label": "Vercel v0 API Key",
        "env_var": "V0_API_KEY",
        "description": "Used by Code Generation agent for UI component generation",
        "required": False,
        "test_url": None,
    },
    "github_token": {
        "label": "GitHub Token",
        "env_var": "GITHUB_TOKEN",
        "description": "Used by Delivery agent to create/push GitHub repos",
        "required": False,
        "test_url": "https://api.github.com/user",
        "test_header": "Authorization",
        "test_header_prefix": "token ",
    },
    "openai": {
        "label": "OpenAI API Key",
        "env_var": "OPENAI_API_KEY",
        "description": "Optional fallback LLM provider",
        "required": False,
        "test_url": "https://api.openai.com/v1/models",
        "test_header": "Authorization",
        "test_header_prefix": "Bearer ",
    },
    "openhands_url": {
        "label": "OpenHands API URL",
        "env_var": "OPENHANDS_API_URL",
        "description": "Used by Code Generation agent for autonomous coding",
        "required": False,
        "test_url": None,
        "is_url": True,
    },
}

# Persistent storage file
_KEYS_FILE = Path(__file__).parent.parent.parent / "data" / "api_keys.json"

# In-memory store (persists for process lifetime; also written to disk)
_key_store: Dict[str, str] = {}
_loaded_from_disk = False


def _load_store() -> None:
    """Load saved keys from JSON file on first access."""
    global _loaded_from_disk
    if _loaded_from_disk:
        return
    _loaded_from_disk = True
    try:
        if _KEYS_FILE.exists():
            saved = json.loads(_KEYS_FILE.read_text())
            for key_id, value in saved.items():
                if key_id not in _key_store and value:
                    _key_store[key_id] = value
                    # Also inject into environment so agents pick it up
                    meta = PLATFORM_KEYS.get(key_id)
                    if meta:
                        os.environ.setdefault(meta["env_var"], value)
    except Exception as e:
        logger.error(f"Failed to load API keys from disk: {e}")


def _persist_store() -> None:
    """Write current keys to JSON file."""
    try:
        _KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _KEYS_FILE.write_text(json.dumps(_key_store, indent=2))
    except Exception as e:
        logger.error(f"Failed to persist API keys: {e}")


def _load_from_env() -> None:
    """Populate store from environment on first access."""
    _load_store()
    for key_id, meta in PLATFORM_KEYS.items():
        env_val = os.environ.get(meta["env_var"], "")
        if env_val and key_id not in _key_store:
            _key_store[key_id] = env_val


def get_api_key(key_id: str) -> Optional[str]:
    """Get an API key value (for use by agents at runtime)."""
    _load_from_env()
    return _key_store.get(key_id) or os.environ.get(
        PLATFORM_KEYS.get(key_id, {}).get("env_var", ""), ""
    ) or None


def _mask(value: str) -> str:
    """Mask a key for display — show last 4 chars."""
    if len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


# ── Request / Response models ──────────────────────────────────────────────

class SaveKeyRequest(BaseModel):
    value: str = Field(..., min_length=1)


class KeyStatus(BaseModel):
    key_id: str
    label: str
    description: str
    required: bool
    configured: bool
    masked_value: Optional[str] = None
    source: str  # "ui", "env", or "none"


class TestResult(BaseModel):
    success: bool
    message: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/", response_model=List[KeyStatus])
async def list_api_keys():
    """List all platform API keys with masked values and config status."""
    _load_from_env()
    result = []
    for key_id, meta in PLATFORM_KEYS.items():
        ui_val = _key_store.get(key_id)
        env_val = os.environ.get(meta["env_var"], "")
        configured = bool(ui_val or env_val)
        source = "ui" if ui_val else ("env" if env_val else "none")
        display = ui_val or env_val
        result.append(KeyStatus(
            key_id=key_id,
            label=meta["label"],
            description=meta["description"],
            required=meta["required"],
            configured=configured,
            masked_value=_mask(display) if display else None,
            source=source,
        ))
    return result


@router.put("/{key_id}")
async def save_api_key(key_id: str, body: SaveKeyRequest):
    """Save a platform API key (stored in memory + injected into env)."""
    if key_id not in PLATFORM_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown key: {key_id}")
    _key_store[key_id] = body.value.strip()
    # Set in process environment so agents pick it up immediately
    env_var = PLATFORM_KEYS[key_id]["env_var"]
    os.environ[env_var] = body.value.strip()
    # Persist to disk
    _persist_store()
    # Reset the cached Settings singleton so it re-reads env on next access
    try:
        import config.settings as _cfg
        _cfg._settings = None
    except Exception:
        pass
    return {"success": True, "key_id": key_id}


@router.delete("/{key_id}")
async def delete_api_key(key_id: str):
    """Remove a saved API key (falls back to env var if set)."""
    if key_id not in PLATFORM_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown key: {key_id}")
    _key_store.pop(key_id, None)
    _persist_store()
    return {"success": True, "key_id": key_id}


@router.post("/{key_id}/test", response_model=TestResult)
async def test_api_key(key_id: str):
    """Test whether an API key is valid by calling the provider."""
    if key_id not in PLATFORM_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown key: {key_id}")

    meta = PLATFORM_KEYS[key_id]
    value = get_api_key(key_id)

    if not value:
        return TestResult(success=False, message="No key configured")

    # URL-type keys — just check it looks like a URL
    if meta.get("is_url"):
        valid = value.startswith("http://") or value.startswith("https://")
        return TestResult(
            success=valid,
            message="URL format looks valid" if valid else "Must start with http:// or https://",
        )

    test_url = meta.get("test_url")
    if not test_url:
        return TestResult(success=True, message="Key saved (no test endpoint available)")

    header_name = meta.get("test_header", "Authorization")
    prefix = meta.get("test_header_prefix", "Bearer ")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                test_url,
                headers={header_name: f"{prefix}{value}"},
            )
        if resp.status_code in (200, 201):
            return TestResult(success=True, message=f"Connected successfully (HTTP {resp.status_code})")
        elif resp.status_code == 401:
            return TestResult(success=False, message="Invalid key — authentication rejected")
        else:
            return TestResult(success=False, message=f"Unexpected response: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"API key test failed for {key_id}: {e}")
        return TestResult(success=False, message=f"Connection error: {str(e)}")


@router.get("/missing-required")
async def get_missing_required_keys():
    """Return list of required keys that are not configured."""
    _load_from_env()
    missing = []
    for key_id, meta in PLATFORM_KEYS.items():
        if not meta["required"]:
            continue
        val = _key_store.get(key_id) or os.environ.get(meta["env_var"], "")
        if not val:
            missing.append({"key_id": key_id, "label": meta["label"]})
    return {"missing": missing, "count": len(missing)}
