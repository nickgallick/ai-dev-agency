"""
Phase 11C: Queue API Routes

Endpoints for project queue management:
- Get queue status
- Add to queue
- Remove from queue
- Reprioritize
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from models.project import Project
from task_queue.manager import (
    QueueManager,
    QueuePriority,
    get_queue_manager
)


router = APIRouter(prefix="/queue", tags=["queue"])


# Request/Response models
class EnqueueRequest(BaseModel):
    project_id: str = Field(..., description="Project UUID")
    priority: str = Field(
        default="normal",
        description="Priority level: urgent, normal, background"
    )


class ReprioritizeRequest(BaseModel):
    priority: str = Field(..., description="New priority level")


class QueueStatusResponse(BaseModel):
    queue_length: int
    active_count: int
    max_concurrent: int
    has_capacity: bool
    queue_items: list
    active_projects: list


class ProjectQueueStatus(BaseModel):
    project_id: str
    in_queue: bool
    position: Optional[int]
    priority: Optional[str]
    estimated_wait_seconds: Optional[float]


# Endpoints
@router.get("/status", response_model=QueueStatusResponse)
async def get_queue_status():
    """
    Get full queue status.
    
    Returns queue length, active projects, and all queued items.
    """
    manager = get_queue_manager()
    status = manager.get_queue_status()
    
    return QueueStatusResponse(**status)


@router.get("/{project_id}/status", response_model=ProjectQueueStatus)
async def get_project_queue_status(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get queue status for a specific project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    manager = get_queue_manager()
    position = manager.get_queue_position(str(project_id))
    
    if position is None:
        return ProjectQueueStatus(
            project_id=str(project_id),
            in_queue=False,
            position=None,
            priority=None,
            estimated_wait_seconds=None
        )
    
    estimated_wait = manager.get_estimated_wait(str(project_id))
    
    # Get priority from project
    priority = project.queue_priority or "normal"
    
    return ProjectQueueStatus(
        project_id=str(project_id),
        in_queue=True,
        position=position,
        priority=priority,
        estimated_wait_seconds=estimated_wait
    )


@router.post("/enqueue")
async def enqueue_project(
    request: EnqueueRequest,
    db: Session = Depends(get_db)
):
    """
    Add a project to the queue.
    
    Priority levels:
    - urgent: Processed immediately (jumps queue)
    - normal: Standard FIFO processing
    - background: Yields to higher priorities
    """
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Validate priority
    try:
        priority = QueuePriority(request.priority)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority. Must be one of: {[p.value for p in QueuePriority]}"
        )
    
    manager = get_queue_manager()
    
    # Add to queue
    position, estimated_wait = manager.enqueue_project(
        project_id=request.project_id,
        priority=priority,
        metadata={
            "name": project.name,
            "type": project.project_type.value if project.project_type else None,
            "brief": project.brief[:100] if project.brief else None
        }
    )
    
    # Update project queue fields
    from datetime import datetime
    project.queue_priority = priority.value
    project.queue_position = position
    project.queued_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "project_id": request.project_id,
        "position": position,
        "priority": priority.value,
        "estimated_wait_seconds": estimated_wait
    }


@router.delete("/{project_id}")
async def remove_from_queue(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Remove a project from the queue.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    manager = get_queue_manager()
    removed = manager.remove_from_queue(str(project_id))
    
    if removed:
        project.queue_position = None
        project.queued_at = None
        db.commit()
    
    return {
        "success": removed,
        "message": "Removed from queue" if removed else "Project was not in queue"
    }


@router.post("/{project_id}/reprioritize")
async def reprioritize_project(
    project_id: UUID,
    request: ReprioritizeRequest,
    db: Session = Depends(get_db)
):
    """
    Change the priority of a queued project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Validate priority
    try:
        priority = QueuePriority(request.priority)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority. Must be one of: {[p.value for p in QueuePriority]}"
        )
    
    manager = get_queue_manager()
    success = manager.reprioritize(str(project_id), priority)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project not found in queue"
        )
    
    # Update project
    project.queue_priority = priority.value
    
    # Get new position
    new_position = manager.get_queue_position(str(project_id))
    project.queue_position = new_position
    
    db.commit()
    
    return {
        "success": True,
        "project_id": str(project_id),
        "new_priority": priority.value,
        "new_position": new_position
    }


class MoveRequest(BaseModel):
    direction: str = Field(..., description="'up' or 'down'")


@router.post("/{project_id}/move")
async def move_project_in_queue(
    project_id: UUID,
    request: MoveRequest,
    db: Session = Depends(get_db)
):
    """Move a queued project up or down one position."""
    if request.direction not in ("up", "down"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="direction must be 'up' or 'down'"
        )

    manager = get_queue_manager()
    success = manager.move_in_queue(str(project_id), request.direction)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot move project (not in queue or already at boundary)"
        )

    new_position = manager.get_queue_position(str(project_id))
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.queue_position = new_position
        db.commit()

    return {
        "success": True,
        "project_id": str(project_id),
        "new_position": new_position,
    }


@router.get("/stats")
async def get_queue_stats():
    """
    Get queue statistics and worker status.
    """
    manager = get_queue_manager()
    status = manager.get_queue_status()
    
    # Calculate stats
    urgent_count = sum(
        1 for item in status.get("queue_items", [])
        if item.get("priority") == "urgent"
    )
    normal_count = sum(
        1 for item in status.get("queue_items", [])
        if item.get("priority") == "normal"
    )
    background_count = sum(
        1 for item in status.get("queue_items", [])
        if item.get("priority") == "background"
    )
    
    return {
        "queue_length": status.get("queue_length", 0),
        "active_count": status.get("active_count", 0),
        "max_concurrent": status.get("max_concurrent", 2),
        "capacity_available": status.get("has_capacity", True),
        "by_priority": {
            "urgent": urgent_count,
            "normal": normal_count,
            "background": background_count
        },
        "average_wait_seconds": 300 * (status.get("queue_length", 0) / max(status.get("max_concurrent", 2), 1))
    }
