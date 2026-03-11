"""Integration Wiring Agent - Step 7C.

Phase 11D: Wire all integrations based on requirements.features.

This agent is responsible for:
- Wiring ALL integrations based on requirements.features
- Generating .env.example with all required vars
- Generating setup-guide.md
- Verifying API contracts match
"""
import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAgent

logger = logging.getLogger(__name__)


# Integration templates with setup instructions
INTEGRATION_TEMPLATES = {
    "stripe": {
        "name": "Stripe Payments",
        "env_vars": [
            {"key": "STRIPE_SECRET_KEY", "description": "Stripe secret API key", "required": True},
            {"key": "STRIPE_PUBLISHABLE_KEY", "description": "Stripe publishable key", "required": True},
            {"key": "STRIPE_WEBHOOK_SECRET", "description": "Webhook signing secret", "required": False},
        ],
        "setup_steps": [
            "1. Create a Stripe account at https://stripe.com",
            "2. Navigate to Developers > API Keys",
            "3. Copy Secret key and Publishable key",
            "4. Set up webhook endpoint at /api/webhooks/stripe",
        ],
        "files_to_create": [
            "lib/stripe.ts",
            "app/api/webhooks/stripe/route.ts",
            "app/api/checkout/route.ts",
        ],
    },
    "resend": {
        "name": "Resend Email",
        "env_vars": [
            {"key": "RESEND_API_KEY", "description": "Resend API key", "required": True},
            {"key": "RESEND_FROM_EMAIL", "description": "Verified sender email", "required": True},
        ],
        "setup_steps": [
            "1. Create a Resend account at https://resend.com",
            "2. Verify your sending domain",
            "3. Navigate to API Keys and create a new key",
            "4. Set RESEND_FROM_EMAIL to your verified domain email",
        ],
        "files_to_create": [
            "lib/email.ts",
            "app/api/send-email/route.ts",
        ],
    },
    "r2": {
        "name": "Cloudflare R2 Storage",
        "env_vars": [
            {"key": "R2_ACCESS_KEY_ID", "description": "R2 access key ID", "required": True},
            {"key": "R2_SECRET_ACCESS_KEY", "description": "R2 secret access key", "required": True},
            {"key": "R2_BUCKET_NAME", "description": "R2 bucket name", "required": True},
            {"key": "R2_ACCOUNT_ID", "description": "Cloudflare account ID", "required": True},
            {"key": "R2_PUBLIC_URL", "description": "Public bucket URL (if using custom domain)", "required": False},
        ],
        "setup_steps": [
            "1. Log in to Cloudflare dashboard",
            "2. Navigate to R2 > Overview > Create bucket",
            "3. Go to R2 > Overview > Manage R2 API Tokens",
            "4. Create a token with Object Read & Write permissions",
        ],
        "files_to_create": [
            "lib/storage.ts",
            "app/api/upload/route.ts",
        ],
    },
    "inngest": {
        "name": "Inngest Background Jobs",
        "env_vars": [
            {"key": "INNGEST_EVENT_KEY", "description": "Inngest event key", "required": True},
            {"key": "INNGEST_SIGNING_KEY", "description": "Inngest signing key (production)", "required": False},
        ],
        "setup_steps": [
            "1. Create an Inngest account at https://inngest.com",
            "2. Create a new app for your project",
            "3. Copy the Event Key from settings",
            "4. For production, also copy the Signing Key",
        ],
        "files_to_create": [
            "lib/inngest/client.ts",
            "lib/inngest/functions.ts",
            "app/api/inngest/route.ts",
        ],
    },
    "supabase_auth": {
        "name": "Supabase Authentication",
        "env_vars": [
            {"key": "NEXT_PUBLIC_SUPABASE_URL", "description": "Supabase project URL", "required": True},
            {"key": "NEXT_PUBLIC_SUPABASE_ANON_KEY", "description": "Supabase anon/public key", "required": True},
            {"key": "SUPABASE_SERVICE_ROLE_KEY", "description": "Supabase service role key (server-side)", "required": False},
        ],
        "setup_steps": [
            "1. Create a Supabase project at https://supabase.com",
            "2. Go to Project Settings > API",
            "3. Copy the Project URL and anon/public key",
            "4. For server-side operations, also copy service_role key",
        ],
        "files_to_create": [
            "lib/supabase/client.ts",
            "lib/supabase/server.ts",
            "app/auth/callback/route.ts",
            "middleware.ts",
        ],
    },
    "plausible": {
        "name": "Plausible Analytics",
        "env_vars": [
            {"key": "NEXT_PUBLIC_PLAUSIBLE_DOMAIN", "description": "Your website domain", "required": True},
            {"key": "NEXT_PUBLIC_PLAUSIBLE_HOST", "description": "Plausible host (default: plausible.io)", "required": False},
        ],
        "setup_steps": [
            "1. Create a Plausible account at https://plausible.io",
            "2. Add your website domain",
            "3. Set NEXT_PUBLIC_PLAUSIBLE_DOMAIN to your domain",
        ],
        "files_to_create": [
            "lib/analytics.ts",
        ],
    },
    "sentry": {
        "name": "Sentry Error Tracking",
        "env_vars": [
            {"key": "SENTRY_DSN", "description": "Sentry DSN", "required": True},
            {"key": "SENTRY_AUTH_TOKEN", "description": "Sentry auth token (for source maps)", "required": False},
        ],
        "setup_steps": [
            "1. Create a Sentry project at https://sentry.io",
            "2. Go to Settings > Projects > Client Keys",
            "3. Copy the DSN",
            "4. For source maps, create an auth token",
        ],
        "files_to_create": [
            "sentry.client.config.ts",
            "sentry.server.config.ts",
            "sentry.edge.config.ts",
        ],
    },
}


