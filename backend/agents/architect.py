"""Architect Agent - Step 3.

Phase 11D: Enhanced with structured requirements, KB integration, and dynamic pooling support.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAgent

logger = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    """Creates detailed technical architecture and build plans.
    
    Phase 11 Enhancements:
    - Read requirements.features dict (explicit feature flags)
    - Read requirements.pages list (exact pages to build)
    - Read requirements.tech_stack
    - Query KB for successful architectures
    - Load template architecture if template_id exists
    - Output page_dependency_graph for dynamic pooling (>10 pages)
    - Output build_manifest.json (single source of truth)
    - Plan integrations based on features (Stripe, Resend, R2, etc.)
    - Write architecture decisions to KB
    """
    
    name = "architect"
    description = "Architect Agent"
    step_number = 3
    
    # Integration mappings based on features
    INTEGRATION_MAPPINGS = {
        "payments": {"service": "stripe", "env_vars": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY"]},
        "billing": {"service": "stripe", "env_vars": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"]},
        "email": {"service": "resend", "env_vars": ["RESEND_API_KEY"]},
        "file_upload": {"service": "r2", "env_vars": ["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME", "R2_ACCOUNT_ID"]},
        "background_jobs": {"service": "inngest", "env_vars": ["INNGEST_EVENT_KEY"]},
        "authentication": {"service": "supabase_auth", "env_vars": ["SUPABASE_URL", "SUPABASE_ANON_KEY"]},
        "analytics": {"service": "plausible", "env_vars": ["PLAUSIBLE_DOMAIN"]},
        "error_tracking": {"service": "sentry", "env_vars": ["SENTRY_DSN"]},
    }
    
    SYSTEM_PROMPT = """You are the Architect Agent for an AI development agency.

Your job is to create a hyper-specific build plan that will be used to generate code.
You must produce detailed specifications that leave no ambiguity.

Important Phase 11 Requirements:
1. If the project has >10 pages, generate a page_dependency_graph for dynamic pooling
2. Generate a build_manifest.json as the single source of truth
3. Plan all integrations based on the features requested
4. Support both light and dark mode if dark_mode="both" in design preferences

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
            "data_requirements": "none or list of data needed",
            "dependencies": [] // Pages this page depends on (for dynamic pooling)
        }
    ],
    "page_dependency_graph": {
        // Only for projects with >10 pages
        "batches": [
            {"batch": 1, "pages": ["Home", "About"], "can_parallelize": true},
            {"batch": 2, "pages": ["Dashboard"], "depends_on_batch": 1}
        ]
    },
    "components": [
        {
            "name": "ComponentName",
            "purpose": "What it does",
            "props": [{"name": "propName", "type": "string", "required": true}],
            "state": ["if any local state"],
            "reused_in": ["page1", "page2"],
            "supports_dark_mode": true
        }
    ],
    "integrations": [
        {
            "service": "stripe",
            "purpose": "Payment processing",
            "env_vars": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY"],
            "setup_steps": ["Create Stripe account", "Get API keys"]
        }
    ],
    "api_endpoints": [...],
    "database_schema": {...},
    "file_structure": [...],
    "build_order": [...],
    "build_manifest": {
        "version": "1.0.0",
        "project_type": "web_complex",
        "total_pages": 5,
        "total_components": 12,
        "requires_backend": true,
        "integrations": ["stripe", "resend"],
        "dark_mode": true,
        "estimated_tokens": 50000
    }
}"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create architecture plan based on research and classification.
        
        Phase 11 Enhanced:
        - Reads structured requirements
        - Queries KB for successful architectures
        - Loads template if provided
        - Outputs dependency graph for dynamic pooling
        - Plans integrations
        - Writes to KB
        """
        classification = input_data.get("classification", {})
        research = input_data.get("research", {})
        brief = input_data.get("brief", "")
        cost_profile = input_data.get("cost_profile", "balanced")
        
        # Phase 11: Extract structured requirements
        requirements = input_data.get("requirements", {})
        features = self._extract_features(requirements)
        pages = self._extract_pages(requirements)
        tech_stack = requirements.get("tech_stack", {})
        design_prefs = requirements.get("design_preferences", {})
        dark_mode = design_prefs.get("color_scheme", "system")
        template_data = input_data.get("template_data")
        
        # Phase 11B: Query KB for successful architectures
        kb_context = await self._query_knowledge_base(
            project_type=requirements.get("project_type") or classification.get("project_type"),
            industry=requirements.get("industry"),
            features=features
        )
        
        # Determine required integrations based on features
        integrations = self._plan_integrations(features)
        
        model = self._select_model(cost_profile)
        
        # Build context
        context_parts = []
        
        if features:
            context_parts.append(f"Required Features: {', '.join(features)}")
        if pages:
            context_parts.append(f"Required Pages: {', '.join(pages)}")
        if tech_stack:
            context_parts.append(f"Tech Stack Preferences: {json.dumps(tech_stack)}")
        if dark_mode in ["both", "system"]:
            context_parts.append("Dark Mode: Required (support both light and dark themes)")
        if integrations:
            context_parts.append(f"Required Integrations: {json.dumps(integrations)}")
        
        # Template context
        if template_data:
            context_parts.append(f"\nUsing Template: {template_data.get('name', 'Unknown')}")
            if template_data.get("architecture"):
                context_parts.append(f"Template Architecture: {json.dumps(template_data['architecture'])[:500]}")
        
        # KB context
        if kb_context.get("similar_architectures"):
            context_parts.append(f"\nSuccessful Similar Architectures Found:")
            for arch in kb_context["similar_architectures"][:2]:
                context_parts.append(f"- {arch.get('title', 'Untitled')}")
        
        context = "\n".join(context_parts)
        
        prompt = f"""Create a detailed technical architecture for this project:

