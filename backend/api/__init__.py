"""API routes for the AI Dev Agency."""
from .projects import router as projects_router
from .agents import router as agents_router
from .costs import router as costs_router
from .health import router as health_router

__all__ = ["projects_router", "agents_router", "costs_router", "health_router"]