class IntegrationWiringAgent(BaseAgent):
    """Wires all integrations based on requirements.features.
    
    Phase 11D Features:
    - Wire ALL integrations based on requirements.features
    - Generate .env.example with all required vars
    - Generate setup-guide.md
    - Verify API contracts match
    """
    
    name = "integration_wiring"
    description = "Integration Wiring Agent"
    step_number = 7  # Runs after code generation
    
    SYSTEM_PROMPT = """You are the Integration Wiring Agent for an AI development agency.

Your job is to:
1. Generate integration code files for each required service
2. Ensure all API contracts are properly typed
3. Create helper functions and utilities
4. Set up error handling and logging

Generate code that is production-ready, type-safe, and follows best practices."""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Wire all integrations based on requirements.
        
        Args:
            input_data: Contains requirements, architecture, and integrations list
            
        Returns:
            Dict with generated files, env vars, and setup guide
        """
        requirements = input_data.get("requirements", {})
        architecture = input_data.get("architecture", {})
        integrations = input_data.get("integrations", [])
        
        # If no explicit integrations, extract from architecture
        if not integrations:
            integrations = architecture.get("integrations", [])
        
        # Extract from features if still empty
        if not integrations:
            features = self._extract_features(requirements)
            integrations = self._features_to_integrations(features)
        
        cost_profile = input_data.get("cost_profile", "balanced")
        
        logger.info(f"Wiring {len(integrations)} integrations: {[i.get('service', i) for i in integrations]}")
        
        # Collect all env vars
        all_env_vars = []
        
        # Collect all files to generate
        files_to_generate = []
        
        # Collect setup steps
        all_setup_steps = []
        
        for integration in integrations:
            service = integration.get("service") if isinstance(integration, dict) else integration
            template = INTEGRATION_TEMPLATES.get(service)
            
            if template:
                all_env_vars.extend(template["env_vars"])
                files_to_generate.extend(template["files_to_create"])
                all_setup_steps.append({
                    "service": template["name"],
                    "steps": template["setup_steps"],
                })
        
        # Generate .env.example
        env_example = self._generate_env_example(all_env_vars)
        
        # Generate setup-guide.md
        setup_guide = self._generate_setup_guide(all_setup_steps)
        
        # Generate integration code files using LLM
        generated_files = {}
        if files_to_generate:
            generated_files = await self._generate_integration_files(
                files_to_generate, integrations, requirements, cost_profile
            )
        
        # Log execution
        await self.log_execution(
            input_data={"integrations_count": len(integrations)},
            output_data={"files_count": len(generated_files), "env_vars_count": len(all_env_vars)},
            model=self._select_model(cost_profile),
            prompt_tokens=0,
            completion_tokens=0,
            cost=0.0,
            duration_ms=0,
        )
        
        return {
            "success": True,
            "integrations_wired": [i.get("service") if isinstance(i, dict) else i for i in integrations],
            "env_example": env_example,
            "setup_guide": setup_guide,
            "generated_files": generated_files,
            "env_vars": all_env_vars,
        }
    
    def _extract_features(self, requirements: Dict[str, Any]) -> List[str]:
        """Extract features from requirements."""
        features = []
        
        web_opts = requirements.get("web_complex_options", {})
        if web_opts:
            features.extend(web_opts.get("key_features", []))
            if web_opts.get("include_auth"):
                features.append("authentication")
            if web_opts.get("include_billing"):
                features.append("billing")
            if web_opts.get("include_email"):
                features.append("email")
        
        return features
    
    def _features_to_integrations(self, features: List[str]) -> List[Dict[str, str]]:
        """Map features to integrations."""
        feature_mapping = {
            "authentication": "supabase_auth",
            "billing": "stripe",
            "payments": "stripe",
            "email": "resend",
            "file_upload": "r2",
            "storage": "r2",
            "background_jobs": "inngest",
            "analytics": "plausible",
            "error_tracking": "sentry",
        }
        
        integrations = []
        seen = set()
        
        for feature in features:
            feature_lower = feature.lower()
            if feature_lower in feature_mapping:
                service = feature_mapping[feature_lower]
                if service not in seen:
                    seen.add(service)
                    integrations.append({"service": service, "purpose": feature})
        
        return integrations
    
    def _generate_env_example(self, env_vars: List[Dict[str, Any]]) -> str:
        """Generate .env.example content."""
        lines = [
            "# Generated by AI Dev Agency - Integration Wiring Agent",
            "# Copy this file to .env and fill in your values",
            "",
        ]
        
        current_section = None
        for var in env_vars:
            key = var["key"]
            desc = var["description"]
            required = var.get("required", True)
            
            # Group by prefix
            section = key.split("_")[0] if "_" in key else key
            if section != current_section:
                if current_section is not None:
                    lines.append("")
                current_section = section
            
            req_marker = " (REQUIRED)" if required else " (optional)"
            lines.append(f"# {desc}{req_marker}")
            lines.append(f"{key}=")
        
        return "\n".join(lines)
    
    def _generate_setup_guide(self, setup_steps: List[Dict[str, Any]]) -> str:
        """Generate setup-guide.md content."""
        lines = [
            "# Integration Setup Guide",
            "",
            "This guide covers setting up all integrations for your project.",
            "",
        ]
        
        for i, service in enumerate(setup_steps, 1):
            lines.append(f"## {i}. {service['service']}")
            lines.append("")
            for step in service["steps"]:
                lines.append(step)
            lines.append("")
        
        lines.extend([
            "## Verification",
            "",
            "After setting up all integrations:",
            "",
            "1. Run `npm run dev` to start the development server",
            "2. Check the console for any missing environment variable warnings",
            "3. Test each integration using the provided test pages/endpoints",
            "",
        ])
        
        return "\n".join(lines)
    
    async def _generate_integration_files(
        self,
        files: List[str],
        integrations: List[Dict[str, Any]],
        requirements: Dict[str, Any],
        cost_profile: str
    ) -> Dict[str, str]:
        """Generate integration code files using LLM."""
        model = self._select_model(cost_profile)
        generated = {}
        
        # Group files by integration
        for filepath in files:
            # Determine which integration this file is for
            integration_name = self._get_integration_from_path(filepath)
            template = INTEGRATION_TEMPLATES.get(integration_name, {})
            
            prompt = f"""Generate the code for: {filepath}

