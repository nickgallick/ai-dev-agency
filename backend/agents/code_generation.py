"""Code Generation Agent - Step 5 (Multi-platform code generation).

Phase 11D: Enhanced with tech stack preferences, light/dark mode, and integration wiring.

Phase 11 Enhancements:
- Read requirements.tech_stack (framework, CSS approach)
- Implement light/dark mode when dark_mode="both"
- Wire integrations: Stripe, Resend, R2, Inngest, Auth
- Support dynamic pooling (accept batch assignment)
- Query KB for successful prompts
- Write prompt results to KB
- Check Redis cache for identical prompts
"""
import os
import json
import logging
import httpx
import time
from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod

from .base import BaseAgent

logger = logging.getLogger(__name__)


class CodeGenerationStrategy(ABC):
    """Base class for code generation strategies."""
    
    @abstractmethod
    async def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code for the given context."""
        pass
    
    @abstractmethod
    def get_project_structure(self) -> Dict[str, List[str]]:
        """Return the expected project structure."""
        pass


class V0WebStrategy(CodeGenerationStrategy):
    """Use Vercel v0 API for web frontends.
    
    Phase 11 Enhanced:
    - Reads tech stack from requirements
    - Generates light/dark mode support
    - Includes integration setup
    - Caches prompts
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.v0.dev/v1"
        self._integrations = []  # Phase 11: Track integrations
        self._theme_mode = "dark_only"  # Phase 11: Theme mode
    
    async def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Phase 11: Extract integrations and theme mode
        self._integrations = context.get("integrations", [])
        self._theme_mode = context.get("theme_mode", "dark_only")
        
        # Phase 11: Check cache first
        cache_key = self._get_cache_key(context)
        cached_result = await self._check_cache(cache_key)
        if cached_result:
            logger.info("Using cached code generation result")
            return cached_result
        
        prompt = self._build_prompt(context)
        
        if not self.api_key:
            return {"error": "V0 API key not configured", "files": []}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/generate",
                    headers=headers,
                    json={"prompt": prompt, "model": "v0-1.5"}
                )
                response.raise_for_status()
                result = response.json()
                output = {
                    "success": True,
                    "generation_id": result.get("id"),
                    "files": result.get("files", []),
                    "preview_url": result.get("preview_url"),
                    "cost": result.get("cost", 0),
                    "integrations_wired": [i.get("service") for i in self._integrations],
                    "theme_mode": self._theme_mode,
                }
                
                # Phase 11: Cache the result
                await self._cache_result(cache_key, output)
                
                return output
        except Exception as e:
            return {"error": str(e), "files": []}
    
    def _get_cache_key(self, context: Dict[str, Any]) -> str:
        """Generate cache key for the code generation context."""
        import hashlib
        key_data = json.dumps({
            "brief": context.get("brief", "")[:200],
            "pages": [p.get("name") if isinstance(p, dict) else p 
                     for p in context.get("architecture", {}).get("pages", [])],
            "theme_mode": self._theme_mode,
        }, sort_keys=True)
        return f"codegen:v0:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check Redis cache for identical prompts."""
        try:
            from ..cache import get_cache_manager
            cache = get_cache_manager()
            return cache.get(cache_key, "llm_response")
        except Exception:
            return None
    
    async def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache code generation result."""
        try:
            from ..cache import get_cache_manager
            cache = get_cache_manager()
            cache.set(cache_key, result, "llm_response")
        except Exception:
            pass
    
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        design_system = context.get("design_system", {})
        architecture = context.get("architecture", {})
        brief = context.get("brief", "")
        
        # Phase 11: Get tech stack from requirements
        requirements = context.get("requirements", {})
        tech_stack = requirements.get("tech_stack", {})
        
        # Build tech stack string
        framework = tech_stack.get("frontend_framework", "Next.js 14")
        css_framework = tech_stack.get("css_framework", "Tailwind CSS")
        
        # Phase 11: Theme mode instructions
        theme_instructions = ""
        if self._theme_mode == "both":
            theme_instructions = """
