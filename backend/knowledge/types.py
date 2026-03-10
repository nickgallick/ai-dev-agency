"""Phase 11B: Knowledge Entry Types

Defines the types of knowledge that can be stored in the knowledge base.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class KnowledgeEntryType(str, Enum):
    """Types of knowledge entries in the knowledge base."""
    ARCHITECTURE_DECISION = "architecture_decision"  # Tech stack choices, patterns
    QA_FINDING = "qa_finding"  # Bugs found and fixes applied
    PROMPT_RESULT = "prompt_result"  # v0/LLM prompts that worked well
    CODE_PATTERN = "code_pattern"  # Reusable code snippets
    USER_PREFERENCE = "user_preference"  # User's stated preferences
    DESIGN_TOKEN = "design_token"  # Design system decisions
    RESEARCH_OUTPUT = "research_output"  # Research agent findings
    DEPLOYMENT_CONFIG = "deployment_config"  # Deployment configurations
    COST_DATA = "cost_data"  # Cost optimization learnings
    SECURITY_FINDING = "security_finding"  # Security patterns and fixes
    BRAND_GUIDELINE = "brand_guideline"  # Brand-related knowledge
    REJECTION_REASON = "rejection_reason"  # Why outputs were rejected


class KnowledgeEntry(BaseModel):
    """Pydantic model for knowledge entry."""
    id: Optional[str] = None
    entry_type: KnowledgeEntryType
    title: str
    content: str
    project_id: Optional[str] = None
    project_type: Optional[str] = None
    industry: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    agent_name: Optional[str] = None
    quality_score: Optional[float] = None
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class KnowledgeQueryResult(BaseModel):
    """Result from knowledge base query."""
    entry: KnowledgeEntry
    similarity_score: float
    relevance_explanation: Optional[str] = None


class KnowledgeStats(BaseModel):
    """Statistics about the knowledge base."""
    total_entries: int
    entries_by_type: Dict[str, int]
    entries_by_agent: Dict[str, int]
    entries_by_project_type: Dict[str, int]
    average_quality_score: float
    most_used_entries: List[Dict[str, Any]]
    recent_entries: List[Dict[str, Any]]
