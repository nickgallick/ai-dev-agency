"""API route modules."""

from .mcp import router as mcp_router
from .revisions import router as revisions_router
from .analytics import router as analytics_router
from .integrations import router as integrations_router  # Phase 10
from .templates import router as templates_router  # Phase 11B
from .knowledge import router as knowledge_router  # Phase 11B
from .checkpoints import router as checkpoints_router  # Phase 11C
from .queue import router as queue_router  # Phase 11C
from .export import router as export_router  # Phase 11C
from .api_keys import router as api_keys_router  # Platform API keys

__all__ = [
    "mcp_router",
    "revisions_router",
    "analytics_router",
    "integrations_router",
    "templates_router",
    "knowledge_router",
    "checkpoints_router",
    "queue_router",
    "export_router",
    "api_keys_router",
]
