"""Phase 10: Integration modules for AI Dev Agency.

Agency System Integrations (used by agents during project generation):
- Figma MCP: Extract design context from Figma files
- BrowserStack: Cross-browser testing on real devices

Generated Project Defaults (injected into generated projects):
- Resend: Email functionality for SaaS projects
- Cloudflare R2: File storage integration
- Inngest: Background job processing
"""

from .figma_mcp import FigmaMCPClient, FigmaDesignContext
from .browserstack import BrowserStackClient, BrowserStackTestResult
from .resend import ResendHelper, generate_resend_code
from .cloudflare_r2 import R2Helper, generate_r2_code
from .inngest import InngestHelper, generate_inngest_code

__all__ = [
    # Figma MCP
    "FigmaMCPClient",
    "FigmaDesignContext",
    # BrowserStack
    "BrowserStackClient",
    "BrowserStackTestResult",
    # Resend
    "ResendHelper",
    "generate_resend_code",
    # Cloudflare R2
    "R2Helper",
    "generate_r2_code",
    # Inngest
    "InngestHelper",
    "generate_inngest_code",
]
