"""API route modules."""

from .mcp import router as mcp_router
from .revisions import router as revisions_router
from .analytics import router as analytics_router
from .integrations import router as integrations_router  # Phase 10

__all__ = ["mcp_router", "revisions_router", "analytics_router", "integrations_router"]
