"""Intake & Classification Agent - Step 1.

Phase 11A: Enhanced with real-time brief analysis for Smart Adaptive Intake System.
"""
import json
from typing import Any, Dict, List, Optional

from .base import BaseAgent


# Cost estimates by project type and profile
COST_ESTIMATES = {
    "web_simple": {"budget": "$1-3", "balanced": "$5-10", "premium": "$15-30"},
    "web_complex": {"budget": "$3-8", "balanced": "$10-20", "premium": "$30-60"},
    "mobile_native_ios": {"budget": "$4-10", "balanced": "$12-25", "premium": "$40-80"},
    "mobile_cross_platform": {"budget": "$3-8", "balanced": "$10-20", "premium": "$35-70"},
    "mobile_pwa": {"budget": "$2-5", "balanced": "$6-12", "premium": "$20-40"},
    "desktop_app": {"budget": "$3-8", "balanced": "$8-18", "premium": "$30-60"},
    "chrome_extension": {"budget": "$1-3", "balanced": "$4-8", "premium": "$12-25"},
    "cli_tool": {"budget": "$0.5-2", "balanced": "$2-5", "premium": "$8-15"},
    "python_api": {"budget": "$1-4", "balanced": "$5-12", "premium": "$15-35"},
    "python_saas": {"budget": "$4-12", "balanced": "$15-30", "premium": "$50-100"},
}


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
    
    # Industry keywords for detection
    INDUSTRY_KEYWORDS = {
        "healthcare": ["healthcare", "medical", "hospital", "clinic", "patient", "doctor", "health"],
        "fintech": ["fintech", "banking", "finance", "payment", "trading", "investment", "crypto", "wallet"],
        "ecommerce": ["e-commerce", "ecommerce", "shop", "store", "cart", "product", "checkout", "retail"],
        "education": ["education", "learning", "course", "student", "school", "university", "training"],
        "real_estate": ["real estate", "property", "listing", "rental", "apartment", "house"],
        "food_delivery": ["food", "restaurant", "delivery", "menu", "order", "catering"],
        "travel": ["travel", "hotel", "booking", "flight", "vacation", "tour"],
        "fitness": ["fitness", "gym", "workout", "exercise", "health", "yoga"],
        "social": ["social", "community", "network", "chat", "messaging", "forum"],
        "productivity": ["productivity", "task", "project management", "todo", "calendar", "scheduling"],
    }
    
    # Feature keywords for suggestions
    FEATURE_KEYWORDS = {
        "authentication": ["login", "auth", "user", "account", "register", "sign up", "sign in"],
        "dashboard": ["dashboard", "admin", "analytics", "metrics", "reports"],
        "payments": ["payment", "stripe", "billing", "subscription", "checkout", "pricing"],
        "notifications": ["notification", "alert", "email", "push", "reminder"],
        "search": ["search", "filter", "find", "query"],
        "file_upload": ["upload", "file", "image", "attachment", "media"],
        "chat": ["chat", "message", "conversation", "real-time"],
        "api": ["api", "integration", "webhook", "endpoint"],
        "social_login": ["google login", "oauth", "social login", "github login"],
        "dark_mode": ["dark mode", "theme", "light mode"],
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
    
    def _detect_industry(self, brief: str) -> Optional[str]:
        """Detect industry from keywords in the brief."""
        brief_lower = brief.lower()
        
        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in brief_lower:
                    return industry
        
        return None
    
    def _detect_features(self, brief: str) -> List[str]:
        """Detect suggested features from keywords in the brief."""
        brief_lower = brief.lower()
        features = []
        
        for feature, keywords in self.FEATURE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in brief_lower:
                    features.append(feature)
                    break
        
        return features
    
    def _estimate_complexity(self, brief: str, detected_type: Optional[str], features: List[str]) -> str:
        """Estimate project complexity based on brief analysis."""
        # Simple heuristics
        word_count = len(brief.split())
        feature_count = len(features)
        
        # Complex types
        complex_types = ["python_saas", "web_complex", "mobile_native_ios", "desktop_app"]
        
        if detected_type in complex_types or feature_count >= 4 or word_count > 200:
            return "complex"
        elif feature_count >= 2 or word_count > 80:
            return "medium"
        else:
            return "simple"
    
    def _suggest_pages(self, detected_type: Optional[str], features: List[str], brief: str) -> List[str]:
        """Suggest pages/screens based on project type and features."""
        pages = []
        brief_lower = brief.lower()
        
        # Base pages by type
        if detected_type in ["web_simple", "web_complex", "python_saas"]:
            pages.append("Home")
            if "about" in brief_lower:
                pages.append("About")
            if "contact" in brief_lower:
                pages.append("Contact")
        
        # Feature-based pages
        if "authentication" in features:
            pages.extend(["Login", "Register", "Profile"])
        if "dashboard" in features:
            pages.append("Dashboard")
        if "payments" in features:
            pages.extend(["Pricing", "Checkout"])
        
        # Mobile-specific screens
        if detected_type in ["mobile_native_ios", "mobile_cross_platform", "mobile_pwa"]:
            if not pages:
                pages = ["Home", "Settings"]
            if "authentication" in features and "Login" not in pages:
                pages.extend(["Login", "Profile"])
        
        return pages[:8]  # Limit to 8 suggestions
    
    async def analyze_brief(self, brief: str) -> Dict[str, Any]:
        """
        Phase 11A: Real-time brief analysis for the Smart Adaptive Intake form.
        
        Uses fast/cheap model (deepseek) for quick response times.
        Returns auto-detected values without fully classifying the project.
        
        Args:
            brief: The project description text to analyze
            
        Returns:
            Dict with detected_project_type, confidence, suggested_features,
            suggested_pages, detected_industry, complexity_estimate, cost_estimate
        """
        if not brief or len(brief.strip()) < 10:
            return {
                "detected_project_type": None,
                "confidence": 0.0,
                "suggested_features": [],
                "suggested_pages": [],
                "detected_industry": None,
                "complexity_estimate": "simple",
                "cost_estimate": COST_ESTIMATES.get("web_simple", {}),
                "warnings": []
            }
        
        # Keyword-based detection (fast, no LLM call)
        detected_types = self._detect_project_type_hints(brief)
        detected_type = detected_types[0] if detected_types else "web_simple"
        confidence = 0.9 if detected_types else 0.5
        
        detected_industry = self._detect_industry(brief)
        detected_features = self._detect_features(brief)
        complexity = self._estimate_complexity(brief, detected_type, detected_features)
        suggested_pages = self._suggest_pages(detected_type, detected_features, brief)
        
        # Get cost estimates for detected type
        cost_estimate = COST_ESTIMATES.get(detected_type, COST_ESTIMATES["web_simple"])
        
        # Generate warnings
        warnings = []
        if len(brief.split()) < 20:
            warnings.append("Brief is quite short. Add more details for better results.")
        if not detected_types:
            warnings.append("Could not confidently detect project type. Please select manually.")
        if complexity == "complex" and "authentication" not in detected_features:
            warnings.append("Complex project detected. Consider adding authentication.")
        
        # For longer briefs, optionally use LLM for better suggestions
        # (disabled by default to keep it fast)
        use_llm_enhancement = False
        if use_llm_enhancement and len(brief.split()) > 50:
            try:
                enhanced = await self._llm_enhance_analysis(brief, detected_type, detected_features)
                if enhanced.get("suggested_features"):
                    detected_features = list(set(detected_features + enhanced["suggested_features"]))
                if enhanced.get("suggested_pages"):
                    suggested_pages = list(set(suggested_pages + enhanced["suggested_pages"]))
            except Exception:
                pass  # Silently fail, use keyword-based results
        
        return {
            "detected_project_type": detected_type,
            "confidence": confidence,
            "suggested_features": detected_features,
            "suggested_pages": suggested_pages,
            "detected_industry": detected_industry,
            "complexity_estimate": complexity,
            "cost_estimate": cost_estimate,
            "warnings": warnings
        }
    
    async def _llm_enhance_analysis(
        self, 
        brief: str, 
        detected_type: str, 
        detected_features: List[str]
    ) -> Dict[str, Any]:
        """
        Optional LLM-based enhancement for brief analysis.
        Uses fast/cheap model for quick responses.
        """
        prompt = f"""Analyze this project brief and suggest additional features and pages.
Current detected type: {detected_type}
Current detected features: {', '.join(detected_features) if detected_features else 'none'}

Brief:
{brief}

Respond with JSON only:
{{
    "suggested_features": ["feature1", "feature2"],
    "suggested_pages": ["Page1", "Page2"]
}}"""
        
        result = await self.call_llm(
            prompt=prompt,
            model="deepseek/deepseek-chat",  # Fast, cheap model
            temperature=0.3,
            max_tokens=200,
        )
        
        try:
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                return json.loads(content[start:end])
        except Exception:
            pass
        
        return {}
