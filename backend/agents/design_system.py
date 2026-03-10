"""Design System Agent - Step 4.

Phase 11D: Enhanced with design preferences, Figma integration, and dual-theme support.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAgent

logger = logging.getLogger(__name__)


class DesignSystemAgent(BaseAgent):
    """Creates comprehensive design system specifications.
    
    Phase 11 Enhancements:
    - Read requirements.design.style (modern_minimal/bold_vibrant/playful/corporate)
    - Read requirements.design.color_preference
    - Read requirements.design.dark_mode (both/dark_only/light_only)
    - Use Figma data as primary source if available
    - Generate FULL light + dark tokens when dark_mode="both"
    - Query KB for successful design tokens
    - Output Tailwind config with all tokens
    - Write design tokens to KB
    """
    
    name = "design_system"
    description = "Design System Agent"
    step_number = 4
    
    # Style presets for different design styles
    STYLE_PRESETS = {
        "minimal": {
            "spacing": "generous",
            "border_radius": "medium",
            "shadows": "subtle",
            "animations": "subtle",
        },
        "bold": {
            "spacing": "tight",
            "border_radius": "large",
            "shadows": "prominent",
            "animations": "dynamic",
        },
        "playful": {
            "spacing": "comfortable",
            "border_radius": "rounded",
            "shadows": "soft",
            "animations": "bouncy",
        },
        "corporate": {
            "spacing": "structured",
            "border_radius": "small",
            "shadows": "minimal",
            "animations": "professional",
        },
        "elegant": {
            "spacing": "generous",
            "border_radius": "subtle",
            "shadows": "refined",
            "animations": "smooth",
        },
    }
    
    SYSTEM_PROMPT = """You are the Design System Agent for an AI development agency.

Your job is to create a complete, production-ready design system that follows 2026 design trends:
- Bento grid layouts
- Glassmorphism with subtle gradients
- Micro-interactions and smooth animations
- Dark mode first with optional light mode
- Mobile-first responsive design
- Accessible color contrasts (WCAG AA minimum)

IMPORTANT Phase 11 Requirements:
1. If dark_mode="both", generate COMPLETE separate color palettes for both themes
2. If Figma tokens are provided, use them as the PRIMARY source
3. Match the design_style preference (minimal/bold/playful/corporate/elegant)
4. All colors must pass WCAG AA contrast requirements

