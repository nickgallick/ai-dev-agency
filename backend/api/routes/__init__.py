"""API route modules."""

from .mcp import router as mcp_router
from .revisions import router as revisions_router
from .analytics import router as analytics_router
from .integrations import router as integrations_router  # Phase 10
from .templates import router as templates_router  # Phase 11B
from .knowledge import router as knowledge_router  # Phase 11B

__all__ = [
    "mcp_router", 
    "revisions_router", 
    "analytics_router", 
    "integrations_router",
    "templates_router",
    "knowledge_router",
]
