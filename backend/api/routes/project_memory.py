"""Project Memory API (#12)

Persistent project-level memory — decisions, preferences, and context
that survive across pipeline runs. Uses the knowledge_base table with
project_id scoping.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from models.project import Project
from models.knowledge_base import KnowledgeBase

router = APIRouter(prefix="/projects/{project_id}/memory", tags=["project-memory"])


# ── Request / Response models ──────────────────────────────────────

class MemoryEntryCreate(BaseModel):
    category: str = Field(
        ...,
        description="Category: decision, preference, context, lesson, constraint",
    )
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=10000)
    tags: Optional[List[str]] = None


class MemoryEntryUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, max_length=10000)
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class MemoryEntryResponse(BaseModel):
    id: str
    category: str
    title: str
    content: str
    agent_name: Optional[str]
    quality_score: Optional[float]
    usage_count: int
    tags: Optional[List[str]]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


MEMORY_CATEGORIES = [
    "decision",       # Architecture/tech decisions made during builds
    "preference",     # User style/tool preferences
    "context",        # Background context about the project
    "lesson",         # Lessons learned from previous runs
    "constraint",     # Hard constraints / requirements
]

# Map categories to knowledge_base entry_type values
_CATEGORY_TO_ENTRY_TYPE = {
    "decision": "architecture_decision",
    "preference": "user_preference",
    "context": "prompt_result",
    "lesson": "qa_finding",
    "constraint": "code_pattern",
}

_ENTRY_TYPE_TO_CATEGORY = {v: k for k, v in _CATEGORY_TO_ENTRY_TYPE.items()}


def _entry_type_for(category: str) -> str:
    return _CATEGORY_TO_ENTRY_TYPE.get(category, "user_preference")


def _category_for(entry_type: str) -> str:
    return _ENTRY_TYPE_TO_CATEGORY.get(entry_type, "context")


def _to_response(entry: KnowledgeBase) -> MemoryEntryResponse:
    return MemoryEntryResponse(
        id=str(entry.id),
        category=_category_for(entry.entry_type),
        title=entry.title,
        content=entry.content,
        agent_name=entry.agent_name,
        quality_score=entry.quality_score,
        usage_count=entry.usage_count,
        tags=entry.tags,
        created_at=entry.created_at.isoformat() if entry.created_at else None,
        updated_at=entry.updated_at.isoformat() if entry.updated_at else None,
    )


def _validate_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("", response_model=List[MemoryEntryResponse])
async def list_project_memory(
    project_id: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List all memory entries for a project."""
    _validate_project(db, project_id)

    query = db.query(KnowledgeBase).filter(KnowledgeBase.project_id == project_id)

    if category and category in MEMORY_CATEGORIES:
        query = query.filter(
            KnowledgeBase.entry_type == _entry_type_for(category)
        )

    # Memory entries are tagged with "project_memory"
    query = query.filter(KnowledgeBase.tags.contains(["project_memory"]))
    entries = query.order_by(KnowledgeBase.created_at.desc()).limit(limit).all()

    return [_to_response(e) for e in entries]


@router.post("", response_model=MemoryEntryResponse, status_code=201)
async def create_memory_entry(
    project_id: str,
    body: MemoryEntryCreate,
    db: Session = Depends(get_db),
):
    """Create a new memory entry for a project."""
    project = _validate_project(db, project_id)

    if body.category not in MEMORY_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {MEMORY_CATEGORIES}",
        )

    tags = list(body.tags or [])
    if "project_memory" not in tags:
        tags.append("project_memory")

    entry = KnowledgeBase(
        id=uuid.uuid4(),
        entry_type=_entry_type_for(body.category),
        title=body.title,
        content=body.content,
        project_id=project_id,
        project_type=project.project_type.value if project.project_type else None,
        quality_score=0.8,
        usage_count=0,
        tags=tags,
        entry_metadata={"source": "project_memory", "category": body.category},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return _to_response(entry)


@router.put("/{entry_id}", response_model=MemoryEntryResponse)
async def update_memory_entry(
    project_id: str,
    entry_id: str,
    body: MemoryEntryUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing memory entry."""
    _validate_project(db, project_id)

    entry = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.id == entry_id, KnowledgeBase.project_id == project_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Memory entry not found")

    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    if body.category is not None and body.category in MEMORY_CATEGORIES:
        entry.entry_type = _entry_type_for(body.category)
    if body.tags is not None:
        tags = list(body.tags)
        if "project_memory" not in tags:
            tags.append("project_memory")
        entry.tags = tags

    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)

    return _to_response(entry)


@router.delete("/{entry_id}")
async def delete_memory_entry(
    project_id: str,
    entry_id: str,
    db: Session = Depends(get_db),
):
    """Delete a memory entry."""
    _validate_project(db, project_id)

    entry = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.id == entry_id, KnowledgeBase.project_id == project_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Memory entry not found")

    db.delete(entry)
    db.commit()

    return {"status": "deleted", "id": entry_id}


@router.get("/categories")
async def get_memory_categories():
    """Get available memory categories."""
    return {
        "categories": [
            {"value": "decision", "label": "Architecture Decision", "description": "Tech and design decisions made during builds"},
            {"value": "preference", "label": "Preference", "description": "Style, tool, and workflow preferences"},
            {"value": "context", "label": "Context", "description": "Background information about the project"},
            {"value": "lesson", "label": "Lesson Learned", "description": "Insights from previous pipeline runs"},
            {"value": "constraint", "label": "Constraint", "description": "Hard requirements and limitations"},
        ]
    }


@router.get("/summary")
async def get_memory_summary(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get a summary of project memory for pipeline context injection."""
    _validate_project(db, project_id)

    entries = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.project_id == project_id,
            KnowledgeBase.tags.contains(["project_memory"]),
        )
        .order_by(KnowledgeBase.quality_score.desc().nullslast())
        .all()
    )

    by_category: dict = {}
    for entry in entries:
        cat = _category_for(entry.entry_type)
        by_category.setdefault(cat, []).append({
            "title": entry.title,
            "content": entry.content,
        })

    return {
        "project_id": project_id,
        "total_entries": len(entries),
        "by_category": by_category,
    }
