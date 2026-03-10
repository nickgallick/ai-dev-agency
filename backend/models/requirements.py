"""Phase 11A: Structured Project Requirements Models."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ProjectTypeEnum(str, Enum):
    """Supported project types."""
    web_simple = "web_simple"
    web_complex = "web_complex"
    mobile_native_ios = "mobile_native_ios"
    mobile_cross_platform = "mobile_cross_platform"
    mobile_pwa = "mobile_pwa"
    desktop_app = "desktop_app"
    chrome_extension = "chrome_extension"
    cli_tool = "cli_tool"
    python_api = "python_api"
    python_saas = "python_saas"


class MobileFramework(str, Enum):
    """Mobile framework options."""
    react_native = "react_native"
    flutter = "flutter"
    expo = "expo"


class DesktopFramework(str, Enum):
    """Desktop framework options."""
    electron = "electron"
    tauri = "tauri"
    pyqt = "pyqt"


class BuildMode(str, Enum):
    """Build execution modes."""
    full_auto = "full_auto"  # Run entire pipeline automatically
    step_approval = "step_approval"  # Pause after each major step for approval
    preview_only = "preview_only"  # Generate plan/preview only, no execution


# ============ Design Preferences ============
class ColorScheme(str, Enum):
    """Color scheme options."""
    light = "light"
    dark = "dark"
    system = "system"  # Follows system preference


class DesignStyle(str, Enum):
    """Design style options."""
    minimal = "minimal"
    playful = "playful"
    corporate = "corporate"
    bold = "bold"
    elegant = "elegant"


class DesignPreferences(BaseModel):
    """Design preferences for the project."""
    color_scheme: ColorScheme = Field(default=ColorScheme.system, description="Light/dark mode preference")
    primary_color: Optional[str] = Field(None, description="Primary brand color (hex)")
    secondary_color: Optional[str] = Field(None, description="Secondary color (hex)")
    design_style: DesignStyle = Field(default=DesignStyle.minimal, description="Overall design style")
    font_preference: Optional[str] = Field(None, description="Preferred font family")
    enable_animations: bool = Field(default=True, description="Enable micro-animations")
    glassmorphism: bool = Field(default=True, description="Use glassmorphic design elements")
    
    class Config:
        use_enum_values = True


# ============ Tech Stack Preferences ============
class TechStack(BaseModel):
    """Technology stack preferences."""
    # Frontend
    frontend_framework: Optional[str] = Field(None, description="e.g., Next.js, React, Vue, Svelte")
    css_framework: Optional[str] = Field(None, description="e.g., Tailwind, CSS Modules, styled-components")
    
    # Backend
    backend_framework: Optional[str] = Field(None, description="e.g., FastAPI, Express, Django")
    database: Optional[str] = Field(None, description="e.g., PostgreSQL, MongoDB, Supabase")
    
    # Mobile specific
    mobile_framework: Optional[MobileFramework] = Field(None, description="Mobile framework preference")
    
    # Desktop specific
    desktop_framework: Optional[DesktopFramework] = Field(None, description="Desktop framework preference")
    
    # Additional services
    auth_provider: Optional[str] = Field(None, description="e.g., Supabase Auth, Auth0, Clerk")
    file_storage: Optional[str] = Field(None, description="e.g., Cloudflare R2, S3, Supabase Storage")
    
    class Config:
        use_enum_values = True


# ============ Deployment Configuration ============
class DeploymentConfig(BaseModel):
    """Deployment preferences and configuration."""
    platform: Optional[str] = Field(None, description="Deployment platform (Vercel, Railway, etc)")
    auto_deploy: bool = Field(default=True, description="Auto-deploy on completion")
    domain: Optional[str] = Field(None, description="Custom domain if available")
    
    # Mobile specific
    submit_to_app_store: bool = Field(default=False, description="Submit iOS app to App Store")
    submit_to_play_store: bool = Field(default=False, description="Submit to Google Play Store")
    
    # Desktop specific
    build_for_mac: bool = Field(default=True, description="Build macOS binary")
    build_for_windows: bool = Field(default=True, description="Build Windows binary")
    build_for_linux: bool = Field(default=False, description="Build Linux binary")
    notarize_mac: bool = Field(default=False, description="Apple notarization for macOS")
    
    # CLI/Package specific
    publish_to_npm: bool = Field(default=False, description="Publish to npm registry")
    publish_to_pypi: bool = Field(default=False, description="Publish to PyPI")


# ============ Conditional Fields by Project Type ============
class WebComplexFields(BaseModel):
    """Additional fields for web_complex/saas projects."""
    key_features: List[str] = Field(default_factory=list, description="Key features to include")
    pages: List[str] = Field(default_factory=list, description="Pages/routes to create")
    include_auth: bool = Field(default=False, description="Include authentication")
    include_dashboard: bool = Field(default=False, description="Include admin dashboard")
    include_billing: bool = Field(default=False, description="Include billing/subscriptions")
    include_email: bool = Field(default=False, description="Include email functionality")


class WebSimpleFields(BaseModel):
    """Additional fields for web_simple projects."""
    num_pages: int = Field(default=1, ge=1, le=20, description="Number of pages")
    sections: List[str] = Field(default_factory=list, description="Sections to include")
    include_contact_form: bool = Field(default=False, description="Include contact form")
    include_blog: bool = Field(default=False, description="Include blog section")


class MobileFields(BaseModel):
    """Additional fields for mobile projects."""
    platforms: List[str] = Field(default_factory=lambda: ["ios", "android"], description="Target platforms")
    framework: Optional[MobileFramework] = Field(None, description="Mobile framework")
    submit_to_stores: bool = Field(default=False, description="Submit to app stores")
    include_push_notifications: bool = Field(default=False, description="Include push notifications")
    include_offline_support: bool = Field(default=False, description="Include offline support")


class CLIFields(BaseModel):
    """Additional fields for CLI tools."""
    language: str = Field(default="python", description="Programming language (python/node)")
    package_name: Optional[str] = Field(None, description="Package name for registry")
    publish_to_registry: bool = Field(default=False, description="Publish to npm/pypi")


class DesktopFields(BaseModel):
    """Additional fields for desktop apps."""
    target_platforms: List[str] = Field(default_factory=lambda: ["mac", "windows"], description="Target platforms")
    framework: Optional[DesktopFramework] = Field(None, description="Desktop framework")
    include_auto_update: bool = Field(default=False, description="Include auto-update functionality")


# ============ Main Project Requirements ============
class ProjectRequirements(BaseModel):
    """Complete structured project requirements."""
    # Core fields
    brief: str = Field(..., min_length=10, description="Project description")
    project_type: ProjectTypeEnum = Field(..., description="Type of project to build")
    name: Optional[str] = Field(None, description="Project name")
    cost_profile: str = Field(default="balanced", description="budget/balanced/premium")
    
    # Common fields
    industry: Optional[str] = Field(None, description="Industry/vertical (e.g., healthcare, fintech)")
    target_audience: Optional[str] = Field(None, description="Target audience description")
    reference_urls: List[str] = Field(default_factory=list, description="Reference/inspiration URLs")
    
    # Design
    design_preferences: DesignPreferences = Field(default_factory=DesignPreferences)
    figma_url: Optional[str] = Field(None, description="Figma design file URL")
    
    # Tech
    tech_stack: TechStack = Field(default_factory=TechStack)
    
    # Deployment
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    
    # Conditional fields (populated based on project_type)
    web_complex_options: Optional[WebComplexFields] = None
    web_simple_options: Optional[WebSimpleFields] = None
    mobile_options: Optional[MobileFields] = None
    cli_options: Optional[CLIFields] = None
    desktop_options: Optional[DesktopFields] = None
    
    # Advanced
    custom_instructions: Optional[str] = Field(None, description="Additional custom instructions")
    template_id: Optional[str] = Field(None, description="Template/preset to base project on")
    build_mode: BuildMode = Field(default=BuildMode.full_auto, description="Build execution mode")
    
    # Integration config (Phase 10)
    integration_config: Dict[str, Any] = Field(default_factory=dict, description="Integration settings")
    
    class Config:
        use_enum_values = True


# ============ Brief Analysis Response ============
class BriefAnalysis(BaseModel):
    """Response from real-time brief analysis."""
    detected_project_type: Optional[ProjectTypeEnum] = Field(None, description="Auto-detected project type")
    confidence: float = Field(default=0.0, ge=0, le=1, description="Detection confidence")
    suggested_features: List[str] = Field(default_factory=list, description="Suggested features")
    suggested_pages: List[str] = Field(default_factory=list, description="Suggested pages/screens")
    detected_industry: Optional[str] = Field(None, description="Detected industry")
    complexity_estimate: str = Field(default="medium", description="simple/medium/complex")
    cost_estimate: Dict[str, str] = Field(default_factory=dict, description="Cost estimates by profile")
    warnings: List[str] = Field(default_factory=list, description="Any warnings or suggestions")
    
    class Config:
        use_enum_values = True
