"""Figma & Screenshot Import for Design Context (#23)

Accept Figma URLs or screenshot uploads as design input to the Design System agent.
Extracts design tokens from Figma API and analyzes screenshots via LLM vision.
"""
import base64
import json
import logging
import os
import re
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from models.project import Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/design-import", tags=["design-import"])

# Where uploaded screenshots are stored
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/design_uploads"))
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ── Models ─────────────────────────────────────────────────────────

class FigmaImportRequest(BaseModel):
    figma_url: str = Field(..., description="Figma file URL")
    extract_colors: bool = Field(True)
    extract_typography: bool = Field(True)
    extract_spacing: bool = Field(True)
    extract_components: bool = Field(True)


class DesignTokens(BaseModel):
    source: str  # "figma" or "screenshot"
    colors: Dict[str, Any] = {}
    typography: Dict[str, Any] = {}
    spacing: Dict[str, Any] = {}
    components: List[Dict[str, Any]] = []
    layout_description: str = ""
    style_analysis: str = ""
    raw_data: Optional[Dict[str, Any]] = None


class FigmaImportResult(BaseModel):
    status: str
    figma_file_key: Optional[str]
    figma_file_name: Optional[str]
    tokens: DesignTokens
    pages_found: int = 0
    components_found: int = 0
    styles_found: int = 0


class ScreenshotAnalysisResult(BaseModel):
    status: str
    filename: str
    tokens: DesignTokens
    screenshot_path: str


# ── Figma API helpers ──────────────────────────────────────────────

def _parse_figma_url(url: str) -> Optional[str]:
    """Extract file key from Figma URL."""
    patterns = [
        r"figma\.com/(?:file|design)/([a-zA-Z0-9]+)",
        r"figma\.com/proto/([a-zA-Z0-9]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def _fetch_figma_file(file_key: str, access_token: str) -> Dict[str, Any]:
    """Fetch a Figma file via the REST API."""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"https://api.figma.com/v1/files/{file_key}",
            headers={"X-Figma-Token": access_token},
            params={"geometry": "paths"},
        )
        if response.status_code == 403:
            raise HTTPException(status_code=403, detail="Figma access denied. Check your FIGMA_ACCESS_TOKEN.")
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Figma API error: {response.status_code} — {response.text[:200]}",
            )
        return response.json()


async def _fetch_figma_styles(file_key: str, access_token: str) -> Dict[str, Any]:
    """Fetch styles from a Figma file."""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"https://api.figma.com/v1/files/{file_key}/styles",
            headers={"X-Figma-Token": access_token},
        )
        if response.status_code != 200:
            return {"meta": {"styles": []}}
        return response.json()


