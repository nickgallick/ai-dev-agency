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

    def __post_init__(self):
        """Validate settings after initialization."""
        if self.docker_integration_mode not in ["sdk", "subprocess"]:
            raise ValueError(
                f"Invalid DOCKER_INTEGRATION_MODE: {self.docker_integration_mode}"
            )
