"""Pydantic schemas for AI Dev Agency."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    """Types of projects that can be generated."""
    WEB_SIMPLE = "web_simple"
    WEB_COMPLEX = "web_complex"
    MOBILE_APP = "mobile_app"
    DASHBOARD = "dashboard"
    API = "api"
    LANDING_PAGE = "landing_page"
    E_COMMERCE = "e_commerce"
    PORTFOLIO = "portfolio"


class AgentStatus(str, Enum):
    """Status of an agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CostProfile(str, Enum):
    """Cost optimization profiles."""
    BUDGET = "budget"
    BALANCED = "balanced"
    PREMIUM = "premium"


class ProjectBrief(BaseModel):
    """Input brief for a project."""
    name: str
    description: str
    project_type: ProjectType
    reference_urls: List[str] = Field(default_factory=list)
    tech_stack: Optional[str] = None
    target_audience: Optional[str] = None
    brand_guidelines: Optional[Dict[str, Any]] = None
    features: List[str] = Field(default_factory=list)
    tone: Optional[str] = "professional"
    industry: Optional[str] = None


class DesignSystemOutput(BaseModel):
    """Output from Design System Agent."""
    primary_color: str
    secondary_color: str
    accent_color: str
    background_color: str
    text_color: str
    font_family: str
    heading_font: Optional[str] = None
    spacing_unit: int = 8
    border_radius: int = 8
    design_tokens: Dict[str, Any] = Field(default_factory=dict)


class AssetMetadata(BaseModel):
    """Metadata for a generated asset."""
    filename: str
    path: str
    width: int
    height: int
    format: str
    size_bytes: int
    asset_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AssetGenerationOutput(BaseModel):
    """Output from Asset Generation Agent."""
    assets: List[AssetMetadata] = Field(default_factory=list)
    favicon_paths: Dict[str, str] = Field(default_factory=dict)
    og_image_path: Optional[str] = None
    app_icon_paths: Dict[str, str] = Field(default_factory=dict)
    placeholder_images: List[str] = Field(default_factory=list)
    svg_illustrations: List[str] = Field(default_factory=list)


class ContentData(BaseModel):
    """Content for a specific section or page."""
    page_name: str
    headline: Optional[str] = None
    subheadline: Optional[str] = None
    body_text: Optional[str] = None
    cta_text: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    additional_content: Dict[str, Any] = Field(default_factory=dict)


class ContentGenerationOutput(BaseModel):
    """Output from Content Generation Agent."""
    pages: List[ContentData] = Field(default_factory=list)
    global_content: Dict[str, str] = Field(default_factory=dict)
    alt_texts: Dict[str, str] = Field(default_factory=dict)
    seo_keywords: List[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    """Base output for any agent."""
    agent_name: str
    status: AgentStatus
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    token_usage: int = 0
    cost: float = 0.0
    model_used: Optional[str] = None


class SecurityFinding(BaseModel):
    """A security vulnerability finding."""
    rule_id: str
    severity: str
    message: str
    file_path: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    fix_suggestion: Optional[str] = None
    auto_fixed: bool = False


class SecurityReport(BaseModel):
    """Output from Security Agent."""
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    findings: List[SecurityFinding] = Field(default_factory=list)
    auto_fixed_count: int = 0
    scan_duration_seconds: float = 0.0


class SEOIssue(BaseModel):
    """An SEO issue or recommendation."""
    category: str
    title: str
    description: str
    impact: str
    recommendation: Optional[str] = None


class SEOReport(BaseModel):
    """Output from SEO Agent."""
    performance_score: float = 0.0
    accessibility_score: float = 0.0
    best_practices_score: float = 0.0
    seo_score: float = 0.0
    issues: List[SEOIssue] = Field(default_factory=list)
    meta_tags_generated: bool = False
    sitemap_generated: bool = False
    robots_txt_generated: bool = False


class AccessibilityIssue(BaseModel):
    """An accessibility violation."""
    id: str
    impact: str
    description: str
    help_url: Optional[str] = None
    nodes_affected: int = 0
    fix_suggestion: Optional[str] = None


class AccessibilityReport(BaseModel):
    """Output from Accessibility Agent."""
    total_violations: int = 0
    critical_count: int = 0
    serious_count: int = 0
    moderate_count: int = 0
    minor_count: int = 0
    violations: List[AccessibilityIssue] = Field(default_factory=list)
    passes: int = 0
    incomplete: int = 0
    wcag_compliant: bool = False