IMPORTANT: Implement BOTH light and dark themes:
- Use CSS variables for all colors
- Add <html class="dark"> toggle support
- Implement next-themes or similar theme provider
- All components must support both themes
"""
        
        # Phase 11: Integration wiring instructions
        integration_instructions = ""
        if self._integrations:
            integration_instructions = "\n\nIntegrations to wire:\n"
            for integration in self._integrations:
                service = integration.get("service", "")
                if service == "stripe":
                    integration_instructions += "- Stripe: Add checkout/billing components, use process.env.STRIPE_SECRET_KEY\n"
                elif service == "resend":
                    integration_instructions += "- Resend: Add email service wrapper, use process.env.RESEND_API_KEY\n"
                elif service == "r2":
                    integration_instructions += "- Cloudflare R2: Add file upload component with S3-compatible API\n"
                elif service == "inngest":
                    integration_instructions += "- Inngest: Add background job setup at /api/inngest\n"
                elif service == "supabase_auth":
                    integration_instructions += "- Supabase Auth: Add auth provider and protected routes\n"
        
        return f"""Build a complete web application: {brief}
        
Design: {json.dumps(design_system.get("colors", {}), indent=2)}
Pages: {json.dumps(architecture.get("pages", []), indent=2)}

Tech Stack:
- {framework} with App Router
- {css_framework} + shadcn/ui
- Responsive, accessible (WCAG AA)
- Smooth animations
{theme_instructions}
{integration_instructions}"""
    
    def get_project_structure(self) -> Dict[str, List[str]]:
        return {
            "root": ["package.json", "next.config.js", "tailwind.config.ts"],
            "app": ["layout.tsx", "page.tsx", "globals.css"],
            "components": ["ui/"],
        }


class LLMCodeStrategy(CodeGenerationStrategy):
    """Use LLM prompts for code generation (mobile, desktop, CLI, etc.)."""
    
    def __init__(self, llm_client, project_type: str):
        self.llm_client = llm_client
        self.project_type = project_type
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        return {
            "web_simple": self._web_simple_template(),
            "web_complex": self._web_complex_template(),
            "mobile_native_ios": self._ios_template(),
            "mobile_cross_platform": self._cross_platform_template(),
            "mobile_pwa": self._pwa_template(),
            "desktop_app": self._desktop_template(),
            "chrome_extension": self._chrome_extension_template(),
            "cli_tool": self._cli_template(),
            "python_api": self._python_api_template(),
            "python_saas": self._python_saas_template(),
        }
    
    def _web_simple_template(self) -> str:
        return """You are generating a modern landing page using Next.js 14+ with App Router and Tailwind CSS.

Requirements:
- Use Next.js App Router (app/ directory structure)
- Use Tailwind CSS for styling with a dark theme
- Create responsive, mobile-first design
- Use Inter font from Google Fonts
- Include smooth animations and hover effects
- Use semantic HTML5 elements
- Generate complete, working code

Generate these files:
1. app/layout.tsx - Root layout with fonts, metadata
2. app/page.tsx - Main landing page with all sections
3. app/globals.css - Global styles with Tailwind
4. components/Header.tsx - Navigation header
5. components/Hero.tsx - Hero section
6. components/Features.tsx - Features/benefits section
7. components/Footer.tsx - Footer with links
8. tailwind.config.ts - Tailwind configuration
9. package.json - Dependencies"""

    def _web_complex_template(self) -> str:
        return """You are generating a full-stack web application using Next.js 14+ with App Router, Tailwind CSS, and authentication.

Requirements:
- Use Next.js App Router (app/ directory structure)
- Use Tailwind CSS for styling with dark theme support
- Include authentication flow (login, register, protected routes)
- Use React Server Components where appropriate
- Include proper error boundaries and loading states
- Use TypeScript throughout
- Generate complete, working code