Respond ONLY with valid JSON in this format:
{
    "design_philosophy": "Overall design approach",
    "theme_mode": "both" | "dark_only" | "light_only",
    "colors": {
        "light": {
            "primary": {"default": "#hex", "hover": "#hex", "active": "#hex"},
            "secondary": {"default": "#hex", "hover": "#hex", "active": "#hex"},
            "accent": {"default": "#hex"},
            "background": {"primary": "#hex", "secondary": "#hex", "tertiary": "#hex"},
            "text": {"primary": "#hex", "secondary": "#hex", "muted": "#hex"},
            "border": {"default": "#hex", "focus": "#hex"},
            "status": {"success": "#hex", "warning": "#hex", "error": "#hex", "info": "#hex"}
        },
        "dark": {
            // Same structure as light
        }
    },
    "typography": {
        "font_family": {
            "heading": "font-family string",
            "body": "font-family string",
            "mono": "font-family string"
        },
        "scale": {...},
        "weights": {...},
        "line_heights": {...}
    },
    "spacing": {...},
    "border_radius": {...},
    "shadows": {
        "light": {...},
        "dark": {...}
    },
    "animations": {...},
    "breakpoints": {...},
    "glassmorphism": {
        "light": {"background": "rgba(...)", "blur": "12px", "border": "rgba(...)"},
        "dark": {"background": "rgba(...)", "blur": "12px", "border": "rgba(...)"}
    },
    "component_styles": {
        "button": {...},
        "input": {...},
        "card": {...}
    },
    "tailwind_config_extend": {
        "colors": {},
        "fontFamily": {},
        "animation": {},
        "keyframes": {}
    },
    "css_variables": {
        ":root": {...},
        ".dark": {...}
    }
}"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create design system based on research and architecture.
        
        Phase 11 Enhanced:
        - Reads design preferences from structured requirements
        - Uses Figma tokens as primary source if available
        - Generates both light and dark themes when needed
        - Queries and writes to KB
        """
        classification = input_data.get("classification", {})
        research = input_data.get("research", {})
        architecture = input_data.get("architecture", {})
        brief = input_data.get("brief", "")
        cost_profile = input_data.get("cost_profile", "balanced")
        
        # Phase 11: Extract structured requirements
        requirements = input_data.get("requirements", {})
        design_prefs = requirements.get("design_preferences", {})
        design_style = design_prefs.get("design_style", "minimal")
        color_scheme = design_prefs.get("color_scheme", "system")  # light/dark/system
        primary_color = design_prefs.get("primary_color")
        secondary_color = design_prefs.get("secondary_color")
        enable_glassmorphism = design_prefs.get("glassmorphism", True)
        enable_animations = design_prefs.get("enable_animations", True)
        
        # Phase 11: Get Figma tokens from research output
        figma_tokens = research.get("figma_tokens") or input_data.get("figma_tokens")
        
        # Determine theme mode
        theme_mode = self._determine_theme_mode(color_scheme)
        
        # Phase 11B: Query KB for successful design tokens
        kb_context = await self._query_knowledge_base(
            project_type=requirements.get("project_type") or classification.get("project_type"),
            design_style=design_style,
            industry=requirements.get("industry")
        )
        
        model = self._select_model(cost_profile)
        
        # Build design context
        context_parts = []
        
        context_parts.append(f"Design Style: {design_style}")
        context_parts.append(f"Theme Mode: {theme_mode}")
        
        style_preset = self.STYLE_PRESETS.get(design_style, {})
        if style_preset:
            context_parts.append(f"Style Preset Characteristics: {json.dumps(style_preset)}")
        
        if primary_color:
            context_parts.append(f"Primary Color: {primary_color}")
        if secondary_color:
            context_parts.append(f"Secondary Color: {secondary_color}")
        
        context_parts.append(f"Glassmorphism: {'enabled' if enable_glassmorphism else 'disabled'}")
        context_parts.append(f"Animations: {'enabled' if enable_animations else 'disabled'}")
        
        # Figma tokens as PRIMARY source
        if figma_tokens:
            context_parts.append(f"\nFIGMA DESIGN TOKENS (USE AS PRIMARY SOURCE):")
            context_parts.append(json.dumps(figma_tokens, indent=2)[:1000])
        
        # KB context
        if kb_context.get("similar_designs"):
            context_parts.append(f"\nSuccessful Similar Design Systems Found:")
            for design in kb_context["similar_designs"][:2]:
                context_parts.append(f"- {design.get('title', 'Untitled')}")
        
        context = "\n".join(context_parts)
        
        prompt = f"""Create a comprehensive design system for this project:

Original Brief:
{brief}

Project Type: {classification.get('project_type', 'web_simple')}
Target Audience: {classification.get('target_audience', 'general')}

Design Requirements:
{context}

Research Color Recommendations:
{json.dumps(research.get('color_recommendations', {}), indent=2)}

Research Typography Recommendations:
{json.dumps(research.get('typography_recommendations', {}), indent=2)}

