"""Project brief wizard: completeness scoring and prompt enhancement.

Bad input cascades through all 20 agents. This module catches gaps
before any tokens are spent by:

1. **Completeness scoring** — Checks if the brief covers all dimensions
   needed for a quality build (purpose, audience, features, design, etc.)
2. **Prompt enhancement** — Generates an improved version of the brief
   with missing details filled in based on detected project type
3. **Gap detection** — Identifies specific missing elements the user
   should add

All operations are local (no LLM calls) for instant response.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ── Completeness dimensions ──────────────────────────────────────────────

# Each dimension has keywords that indicate it's been addressed in the brief

_DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "purpose": [
        "build", "create", "make", "develop", "want", "need",
        "app", "website", "platform", "tool", "system", "service",
    ],
    "audience": [
        "user", "customer", "client", "visitor", "admin", "team",
        "employee", "student", "patient", "audience", "target",
        "people", "business", "consumer", "b2b", "b2c",
    ],
    "features": [
        "login", "auth", "dashboard", "search", "filter", "upload",
        "payment", "checkout", "cart", "notification", "message",
        "chat", "profile", "settings", "analytics", "report",
        "form", "list", "table", "gallery", "map", "calendar",
        "api", "integration", "webhook", "export", "import",
    ],
    "design": [
        "design", "style", "theme", "color", "dark", "light",
        "minimal", "modern", "clean", "professional", "playful",
        "responsive", "mobile", "layout", "ui", "ux", "animation",
        "glassmorphism", "gradient", "font", "typography",
    ],
    "tech_stack": [
        "react", "vue", "angular", "next", "nuxt", "svelte",
        "tailwind", "bootstrap", "node", "express", "django",
        "flask", "fastapi", "postgres", "mysql", "mongo",
        "firebase", "supabase", "aws", "vercel", "docker",
        "typescript", "python", "javascript", "swift", "kotlin",
    ],
    "data": [
        "database", "data", "store", "save", "persist", "model",
        "schema", "table", "collection", "record", "field",
        "crud", "query", "cache", "redis", "storage",
    ],
    "pages": [
        "page", "screen", "view", "route", "home", "about",
        "contact", "pricing", "landing", "blog", "faq",
        "onboarding", "wizard", "step", "flow",
    ],
    "scale": [
        "scale", "performance", "fast", "concurrent", "real-time",
        "large", "enterprise", "production", "deploy", "hosting",
        "cdn", "cache", "load", "traffic",
    ],
}

# Weights for each dimension (sum to ~1.0)
_DIMENSION_WEIGHTS: Dict[str, float] = {
    "purpose": 0.25,    # Most important — what are we building?
    "features": 0.20,   # What does it do?
    "audience": 0.12,   # Who is it for?
    "pages": 0.12,      # What screens/routes?
    "design": 0.10,     # How should it look?
    "tech_stack": 0.08, # What tech to use?
    "data": 0.08,       # Data model needs?
    "scale": 0.05,      # Scale requirements?
}

# Per project type, which dimensions matter more
_TYPE_DIMENSION_BOOSTS: Dict[str, Dict[str, float]] = {
    "web_simple": {"pages": 0.20, "design": 0.15, "features": 0.10},
    "web_complex": {"features": 0.25, "data": 0.15, "audience": 0.15},
    "python_saas": {"features": 0.25, "data": 0.20, "audience": 0.15},
    "mobile_native_ios": {"features": 0.20, "design": 0.15, "audience": 0.15},
    "mobile_cross_platform": {"features": 0.20, "design": 0.15},
    "python_api": {"data": 0.25, "features": 0.20, "scale": 0.15},
    "cli_tool": {"features": 0.25, "purpose": 0.30},
    "chrome_extension": {"features": 0.25, "purpose": 0.25},
    "desktop_app": {"features": 0.20, "design": 0.15},
}


# ── Data classes ─────────────────────────────────────────────────────────

@dataclass
class BriefScore:
    """Completeness assessment of a project brief."""
    overall: float                            # 0.0-1.0
    dimensions: Dict[str, float]              # per-dimension scores
    missing: List[str]                        # what's missing
    suggestions: List[str]                    # how to improve
    word_count: int
    quality_label: str                        # "poor", "fair", "good", "excellent"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(self.overall, 2),
            "dimensions": {k: round(v, 2) for k, v in self.dimensions.items()},
            "missing": self.missing,
            "suggestions": self.suggestions,
            "word_count": self.word_count,
            "quality_label": self.quality_label,
        }


@dataclass
class EnhancedBrief:
    """An enhanced version of the user's brief with gaps filled."""
    original: str
    enhanced: str
    additions: List[str]                      # What was added
    score_before: float
    score_after: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "enhanced": self.enhanced,
            "additions": self.additions,
            "score_before": round(self.score_before, 2),
            "score_after": round(self.score_after, 2),
        }


