"""Intake & Classification Agent - Step 1.

Phase 11A: Enhanced with real-time brief analysis for Smart Adaptive Intake System.
Phase 11B: Knowledge Base integration - query similar projects, estimate token budgets.
Phase 11D: Agent updates - use structured ProjectRequirements, load templates.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAgent

logger = logging.getLogger(__name__)


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

# Default token budgets by agent (can be refined from KB data)
DEFAULT_TOKEN_BUDGETS = {
    "intake": 2000,
    "research": 15000,
    "architect": 20000,
    "design_system": 10000,
    "asset_generation": 5000,
    "content_generation": 15000,
    "code_generation": 50000,
    "integration_wiring": 10000,
    "security": 5000,
    "seo": 5000,
    "accessibility": 5000,
    "qa_testing": 15000,
    "deployment": 5000,
    "delivery": 5000,
}


class IntakeAgent(BaseAgent):
    """Classifies project briefs and extracts key information.
    
    Phase 11 Enhancements:
    - Uses structured ProjectRequirements from frontend
    - Queries knowledge base for similar past projects
    - Attaches KB context to pipeline state
    - Estimates per-agent token budgets from past data
    - Loads template if template_id provided
    """
    
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
    "project_type": "web_simple" | "web_complex" | etc.,
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
        """Process the project brief and classify it.
        
        Phase 11 Enhanced:
        - Accepts structured ProjectRequirements
        - Queries KB for similar projects
        - Loads template if template_id provided
        - Estimates token budgets from past data
        """
        # Extract data from input (supports both legacy and structured formats)
        requirements = input_data.get("requirements", {})
        brief = requirements.get("brief") or input_data.get("brief", "")
        cost_profile = requirements.get("cost_profile") or input_data.get("cost_profile", "balanced")
        is_revision = input_data.get("is_revision", False)
        existing_project_type = input_data.get("existing_project_type")
        template_id = requirements.get("template_id") or input_data.get("template_id")
        
        # Phase 11B: Query knowledge base for similar projects
        kb_context = await self._query_knowledge_base(brief, requirements)
        
        # Phase 11: Load template if provided
        template_data = None
        if template_id:
            template_data = await self._load_template(template_id)
        
        # Phase 11: Estimate token budgets from KB data
        token_budgets = await self._estimate_token_budgets(
            project_type=requirements.get("project_type"),
            complexity=requirements.get("complexity_estimate", "medium"),
            kb_context=kb_context
        )
        
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
        
        # Include KB context if available
        kb_hint = ""
        if kb_context.get("similar_projects"):
            kb_hint = f"\n\nSimilar past projects found in knowledge base:\n"
            for proj in kb_context["similar_projects"][:3]:
                kb_hint += f"- {proj.get('title', 'Untitled')}: {proj.get('summary', '')[:100]}...\n"
        
        # Include template context if loaded
        template_hint = ""
        if template_data:
            template_hint = f"\n\nUsing template: {template_data.get('name', 'Unknown')}\n"
            template_hint += f"Template type: {template_data.get('project_type', 'Unknown')}\n"
            if template_data.get("pages"):
                template_hint += f"Template pages: {', '.join(template_data['pages'][:5])}\n"
        
        prompt = f"""Analyze this project brief and classify it:

