"""Phase 11B: Knowledge Base Module

RAG-based knowledge storage and retrieval for improving agent performance.
"""
from .types import KnowledgeEntryType
from .embeddings import generate_embedding, compute_similarity
from .base import (
    store_knowledge,
    query_knowledge,
    get_relevant_knowledge,
    store_architecture_decision,
    store_qa_finding,
    store_prompt_result,
    store_code_pattern,
    store_user_preference,
    update_knowledge_quality_score,
)
from .capture import (
    capture_agent_knowledge,
    capture_project_knowledge,
    auto_generate_template,
)

__all__ = [
    # Types
    "KnowledgeEntryType",
    # Embeddings
    "generate_embedding",
    "compute_similarity",
    # Base operations
    "store_knowledge",
    "query_knowledge",
    "get_relevant_knowledge",
    "store_architecture_decision",
    "store_qa_finding",
    "store_prompt_result",
    "store_code_pattern",
    "store_user_preference",
    "update_knowledge_quality_score",
    # Capture
    "capture_agent_knowledge",
    "capture_project_knowledge",
    "auto_generate_template",
]