def _extract_figma_colors(document: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively extract color fills from Figma document."""
    colors: Dict[str, str] = {}

    def _walk(node: Dict[str, Any]):
        # Extract from fills
        fills = node.get("fills", [])
        for fill in fills:
            if fill.get("type") == "SOLID" and fill.get("visible", True):
                c = fill.get("color", {})
                r = int(c.get("r", 0) * 255)
                g = int(c.get("g", 0) * 255)
                b = int(c.get("b", 0) * 255)
                a = round(c.get("a", 1), 2)
                hex_val = f"#{r:02x}{g:02x}{b:02x}"
                name = node.get("name", "").lower().replace(" ", "_").replace("/", "_")
                if name and hex_val not in colors.values():
                    colors[name] = hex_val

        # Recurse children
        for child in node.get("children", []):
            _walk(child)

    _walk(document)
    return colors


def _extract_figma_typography(document: Dict[str, Any]) -> Dict[str, Any]:
    """Extract typography styles from Figma document."""
    typography: Dict[str, Any] = {}

    def _walk(node: Dict[str, Any]):
        style = node.get("style", {})
        if style.get("fontFamily"):
            name = node.get("name", "").lower().replace(" ", "_").replace("/", "_")
            if name:
                typography[name] = {
                    "fontFamily": style.get("fontFamily"),
                    "fontSize": style.get("fontSize"),
                    "fontWeight": style.get("fontWeight"),
                    "lineHeight": style.get("lineHeightPx"),
                    "letterSpacing": style.get("letterSpacing"),
                }

        for child in node.get("children", []):
            _walk(child)

    _walk(document)
    return typography


def _extract_figma_spacing(document: Dict[str, Any]) -> Dict[str, Any]:
    """Extract spacing values from Figma auto-layout frames."""
    spacing: Dict[str, Any] = {}

    def _walk(node: Dict[str, Any]):
        if node.get("layoutMode"):
            name = node.get("name", "frame").lower().replace(" ", "_")
            spacing[name] = {
                "padding_top": node.get("paddingTop", 0),
                "padding_right": node.get("paddingRight", 0),
                "padding_bottom": node.get("paddingBottom", 0),
                "padding_left": node.get("paddingLeft", 0),
                "item_spacing": node.get("itemSpacing", 0),
                "layout_mode": node.get("layoutMode"),
            }

        for child in node.get("children", []):
            _walk(child)

    _walk(document)
    return spacing


def _extract_figma_components(document: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract component definitions from Figma document."""
    components: List[Dict[str, Any]] = []

    def _walk(node: Dict[str, Any]):
        if node.get("type") in ("COMPONENT", "COMPONENT_SET"):
            comp = {
                "name": node.get("name"),
                "type": node.get("type"),
                "description": node.get("description", ""),
                "width": node.get("absoluteBoundingBox", {}).get("width"),
                "height": node.get("absoluteBoundingBox", {}).get("height"),
            }
            components.append(comp)

        for child in node.get("children", []):
            _walk(child)

    _walk(document)
    return components


# ── Screenshot analysis via LLM ────────────────────────────────────

async def _analyze_screenshot_with_llm(image_data: bytes, filename: str) -> DesignTokens:
    """Analyze a design screenshot using LLM vision to extract design tokens."""
    try:
        from utils.llm_client import call_openrouter

        b64_image = base64.b64encode(image_data).decode("utf-8")
        mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"

        prompt = """Analyze this UI design screenshot and extract design tokens as JSON:

{
  "colors": {"primary": "#hex", "secondary": "#hex", "background": "#hex", "text": "#hex", "accent": "#hex"},
  "typography": {"heading_font": "font name", "body_font": "font name", "heading_size": "px", "body_size": "px"},
  "spacing": {"base": "px", "section_gap": "px", "element_gap": "px"},
  "style_analysis": "Brief description of the design style, layout pattern, and visual approach",
  "layout_description": "Description of the layout structure, grid, navigation pattern"
}

Focus on extracting actionable design tokens that can be used to recreate this design.
Return ONLY valid JSON."""

        response = await call_openrouter(
            prompt=prompt,
            model="anthropic/claude-3-haiku",
            system_prompt="You are a design system analyst. Extract design tokens from UI screenshots. Return only valid JSON.",
            temperature=0.3,
            max_tokens=2000,
            images=[{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_image}"}}],
        )

        content = response.get("content", "{}")

        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            tokens_data = json.loads(json_match.group())
        else:
            tokens_data = {}

        return DesignTokens(
            source="screenshot",
            colors=tokens_data.get("colors", {}),
            typography=tokens_data.get("typography", {}),
            spacing=tokens_data.get("spacing", {}),
            style_analysis=tokens_data.get("style_analysis", ""),
            layout_description=tokens_data.get("layout_description", ""),
        )

    except ImportError:
        logger.warning("LLM client not available for screenshot analysis")
        return DesignTokens(
            source="screenshot",
            style_analysis="Screenshot uploaded but LLM analysis not available. The design system agent will use the uploaded image as reference.",
        )
    except Exception as e:
        logger.warning(f"Screenshot analysis failed: {e}")
        return DesignTokens(
            source="screenshot",
            style_analysis=f"Screenshot uploaded. Analysis error: {str(e)[:100]}",
        )


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/figma", response_model=FigmaImportResult)
async def import_from_figma(
    project_id: str,
    body: FigmaImportRequest,
    db: Session = Depends(get_db),
):
    """Import design tokens from a Figma file URL."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get Figma access token
    access_token = os.getenv("FIGMA_ACCESS_TOKEN")

    # Also check integration store
    if not access_token:
        try:
            from api.routes.integrations import get_integration_value
            access_token = get_integration_value("FIGMA_ACCESS_TOKEN")
        except Exception:
            pass

    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="FIGMA_ACCESS_TOKEN not configured. Add it in Settings > Integrations.",
        )

    # Parse file key from URL
    file_key = _parse_figma_url(body.figma_url)
    if not file_key:
        raise HTTPException(status_code=400, detail="Invalid Figma URL format")

    # Fetch Figma file
    figma_data = await _fetch_figma_file(file_key, access_token)
    document = figma_data.get("document", {})
    file_name = figma_data.get("name", "Untitled")

    # Extract tokens
    colors = _extract_figma_colors(document) if body.extract_colors else {}
    typography = _extract_figma_typography(document) if body.extract_typography else {}
    spacing = _extract_figma_spacing(document) if body.extract_spacing else {}
    components = _extract_figma_components(document) if body.extract_components else []

    # Count pages
    pages = document.get("children", [])

    # Fetch styles
    styles_data = await _fetch_figma_styles(file_key, access_token)
    styles = styles_data.get("meta", {}).get("styles", [])

    tokens = DesignTokens(
        source="figma",
        colors=colors,
        typography=typography,
        spacing=spacing,
        components=components,
        style_analysis=f"Imported from Figma file '{file_name}' with {len(pages)} pages, {len(components)} components, {len(styles)} styles",
        layout_description=f"Figma file contains {len(pages)} pages: {', '.join(p.get('name', '') for p in pages[:5])}",
    )

    # Store in project requirements for the design system agent
    reqs = dict(project.requirements or {})
    reqs["figma_tokens"] = {
        "source": "figma",
        "file_key": file_key,
        "file_name": file_name,
        "colors": colors,
        "typography": typography,
        "spacing": spacing,
        "components": [c for c in components[:20]],  # Limit to prevent JSONB bloat
    }
    reqs["figma_url"] = body.figma_url
    project.requirements = reqs
    project.figma_url = body.figma_url
    db.commit()

    return FigmaImportResult(
        status="imported",
        figma_file_key=file_key,
        figma_file_name=file_name,
        tokens=tokens,
        pages_found=len(pages),
        components_found=len(components),
        styles_found=len(styles),
    )


@router.post("/screenshot", response_model=ScreenshotAnalysisResult)
async def import_screenshot(
    project_id: str,
    file: UploadFile = File(..., description="Design screenshot (PNG, JPG, WebP)"),
    db: Session = Depends(get_db),
):
    """Upload a design screenshot for LLM-powered analysis and token extraction."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate file type
    allowed = {"image/png", "image/jpeg", "image/webp", "image/jpg"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}. Use PNG, JPG, or WebP.")

    # Read file
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_FILE_SIZE // (1024*1024)}MB.")

    # Save file
    upload_path = UPLOAD_DIR / project_id
    upload_path.mkdir(parents=True, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "png"
    saved_name = f"design_{uuid.uuid4().hex[:8]}.{ext}"
    saved_path = upload_path / saved_name
    saved_path.write_bytes(data)

    # Analyze with LLM vision
    tokens = await _analyze_screenshot_with_llm(data, file.filename or saved_name)

    # Store in project requirements
    reqs = dict(project.requirements or {})
    screenshots = reqs.get("design_screenshots", [])
    if not isinstance(screenshots, list):
        screenshots = []
    screenshots.append({
        "filename": saved_name,
        "original_name": file.filename,
        "path": str(saved_path),
        "uploaded_at": datetime.utcnow().isoformat(),
        "tokens": {
            "colors": tokens.colors,
            "typography": tokens.typography,
            "spacing": tokens.spacing,
            "style_analysis": tokens.style_analysis,
            "layout_description": tokens.layout_description,
        },
    })
    reqs["design_screenshots"] = screenshots[-5:]  # Keep last 5
    project.requirements = reqs
    db.commit()

    return ScreenshotAnalysisResult(
        status="analyzed",
        filename=saved_name,
        tokens=tokens,
        screenshot_path=str(saved_path),
    )


@router.get("/tokens", response_model=DesignTokens)
async def get_design_tokens(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get merged design tokens from all imported sources (Figma + screenshots)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    reqs = project.requirements or {}
    figma_tokens = reqs.get("figma_tokens", {})
    screenshots = reqs.get("design_screenshots", [])

    merged_colors = {}
    merged_typo = {}
    merged_spacing = {}
    components = []
    sources = []

    # Figma tokens take priority
    if figma_tokens:
        merged_colors.update(figma_tokens.get("colors", {}))
        merged_typo.update(figma_tokens.get("typography", {}))
        merged_spacing.update(figma_tokens.get("spacing", {}))
        components = figma_tokens.get("components", [])
        sources.append(f"Figma: {figma_tokens.get('file_name', 'unknown')}")

    # Layer screenshot tokens (don't overwrite Figma)
    for ss in screenshots:
        ss_tokens = ss.get("tokens", {})
        for k, v in ss_tokens.get("colors", {}).items():
            if k not in merged_colors:
                merged_colors[k] = v
        for k, v in ss_tokens.get("typography", {}).items():
            if k not in merged_typo:
                merged_typo[k] = v
        sources.append(f"Screenshot: {ss.get('original_name', ss.get('filename', 'unknown'))}")

    return DesignTokens(
        source=", ".join(sources) if sources else "none",
        colors=merged_colors,
        typography=merged_typo,
        spacing=merged_spacing,
        components=components,
        style_analysis=f"Merged tokens from {len(sources)} source(s)",
    )
