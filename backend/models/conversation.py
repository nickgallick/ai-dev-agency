"""Pre-build conversation model for the Conversational Clarification System.

Stores chat messages between the user and AI during the pre-build
clarification phase, before the pipeline starts.
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from .database import Base


class PreBuildConversation(Base):
    """A single message in a pre-build clarification conversation."""
    __tablename__ = "pre_build_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(String(64), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

    # AI analysis metadata (only on assistant messages)
    metadata_ = Column("metadata", JSONB, nullable=True)
    # Whether the AI considers requirements sufficiently clear
    ready_to_build = Column(Boolean, default=False)
