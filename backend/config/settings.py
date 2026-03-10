"""Application settings."""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ai_dev_agency"
    
    # Security
    secret_key: str = "change-me-in-production"
    
    # LLM APIs
    openrouter_api_key: Optional[str] = None
    
    # Code Generation
    vercel_v0_api_key: Optional[str] = None
    
    # GitHub
    github_token: Optional[str] = None
    
    # Deployment Platforms
    vercel_token: Optional[str] = None
    railway_token: Optional[str] = None
    
    # Optional Services
    slack_webhook_url: Optional[str] = None
    sentry_dsn: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
