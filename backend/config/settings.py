"""Configuration settings for AI Dev Agency."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Settings:
    """Application settings."""
    
    # Docker Integration
    docker_integration_mode: str = field(
        default_factory=lambda: os.getenv("DOCKER_INTEGRATION_MODE", "sdk")
    )
    
    # Semgrep Configuration
    semgrep_api_token: Optional[str] = field(
        default_factory=lambda: os.getenv("SEMGREP_API_TOKEN")
    )
    semgrep_image: str = "semgrep/semgrep:latest"
    semgrep_timeout: int = 300
    
    # Lighthouse Configuration
    lighthouse_image: str = "femtopixel/google-lighthouse:latest"
    lighthouse_timeout: int = 300
    
    # Playwright Configuration
    playwright_host: str = field(
        default_factory=lambda: os.getenv("PLAYWRIGHT_HOST", "localhost")
    )
    playwright_port: int = field(
        default_factory=lambda: int(os.getenv("PLAYWRIGHT_PORT", "3200"))
    )
    playwright_image: str = "mcr.microsoft.com/playwright:v1.51.0-noble"
    
    # Project Configuration
    project_temp_dir: str = "/tmp/ai-dev-agency"
    scan_timeout: int = 600
    
    # Auto-fix Configuration
    auto_fix_enabled: bool = field(
        default_factory=lambda: os.getenv("AUTO_FIX_ENABLED", "true").lower() == "true"
    )
    auto_fix_severities: list = field(
        default_factory=lambda: ["critical", "high"]
    )
    
    # API Configuration
    api_host: str = field(
        default_factory=lambda: os.getenv("API_HOST", "0.0.0.0")
    )
    api_port: int = field(
        default_factory=lambda: int(os.getenv("API_PORT", "8000"))
    )
    
    # Database Configuration
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@db:5432/aidevagency"
        )
    )

    # Redis Configuration
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379/0")
    )
    redis_host: str = field(
        default_factory=lambda: os.getenv("REDIS_HOST", "redis")
    )
    redis_port: int = field(
        default_factory=lambda: int(os.getenv("REDIS_PORT", "6379"))
    )
    redis_password: Optional[str] = field(
        default_factory=lambda: os.getenv("REDIS_PASSWORD")
    )

    # ===========================================
    # LLM API Configuration
    # ===========================================
    
    # OpenRouter API Key (required for all LLM calls)
    openrouter_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY")
    )
    
    # Vercel v0 API for code generation
    vercel_v0_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("VERCEL_V0_API_KEY")
    )
    
    # GitHub Token for repository operations
    github_token: Optional[str] = field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN")
    )
    
    # Tavily API for research
    tavily_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("TAVILY_API_KEY")
    )
    
    # OpenAI API Key (for DALL-E image generation)
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    
    # Vercel Token (for deployment)
    vercel_token: Optional[str] = field(
        default_factory=lambda: os.getenv("VERCEL_TOKEN")
    )
    
    # Railway Token (for deployment)
    railway_token: Optional[str] = field(
        default_factory=lambda: os.getenv("RAILWAY_TOKEN")
    )
    
    # Encryption Key for credentials
    encryption_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ENCRYPTION_KEY")
    )
    
    # ===========================================
    # Phase 10: Integration Settings
    # ===========================================
    
    # Figma MCP Integration (Agency System - used by agents during generation)
    figma_access_token: Optional[str] = field(
        default_factory=lambda: os.getenv("FIGMA_ACCESS_TOKEN")
    )
    
    # BrowserStack Integration (Agency System - used by QA Agent)
    browserstack_username: Optional[str] = field(
        default_factory=lambda: os.getenv("BROWSERSTACK_USERNAME")
    )
    browserstack_access_key: Optional[str] = field(
        default_factory=lambda: os.getenv("BROWSERSTACK_ACCESS_KEY")
    )
    
    # Resend Integration (Generated Project Defaults - for email in SaaS projects)
    resend_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("RESEND_API_KEY")
    )
    
    # Cloudflare R2 Integration (Generated Project Defaults - for file storage)
    r2_access_key_id: Optional[str] = field(
        default_factory=lambda: os.getenv("R2_ACCESS_KEY_ID")
    )
    r2_secret_access_key: Optional[str] = field(
        default_factory=lambda: os.getenv("R2_SECRET_ACCESS_KEY")
    )
    r2_bucket_name: Optional[str] = field(
        default_factory=lambda: os.getenv("R2_BUCKET_NAME")
    )
    r2_account_id: Optional[str] = field(
        default_factory=lambda: os.getenv("R2_ACCOUNT_ID")
    )
    
    # Inngest Integration (Generated Project Defaults - for background jobs)
    inngest_event_key: Optional[str] = field(
        default_factory=lambda: os.getenv("INNGEST_EVENT_KEY")
    )
    
    # Helper properties for integration status
    @property
    def figma_configured(self) -> bool:
        """Check if Figma MCP is configured."""
        return bool(self.figma_access_token)
    
    @property
    def browserstack_configured(self) -> bool:
        """Check if BrowserStack is configured."""
        return bool(self.browserstack_username and self.browserstack_access_key)
    
    @property
    def resend_configured(self) -> bool:
        """Check if Resend is configured."""
        return bool(self.resend_api_key)
    
    @property
    def r2_configured(self) -> bool:
        """Check if Cloudflare R2 is configured."""
        return bool(
            self.r2_access_key_id and 
            self.r2_secret_access_key and 
            self.r2_bucket_name and 
            self.r2_account_id
        )
    
    @property
    def inngest_configured(self) -> bool:
        """Check if Inngest is configured."""
        return bool(self.inngest_event_key)

    def __post_init__(self):
        """Validate settings after initialization."""
        if self.docker_integration_mode not in ["sdk", "subprocess"]:
            raise ValueError(
                f"Invalid DOCKER_INTEGRATION_MODE: {self.docker_integration_mode}"
            )


_settings = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
