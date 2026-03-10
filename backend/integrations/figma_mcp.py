"""Figma MCP Server Integration.

Extracts design context from Figma files using the Figma MCP server.
Used by: Research Agent, Design System Agent, Architect Agent

Features:
- get_design_context: Extract layout, structure, and hierarchy
- get_screenshot: Capture visual screenshots of frames/components
- get_variable_defs: Extract design tokens (colors, typography, spacing)
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import aiohttp

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class FigmaDesignContext:
    """Extracted design context from Figma."""
    file_key: str
    file_name: str = ""
    
    # Design tokens
    colors: Dict[str, str] = field(default_factory=dict)  # name: hex
    typography: List[Dict[str, Any]] = field(default_factory=list)
    spacing: List[int] = field(default_factory=list)
    
    # Components and structure
    components: List[Dict[str, Any]] = field(default_factory=list)
    frames: List[Dict[str, Any]] = field(default_factory=list)
    
    # Screenshots (base64 encoded)
    screenshots: Dict[str, str] = field(default_factory=dict)  # node_id: base64
    
    # Raw variable definitions
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    last_modified: Optional[str] = None
    thumbnail_url: Optional[str] = None


class FigmaMCPClient:
    """Client for Figma MCP Server integration."""
    
    FIGMA_API_BASE = "https://api.figma.com/v1"
    
    def __init__(self, access_token: Optional[str] = None):
        """Initialize Figma MCP client.
        
        Args:
            access_token: Figma personal access token. If not provided,
                         falls back to FIGMA_ACCESS_TOKEN env var.
        """
        settings = get_settings()
        self.access_token = access_token or settings.figma_access_token
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if Figma integration is configured."""
        return bool(self.access_token)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "X-Figma-Token": self.access_token,
                    "Content-Type": "application/json",
                }
            )
        return self._session
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def extract_file_key(self, figma_url: str) -> Optional[str]:
        """Extract file key from Figma URL.
        
        Supports:
        - https://www.figma.com/file/KEY/...
        - https://www.figma.com/design/KEY/...
        - https://figma.com/file/KEY/...
        """
        patterns = [
            r'figma\.com/(?:file|design)/([a-zA-Z0-9]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, figma_url)
            if match:
                return match.group(1)
        return None
    
    async def get_design_context(self, figma_url: str) -> FigmaDesignContext:
        """Extract comprehensive design context from a Figma file.
        
        Args:
            figma_url: Figma file URL
            
        Returns:
            FigmaDesignContext with extracted design information
        """
        if not self.is_configured:
            logger.warning("Figma not configured, returning empty context")
            return FigmaDesignContext(file_key="")
        
        file_key = self.extract_file_key(figma_url)
        if not file_key:
            logger.error(f"Could not extract file key from URL: {figma_url}")
            return FigmaDesignContext(file_key="")
        
        context = FigmaDesignContext(file_key=file_key)
        session = await self._get_session()
        
        try:
            # Get file data
            async with session.get(f"{self.FIGMA_API_BASE}/files/{file_key}") as resp:
                if resp.status != 200:
                    logger.error(f"Figma API error: {resp.status}")
                    return context
                data = await resp.json()
            
            context.file_name = data.get("name", "")
            context.last_modified = data.get("lastModified")
            context.thumbnail_url = data.get("thumbnailUrl")
            
            # Extract document structure
            document = data.get("document", {})
            context.frames = self._extract_frames(document)
            context.components = self._extract_components(data.get("components", {}))
            
            # Extract styles/colors
            styles = data.get("styles", {})
            context.colors = self._extract_colors(styles, data)
            context.typography = self._extract_typography(styles, data)
            
            # Get variables if available
            context.variables = await self._get_variables(session, file_key)
            
            logger.info(f"Extracted design context from {context.file_name}")
            
        except Exception as e:
            logger.error(f"Error extracting design context: {e}")
        
        return context
    
    def _extract_frames(self, document: Dict) -> List[Dict[str, Any]]:
        """Extract frame information from document."""
        frames = []
        
        def traverse(node: Dict, depth: int = 0):
            node_type = node.get("type", "")
            if node_type == "FRAME":
                frames.append({
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "width": node.get("absoluteBoundingBox", {}).get("width"),
                    "height": node.get("absoluteBoundingBox", {}).get("height"),
                    "depth": depth,
                })
            for child in node.get("children", []):
                traverse(child, depth + 1)
        
        traverse(document)
        return frames
    
    def _extract_components(self, components: Dict) -> List[Dict[str, Any]]:
        """Extract component definitions."""
        return [
            {
                "key": key,
                "name": comp.get("name"),
                "description": comp.get("description"),
            }
            for key, comp in components.items()
        ]
    
    def _extract_colors(self, styles: Dict, data: Dict) -> Dict[str, str]:
        """Extract color styles."""
        colors = {}
        for style_id, style in styles.items():
            if style.get("styleType") == "FILL":
                name = style.get("name", f"color_{style_id}")
                # Would need to traverse nodes to find the actual color values
                # This is simplified - full implementation would parse fills
                colors[name] = "#000000"  # Placeholder
        return colors
    
    def _extract_typography(self, styles: Dict, data: Dict) -> List[Dict[str, Any]]:
        """Extract typography styles."""
        typography = []
        for style_id, style in styles.items():
            if style.get("styleType") == "TEXT":
                typography.append({
                    "name": style.get("name"),
                    "description": style.get("description", ""),
                })
        return typography
    
    async def _get_variables(self, session: aiohttp.ClientSession, file_key: str) -> Dict:
        """Get variable definitions from Figma file."""
        try:
            async with session.get(
                f"{self.FIGMA_API_BASE}/files/{file_key}/variables/local"
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.debug(f"Could not fetch variables: {e}")
        return {}
    
    async def get_screenshot(self, figma_url: str, node_id: Optional[str] = None) -> Optional[str]:
        """Get screenshot of a Figma file or specific node.
        
        Args:
            figma_url: Figma file URL
            node_id: Optional specific node ID to capture
            
        Returns:
            Base64 encoded PNG image or None
        """
        if not self.is_configured:
            return None
        
        file_key = self.extract_file_key(figma_url)
        if not file_key:
            return None
        
        session = await self._get_session()
        
        try:
            params = {"format": "png", "scale": 2}
            if node_id:
                params["ids"] = node_id
            
            async with session.get(
                f"{self.FIGMA_API_BASE}/images/{file_key}",
                params=params
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    images = data.get("images", {})
                    # Return first image URL
                    if images:
                        return list(images.values())[0]
        except Exception as e:
            logger.error(f"Error getting screenshot: {e}")
        
        return None
    
    async def get_variable_defs(self, figma_url: str) -> Dict[str, Any]:
        """Get raw variable definitions from Figma.
        
        Returns design tokens in structured format:
        - Color variables
        - Number variables (spacing, sizing)
        - String variables
        """
        if not self.is_configured:
            return {}
        
        file_key = self.extract_file_key(figma_url)
        if not file_key:
            return {}
        
        session = await self._get_session()
        return await self._get_variables(session, file_key)


# Convenience function for one-off usage
async def extract_figma_context(figma_url: str) -> FigmaDesignContext:
    """Extract design context from Figma URL.
    
    Usage:
        context = await extract_figma_context("https://figma.com/file/abc123/...")
    """
    client = FigmaMCPClient()
    try:
        return await client.get_design_context(figma_url)
    finally:
        await client.close()
