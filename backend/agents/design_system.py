"""Design System Agent - Step 4."""
import json
from typing import Any, Dict

from .base import BaseAgent


class DesignSystemAgent(BaseAgent):
    """Creates comprehensive design system specifications."""
    
    name = "design_system"
    description = "Design System Agent"
    step_number = 4
    
    SYSTEM_PROMPT = """You are the Design System Agent for an AI development agency.

Your job is to create a complete, production-ready design system that follows 2026 design trends:
- Bento grid layouts
- Glassmorphism with subtle gradients
- Micro-interactions and smooth animations
- Dark mode first with optional light mode
- Mobile-first responsive design
- Accessible color contrasts (WCAG AA minimum)

Respond ONLY with valid JSON in this format:
{
    "design_philosophy": "Overall design approach",
    "colors": {
        "primary": {"default": "#hex", "hover": "#hex", "active": "#hex"},
        "secondary": {"default": "#hex", "hover": "#hex", "active": "#hex"},
        "accent": {"default": "#hex", "hover": "#hex", "active": "#hex"},
        "background": {
            "primary": "#hex",
            "secondary": "#hex",
            "tertiary": "#hex"
        },
        "text": {
            "primary": "#hex",
            "secondary": "#hex",
            "muted": "#hex"
        },
        "border": {"default": "#hex", "focus": "#hex"},
        "status": {
            "success": "#hex",
            "warning": "#hex",
            "error": "#hex",
            "info": "#hex"
        }
    },
    "typography": {
        "font_family": {
            "heading": "font-family string",
            "body": "font-family string",
            "mono": "font-family string"
        },
        "scale": {
            "xs": "0.75rem",
            "sm": "0.875rem",
            "base": "1rem",
            "lg": "1.125rem",
            "xl": "1.25rem",
            "2xl": "1.5rem",
            "3xl": "1.875rem",
            "4xl": "2.25rem",
            "5xl": "3rem"
        },
        "weights": {
            "normal": 400,
            "medium": 500,
            "semibold": 600,
            "bold": 700
        },
        "line_heights": {
            "tight": 1.25,
            "normal": 1.5,
            "relaxed": 1.75
        }
    },
    "spacing": {
        "unit": "4px",
        "scale": [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64]
    },
    "border_radius": {
        "none": "0",
        "sm": "4px",
        "md": "8px",
        "lg": "12px",
        "xl": "16px",
        "2xl": "24px",
        "full": "9999px"
    },
    "shadows": {
        "sm": "shadow definition",
        "md": "shadow definition",
        "lg": "shadow definition",
        "glow": "colored glow shadow"
    },
    "animations": {
        "durations": {
            "fast": "150ms",
            "normal": "300ms",
            "slow": "500ms"
        },
        "easings": {
            "default": "cubic-bezier(0.4, 0, 0.2, 1)",
            "in": "cubic-bezier(0.4, 0, 1, 1)",
            "out": "cubic-bezier(0, 0, 0.2, 1)",
            "bounce": "cubic-bezier(0.68, -0.55, 0.265, 1.55)"
        }
    },
    "breakpoints": {
        "sm": "640px",
        "md": "768px",
        "lg": "1024px",
        "xl": "1280px",
        "2xl": "1536px"
    },
    "component_styles": {
        "button": {
            "primary": "Tailwind classes",
            "secondary": "Tailwind classes",
            "ghost": "Tailwind classes",
            "sizes": {
                "sm": "Tailwind classes",
                "md": "Tailwind classes",
                "lg": "Tailwind classes"
            }
        },
        "input": "Tailwind classes",
        "card": "Tailwind classes",
        "badge": "Tailwind classes"
    },
    "tailwind_config_extend": {
        "colors": {},
        "fontFamily": {},
        "animation": {},
        "keyframes": {}
    }
}"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create design system based on research and architecture."""
        classification = input_data.get("classification", {})
        research = input_data.get("research", {})
        architecture = input_data.get("architecture", {})
        brief = input_data.get("brief", "")
        cost_profile = input_data.get("cost_profile", "balanced")
        
        model = self._select_model(cost_profile)
        
        prompt = f"""Create a comprehensive design system for this project:

Original Brief:
{brief}

Project Type: {classification.get('project_type', 'web_simple')}
Target Audience: {classification.get('target_audience', 'general')}

Research Color Recommendations:
{json.dumps(research.get('color_recommendations', {}), indent=2)}

Research Typography Recommendations:
{json.dumps(research.get('typography_recommendations', {}), indent=2)}

Create a complete design system with all tokens and component styles."""
        
        result = await self.call_llm(
            prompt=prompt,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=8192,
        )
        
        try:
            design_system = json.loads(result["content"])
        except json.JSONDecodeError:
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                design_system = json.loads(content[start:end])
            else:
                design_system = {"error": "Failed to parse response", "raw": content}
        
        await self.log_execution(
            input_data=input_data,
            output_data=design_system,
            model=model,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            cost=result["cost"],
            duration_ms=result["duration_ms"],
        )
        
        return {
            "design_system": design_system,
            "model_used": model,
            "tokens": result["total_tokens"],
            "cost": result["cost"],
        }
    
    def _select_model(self, cost_profile: str) -> str:
        """Select model based on cost profile."""
        models = {
            "budget": "deepseek/deepseek-chat",
            "balanced": "anthropic/claude-sonnet-4",
            "premium": "anthropic/claude-opus-4",
        }
        return models.get(cost_profile, "anthropic/claude-sonnet-4")
