"""Agent Performance model for tracking agent analytics.

Phase 9A - Enhanced Analytics (Agent Performance Intelligence)

Tracks per agent execution:
- project_id, agent_name, model_used
- execution_time_ms
- output_quality (passed_next_stage, revision_count, qa_issues_caused)
- tokens_used (input, output)
- cost
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .database import Base


class AgentPerformance(Base):
    """Agent performance metrics for analytics and optimization."""
    __tablename__ = "agent_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Agent identification
    agent_name = Column(String(100), nullable=False)
    model_used = Column(String(100), nullable=False)
    
    # Execution metrics
    execution_time_ms = Column(Integer, nullable=False, default=0)
    
    # Output quality metrics (JSONB for flexibility)
    output_quality = Column(JSONB, default=dict)
    # Structure:
    # {
    #     "passed_next_stage": true/false,
    #     "revision_count": 0,
    #     "qa_issues_caused": 0,
    #     "quality_score": 0.0-1.0,
    #     "error_occurred": false,
    #     "error_message": null
    # }
    
    # Token usage (JSONB for input/output breakdown)
    tokens_used = Column(JSONB, default=dict)
    # Structure:
    # {
    #     "input_tokens": 0,
    #     "output_tokens": 0,
    #     "total_tokens": 0
    # }
    
    # Cost tracking
    cost = Column(Float, default=0.0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="agent_performance_records")

    __table_args__ = (
        Index("idx_agent_perf_project_id", "project_id"),
        Index("idx_agent_perf_agent_name", "agent_name"),
        Index("idx_agent_perf_model_used", "model_used"),
        Index("idx_agent_perf_created_at", "created_at"),
        # Composite index for common queries
        Index("idx_agent_perf_agent_model", "agent_name", "model_used"),
    )

    def __repr__(self):
        return f"<AgentPerformance(id={self.id}, agent={self.agent_name}, model={self.model_used})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "agent_name": self.agent_name,
            "model_used": self.model_used,
            "execution_time_ms": self.execution_time_ms,
            "output_quality": self.output_quality or {},
            "tokens_used": self.tokens_used or {},
            "cost": self.cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QAFailurePattern(Base):
    """Track recurring QA failure patterns for analysis."""
    __tablename__ = "qa_failure_patterns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Pattern identification
    pattern_hash = Column(String(64), nullable=False, unique=True)  # SHA256 of normalized error
    pattern_type = Column(String(50), nullable=False)  # e.g., "security", "accessibility", "seo", "test_failure"
    
    # Pattern description
    description = Column(String(500), nullable=False)
    sample_error = Column(String(2000), nullable=True)
    
    # Agent that caused the issue
    causing_agent = Column(String(100), nullable=True)
    
    # Occurrence tracking
    occurrence_count = Column(Integer, default=1, nullable=False)
    last_occurred = Column(DateTime, default=datetime.utcnow, nullable=False)
    first_occurred = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Affected projects (stored as JSONB list of project IDs)
    affected_projects = Column(JSONB, default=list)
    
    # Resolution status
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolution_notes = Column(String(1000), nullable=True)
    
    __table_args__ = (
        Index("idx_qa_failure_pattern_type", "pattern_type"),
        Index("idx_qa_failure_occurrence", "occurrence_count"),
        Index("idx_qa_failure_last_occurred", "last_occurred"),
    )
    
    def __repr__(self):
        return f"<QAFailurePattern(type={self.pattern_type}, count={self.occurrence_count})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "pattern_hash": self.pattern_hash,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "sample_error": self.sample_error,
            "causing_agent": self.causing_agent,
            "occurrence_count": self.occurrence_count,
            "last_occurred": self.last_occurred.isoformat() if self.last_occurred else None,
            "first_occurred": self.first_occurred.isoformat() if self.first_occurred else None,
            "affected_projects": self.affected_projects or [],
            "is_resolved": self.is_resolved,
            "resolution_notes": self.resolution_notes,
        }


class CostAccuracyTracking(Base):
    """Track estimated vs actual costs for accuracy improvement."""
    __tablename__ = "cost_accuracy_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Project categorization
    project_type = Column(String(50), nullable=False)
    cost_profile = Column(String(20), nullable=False)  # budget, balanced, premium
    complexity_score = Column(Integer, default=5)  # 1-10
    
    # Cost estimates and actuals
    estimated_cost = Column(Float, nullable=False)
    actual_cost = Column(Float, nullable=True)  # Set when project completes
    
    # Accuracy metrics (computed when project completes)
    accuracy_percentage = Column(Float, nullable=True)  # (1 - abs(diff)/estimated) * 100
    estimation_error = Column(Float, nullable=True)  # actual - estimated
    
    # Timestamps
    estimated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    project = relationship("Project", back_populates="cost_accuracy_record")
    
    __table_args__ = (
        Index("idx_cost_accuracy_project_type", "project_type"),
        Index("idx_cost_accuracy_cost_profile", "cost_profile"),
    )
    
    def __repr__(self):
        return f"<CostAccuracyTracking(project_id={self.project_id}, accuracy={self.accuracy_percentage})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "project_type": self.project_type,
            "cost_profile": self.cost_profile,
            "complexity_score": self.complexity_score,
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost,
            "accuracy_percentage": self.accuracy_percentage,
            "estimation_error": self.estimation_error,
            "estimated_at": self.estimated_at.isoformat() if self.estimated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
