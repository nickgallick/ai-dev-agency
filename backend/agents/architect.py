"""Architect Agent - Step 3."""
import json
from typing import Any, Dict

from .base import BaseAgent


class ArchitectAgent(BaseAgent):
    """Creates detailed technical architecture and build plans."""
    
    name = "architect"
    description = "Architect Agent"
    step_number = 3
    
    SYSTEM_PROMPT = """You are the Architect Agent for an AI development agency.

Your job is to create a hyper-specific build plan that will be used to generate code.
You must produce detailed specifications that leave no ambiguity.

Respond ONLY with valid JSON in this format:
{
    "architecture_overview": "High-level description of the architecture",
    "tech_stack": {
        "frontend": {
            "framework": "Next.js / React / etc",
            "styling": "Tailwind CSS / etc",
            "state_management": "if needed",
            "ui_components": "shadcn/ui / etc"
        },
        "backend": {
            "framework": "if needed",
            "database": "if needed",
            "auth": "if needed"
        }
    },
    "pages": [
        {
            "route": "/",
            "name": "Home",
            "purpose": "Main landing page",
            "sections": [
                {
                    "name": "Hero",
                    "components": ["Heading", "Subheading", "CTA Button", "Hero Image"],
                    "behavior": "Static content with fade-in animation"
                }
            ],
            "data_requirements": "none or list of data needed"
        }
    ],
    "components": [
        {
            "name": "ComponentName",
            "purpose": "What it does",
            "props": [{"name": "propName", "type": "string", "required": true}],
            "state": ["if any local state"],
            "reused_in": ["page1", "page2"]
        }
    ],
    "api_endpoints": [
        {
            "method": "GET/POST/etc",
            "path": "/api/endpoint",
            "purpose": "What it does",
            "request_body": {},
            "response": {}
        }
    ],
    "database_schema": {
        "tables": [
            {
                "name": "table_name",
                "columns": [{"name": "id", "type": "uuid", "primary": true}],
                "relationships": []
            }
        ]
    },
    "file_structure": [
        "src/app/page.tsx",
        "src/components/Header.tsx"
    ],
    "build_order": [
        "Step 1: Set up project with Next.js",
        "Step 2: Create layout and navigation",
        "Step 3: Build home page sections"
    ]
}"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create architecture plan based on research and classification."""
        classification = input_data.get("classification", {})
        research = input_data.get("research", {})
        brief = input_data.get("brief", "")
        cost_profile = input_data.get("cost_profile", "balanced")
        
        model = self._select_model(cost_profile)
        
        prompt = f"""Create a detailed technical architecture for this project:

Original Brief:
{brief}

Project Classification:
{json.dumps(classification, indent=2)}

Research Findings:
{json.dumps(research, indent=2)}

Create a comprehensive, hyper-specific build plan."""
        
        result = await self.call_llm(
            prompt=prompt,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=8192,
        )
        
        try:
            architecture = json.loads(result["content"])
        except json.JSONDecodeError:
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                architecture = json.loads(content[start:end])
            else:
                architecture = {"error": "Failed to parse response", "raw": content}
        
        await self.log_execution(
            input_data=input_data,
            output_data=architecture,
            model=model,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            cost=result["cost"],
            duration_ms=result["duration_ms"],
        )
        
        return {
            "architecture": architecture,
            "model_used": model,
            "tokens": result["total_tokens"],
            "cost": result["cost"],
        }
    
    def _select_model(self, cost_profile: str) -> str:
        """Select model based on cost profile."""
        models = {
            "budget": "anthropic/claude-sonnet-4",
            "balanced": "anthropic/claude-opus-4",
            "premium": "anthropic/claude-opus-4",
        }
        return models.get(cost_profile, "anthropic/claude-opus-4")
