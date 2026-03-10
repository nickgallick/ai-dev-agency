"""Project model for storing project information."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Enum, Float, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from .database import Base


class ProjectType(str, enum.Enum):
    """Supported project types."""
    WEB_SIMPLE = "web_simple"
    WEB_COMPLEX = "web_complex"


class ProjectStatus(str, enum.Enum):
    """Project status states."""
    PENDING = "pending"
    INTAKE = "intake"
    RESEARCH = "research"
    ARCHITECT = "architect"
    DESIGN = "design"
    CODE_GENERATION = "code_generation"
    QA = "qa"
    DEPLOYMENT = "deployment"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class CostProfile(str, enum.Enum):
    """Cost profile presets."""
    BUDGET = "budget"
    BALANCED = "balanced"
    PREMIUM = "premium"


class Project(Base):
    """Project model representing a development project."""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brief = Column(Text, nullable=False)
    name = Column(String(255), nullable=True)
    project_type = Column(
        Enum(ProjectType),
        nullable=True,
        default=ProjectType.WEB_SIMPLE
    )
    status = Column(
        Enum(ProjectStatus),
        nullable=False,
        default=ProjectStatus.PENDING
    )
    cost_estimate = Column(Float, nullable=True)
    cost_profile = Column(
        Enum(CostProfile),
        nullable=False,
        default=CostProfile.BALANCED
    )
    github_repo = Column(String(500), nullable=True)
    live_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # JSONB fields for flexible data storage
    agent_outputs = Column(JSONB, default=dict)
    project_metadata = Column(JSONB, default=dict)  # For reference_urls, tech_stack, etc.
    revision_history = Column(JSONB, default=list)  # For project versioning
    
    # Relationships
    agent_logs = relationship("AgentLog", back_populates="project", cascade="all, delete-orphan")
    cost_tracking = relationship("CostTracking", back_populates="project", cascade="all, delete-orphan")
    deployment_records = relationship("DeploymentRecord", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_project_status", "status"),
        Index("idx_project_type", "project_type"),
        Index("idx_project_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"