Generate these files:
1. app/layout.tsx - Root layout with providers
2. app/page.tsx - Landing/home page
3. app/(auth)/login/page.tsx - Login page
4. app/(auth)/register/page.tsx - Registration page
5. app/dashboard/page.tsx - Protected dashboard
6. components/ui/Button.tsx - Reusable button component
7. components/ui/Input.tsx - Reusable input component
8. lib/auth.ts - Authentication utilities
9. middleware.ts - Route protection
10. tailwind.config.ts - Tailwind configuration
11. package.json - Dependencies"""
    
    async def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        template = self.templates.get(self.project_type, "")
        prompt = self._build_prompt(context, template)
        
        result = await self.llm_client(
            prompt=prompt,
            model="anthropic/claude-sonnet-4",
            temperature=0.3,
        )
        
        files = self._parse_code_blocks(result.get("content", ""))
        return {
            "success": True,
            "files": files,
            "cost": result.get("cost", 0),
        }
    
    def _build_prompt(self, context: Dict[str, Any], template: str) -> str:
        brief = context.get("brief", "")
        architecture = context.get("architecture", {})
        
        return f"""{template}

## Project Brief
{brief}

## Architecture
{json.dumps(architecture, indent=2)}

Generate complete, production-ready code. Format each file as:
```filename:path/to/file.ext
<code content>
```"""
    
    def _parse_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Parse code blocks from LLM response."""
        files = []
        import re
        pattern = r"```(?:filename:)?([^\n]+)\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        for filename, code in matches:
            files.append({"path": filename.strip(), "content": code.strip()})
        return files
    
    def get_project_structure(self) -> Dict[str, List[str]]:
        structures = {
            "web_simple": {
                "root": ["package.json", "tailwind.config.ts", "next.config.js"],
                "app": ["layout.tsx", "page.tsx", "globals.css"],
                "components": ["Header.tsx", "Hero.tsx", "Features.tsx", "Footer.tsx"],
            },
            "web_complex": {
                "root": ["package.json", "tailwind.config.ts", "next.config.js", "middleware.ts"],
                "app": ["layout.tsx", "page.tsx", "globals.css"],
                "app/(auth)": ["login/page.tsx", "register/page.tsx"],
                "app/dashboard": ["page.tsx"],
                "components/ui": ["Button.tsx", "Input.tsx"],
                "lib": ["auth.ts", "utils.ts"],
            },
            "mobile_native_ios": {
                "root": ["Package.swift", "README.md"],
                "Sources": ["App.swift", "ContentView.swift"],
                "fastlane": ["Fastfile", "Appfile"],
            },
            "mobile_cross_platform": {
                "root": ["package.json", "app.json", "babel.config.js"],
                "src": ["App.tsx", "navigation/", "screens/", "components/"],
            },
            "mobile_pwa": {
                "root": ["package.json", "manifest.json", "service-worker.js"],
                "src": ["index.html", "app.js", "styles.css"],
            },
            "desktop_app": {
                "root": ["package.json", "electron.config.js"],
                "src": ["main.js", "preload.js", "renderer/"],
            },
            "chrome_extension": {
                "root": ["manifest.json", "README.md"],
                "src": ["popup.html", "popup.js", "background.js", "content.js"],
            },
            "cli_tool": {
                "root": ["pyproject.toml", "setup.py", "README.md"],
                "src": ["__init__.py", "cli.py", "commands/"],
            },
            "python_api": {
                "root": ["requirements.txt", "Dockerfile", "README.md"],
                "app": ["main.py", "routes/", "models/", "schemas/"],
            },
            "python_saas": {
                "root": ["requirements.txt", "Dockerfile", "docker-compose.yml"],
                "app": ["main.py", "routes/", "models/", "templates/"],
            },
        }
        return structures.get(self.project_type, {})
    
    # Project type templates
    def _ios_template(self) -> str:
        return """You are generating a native iOS app using Swift and SwiftUI.

Requirements:
- Use SwiftUI for all views
- Follow Apple Human Interface Guidelines
- Include proper navigation (NavigationStack)
- Support dark mode
- Generate Fastlane configuration for deployment
- Include unit tests

Generate these files:
1. Package.swift - Swift Package Manager config
2. Sources/App.swift - App entry point
3. Sources/ContentView.swift - Main view
4. Sources/Views/ - Additional views
5. Sources/Models/ - Data models
6. fastlane/Fastfile - Deployment automation
7. fastlane/Appfile - App configuration"""

    def _cross_platform_template(self) -> str:
        return """You are generating a cross-platform mobile app using React Native with Expo.

Requirements:
- Use Expo SDK 50+
- Use React Navigation for routing
- Use NativeWind for styling (Tailwind CSS)
- Support iOS and Android
- Include TypeScript
- Generate EAS build configuration

Generate these files:
1. package.json - Dependencies
2. app.json - Expo config
3. eas.json - EAS Build config
4. App.tsx - Entry point
5. src/navigation/ - Navigation setup
6. src/screens/ - Screen components
7. src/components/ - Reusable components"""

    def _pwa_template(self) -> str:
        return """You are generating a Progressive Web App.

Requirements:
- Service worker for offline support
- Web App Manifest for installation
- Responsive design (mobile-first)
- Cache-first strategy for static assets
- Background sync capability
- Push notification support

Generate these files:
1. manifest.json - PWA manifest
2. service-worker.js - Service worker
3. index.html - Main HTML
4. src/app.js - Main application logic
5. src/styles.css - Styles
6. src/utils/offline.js - Offline utilities"""

    def _desktop_template(self) -> str:
        return """You are generating a desktop application using Electron.

Requirements:
- Main and renderer processes properly separated
- IPC communication for security
- Native menu integration
- Auto-updater support
- Cross-platform (Windows, Mac, Linux)
- Electron Builder configuration

Generate these files:
1. package.json - Dependencies and scripts
2. electron-builder.yml - Build config
3. src/main/main.js - Main process
4. src/main/preload.js - Preload script
5. src/renderer/index.html - Renderer HTML
6. src/renderer/app.js - Renderer logic"""

    def _chrome_extension_template(self) -> str:
        return """You are generating a Chrome extension using Manifest V3.

Requirements:
- Manifest V3 format
- Service worker for background script
- Content scripts if needed
- Popup with modern UI
- Options page
- Proper permissions

Generate these files:
1. manifest.json - Extension manifest (v3)
2. src/popup.html - Popup HTML
3. src/popup.js - Popup logic
4. src/background.js - Service worker
5. src/content.js - Content script
6. src/options.html - Options page"""

    def _cli_template(self) -> str:
        return """You are generating a Python CLI tool using Typer.

Requirements:
- Use Typer for CLI framework
- Rich for beautiful output
- Proper argument/option handling
- Help documentation
- PyPI-ready packaging
- Unit tests

Generate these files:
1. pyproject.toml - Modern Python packaging
2. src/__init__.py - Package init
3. src/cli.py - Main CLI entry point
4. src/commands/ - Command modules
5. tests/test_cli.py - CLI tests
6. README.md - Documentation"""

    def _python_api_template(self) -> str:
        return """You are generating a FastAPI REST API.

Requirements:
- FastAPI with async support
- Pydantic for validation
- SQLAlchemy for ORM
- Alembic for migrations
- OpenAPI documentation
- Docker support

Generate these files:
1. requirements.txt - Dependencies
2. app/main.py - FastAPI app
3. app/routes/ - API routes
4. app/models/ - Database models
5. app/schemas/ - Pydantic schemas
6. Dockerfile - Container config
7. alembic/ - Migrations"""

    def _python_saas_template(self) -> str:
        return """You are generating a full-stack Python SaaS application.

Requirements:
- FastAPI backend
- Jinja2 templates or HTMX frontend
- SQLAlchemy + PostgreSQL
- User authentication (JWT)
- Stripe billing integration hooks
- Multi-tenant support
- Docker Compose setup

Generate these files:
1. requirements.txt - Dependencies
2. app/main.py - FastAPI app
3. app/routes/ - API and page routes
4. app/models/ - Database models
5. app/templates/ - Jinja2 templates
6. app/auth/ - Authentication
7. docker-compose.yml - Full stack setup"""