# ── Scoring ──────────────────────────────────────────────────────────────

def score_brief(brief: str, project_type: str = "web_simple") -> BriefScore:
    """Score a project brief on completeness across all dimensions.

    Returns a BriefScore with per-dimension scores, missing elements,
    and suggestions for improvement.
    """
    words = brief.lower().split()
    word_count = len(words)
    brief_lower = brief.lower()

    # Get dimension weights, boosted by project type
    weights = dict(_DIMENSION_WEIGHTS)
    boosts = _TYPE_DIMENSION_BOOSTS.get(project_type, {})
    for dim, boost in boosts.items():
        weights[dim] = boost

    # Normalize weights
    total_weight = sum(weights.values())
    weights = {k: v / total_weight for k, v in weights.items()}

    # Score each dimension
    dimension_scores: Dict[str, float] = {}
    missing: List[str] = []
    suggestions: List[str] = []

    for dim, keywords in _DIMENSION_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in brief_lower)
        # Score = min(1.0, hits / threshold) — need ~3 keyword hits for full score
        threshold = 3
        score = min(1.0, hits / threshold)
        dimension_scores[dim] = score

        if score < 0.4:
            missing.append(dim)
            suggestions.append(_DIMENSION_SUGGESTIONS.get(dim, f"Add more details about {dim}."))

    # Word count bonus: very short briefs get penalized
    length_factor = min(1.0, word_count / 30)  # full score at 30+ words
    if word_count < 15:
        suggestions.insert(0, f"Your brief is only {word_count} words. Aim for at least 30 words for better results.")

    # Compute weighted overall
    overall = sum(
        dimension_scores.get(dim, 0) * weights.get(dim, 0)
        for dim in weights
    ) * length_factor

    # Quality label
    if overall >= 0.8:
        quality_label = "excellent"
    elif overall >= 0.6:
        quality_label = "good"
    elif overall >= 0.35:
        quality_label = "fair"
    else:
        quality_label = "poor"

    return BriefScore(
        overall=overall,
        dimensions=dimension_scores,
        missing=missing,
        suggestions=suggestions,
        word_count=word_count,
        quality_label=quality_label,
    )


# ── Suggestion text per dimension ────────────────────────────────────────

_DIMENSION_SUGGESTIONS: Dict[str, str] = {
    "purpose": "Clearly state what you want to build and its main goal.",
    "audience": "Describe who will use this (e.g., 'small business owners', 'students').",
    "features": "List key features (e.g., 'user authentication, dashboard, search').",
    "design": "Describe the look and feel (e.g., 'minimal, dark mode, modern').",
    "tech_stack": "Mention preferred technologies if any (e.g., 'React, Tailwind, PostgreSQL').",
    "data": "Describe what data the app stores or processes (e.g., 'user profiles, orders').",
    "pages": "List the main pages or screens (e.g., 'home, dashboard, settings, profile').",
    "scale": "Mention expected scale or performance needs if relevant.",
}


# ── Prompt enhancement ───────────────────────────────────────────────────

