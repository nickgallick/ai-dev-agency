"""Cost tracking model for aggregated cost data."""
import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .database import Base


class CostTracking(Base):
    """Cost tracking model for project-level cost aggregation."""
    __tablename__ = "cost_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Total cost
    total_cost = Column(Float, default=0.0, nullable=False)
    
    # Detailed breakdown by agent, model, etc.
    breakdown = Column(JSONB, default=dict)
    # Example structure:
    # {
    #     "by_agent": {"intake": 0.05, "research": 0.15, ...},
    #     "by_model": {"claude-sonnet": 0.10, "gpt-4": 0.20, ...},
    #     "by_category": {"llm": 0.25, "image_gen": 0.10, "api": 0.05}
    # }
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    project = relationship("Project", back_populates="cost_tracking")

    __table_args__ = (
        Index("idx_cost_tracking_project_id", "project_id"),
        Index("idx_cost_tracking_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<CostTracking(id={self.id}, project_id={self.project_id}, total_cost={self.total_cost})>"
