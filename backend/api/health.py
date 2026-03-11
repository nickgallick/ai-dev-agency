"""Health check API routes."""
import os
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from models import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check including database connectivity."""
    checks = {
        "database": False,
        "openrouter_key": False,
        "v0_key": False,
        "github_token": False,
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    
    # Check API keys
    checks["openrouter_key"] = bool(os.getenv("OPENROUTER_API_KEY"))
    checks["v0_key"] = bool(os.getenv("VERCEL_V0_API_KEY"))
    checks["github_token"] = bool(os.getenv("GITHUB_TOKEN"))
    
    all_ready = all(checks.values())
    
    return {
        "status": "ready" if all_ready else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("/health/circuit-breaker")
async def circuit_breaker_status():
    """Get circuit breaker status for all LLM providers.

    Returns per-provider state (closed/open/half_open), failure counts,
    and success counts.  Useful for monitoring API health.
    """
    from utils.retry import llm_circuit_breaker

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "providers": llm_circuit_breaker.get_status(),
        "config": {
            "failure_threshold": llm_circuit_breaker.failure_threshold,
            "cooldown_seconds": llm_circuit_breaker.cooldown_seconds,
            "window_seconds": llm_circuit_breaker.window_seconds,
        },
    }


@router.post("/health/circuit-breaker/reset")
async def reset_circuit_breaker(provider: str = None):
    """Reset circuit breaker state.  Optionally reset a single provider."""
    from utils.retry import llm_circuit_breaker

    llm_circuit_breaker.reset(provider)
    return {
        "success": True,
        "reset": provider or "all",
    }


@router.get("/health/model-routing")
async def model_routing_summary():
    """Get the full model routing table for all agents and cost profiles.

    Shows which model each agent uses under budget/balanced/premium profiles.
    """
    from config.model_routing import get_routing_summary, AGENT_COMPLEXITY

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "routing": get_routing_summary(),
        "complexity": AGENT_COMPLEXITY,
    }


@router.get("/health/autonomy-tiers")
async def autonomy_tiers_summary():
    """Get available autonomy tiers and their configuration.

    Returns the three tiers (supervised, guided, autonomous) with
    checkpoint agents, timeouts, and descriptions.
    """
    from config.autonomy import get_tiers_summary

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "tiers": get_tiers_summary(),
    }