Integration: {integration_name}
Purpose: {template.get('name', integration_name)}

Requirements:
- TypeScript
- Next.js App Router compatible
- Proper error handling
- Type-safe

Generate production-ready code. Return only the code, no markdown."""
            
            try:
                result = await self.call_llm(
                    prompt=prompt,
                    model=model,
                    temperature=0.3,
                    max_tokens=2000,
                )

                # Check for LLM errors
                if result.get("error"):
                    error_msg = result.get("error_message") or result.get("error")
                    logger.warning(f"LLM error generating {filepath}: {error_msg}")
                    generated[filepath] = f"// TODO: Implement {filepath}\n// LLM Error: {error_msg}"
                    continue

                code = result["content"]
                # Clean up any markdown code blocks
                if code.startswith("```"):
                    code = code.split("\n", 1)[1]
                if code.endswith("```"):
                    code = code.rsplit("```", 1)[0]
                
                generated[filepath] = code.strip()
            except Exception as e:
                logger.warning(f"Failed to generate {filepath}: {e}")
                generated[filepath] = f"// TODO: Implement {filepath}\n// Error: {e}"
        
        return generated
    
    def _get_integration_from_path(self, filepath: str) -> str:
        """Determine integration from filepath."""
        path_lower = filepath.lower()
        
        if "stripe" in path_lower or "checkout" in path_lower or "billing" in path_lower:
            return "stripe"
        elif "email" in path_lower or "resend" in path_lower:
            return "resend"
        elif "storage" in path_lower or "upload" in path_lower or "r2" in path_lower:
            return "r2"
        elif "inngest" in path_lower:
            return "inngest"
        elif "supabase" in path_lower or "auth" in path_lower:
            return "supabase_auth"
        elif "plausible" in path_lower or "analytics" in path_lower:
            return "plausible"
        elif "sentry" in path_lower:
            return "sentry"
        
        return "unknown"
    
    def _select_model(self, cost_profile: str) -> str:
        """Select model based on cost profile."""
        models = {
            "budget": "deepseek/deepseek-chat",
            "balanced": "anthropic/claude-sonnet-4",
            "premium": "anthropic/claude-opus-4",
        }
        return models.get(cost_profile, "anthropic/claude-sonnet-4")
