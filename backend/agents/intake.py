"""Intake & Classification Agent - Step 1."""
import json
from typing import Any, Dict, List

from .base import BaseAgent


class IntakeAgent(BaseAgent):
    """Classifies project briefs and extracts key information."""
    
    name = "intake"
    description = "Intake & Classification Agent"
    step_number = 1
    
    # Keywords for project type detection
    PROJECT_TYPE_KEYWORDS = {
        "mobile_native_ios": ["ios", "iphone", "ipad", "swift", "swiftui", "app store", "native ios", "apple"],
        "mobile_cross_platform": ["react native", "flutter", "expo", "cross-platform mobile", "android and ios", "mobile app"],
        "mobile_pwa": ["pwa", "progressive web app", "offline-first", "installable web", "service worker"],
        "desktop_app": ["desktop app", "electron", "tauri", "pyqt", "windows app", "mac app", "cross-platform desktop"],
        "chrome_extension": ["chrome extension", "browser extension", "firefox addon", "browser plugin", "manifest v3"],
        "cli_tool": ["cli", "command line", "terminal", "command-line tool", "shell", "click", "typer"],
        "python_api": ["api", "rest api", "fastapi", "flask api", "backend api", "api endpoint"],
        "python_saas": ["saas", "software as a service", "subscription", "multi-tenant", "billing", "full-stack python"],
        "web_complex": ["dashboard", "admin panel", "e-commerce", "authentication", "database", "multi-page app", "web app"],
        "web_simple": ["landing page", "portfolio", "blog", "brochure", "static site", "simple website"],
    }
    
    SYSTEM_PROMPT = """You are the Intake & Classification Agent for an AI development agency.
    
Your job is to analyze project briefs and:
1. Classify the project type from the 10 supported types
2. Extract key requirements
3. Identify the target audience
4. Note any special requirements or constraints
5. Estimate project complexity

Project Type Definitions:
- web_simple: Landing pages, portfolios, small business sites, blogs (1-5 pages, no complex backend)
- web_complex: Multi-page apps with authentication, databases, APIs, dashboards, e-commerce
- mobile_native_ios: Native iOS apps using Swift/SwiftUI for iPhone/iPad
- mobile_cross_platform: Mobile apps using React Native (Expo) or Flutter for iOS and Android
- mobile_pwa: Progressive Web Apps with offline support, service workers, installable on mobile
- desktop_app: Desktop applications using Electron, Tauri, or PyQt for Windows/Mac/Linux
- chrome_extension: Chrome browser extensions with manifest v3
- cli_tool: Command-line tools using Python (Click/Typer) or Node (Commander)
- python_api: REST APIs using FastAPI or Flask
- python_saas: Full-stack Python SaaS apps (FastAPI + templates/HTMX + database)

Respond ONLY with valid JSON in this format:
{
    "project_type": "web_simple" | "web_complex" | "mobile_native_ios" | "mobile_cross_platform" | "mobile_pwa" | "desktop_app" | "chrome_extension" | "cli_tool" | "python_api" | "python_saas",
    "project_name": "suggested name for the project",
    "summary": "2-3 sentence summary of what will be built",
    "key_features": ["feature1", "feature2", ...],
    "target_audience": "description of target users",
    "complexity_score": 1-10,
    "platform_details": {
        "primary_platform": "iOS | Android | Web | Desktop | CLI",
        "secondary_platforms": ["list of other platforms if cross-platform"],
        "framework_preference": "suggested framework based on requirements"
    },
    "requires_backend": true/false,
    "requires_database": true/false,
    "requires_auth": true/false,
    "requires_deployment": true/false,
    "deployment_target": "app_store | play_store | web | desktop | npm | pypi | chrome_web_store",
    "special_requirements": ["any special notes"],
    "recommended_tech_stack": {
        "language": "Swift | TypeScript | Python | Dart",
        "framework": "recommended framework",
        "backend": "if needed",
        "database": "if needed",
        "deployment": "recommended deployment platform"
    },
    "estimated_development_hours": number,
    "revision_scope": "new_project" | "small_tweak" | "medium_feature" | "major_addition"
}"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the project brief and classify it."""
        brief = input_data.get("brief", "")
        cost_profile = input_data.get("cost_profile", "balanced")
        is_revision = input_data.get("is_revision", False)
        existing_project_type = input_data.get("existing_project_type")
        
        # Pre-analyze keywords for hints
        detected_types = self._detect_project_type_hints(brief)
        
        # Select model based on cost profile
        model = self._select_model(cost_profile)
        
        revision_context = ""
        if is_revision and existing_project_type:
            revision_context = f"""
NOTE: This is a REVISION request for an existing {existing_project_type} project.
Classify the revision_scope as:
- small_tweak: Minor UI changes, text updates, bug fixes
- medium_feature: New pages, components, or features within existing architecture
- major_addition: Significant new capabilities requiring architectural changes
"""
        
        type_hints = ""
        if detected_types:
            type_hints = f"\nDetected keywords suggest these project types: {', '.join(detected_types)}"
        
        prompt = f"""Analyze this project brief and classify it:

---
{brief}
---
{revision_context}{type_hints}

Provide your classification as JSON."""
        
        result = await self.call_llm(
            prompt=prompt,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.3,
        )
        
        # Parse the JSON response
        try:
            classification = json.loads(result["content"])
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                classification = json.loads(content[start:end])
            else:
                classification = {"error": "Failed to parse response", "raw": content}
        
        # Log the execution
        await self.log_execution(
            input_data=input_data,
            output_data=classification,
            model=model,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            cost=result["cost"],
            duration_ms=result["duration_ms"],
        )
        
        return {
            "classification": classification,
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
    
    def _detect_project_type_hints(self, brief: str) -> List[str]:
        """Detect potential project types from keywords in the brief."""
        brief_lower = brief.lower()
        detected = []
        
        for project_type, keywords in self.PROJECT_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in brief_lower:
                    detected.append(project_type)
                    break
        
        return detected
