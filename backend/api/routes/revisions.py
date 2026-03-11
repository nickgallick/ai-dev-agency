"""Revisions API routes for project modifications."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import get_db, Project, ProjectStatus
from agents.revision_handler import RevisionHandlerAgent, RevisionScope


router = APIRouter(prefix="/api/projects", tags=["revisions"])


# Request/Response models
class RevisionRequest(BaseModel):
    """Request model for creating a revision."""
    revision_brief: str = Field(..., description="Description of the changes needed")
    priority: str = Field(default="normal", description="Priority: low, normal, high")
    
    class Config:
        json_schema_extra = {
            "example": {
                "revision_brief": "Add a contact form to the homepage with email validation",
                "priority": "normal",
            }
        }


class RevisionScopeResponse(BaseModel):
    """Response model for revision scope analysis."""
    scope_type: str
    affected_files: List[str]
    affected_agents: List[str]
    estimated_cost: float
    risk_level: str
    requires_regression_tests: bool


class RevisionResponse(BaseModel):
    """Response model for a revision."""
    id: str
    project_id: str
    revision_brief: str
    scope: RevisionScopeResponse
    status: str  # pending, in_progress, completed, failed
    created_at: str
    completed_at: Optional[str] = None
    git_commit_sha: Optional[str] = None
    files_modified: List[str] = []
    files_created: List[str] = []
    errors: List[str] = []


class RevisionHistoryItem(BaseModel):
    """A single revision history entry."""
    id: str
    brief: str
    scope_type: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    git_commit_sha: Optional[str] = None
    cost: float = 0.0


class RevisionHistoryResponse(BaseModel):
    """Response model for revision history."""
    project_id: str
    total_revisions: int
    revisions: List[RevisionHistoryItem]


@router.post("/{project_id}/revisions", response_model=RevisionResponse)
async def request_revision(
    project_id: UUID,
    request: RevisionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Request a revision for an existing project.
    
    This endpoint analyzes the revision request and determines:
    - Scope (small_tweak, medium_feature, major_addition)
    - Which files need to be modified
    - Which agents need to be activated
    - Estimated cost and risk level
    """
    # Get the project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if project is in a valid state for revisions
    if project.status not in [ProjectStatus.COMPLETED, ProjectStatus.PAUSED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create revision for project in {project.status} status"
        )
    
    # Create revision handler
    handler = RevisionHandlerAgent(project_id=str(project_id), db_session=db)
    
    # Analyze the revision scope
    try:
        analysis = await handler.execute({
            "revision_brief": request.revision_brief,
            "project_path": project.project_metadata.get("project_path", ""),
            "project_type": project.project_type.value if project.project_type else "web_simple",
            "cost_profile": project.cost_profile.value if project.cost_profile else "balanced",
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze revision: {str(e)}")
    
    scope_data = analysis.get("scope", {})
    
    # Create revision record
    revision_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    revision_record = {
        "id": revision_id,
        "brief": request.revision_brief,
        "scope_type": scope_data.get("type", "medium_feature"),
        "affected_agents": scope_data.get("affected_agents", []),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "priority": request.priority,
    }
    
    # Add to revision history
    revision_history = project.revision_history or []
    revision_history.append(revision_record)
    project.revision_history = revision_history
    
    # Update project status
    project.status = ProjectStatus.PAUSED
    project.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Schedule the revision processing in background
    background_tasks.add_task(
        process_revision,
        project_id=str(project_id),
        revision_id=revision_id,
        revision_brief=request.revision_brief,
        scope=scope_data,
    )
    
    return RevisionResponse(
        id=revision_id,
        project_id=str(project_id),
        revision_brief=request.revision_brief,
        scope=RevisionScopeResponse(
            scope_type=scope_data.get("type", "medium_feature"),
            affected_files=scope_data.get("affected_files", []),
            affected_agents=scope_data.get("affected_agents", []),
            estimated_cost=scope_data.get("estimated_cost", 0.0),
            risk_level=scope_data.get("risk_level", "medium"),
            requires_regression_tests=scope_data.get("requires_regression_tests", True),
        ),
        status="pending",
        created_at=revision_record["created_at"],
    )


@router.get("/{project_id}/revisions", response_model=RevisionHistoryResponse)
async def list_revisions(
    project_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get the revision history for a project.
    
    Returns all past revisions with their status, scope, and git commit references.
    """
    # Get the project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    revision_history = project.revision_history or []
    
    revisions = [
        RevisionHistoryItem(
            id=rev.get("id", "unknown"),
            brief=rev.get("brief", ""),
            scope_type=rev.get("scope_type", "medium_feature"),
            status=rev.get("status", "unknown"),
            created_at=rev.get("created_at", ""),
            completed_at=rev.get("completed_at"),
            git_commit_sha=rev.get("git_commit_sha"),
            cost=rev.get("cost", 0.0),
        )
        for rev in revision_history
    ]
    
    return RevisionHistoryResponse(
        project_id=str(project_id),
        total_revisions=len(revisions),
        revisions=revisions,
    )


@router.get("/{project_id}/revisions/{revision_id}", response_model=RevisionResponse)
async def get_revision(
    project_id: UUID,
    revision_id: str,
    db: Session = Depends(get_db),
):
    """
    Get details of a specific revision.
    """
    # Get the project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    revision_history = project.revision_history or []
    
    # Find the specific revision
    revision = None
    for rev in revision_history:
        if rev.get("id") == revision_id:
            revision = rev
            break
    
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    
    return RevisionResponse(
        id=revision.get("id", "unknown"),
        project_id=str(project_id),
        revision_brief=revision.get("brief", ""),
        scope=RevisionScopeResponse(
            scope_type=revision.get("scope_type", "medium_feature"),
            affected_files=revision.get("affected_files", []),
            affected_agents=revision.get("affected_agents", []),
            estimated_cost=revision.get("estimated_cost", 0.0),
            risk_level=revision.get("risk_level", "medium"),
            requires_regression_tests=revision.get("requires_regression_tests", True),
        ),
        status=revision.get("status", "unknown"),
        created_at=revision.get("created_at", ""),
        completed_at=revision.get("completed_at"),
        git_commit_sha=revision.get("git_commit_sha"),
        files_modified=revision.get("files_modified", []),
        files_created=revision.get("files_created", []),
        errors=revision.get("errors", []),
    )


@router.post("/{project_id}/revisions/{revision_id}/rollback")
async def rollback_revision(
    project_id: UUID,
    revision_id: str,
    db: Session = Depends(get_db),
):
    """
    Rollback to a previous revision using git checkout.
    
    This will restore the codebase to the state at the specified revision.
    """
    # Get the project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    revision_history = project.revision_history or []
    
    # Find the specific revision
    revision = None
    for rev in revision_history:
        if rev.get("id") == revision_id:
            revision = rev
            break
    
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    
    git_sha = revision.get("git_commit_sha")
    if not git_sha:
        raise HTTPException(
            status_code=400, 
            detail="No git commit SHA available for this revision"
        )
    
    project_path = project.project_metadata.get("project_path", "")
    if not project_path:
        raise HTTPException(
            status_code=400,
            detail="Project path not available"
        )
    
    # Create handler and rollback
    handler = RevisionHandlerAgent(project_id=str(project_id), db_session=db)
    success = handler.rollback_to_revision(project_path, git_sha)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to rollback to the specified revision"
        )
    
    # Add rollback record to history
    rollback_record = {
        "id": f"rollback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "brief": f"Rollback to revision {revision_id}",
        "scope_type": "rollback",
        "status": "completed",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "git_commit_sha": git_sha,
        "target_revision": revision_id,
    }
    revision_history.append(rollback_record)
    project.revision_history = revision_history
    project.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully rolled back to revision {revision_id}",
        "rollback_id": rollback_record["id"],
        "git_commit_sha": git_sha,
    }


async def process_revision(
    project_id: str,
    revision_id: str,
    revision_brief: str,
    scope: Dict[str, Any],
):
    """
    Background task to process a revision.

    Activates the necessary agents and applies changes based on scope.
    """
    from models import SessionLocal, Project, ProjectStatus

    db = SessionLocal()
    try:
        # Update revision status to in_progress
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        revision_history = project.revision_history or []
        for rev in revision_history:
            if rev.get("id") == revision_id:
                rev["status"] = "in_progress"
                break
        project.revision_history = revision_history
        project.status = ProjectStatus.PAUSED
        project.updated_at = datetime.utcnow()
        db.commit()

        # Run the revision handler agent
        handler = RevisionHandlerAgent(project_id=project_id, db_session=db)
        result = await handler.execute({
            "revision_brief": revision_brief,
            "project_path": project.project_metadata.get("project_path", "") if project.project_metadata else "",
            "project_type": project.project_type.value if project.project_type else "web_simple",
            "cost_profile": project.cost_profile.value if project.cost_profile else "balanced",
            "scope": scope,
        })

        # Update revision status to completed
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            revision_history = project.revision_history or []
            for rev in revision_history:
                if rev.get("id") == revision_id:
                    success = result.get("success", False) if isinstance(result, dict) else False
                    rev["status"] = "completed" if success else "failed"
                    rev["completed_at"] = datetime.utcnow().isoformat()
                    if isinstance(result, dict):
                        rev["files_modified"] = result.get("files_modified", [])
                        rev["files_created"] = result.get("files_created", [])
                        rev["git_commit_sha"] = result.get("git_commit_sha")
                    break
            project.revision_history = revision_history
            project.status = ProjectStatus.COMPLETED
            project.updated_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                revision_history = project.revision_history or []
                for rev in revision_history:
                    if rev.get("id") == revision_id:
                        rev["status"] = "failed"
                        rev["completed_at"] = datetime.utcnow().isoformat()
                        rev["errors"] = [str(e)]
                        break
                project.revision_history = revision_history
                project.status = ProjectStatus.COMPLETED
                project.updated_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
