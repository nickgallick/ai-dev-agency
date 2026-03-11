"""Structured audit log model for pipeline decisions and system events.

Every significant pipeline decision, state transition, or system event
is recorded here with structured metadata for querying and debugging.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .database import Base


class AuditLog(Base):
    """Structured audit log for pipeline decisions and system events."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event classification
    event_type = Column(String(50), nullable=False)
    # Examples: pipeline_start, agent_start, agent_complete, agent_fail,
    #           agent_skip, agent_retry, checkpoint_save, checkpoint_resume,
    #           queue_enqueue, queue_dequeue, cost_alert, dependency_skip

    # Context
    project_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    agent_name = Column(String(100), nullable=True)

    # Human-readable summary
    message = Column(Text, nullable=False)

    # Structured payload — everything needed to reproduce/debug the decision
    details = Column(JSONB, nullable=False, default=dict)
    # Examples:
    #   agent_skip:    {"reason": "dependency_failed", "failed_dep": "security", "downstream": ["qa"]}
    #   cost_alert:    {"current_cost": 12.50, "threshold": 50.0, "percentage": 25.0}
    #   agent_retry:   {"retry_count": 2, "max_retries": 3, "reset_nodes": ["code_generation", ...]}
    #   checkpoint_resume: {"resumed_from_step": 8, "skipped_agents": ["intake", ...]}

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    duration_ms = Column(String(20), nullable=True)  # for events with duration

    __table_args__ = (
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_project_time", "project_id", "timestamp"),
    )

    def __repr__(self):
        return f"<AuditLog({self.event_type}: {self.message[:60]})>"
