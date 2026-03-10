"""Code Generation Agent - Step 5 (using v0 Platform API)."""
import os
import json
import httpx
import time
from typing import Any, Dict, Optional

from .base import BaseAgent


class CodeGenerationAgent(BaseAgent):
    """Generates code using Vercel v0 Platform API."""
    
    name = "code_generation"
    description = "Code Generation Agent (v0 Platform API)"
    step_number = 5
    
    def __init__(self, project_id: str, db_session=None):
        super().__init__(project_id, db_session)
        self.v0_api_key = os.getenv("VERCEL_V0_API_KEY")
        self.v0_base_url = "https://api.v0.dev/v1"
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code using v0 Platform API."""
        architecture = input_data.get("architecture", {})
        design_system = input_data.get("design_system", {})
        brief = input_data.get("brief", "")
        
        # Build the v0 prompt with all context
        v0_prompt = self._build_v0_prompt(brief, architecture, design_system)
        
        start_time = time.time()
        
        # Call v0 API
        result = await self._call_v0_api(v0_prompt)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        await self.log_execution(
            input_data={"prompt": v0_prompt[:1000]},  # Truncate for logging
            output_data=result,
            model="v0-platform-api",
            prompt_tokens=len(v0_prompt.split()),
            completion_tokens=len(str(result).split()),
            cost=result.get("cost", 0),
            duration_ms=duration_ms,
        )
        
        return result
    
    def _build_v0_prompt(self, brief: str, architecture: Dict, design_system: Dict) -> str:
        """Build a comprehensive prompt for v0."""
        colors = design_system.get("colors", {})
        typography = design_system.get("typography", {})
        pages = architecture.get("pages", [])
        
        prompt_parts = [
            f"Build a complete web application based on this brief: {brief}",
            "",
            "## Design System",
            f"Primary color: {colors.get('primary', {}).get('default', '#3b82f6')}",
            f"Background: {colors.get('background', {}).get('primary', '#ffffff')}",
            f"Text: {colors.get('text', {}).get('primary', '#1f2937')}",
            f"Font: {typography.get('font_family', {}).get('body', 'Inter')}",
            "",
            "## Pages to Build",
        ]
        
        for page in pages:
            prompt_parts.append(f"- {page.get('route', '/')}: {page.get('name', 'Page')} - {page.get('purpose', '')}")
            for section in page.get("sections", []):
                prompt_parts.append(f"  - Section: {section.get('name', '')} with {', '.join(section.get('components', []))}")
        
        prompt_parts.extend([
            "",
            "## Technical Requirements",
            "- Use Next.js 14 with App Router",
            "- Use Tailwind CSS for styling",
            "- Use shadcn/ui components",
            "- Make it fully responsive (mobile-first)",
            "- Include smooth animations and micro-interactions",
            "- Ensure accessibility (WCAG AA)",
            "",
            "Generate complete, production-ready code."
        ])
        
        return "\n".join(prompt_parts)
    
    async def _call_v0_api(self, prompt: str) -> Dict[str, Any]:
        """Call the v0 Platform API."""
        if not self.v0_api_key:
            return {
                "error": "V0 API key not configured",
                "code": None,
                "files": [],
            }
        
        headers = {
            "Authorization": f"Bearer {self.v0_api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "prompt": prompt,
            "model": "v0-1.5",  # Latest v0 model
        }
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.v0_base_url}/generate",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "generation_id": result.get("id"),
                    "files": result.get("files", []),
                    "preview_url": result.get("preview_url"),
                    "cost": result.get("cost", 0),
                }
        except httpx.HTTPStatusError as e:
            return {
                "error": f"v0 API error: {e.response.status_code}",
                "details": e.response.text,
            }
        except Exception as e:
            return {
                "error": f"Failed to call v0 API: {str(e)}",
            }
