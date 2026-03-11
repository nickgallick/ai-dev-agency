"""Pipeline checkpoint model for crash recovery and resume.

Stores the full pipeline state after each agent completes, enabling
resume-from-checkpoint on failure without re-running finished agents.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .database import Base


class PipelineCheckpoint(Base):
    """Stores a pipeline checkpoint after each agent completes."""
    __tablename__ = "pipeline_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Which agent just finished
    agent_name = Column(String(100), nullable=False)
    agent_status = Column(String(20), nullable=False)  # completed, failed, skipped

    # Full DAG state: {node_id: {"status": "completed", "result_summary": {...}}}
    node_states = Column(JSONB, nullable=False, default=dict)

    # Shared pipeline context (brief, requirements, accumulated results refs)
    pipeline_context = Column(JSONB, nullable=False, default=dict)

    # Pipeline config snapshot
    pipeline_config = Column(JSONB, nullable=False, default=dict)

    # Cost state
    total_cost = Column(Float, default=0.0)
    cost_breakdown = Column(JSONB, default=dict)

    # Ordering
    step_number = Column(Integer, nullable=False)  # 1-indexed ordinal
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_checkpoint_project_step", "project_id", "step_number"),
        Index("idx_checkpoint_project_latest", "project_id", "created_at"),
    )

    def __repr__(self):
        return (
            f"<PipelineCheckpoint(project={self.project_id}, "
            f"agent={self.agent_name}, step={self.step_number})>"
        )
