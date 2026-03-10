"""Deployment record model for tracking deployments."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from .database import Base


class DeploymentPlatform(str, enum.Enum):
    """Supported deployment platforms."""
    VERCEL = "vercel"
    RAILWAY = "railway"
    SUPABASE = "supabase"
    GITHUB_PAGES = "github_pages"
    NETLIFY = "netlify"
    MANUAL = "manual"


class DeploymentStatus(str, enum.Enum):
    """Deployment status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentRecord(Base):
    """Deployment record model for tracking project deployments."""
    __tablename__ = "deployment_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Deployment info
    platform = Column(Enum(DeploymentPlatform), nullable=False)
    url = Column(String(500), nullable=True)
    status = Column(Enum(DeploymentStatus), nullable=False, default=DeploymentStatus.PENDING)
    
    # Version tracking
    version = Column(String(50), nullable=True)  # Git SHA or version tag
    commit_sha = Column(String(40), nullable=True)
    
    # Timestamps
    deployed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Additional metadata
    deployment_config = Column(JSONB, default=dict)  # Platform-specific config
    logs = Column(Text, nullable=True)  # Deployment logs
    error_message = Column(Text, nullable=True)
    
    # Relationship
    project = relationship("Project", back_populates="deployment_records")

    __table_args__ = (
        Index("idx_deployment_project_id", "project_id"),
        Index("idx_deployment_platform", "platform"),
        Index("idx_deployment_status", "status"),
        Index("idx_deployment_deployed_at", "deployed_at"),
    )

    def __repr__(self):
        return f"<DeploymentRecord(id={self.id}, platform={self.platform}, status={self.status})>"