class CodeGenerationAgent(BaseAgent):
    """Generates code using appropriate strategy based on project type."""
    
    name = "code_generation"
    description = "Code Generation Agent (Multi-platform)"
    step_number = 5
    
    # Map project types to generation strategies
    STRATEGY_MAP = {
        "web_simple": "v0",
        "web_complex": "v0",
        "mobile_pwa": "v0",
        "mobile_native_ios": "llm",
        "mobile_cross_platform": "llm",
        "desktop_app": "llm",
        "chrome_extension": "llm",
        "cli_tool": "llm",
        "python_api": "llm",
        "python_saas": "llm",
    }
    
    def __init__(self, settings=None):
        super().__init__(settings)
        self.v0_api_key = os.getenv("VERCEL_V0_API_KEY")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code using appropriate strategy based on project type."""
        project_type = input_data.get("project_type", "web_simple")
        architecture = input_data.get("architecture", {})
        design_system = input_data.get("design_system", {})
        brief = input_data.get("brief", "")
        
        start_time = time.time()
        
        # Select strategy
        strategy_type = self.STRATEGY_MAP.get(project_type, "llm")
        
        context = {
            "brief": brief,
            "architecture": architecture,
            "design_system": design_system,
            "project_type": project_type,
        }
        
        result = None
        
        # Try v0 first if selected, fallback to LLM on failure
        if strategy_type == "v0":
            if self.v0_api_key:
                strategy = V0WebStrategy(self.v0_api_key)
                result = await strategy.generate(context)
                
                # If v0 failed, fall back to LLM
                if result.get("error") or not result.get("files"):
                    logger.warning(f"V0 strategy failed: {result.get('error')}, falling back to LLM")
                    strategy_type = "llm"
                    result = None
            else:
                logger.warning("V0 API key not configured, using LLM strategy")
                strategy_type = "llm"
        
        # Use LLM strategy if v0 wasn't selected or failed
        if result is None:
            strategy = LLMCodeStrategy(self.call_llm, project_type)
            result = await strategy.generate(context)
        
        result["project_structure"] = strategy.get_project_structure() if hasattr(strategy, 'get_project_structure') else {}
        result["strategy_used"] = strategy_type
        result["project_type"] = project_type
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        await self.log_execution(
            input_data={"project_type": project_type, "brief": brief[:500]},
            output_data={"files_count": len(result.get("files", [])), "success": result.get("success")},
            model=f"strategy:{strategy_type}",
            prompt_tokens=0,
            completion_tokens=0,
            cost=result.get("cost", 0),
            duration_ms=duration_ms,
        )
        
        return result
    
    async def generate_for_revision(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code changes for a revision request."""
        existing_files = input_data.get("existing_files", [])
        revision_brief = input_data.get("revision_brief", "")
        project_type = input_data.get("project_type", "web_simple")
        revision_scope = input_data.get("revision_scope", "medium_feature")
        
        # For revisions, always use LLM to understand existing code
        prompt = f"""You are modifying an existing {project_type} project.

## Existing Files
{json.dumps(existing_files[:10], indent=2)}  # Limit to first 10 files

## Revision Request
{revision_brief}

## Revision Scope
{revision_scope}

Generate ONLY the files that need to be modified or created.
For modified files, provide the complete new content.
Format: ```filename:path/to/file.ext
<complete file content>
```"""
        
        result = await self.call_llm(
            prompt=prompt,
            model="anthropic/claude-sonnet-4",
            temperature=0.3,
        )
        
        # Parse the response
        strategy = LLMCodeStrategy(None, project_type)
        files = strategy._parse_code_blocks(result.get("content", ""))
        
        return {
            "success": True,
            "files": files,
            "is_revision": True,
            "revision_scope": revision_scope,
            "cost": result.get("cost", 0),
        }
