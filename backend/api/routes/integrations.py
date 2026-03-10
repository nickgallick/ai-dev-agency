"""Phase 10: Integrations API routes.

Provides endpoints for:
- Integration status checking
- Integration configuration management
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...config.settings import get_settings

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationStatus(BaseModel):
    """Status of an integration."""
    name: str
    configured: bool
    description: str
    category: str  # "agency_system" or "generated_project"
    required_vars: list[str]


class AllIntegrationsResponse(BaseModel):
    """Response with all integration statuses."""
    integrations: Dict[str, IntegrationStatus]
    agency_system_count: int
    generated_project_count: int
    total_configured: int


@router.get("/status", response_model=AllIntegrationsResponse)
async def get_integration_status():
    """Get status of all integrations."""
    settings = get_settings()
    
    integrations = {
        "figma": IntegrationStatus(
            name="Figma MCP",
            configured=settings.figma_configured,
            description="Extract design context from Figma files",
            category="agency_system",
            required_vars=["FIGMA_ACCESS_TOKEN"],
        ),
        "browserstack": IntegrationStatus(
            name="BrowserStack",
            configured=settings.browserstack_configured,
            description="Cross-browser testing on real devices",
            category="agency_system",
            required_vars=["BROWSERSTACK_USERNAME", "BROWSERSTACK_ACCESS_KEY"],
        ),
        "resend": IntegrationStatus(
            name="Resend",
            configured=settings.resend_configured,
            description="Email integration for generated SaaS projects",
            category="generated_project",
            required_vars=["RESEND_API_KEY"],
        ),
        "r2": IntegrationStatus(
            name="Cloudflare R2",
            configured=settings.r2_configured,
            description="File storage for generated projects",
            category="generated_project",
            required_vars=["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME", "R2_ACCOUNT_ID"],
        ),
        "inngest": IntegrationStatus(
            name="Inngest",
            configured=settings.inngest_configured,
            description="Background jobs for generated SaaS projects",
            category="generated_project",
            required_vars=["INNGEST_EVENT_KEY"],
        ),
    }
    
    agency_count = sum(1 for i in integrations.values() if i.category == "agency_system" and i.configured)
    project_count = sum(1 for i in integrations.values() if i.category == "generated_project" and i.configured)
    total_configured = sum(1 for i in integrations.values() if i.configured)
    
    return AllIntegrationsResponse(
        integrations=integrations,
        agency_system_count=agency_count,
        generated_project_count=project_count,
        total_configured=total_configured,
    )


@router.get("/status/{integration_name}")
async def get_single_integration_status(integration_name: str):
    """Get status of a specific integration."""
    all_status = await get_integration_status()
    
    if integration_name not in all_status.integrations:
        raise HTTPException(
            status_code=404,
            detail=f"Integration '{integration_name}' not found"
        )
    
    return all_status.integrations[integration_name]


class TestFigmaRequest(BaseModel):
    """Request to test Figma connection."""
    figma_url: str


@router.post("/test/figma")
async def test_figma_connection(request: TestFigmaRequest):
    """Test Figma connection with a URL."""
    from ...integrations.figma_mcp import FigmaMCPClient
    
    client = FigmaMCPClient()
    
    if not client.is_configured:
        return {
            "success": False,
            "error": "Figma not configured. Set FIGMA_ACCESS_TOKEN.",
        }
    
    try:
        context = await client.get_design_context(request.figma_url)
        await client.close()
        
        return {
            "success": True,
            "file_name": context.file_name,
            "frames_count": len(context.frames),
            "components_count": len(context.components),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/test/browserstack")
async def test_browserstack_connection():
    """Test BrowserStack connection."""
    from ...integrations.browserstack import BrowserStackClient
    
    client = BrowserStackClient()
    
    if not client.is_configured:
        return {
            "success": False,
            "error": "BrowserStack not configured. Set BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY.",
        }
    
    try:
        plan = await client.get_plan_usage()
        await client.close()
        
        return {
            "success": True,
            "plan": plan,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
