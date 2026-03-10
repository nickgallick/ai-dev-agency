"""Phase 11B: Knowledge Base API

API routes for interacting with the knowledge base.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from models.database import get_db
from models.knowledge_base import KnowledgeBase
from knowledge.base import (
    query_knowledge,
    store_user_preference,
    get_knowledge_stats,
    update_knowledge_quality_score,
)
from knowledge.types import KnowledgeEntryType, KnowledgeStats, KnowledgeEntry

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# Pydantic models

class PreferenceCreate(BaseModel):
    title: str
    preference: str
    category: str  # tech_stack, design, deployment, code_style, etc.
    tags: Optional[List[str]] = None


class SearchQuery(BaseModel):
    query: str
    entry_types: Optional[List[str]] = None
    project_type: Optional[str] = None
    industry: Optional[str] = None
    agent_name: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    min_quality_score: Optional[float] = None
    limit: int = 10


class KnowledgeEntryResponse(BaseModel):
    id: str
    entry_type: str
    title: str
    content: str
    project_id: Optional[str]
    project_type: Optional[str]
    industry: Optional[str]
    tech_stack: Optional[List[str]]
    agent_name: Optional[str]
    quality_score: Optional[float]
    usage_count: int
    last_used_at: Optional[str]
    created_at: Optional[str]
    tags: Optional[List[str]]
    similarity_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class KnowledgeStatsResponse(BaseModel):
    total_entries: int
    entries_by_type: dict
    entries_by_agent: dict
    entries_by_project_type: dict
    average_quality_score: float
    most_used_entries: List[dict]
    recent_entries: List[dict]


# API Routes

@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_stats(
    db: Session = Depends(get_db),
):
    """Get knowledge base statistics."""
    stats = get_knowledge_stats(db)
    return KnowledgeStatsResponse(
        total_entries=stats.total_entries,
        entries_by_type=stats.entries_by_type,
        entries_by_agent=stats.entries_by_agent,
        entries_by_project_type=stats.entries_by_project_type,
        average_quality_score=stats.average_quality_score,
        most_used_entries=stats.most_used_entries,
        recent_entries=stats.recent_entries,
    )


@router.post("/search", response_model=List[KnowledgeEntryResponse])
async def search_knowledge(
    search: SearchQuery,
    db: Session = Depends(get_db),
):
    """Search the knowledge base with semantic + metadata filtering."""
    # Convert entry type strings to enums
    entry_types = None
    if search.entry_types:
        entry_types = [
            KnowledgeEntryType(t) for t in search.entry_types
            if t in [e.value for e in KnowledgeEntryType]
        ]
    
    results = await query_knowledge(
        db=db,
        query_text=search.query,
        entry_types=entry_types,
        project_type=search.project_type,
        industry=search.industry,
        agent_name=search.agent_name,
        tech_stack=search.tech_stack,
        min_quality_score=search.min_quality_score,
        limit=search.limit,
    )
    
    return [
        KnowledgeEntryResponse(
            id=r.entry.id,
            entry_type=r.entry.entry_type.value,
            title=r.entry.title,
            content=r.entry.content,
            project_id=r.entry.project_id,
            project_type=r.entry.project_type,
            industry=r.entry.industry,
            tech_stack=r.entry.tech_stack,
            agent_name=r.entry.agent_name,
            quality_score=r.entry.quality_score,
            usage_count=r.entry.usage_count,
            last_used_at=r.entry.last_used_at.isoformat() if r.entry.last_used_at else None,
            created_at=r.entry.created_at.isoformat() if r.entry.created_at else None,
            tags=r.entry.tags,
            similarity_score=r.similarity_score,
        )
        for r in results
    ]


@router.post("/preference", response_model=KnowledgeEntryResponse)
async def store_preference(
    preference: PreferenceCreate,
    db: Session = Depends(get_db),
):
    """Store a user preference in the knowledge base."""
    entry = await store_user_preference(
        db=db,
        title=preference.title,
        preference=preference.preference,
        category=preference.category,
        tags=preference.tags,
    )
    
    return KnowledgeEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type,
        title=entry.title,
        content=entry.content,
        project_id=entry.project_id,
        project_type=entry.project_type,
        industry=entry.industry,
        tech_stack=entry.tech_stack,
        agent_name=entry.agent_name,
        quality_score=entry.quality_score,
        usage_count=entry.usage_count,
        last_used_at=entry.last_used_at.isoformat() if entry.last_used_at else None,
        created_at=entry.created_at.isoformat() if entry.created_at else None,
        tags=entry.tags,
    )


@router.get("/entries", response_model=List[KnowledgeEntryResponse])
async def list_entries(
    entry_type: Optional[str] = Query(None, description="Filter by entry type"),
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List knowledge base entries with filtering."""
    query = db.query(KnowledgeBase)
    
    if entry_type:
        query = query.filter(KnowledgeBase.entry_type == entry_type)
    if agent_name:
        query = query.filter(KnowledgeBase.agent_name == agent_name)
    if project_type:
        query = query.filter(KnowledgeBase.project_type == project_type)
    
    # Order by created_at desc (newest first)
    query = query.order_by(KnowledgeBase.created_at.desc())
    
    entries = query.offset(offset).limit(limit).all()
    
    return [
        KnowledgeEntryResponse(
            id=e.id,
            entry_type=e.entry_type,
            title=e.title,
            content=e.content,
            project_id=e.project_id,
            project_type=e.project_type,
            industry=e.industry,
            tech_stack=e.tech_stack,
            agent_name=e.agent_name,
            quality_score=e.quality_score,
            usage_count=e.usage_count,
            last_used_at=e.last_used_at.isoformat() if e.last_used_at else None,
            created_at=e.created_at.isoformat() if e.created_at else None,
            tags=e.tags,
        )
        for e in entries
    ]


@router.get("/entry/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_entry(
    entry_id: str,
    db: Session = Depends(get_db),
):
    """Get a knowledge entry by ID."""
    entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return KnowledgeEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type,
        title=entry.title,
        content=entry.content,
        project_id=entry.project_id,
        project_type=entry.project_type,
        industry=entry.industry,
        tech_stack=entry.tech_stack,
        agent_name=entry.agent_name,
        quality_score=entry.quality_score,
        usage_count=entry.usage_count,
        last_used_at=entry.last_used_at.isoformat() if entry.last_used_at else None,
        created_at=entry.created_at.isoformat() if entry.created_at else None,
        tags=entry.tags,
    )


@router.put("/entry/{entry_id}/quality")
async def update_quality(
    entry_id: str,
    quality_score: float = Query(..., ge=0, le=1, description="Quality score 0-1"),
    db: Session = Depends(get_db),
):
    """Update the quality score of a knowledge entry."""
    entry = await update_knowledge_quality_score(db, entry_id, quality_score)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {
        "status": "updated",
        "id": entry_id,
        "new_quality_score": entry.quality_score,
    }


@router.delete("/entry/{entry_id}")
async def delete_entry(
    entry_id: str,
    db: Session = Depends(get_db),
):
    """Delete a knowledge entry."""
    entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    db.delete(entry)
    db.commit()
    
    return {"status": "deleted", "id": entry_id}


@router.get("/types")
async def get_entry_types():
    """Get all available knowledge entry types."""
    return {
        "types": [
            {"value": t.value, "name": t.name.replace("_", " ").title()}
            for t in KnowledgeEntryType
        ]
    }