{"IMPORTANT: Generate COMPLETE color palettes for BOTH light and dark themes." if theme_mode == "both" else ""}
{"IMPORTANT: Use the Figma tokens provided as the PRIMARY source for colors and typography." if figma_tokens else ""}

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
        
        # Ensure theme_mode is set
        if "theme_mode" not in design_system:
            design_system["theme_mode"] = theme_mode
        
        # Generate CSS variables for easy theme switching
        if "css_variables" not in design_system:
            design_system["css_variables"] = self._generate_css_variables(design_system)
        
        # Generate Tailwind config
        if "tailwind_config_extend" not in design_system:
            design_system["tailwind_config_extend"] = self._generate_tailwind_config(design_system)
        
        await self.log_execution(
            input_data=input_data,
            output_data=design_system,
            model=model,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            cost=result["cost"],
            duration_ms=result["duration_ms"],
        )
        
        # Phase 11B: Write design tokens to KB
        await self._write_to_knowledge_base(design_system, requirements, design_style)
        
        return {
            "design_system": design_system,
            "theme_mode": theme_mode,
            "tailwind_config": design_system.get("tailwind_config_extend"),
            "css_variables": design_system.get("css_variables"),
            "figma_tokens_used": figma_tokens is not None,
            "model_used": model,
            "tokens": result["total_tokens"],
            "cost": result["cost"],
        }
    
    def _determine_theme_mode(self, color_scheme: str) -> str:
        """Determine theme mode from color scheme preference."""
        if color_scheme == "dark":
            return "dark_only"
        elif color_scheme == "light":
            return "light_only"
        else:  # system or both
            return "both"
    
    def _generate_css_variables(self, design_system: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """Generate CSS variables for theme switching."""
        css_vars = {":root": {}, ".dark": {}}
        
        colors = design_system.get("colors", {})
        
        # Light theme (default)
        light_colors = colors.get("light", colors)
        for category, values in light_colors.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    if isinstance(value, str):
                        css_vars[":root"][f"--color-{category}-{key}"] = value
                    elif isinstance(value, dict) and "default" in value:
                        css_vars[":root"][f"--color-{category}-{key}"] = value["default"]
        
        # Dark theme
        dark_colors = colors.get("dark", {})
        for category, values in dark_colors.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    if isinstance(value, str):
                        css_vars[".dark"][f"--color-{category}-{key}"] = value
                    elif isinstance(value, dict) and "default" in value:
                        css_vars[".dark"][f"--color-{category}-{key}"] = value["default"]
        
        return css_vars
    
    def _generate_tailwind_config(self, design_system: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Tailwind config extension."""
        config = {
            "colors": {},
            "fontFamily": {},
            "animation": {},
            "keyframes": {},
        }
        
        # Map CSS variables to Tailwind
        config["colors"]["primary"] = "var(--color-primary-default)"
        config["colors"]["secondary"] = "var(--color-secondary-default)"
        config["colors"]["accent"] = "var(--color-accent-default)"
        
        typography = design_system.get("typography", {}).get("font_family", {})
        if typography:
            config["fontFamily"]["heading"] = typography.get("heading", "sans-serif")
            config["fontFamily"]["body"] = typography.get("body", "sans-serif")
            config["fontFamily"]["mono"] = typography.get("mono", "monospace")
        
        return config
    
    async def _query_knowledge_base(
        self,
        project_type: Optional[str],
        design_style: str,
        industry: Optional[str]
    ) -> Dict[str, Any]:
        """Query KB for successful design tokens."""
        try:
            from ..knowledge import query_knowledge, KnowledgeEntryType
            from ..models import get_db
            
            db = next(get_db())
            
            query_text = f"{design_style} design system {project_type} {industry}"
            
            results = await query_knowledge(
                db=db,
                query_text=query_text,
                entry_types=[KnowledgeEntryType.DESIGN_INSPIRATION],
                min_quality_score=0.7,
                limit=3,
            )
            
            return {
                "similar_designs": [
                    {
                        "id": r.entry.id,
                        "title": r.entry.title,
                        "content": r.entry.content[:300],
                        "similarity": r.similarity_score,
                    }
                    for r in results
                ]
            }
        except Exception as e:
            logger.debug(f"KB query failed: {e}")
            return {"similar_designs": []}
    
    async def _write_to_knowledge_base(
        self,
        design_system: Dict[str, Any],
        requirements: Dict[str, Any],
        design_style: str
    ) -> None:
        """Write design tokens to KB."""
        try:
            from ..knowledge import store_knowledge, KnowledgeEntryType
            from ..models import get_db
            
            db = next(get_db())
            
            title = f"Design System: {design_style} - {requirements.get('project_type', 'Unknown')}"
            content = json.dumps(design_system, indent=2)
            
            await store_knowledge(
                db=db,
                entry_type=KnowledgeEntryType.DESIGN_INSPIRATION,
                title=title,
                content=content,
                project_type=requirements.get("project_type"),
                industry=requirements.get("industry"),
                agent_name=self.name,
                quality_score=0.8,
                tags=["design-system", design_style, "tailwind"],
                metadata={
                    "theme_mode": design_system.get("theme_mode"),
                    "has_glassmorphism": "glassmorphism" in design_system,
                }
            )
        except Exception as e:
            logger.debug(f"KB write failed: {e}")
    
    def _select_model(self, cost_profile: str) -> str:
        """Select model based on cost profile."""
        models = {
            "budget": "deepseek/deepseek-chat",
            "balanced": "anthropic/claude-sonnet-4",
            "premium": "anthropic/claude-opus-4",
        }
        return models.get(cost_profile, "anthropic/claude-sonnet-4")
