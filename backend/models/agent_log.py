"""Agent log model for tracking LLM calls and agent execution."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .database import Base


class AgentLog(Base):
    """Agent log model for debugging and cost tracking."""
    __tablename__ = "agent_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Agent identification
    agent_name = Column(String(100), nullable=False)
    agent_step = Column(Integer, nullable=True)  # Pipeline step number
    
    # Model and token tracking
    model_used = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Cost and timing
    cost = Column(Float, default=0.0)
    duration_ms = Column(Integer, default=0)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Input/Output data
    input_data = Column(JSONB, default=dict)  # Prompt and context
    output_data = Column(JSONB, default=dict)  # Response and parsed output
    
    # Status and error tracking
    status = Column(String(50), default="completed")  # completed, failed, timeout
    error_message = Column(Text, nullable=True)
    
    # Relationship
    project = relationship("Project", back_populates="agent_logs")

    __table_args__ = (
        Index("idx_agent_log_project_id", "project_id"),
        Index("idx_agent_log_agent_name", "agent_name"),
        Index("idx_agent_log_timestamp", "timestamp"),
        Index("idx_agent_log_model", "model_used"),
    )

    def __repr__(self):
        return f"<AgentLog(id={self.id}, agent={self.agent_name}, model={self.model_used})>"
