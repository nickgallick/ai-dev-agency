"""Phase 11A: Project Preset Model for saved configurations."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .database import Base


class ProjectPreset(Base):
    """Stores saved project configurations/presets."""
    __tablename__ = "project_presets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Lucide icon name
    
    # Stored configuration (matches ProjectRequirements structure)
    config = Column(JSONB, nullable=False, default=dict)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    use_count = Column(String(20), default="0")  # Track usage for popularity sorting
    
    # Optional: Link to user if auth is enabled
    # user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    def __repr__(self):
        return f"<ProjectPreset {self.name}>"
