"""Phase 11B: Project Template Model

SQLAlchemy model for storing reusable project templates.
"""
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from .database import Base


class ProjectTemplate(Base):
    """Project template for quick project creation."""
    __tablename__ = "project_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    project_type = Column(String(50), nullable=False)
    industry = Column(String(100), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)

    # Template content
    brief_template = Column(Text, nullable=True)  # Pre-filled brief text
    requirements = Column(JSONB, nullable=True)  # Pre-filled structured requirements
    design_tokens = Column(JSONB, nullable=True)  # Saved design system
    tech_stack = Column(JSONB, nullable=True)  # Saved tech stack
    features = Column(JSONB, nullable=True)  # Feature list

    # Source project (if auto-generated)
    source_project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=True)
    is_auto_generated = Column(Boolean, default=False)  # True if created from successful project
    is_public = Column(Boolean, default=True)  # Visible to all users

    # Quality metrics from source project
    qa_score = Column(Float, nullable=True)
    build_success_count = Column(Integer, default=0)  # How many times template used successfully
    total_usage_count = Column(Integer, default=0)

    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Additional data
    template_metadata = Column(JSONB, nullable=True)
    tags = Column(ARRAY(String(50)), nullable=True)
    
    # Relationships
    source_project = relationship("Project", foreign_keys=[source_project_id])
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "industry": self.industry,
            "thumbnail_url": self.thumbnail_url,
            "brief_template": self.brief_template,
            "requirements": self.requirements,
            "design_tokens": self.design_tokens,
            "tech_stack": self.tech_stack,
            "features": self.features,
            "source_project_id": str(self.source_project_id) if self.source_project_id else None,
            "is_auto_generated": self.is_auto_generated,
            "is_public": self.is_public,
            "qa_score": self.qa_score,
            "build_success_count": self.build_success_count,
            "total_usage_count": self.total_usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "template_metadata": self.template_metadata,
            "tags": self.tags,
        }