---
{brief}
---
{revision_context}{type_hints}{kb_hint}{template_hint}

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
            # Phase 11 additions
            "kb_context": kb_context,
            "template_data": template_data,
            "token_budgets": token_budgets,
            "structured_requirements": requirements if requirements else None,
        }
    
    async def _query_knowledge_base(self, brief: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Query KB for similar past projects and relevant knowledge.
        
        Phase 11B: Knowledge Base integration.
        """
        try:
            from ..knowledge import query_knowledge, KnowledgeEntryType
            from ..models import get_db
            
            db = next(get_db())
            
            # Query for similar projects
            project_type = requirements.get("project_type")
            industry = requirements.get("industry")
            
            similar = await query_knowledge(
                db=db,
                query_text=brief,
                entry_types=[KnowledgeEntryType.PROJECT_SUMMARY],
                project_type=project_type,
                industry=industry,
                min_quality_score=0.7,
                limit=5,
            )
            
            # Query for relevant architecture decisions
            arch_decisions = await query_knowledge(
                db=db,
                query_text=brief,
                entry_types=[KnowledgeEntryType.ARCHITECTURE_DECISION],
                project_type=project_type,
                limit=3,
            )
            
            return {
                "similar_projects": [
                    {
                        "id": r.entry.id,
                        "title": r.entry.title,
                        "summary": r.entry.content[:200],
                        "similarity": r.similarity_score,
                        "quality_score": r.entry.quality_score,
                    }
                    for r in similar
                ],
                "architecture_decisions": [
                    {
                        "id": r.entry.id,
                        "title": r.entry.title,
                        "content": r.entry.content[:300],
                        "similarity": r.similarity_score,
                    }
                    for r in arch_decisions
                ],
            }
        except Exception as e:
            logger.warning(f"KB query failed: {e}")
            return {"similar_projects": [], "architecture_decisions": []}
    
    async def _load_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Load project template from database.
        
        Phase 11: Template support.
        """
        try:
            from ..models import get_db
            from ..models.project_template import ProjectTemplate
            
            db = next(get_db())
            template = db.query(ProjectTemplate).filter(
                ProjectTemplate.id == template_id
            ).first()
            
            if template:
                return {
                    "id": template.id,
                    "name": template.name,
                    "project_type": template.project_type,
                    "pages": template.template_data.get("pages", []),
                    "features": template.template_data.get("features", []),
                    "tech_stack": template.template_data.get("tech_stack", {}),
                    "design_tokens": template.template_data.get("design_tokens", {}),
                    "architecture": template.template_data.get("architecture", {}),
                }
            return None
        except Exception as e:
            logger.warning(f"Template load failed: {e}")
            return None
    
    async def _estimate_token_budgets(
        self, 
        project_type: Optional[str], 
        complexity: str,
        kb_context: Dict[str, Any]
    ) -> Dict[str, int]:
        """Estimate per-agent token budgets from past data.
        
        Phase 11: Token budget estimation.
        """
        budgets = DEFAULT_TOKEN_BUDGETS.copy()
        
        # Adjust based on complexity
        multipliers = {"simple": 0.7, "medium": 1.0, "complex": 1.5}
        multiplier = multipliers.get(complexity, 1.0)
        
        for agent in budgets:
            budgets[agent] = int(budgets[agent] * multiplier)
        
        # Try to get actual data from KB similar projects
        try:
            similar_projects = kb_context.get("similar_projects", [])
            if similar_projects:
                # In a real implementation, we'd query agent logs for these projects
                # and compute average token usage
                pass
        except Exception as e:
            logger.debug(f"Token budget estimation from KB failed: {e}")
        
        return budgets
    
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
        word_count = len(brief.split())
        feature_count = len(features)
        
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
        
        if detected_type in ["web_simple", "web_complex", "python_saas"]:
            pages.append("Home")
            if "about" in brief_lower:
                pages.append("About")
            if "contact" in brief_lower:
                pages.append("Contact")
        
        if "authentication" in features:
            pages.extend(["Login", "Register", "Profile"])
        if "dashboard" in features:
            pages.append("Dashboard")
        if "payments" in features:
            pages.extend(["Pricing", "Checkout"])
        
        if detected_type in ["mobile_native_ios", "mobile_cross_platform", "mobile_pwa"]:
            if not pages:
                pages = ["Home", "Settings"]
            if "authentication" in features and "Login" not in pages:
                pages.extend(["Login", "Profile"])
        
        return pages[:8]
    
    async def analyze_brief(self, brief: str) -> Dict[str, Any]:
        """
        Phase 11A: Real-time brief analysis for the Smart Adaptive Intake form.
        
        Uses fast/cheap model (deepseek) for quick response times.
        Returns auto-detected values without fully classifying the project.
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
        
        detected_types = self._detect_project_type_hints(brief)
        detected_type = detected_types[0] if detected_types else "web_simple"
        confidence = 0.9 if detected_types else 0.5
        
        detected_industry = self._detect_industry(brief)
        detected_features = self._detect_features(brief)
        complexity = self._estimate_complexity(brief, detected_type, detected_features)
        suggested_pages = self._suggest_pages(detected_type, detected_features, brief)
        
        cost_estimate = COST_ESTIMATES.get(detected_type, COST_ESTIMATES["web_simple"])
        
        warnings = []
        if len(brief.split()) < 20:
            warnings.append("Brief is quite short. Add more details for better results.")
        if not detected_types:
            warnings.append("Could not confidently detect project type. Please select manually.")
        if complexity == "complex" and "authentication" not in detected_features:
            warnings.append("Complex project detected. Consider adding authentication.")
        
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