Original Brief:
{brief}

Project Classification:
{json.dumps(classification, indent=2)}

Research Findings:
{json.dumps(research, indent=2)}

Structured Requirements:
{context}

Create a comprehensive, hyper-specific build plan.
{"Generate page_dependency_graph since there are >10 pages." if len(pages) > 10 else ""}
Include build_manifest.json as the single source of truth."""
        
        result = await self.call_llm(
            prompt=prompt,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=8192,
        )

        # Check for LLM errors (missing API key, auth failure, etc.)
        if result.get("error"):
            error_msg = result.get("error_message") or result.get("error")
            return {
                "error": error_msg,
                "architecture": {"error": error_msg},
            }

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
        
        # Ensure build_manifest exists
        if "build_manifest" not in architecture:
            architecture["build_manifest"] = self._generate_build_manifest(
                architecture, requirements, features, integrations
            )
        
        # Ensure integrations are included
        if "integrations" not in architecture:
            architecture["integrations"] = integrations
        
        await self.log_execution(
            input_data=input_data,
            output_data=architecture,
            model=model,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            cost=result["cost"],
            duration_ms=result["duration_ms"],
        )
        
        # Phase 11B: Write architecture decisions to KB
        await self._write_to_knowledge_base(architecture, requirements)
        
        return {
            "architecture": architecture,
            "build_manifest": architecture.get("build_manifest"),
            "page_dependency_graph": architecture.get("page_dependency_graph"),
            "integrations": architecture.get("integrations", integrations),
            "model_used": model,
            "tokens": result["total_tokens"],
            "cost": result["cost"],
        }
    
    def _extract_features(self, requirements: Dict[str, Any]) -> List[str]:
        """Extract feature list from structured requirements."""
        features = []
        
        # From web_complex_options
        web_opts = requirements.get("web_complex_options", {})
        if web_opts:
            features.extend(web_opts.get("key_features", []))
            if web_opts.get("include_auth"):
                features.append("authentication")
            if web_opts.get("include_dashboard"):
                features.append("dashboard")
            if web_opts.get("include_billing"):
                features.append("billing")
            if web_opts.get("include_email"):
                features.append("email")
        
        # From mobile_options
        mobile_opts = requirements.get("mobile_options", {})
        if mobile_opts:
            if mobile_opts.get("include_push_notifications"):
                features.append("notifications")
            if mobile_opts.get("include_offline_support"):
                features.append("offline")
        
        return list(set(features))
    
    def _extract_pages(self, requirements: Dict[str, Any]) -> List[str]:
        """Extract page list from structured requirements."""
        pages = []
        
        # From web_complex_options
        web_opts = requirements.get("web_complex_options", {})
        if web_opts:
            pages.extend(web_opts.get("pages", []))
        
        # From web_simple_options
        simple_opts = requirements.get("web_simple_options", {})
        if simple_opts:
            pages.extend(simple_opts.get("sections", []))
        
        return pages
    
    def _plan_integrations(self, features: List[str]) -> List[Dict[str, Any]]:
        """Plan integrations based on required features."""
        integrations = []
        seen_services = set()
        
        for feature in features:
            mapping = self.INTEGRATION_MAPPINGS.get(feature)
            if mapping and mapping["service"] not in seen_services:
                seen_services.add(mapping["service"])
                integrations.append({
                    "service": mapping["service"],
                    "purpose": feature,
                    "env_vars": mapping["env_vars"],
                    "setup_required": True,
                })
        
        return integrations
    
    def _generate_build_manifest(
        self,
        architecture: Dict[str, Any],
        requirements: Dict[str, Any],
        features: List[str],
        integrations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate build manifest as single source of truth."""
        pages = architecture.get("pages", [])
        components = architecture.get("components", [])
        
        return {
            "version": "1.0.0",
            "project_type": requirements.get("project_type", "web_complex"),
            "total_pages": len(pages),
            "total_components": len(components),
            "requires_backend": architecture.get("tech_stack", {}).get("backend") is not None,
            "features": features,
            "integrations": [i["service"] for i in integrations],
            "dark_mode": requirements.get("design_preferences", {}).get("color_scheme") in ["both", "system", "dark"],
            "estimated_tokens": len(pages) * 5000 + len(components) * 1000,
            "dynamic_pooling_enabled": len(pages) > 10,
        }
    
    async def _query_knowledge_base(
        self,
        project_type: Optional[str],
        industry: Optional[str],
        features: List[str]
    ) -> Dict[str, Any]:
        """Query KB for successful architectures."""
        try:
            from ..knowledge import query_knowledge, KnowledgeEntryType
            from ..models import get_db
            
            db = next(get_db())
            
            query_text = f"{project_type} {industry} architecture {' '.join(features)}"
            
            results = await query_knowledge(
                db=db,
                query_text=query_text,
                entry_types=[KnowledgeEntryType.ARCHITECTURE_DECISION],
                project_type=project_type,
                min_quality_score=0.8,
                limit=3,
            )
            
            return {
                "similar_architectures": [
                    {
                        "id": r.entry.id,
                        "title": r.entry.title,
                        "content": r.entry.content[:500],
                        "similarity": r.similarity_score,
                    }
                    for r in results
                ]
            }
        except Exception as e:
            logger.debug(f"KB query failed: {e}")
            return {"similar_architectures": []}
    
    async def _write_to_knowledge_base(
        self,
        architecture: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> None:
        """Write architecture decisions to KB."""
        try:
            from ..knowledge import store_architecture_decision
            from ..models import get_db
            
            db = next(get_db())
            
            title = f"Architecture: {requirements.get('project_type', 'Unknown')}"
            content = json.dumps(architecture, indent=2)
            
            await store_architecture_decision(
                db=db,
                title=title,
                content=content,
                project_type=requirements.get("project_type"),
                industry=requirements.get("industry"),
                tech_stack=list(architecture.get("tech_stack", {}).get("frontend", {}).values()),
                metadata={
                    "pages": len(architecture.get("pages", [])),
                    "components": len(architecture.get("components", [])),
                    "has_backend": architecture.get("build_manifest", {}).get("requires_backend", False),
                }
            )
        except Exception as e:
            logger.debug(f"KB write failed: {e}")
    
    def _select_model(self, cost_profile: str) -> str:
        """Select model based on cost profile."""
        models = {
            "budget": "anthropic/claude-sonnet-4",
            "balanced": "anthropic/claude-opus-4",
            "premium": "anthropic/claude-opus-4",
        }
        return models.get(cost_profile, "anthropic/claude-opus-4")
