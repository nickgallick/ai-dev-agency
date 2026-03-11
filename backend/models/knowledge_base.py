"""Phase 11B: Knowledge Base Model

SQLAlchemy model for storing knowledge entries with embeddings.
"""
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from .database import Base


class KnowledgeBase(Base):
    """Knowledge base entry with vector embedding for RAG."""
    __tablename__ = "knowledge_base"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_type = Column(String(50), nullable=False)  # architecture_decision, qa_finding, prompt_result, code_pattern, user_preference
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(ARRAY(Float), nullable=True)  # 1536-dim vector for OpenAI embeddings

    # Metadata for filtering
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=True)
    project_type = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=True)
    tech_stack = Column(JSONB, nullable=True)  # ["nextjs", "supabase", "stripe"]
    agent_name = Column(String(50), nullable=True)
    quality_score = Column(Float, nullable=True)  # 0-1, based on downstream acceptance
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Additional data
    entry_metadata = Column(JSONB, nullable=True)  # Flexible storage for type-specific data
    tags = Column(ARRAY(String(50)), nullable=True)
    
    # Relationships
    project = relationship("Project", foreign_keys=[project_id])
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "entry_type": self.entry_type,
            "title": self.title,
            "content": self.content,
            "project_id": str(self.project_id) if self.project_id else None,
            "project_type": self.project_type,
            "industry": self.industry,
            "tech_stack": self.tech_stack,
            "agent_name": self.agent_name,
            "quality_score": self.quality_score,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "entry_metadata": self.entry_metadata,
            "tags": self.tags,
        }
