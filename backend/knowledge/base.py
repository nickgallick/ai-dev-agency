"""Phase 11B: Knowledge Base Core Functions

Core functions for storing and querying the knowledge base.
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc
import logging

from models.knowledge_base import KnowledgeBase
from .types import KnowledgeEntryType, KnowledgeEntry, KnowledgeQueryResult, KnowledgeStats
from .embeddings import generate_embedding, compute_similarity

logger = logging.getLogger(__name__)


async def store_knowledge(
    db: Session,
    entry_type: KnowledgeEntryType,
    title: str,
    content: str,
    project_id: Optional[str] = None,
    project_type: Optional[str] = None,
    industry: Optional[str] = None,
    tech_stack: Optional[List[str]] = None,
    agent_name: Optional[str] = None,
    quality_score: Optional[float] = None,
    entry_metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    created_by: Optional[str] = None,
) -> KnowledgeBase:
    """
    Store a knowledge entry with embedding.
    
    Args:
        db: Database session
        entry_type: Type of knowledge entry
        title: Short title/summary
        content: Full content to store
        project_id: Associated project ID
        project_type: Type of project
        industry: Industry category
        tech_stack: List of technologies
        agent_name: Agent that generated this knowledge
        quality_score: Quality score 0-1
        entry_metadata: Additional metadata
        tags: Tags for categorization
        created_by: User ID who created this
        
    Returns:
        Created KnowledgeBase entry
    """
    # Generate embedding for the content
    embedding_text = f"{title}\n\n{content}"
    embedding = await generate_embedding(embedding_text)
    
    entry = KnowledgeBase(
        id=str(uuid.uuid4()),
        entry_type=entry_type.value,
        title=title,
        content=content,
        embedding=embedding,
        project_id=project_id,
        project_type=project_type,
        industry=industry,
        tech_stack=tech_stack,
        agent_name=agent_name,
        quality_score=quality_score,
        entry_metadata=entry_metadata,
        tags=tags,
        created_by=created_by,
    )
    
    db.add(entry)
    db.commit()
    db.refresh(entry)
    
    logger.info(f"Stored knowledge entry: {entry.id} ({entry_type.value})")
    return entry


async def query_knowledge(
    db: Session,
    query_text: str,
    entry_types: Optional[List[KnowledgeEntryType]] = None,
    project_type: Optional[str] = None,
    industry: Optional[str] = None,
    agent_name: Optional[str] = None,
    tech_stack: Optional[List[str]] = None,
    min_quality_score: Optional[float] = None,
    limit: int = 10,
) -> List[KnowledgeQueryResult]:
    """
    Hybrid search: semantic similarity + metadata filtering.
    
    Args:
        db: Database session
        query_text: Text to search for
        entry_types: Filter by entry types
        project_type: Filter by project type
        industry: Filter by industry
        agent_name: Filter by agent name
        tech_stack: Filter by tech stack (any match)
        min_quality_score: Minimum quality score
        limit: Maximum results to return
        
    Returns:
        List of matching entries with similarity scores
    """
    # Generate embedding for query
    query_embedding = await generate_embedding(query_text)
    
    # Build base query
    query = db.query(KnowledgeBase)
    
    # Apply metadata filters
    if entry_types:
        query = query.filter(KnowledgeBase.entry_type.in_([t.value for t in entry_types]))
    if project_type:
        query = query.filter(KnowledgeBase.project_type == project_type)
    if industry:
        query = query.filter(KnowledgeBase.industry == industry)
    if agent_name:
        query = query.filter(KnowledgeBase.agent_name == agent_name)
    if min_quality_score:
        query = query.filter(KnowledgeBase.quality_score >= min_quality_score)
    if tech_stack:
        # Filter entries that have any of the specified tech stack items
        query = query.filter(KnowledgeBase.tech_stack.op('&&')(tech_stack))
    
    # Get all matching entries
    entries = query.all()
    
    # Compute similarity scores and sort
    results = []
    for entry in entries:
        if entry.embedding and query_embedding:
            similarity = compute_similarity(query_embedding, entry.embedding)
        else:
            # Fall back to keyword matching
            similarity = _keyword_similarity(query_text, f"{entry.title} {entry.content}")
        
        results.append(KnowledgeQueryResult(
            entry=KnowledgeEntry(
                id=entry.id,
                entry_type=KnowledgeEntryType(entry.entry_type),
                title=entry.title,
                content=entry.content,
                project_id=entry.project_id,
                project_type=entry.project_type,
                industry=entry.industry,
                tech_stack=entry.tech_stack,
                agent_name=entry.agent_name,
                quality_score=entry.quality_score,
                usage_count=entry.usage_count,
                last_used_at=entry.last_used_at,
                created_at=entry.created_at,
                metadata=entry.entry_metadata,
                tags=entry.tags,
            ),
            similarity_score=similarity,
        ))
    
    # Sort by similarity and limit
    results.sort(key=lambda x: x.similarity_score, reverse=True)
    return results[:limit]


def _keyword_similarity(query: str, content: str) -> float:
    """Simple keyword-based similarity as fallback."""
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    if not query_words:
        return 0.0
    overlap = len(query_words & content_words)
    return overlap / len(query_words)


async def get_relevant_knowledge(
    db: Session,
    agent_name: str,
    context: Dict[str, Any],
    limit: int = 5,
) -> List[KnowledgeQueryResult]:
    """
    Get relevant knowledge for a specific agent.
    
    Args:
        db: Database session
        agent_name: Name of the agent requesting knowledge
        context: Context including project_type, industry, brief, etc.
        limit: Maximum results
        
    Returns:
        List of relevant knowledge entries
    """
    # Build query text from context
    query_parts = []
    if context.get("brief"):
        query_parts.append(context["brief"])
    if context.get("project_type"):
        query_parts.append(f"Project type: {context['project_type']}")
    if context.get("industry"):
        query_parts.append(f"Industry: {context['industry']}")
    if context.get("features"):
        query_parts.append(f"Features: {', '.join(context['features'])}")
    
    query_text = "\n".join(query_parts) if query_parts else agent_name
    
    # Determine which entry types are relevant for this agent
    agent_knowledge_types = {
        "intake": [KnowledgeEntryType.USER_PREFERENCE, KnowledgeEntryType.REJECTION_REASON],
        "research": [KnowledgeEntryType.RESEARCH_OUTPUT, KnowledgeEntryType.BRAND_GUIDELINE],
        "architect": [KnowledgeEntryType.ARCHITECTURE_DECISION, KnowledgeEntryType.CODE_PATTERN],
        "design_system": [KnowledgeEntryType.DESIGN_TOKEN, KnowledgeEntryType.BRAND_GUIDELINE],
        "code_generation": [KnowledgeEntryType.PROMPT_RESULT, KnowledgeEntryType.CODE_PATTERN],
        "security": [KnowledgeEntryType.SECURITY_FINDING, KnowledgeEntryType.CODE_PATTERN],
        "qa_testing": [KnowledgeEntryType.QA_FINDING, KnowledgeEntryType.CODE_PATTERN],
        "deployment": [KnowledgeEntryType.DEPLOYMENT_CONFIG, KnowledgeEntryType.COST_DATA],
        "code_review": [KnowledgeEntryType.CODE_PATTERN, KnowledgeEntryType.REJECTION_REASON],
        "project_manager": [KnowledgeEntryType.REJECTION_REASON, KnowledgeEntryType.QA_FINDING],
    }
    
    entry_types = agent_knowledge_types.get(agent_name, None)
    
    results = await query_knowledge(
        db=db,
        query_text=query_text,
        entry_types=entry_types,
        project_type=context.get("project_type"),
        industry=context.get("industry"),
        tech_stack=context.get("tech_stack"),
        min_quality_score=0.6,  # Only high-quality knowledge
        limit=limit,
    )
    
    # Update usage statistics
    for result in results:
        entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == result.entry.id).first()
        if entry:
            entry.usage_count += 1
            entry.last_used_at = datetime.utcnow()
    db.commit()
    
    return results


# Convenience functions for specific knowledge types

async def store_architecture_decision(
    db: Session,
    title: str,
    decision: str,
    rationale: str,
    project_id: Optional[str] = None,
    project_type: Optional[str] = None,
    tech_stack: Optional[List[str]] = None,
    **kwargs,
) -> KnowledgeBase:
    """Store an architecture decision."""
    content = f"Decision: {decision}\n\nRationale: {rationale}"
    return await store_knowledge(
        db=db,
        entry_type=KnowledgeEntryType.ARCHITECTURE_DECISION,
        title=title,
        content=content,
        project_id=project_id,
        project_type=project_type,
        tech_stack=tech_stack,
        agent_name="architect",
        **kwargs,
    )


async def store_qa_finding(
    db: Session,
    title: str,
    bug_description: str,
    fix_applied: str,
    project_id: Optional[str] = None,
    **kwargs,
) -> KnowledgeBase:
    """Store a QA finding with its fix."""
    content = f"Bug: {bug_description}\n\nFix: {fix_applied}"
    return await store_knowledge(
        db=db,
        entry_type=KnowledgeEntryType.QA_FINDING,
        title=title,
        content=content,
        project_id=project_id,
        agent_name="qa_testing",
        **kwargs,
    )


async def store_prompt_result(
    db: Session,
    title: str,
    prompt: str,
    result_quality: float,
    project_type: Optional[str] = None,
    **kwargs,
) -> KnowledgeBase:
    """Store a successful prompt for code generation."""
    return await store_knowledge(
        db=db,
        entry_type=KnowledgeEntryType.PROMPT_RESULT,
        title=title,
        content=prompt,
        project_type=project_type,
        quality_score=result_quality,
        agent_name="code_generation",
        **kwargs,
    )


async def store_code_pattern(
    db: Session,
    title: str,
    pattern: str,
    usage_context: str,
    tech_stack: Optional[List[str]] = None,
    **kwargs,
) -> KnowledgeBase:
    """Store a reusable code pattern."""
    content = f"Pattern:\n```\n{pattern}\n```\n\nUsage: {usage_context}"
    return await store_knowledge(
        db=db,
        entry_type=KnowledgeEntryType.CODE_PATTERN,
        title=title,
        content=content,
        tech_stack=tech_stack,
        agent_name="code_review",
        **kwargs,
    )


async def store_user_preference(
    db: Session,
    title: str,
    preference: str,
    category: str,
    created_by: Optional[str] = None,
    **kwargs,
) -> KnowledgeBase:
    """Store a user preference."""
    return await store_knowledge(
        db=db,
        entry_type=KnowledgeEntryType.USER_PREFERENCE,
        title=title,
        content=preference,
        entry_metadata={"category": category},
        created_by=created_by,
        quality_score=1.0,  # User preferences are always relevant
        **kwargs,
    )


async def update_knowledge_quality_score(
    db: Session,
    entry_id: str,
    new_score: float,
) -> Optional[KnowledgeBase]:
    """
    Update the quality score of a knowledge entry based on downstream acceptance.
    
    Args:
        db: Database session
        entry_id: Knowledge entry ID
        new_score: New quality score (0-1)
        
    Returns:
        Updated entry or None
    """
    entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == entry_id).first()
    if entry:
        # Weighted average of old and new score
        if entry.quality_score:
            entry.quality_score = (entry.quality_score * 0.7) + (new_score * 0.3)
        else:
            entry.quality_score = new_score
        db.commit()
        db.refresh(entry)
        return entry
    return None


def get_knowledge_stats(db: Session) -> KnowledgeStats:
    """
    Get statistics about the knowledge base.
    
    Args:
        db: Database session
        
    Returns:
        KnowledgeStats with aggregated data
    """
    # Total entries
    total = db.query(func.count(KnowledgeBase.id)).scalar() or 0
    
    # Entries by type
    by_type = dict(
        db.query(KnowledgeBase.entry_type, func.count(KnowledgeBase.id))
        .group_by(KnowledgeBase.entry_type)
        .all()
    )
    
    # Entries by agent
    by_agent = dict(
        db.query(KnowledgeBase.agent_name, func.count(KnowledgeBase.id))
        .filter(KnowledgeBase.agent_name.isnot(None))
        .group_by(KnowledgeBase.agent_name)
        .all()
    )
    
    # Entries by project type
    by_project_type = dict(
        db.query(KnowledgeBase.project_type, func.count(KnowledgeBase.id))
        .filter(KnowledgeBase.project_type.isnot(None))
        .group_by(KnowledgeBase.project_type)
        .all()
    )
    
    # Average quality score
    avg_score = db.query(func.avg(KnowledgeBase.quality_score)).scalar() or 0.0
    
    # Most used entries
    most_used = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.usage_count > 0)
        .order_by(desc(KnowledgeBase.usage_count))
        .limit(10)
        .all()
    )
    
    # Recent entries
    recent = (
        db.query(KnowledgeBase)
        .order_by(desc(KnowledgeBase.created_at))
        .limit(10)
        .all()
    )
    
    return KnowledgeStats(
        total_entries=total,
        entries_by_type=by_type,
        entries_by_agent=by_agent,
        entries_by_project_type=by_project_type,
        average_quality_score=float(avg_score),
        most_used_entries=[e.to_dict() for e in most_used],
        recent_entries=[e.to_dict() for e in recent],
    )