# Templates for auto-filling missing dimensions based on project type
_ENHANCEMENT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "web_simple": {
        "audience": "Target audience: general web visitors.",
        "design": "Design: clean, modern, responsive layout with mobile-first approach.",
        "pages": "Pages: Home, About, Contact.",
        "tech_stack": "Built with React and Tailwind CSS.",
        "data": "Minimal data requirements — primarily static content.",
    },
    "web_complex": {
        "audience": "Target audience: registered users and administrators.",
        "design": "Design: professional dashboard UI with responsive layout.",
        "pages": "Pages: Landing, Login/Signup, Dashboard, Settings, Profile.",
        "data": "Database: user accounts, application data with CRUD operations.",
        "scale": "Production-ready with proper error handling and loading states.",
    },
    "python_saas": {
        "audience": "Target audience: business users and team administrators.",
        "design": "Design: clean SaaS dashboard with sidebar navigation.",
        "pages": "Pages: Landing, Pricing, Login, Dashboard, Settings, Billing, Team Management.",
        "data": "Database: users, teams, subscriptions, application data.",
        "features": "Core features: authentication, team management, billing/subscriptions, admin dashboard.",
        "scale": "Scalable multi-tenant architecture.",
    },
    "mobile_native_ios": {
        "design": "Design: follows Apple Human Interface Guidelines, native iOS feel.",
        "pages": "Screens: Onboarding, Home, Detail, Profile, Settings.",
        "data": "Local storage with cloud sync capability.",
    },
    "mobile_cross_platform": {
        "design": "Design: cross-platform consistent UI with platform-specific touches.",
        "pages": "Screens: Onboarding, Home, Detail, Profile, Settings.",
    },
    "python_api": {
        "audience": "Consumers: frontend applications and third-party integrations.",
        "data": "RESTful API with structured data models.",
        "scale": "Production API with rate limiting and proper error responses.",
    },
    "cli_tool": {
        "audience": "Users: developers and system administrators.",
        "design": "Clean CLI output with colored formatting and progress indicators.",
    },
    "chrome_extension": {
        "audience": "Users: Chrome browser users.",
        "pages": "UI: popup, options page, and optional sidebar panel.",
    },
    "desktop_app": {
        "design": "Design: native desktop feel with system tray integration.",
        "pages": "Windows: main window, settings, about dialog.",
    },
}


def enhance_brief(
    brief: str,
    project_type: str = "web_simple",
    detected_features: Optional[List[str]] = None,
    detected_pages: Optional[List[str]] = None,
) -> EnhancedBrief:
    """Enhance a project brief by filling in detected gaps.

    Appends sensible defaults for missing dimensions based on the
    project type. Does NOT rewrite the user's original text.

    Returns the enhanced brief alongside a list of what was added.
    """
    score_before = score_brief(brief, project_type)

    additions: List[str] = []
    templates = _ENHANCEMENT_TEMPLATES.get(project_type, _ENHANCEMENT_TEMPLATES.get("web_simple", {}))

    for dim in score_before.missing:
        if dim in templates:
            additions.append(templates[dim])

    # Add detected features/pages if not already in brief
    brief_lower = brief.lower()
    if detected_features:
        missing_features = [f for f in detected_features if f.lower() not in brief_lower]
        if missing_features:
            additions.append(f"Key features: {', '.join(missing_features)}.")

    if detected_pages:
        missing_pages = [p for p in detected_pages if p.lower() not in brief_lower]
        if missing_pages:
            additions.append(f"Main pages: {', '.join(missing_pages)}.")

    # Build enhanced brief
    if additions:
        enhanced = brief.rstrip(". ") + ".\n\nAdditional context:\n" + "\n".join(f"- {a}" for a in additions)
    else:
        enhanced = brief

    score_after = score_brief(enhanced, project_type)

    return EnhancedBrief(
        original=brief,
        enhanced=enhanced,
        additions=additions,
        score_before=score_before.overall,
        score_after=score_after.overall,
    )
