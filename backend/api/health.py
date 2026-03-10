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
