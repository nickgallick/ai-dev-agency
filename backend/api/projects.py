"""Project API routes.

Phase 11A: Enhanced with Smart Adaptive Intake System.
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import get_db, Project, ProjectType, ProjectStatus, CostProfile
from models.requirements import ProjectRequirements, BriefAnalysis
from orchestration import PipelineExecutor
from agents.intake import IntakeAgent

router = APIRouter(prefix="/projects", tags=["projects"])


# ============ Request/Response Models ============

class BriefAnalysisRequest(BaseModel):
    """Request model for brief analysis."""
    brief: str = Field(..., min_length=1, description="Project brief to analyze")


class BriefAnalysisResponse(BaseModel):
    """Response model for brief analysis."""
    detected_project_type: Optional[str] = None
    confidence: float = 0.0
    suggested_features: List[str] = []
    suggested_pages: List[str] = []
    detected_industry: Optional[str] = None
    complexity_estimate: str = "simple"
    cost_estimate: Dict[str, str] = {}
    warnings: List[str] = []


class ProjectCreate(BaseModel):
    """Request model for creating a project."""
    brief: str = Field(..., min_length=10, description="Project description")
    name: Optional[str] = Field(None, description="Optional project name")
    cost_profile: str = Field("balanced", description="Cost profile: budget, balanced, premium")
    project_type: Optional[str] = Field(None, description="Project type override")
    reference_urls: Optional[List[str]] = Field(None, description="Reference URLs for inspiration")
    tech_stack_override: Optional[dict] = Field(None, description="Override tech stack")
    # Phase 10: Integration fields
    figma_url: Optional[str] = Field(None, description="Optional Figma design file URL")
    integration_config: Optional[dict] = Field(None, description="Integration configuration")
    # Phase 11A: Structured requirements
    requirements: Optional[dict] = Field(None, description="Full structured requirements")


class ProjectResponse(BaseModel):
    """Response model for project data."""
    id: str
    brief: str
    name: Optional[str]
    project_type: Optional[str]
    status: str
    cost_profile: str
    cost_estimate: Optional[float]
    github_repo: Optional[str]
    live_url: Optional[str]
    # Phase 10: Integration fields
    figma_url: Optional[str] = None
    integration_config: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============ Brief Analysis Endpoint (Phase 11A) ============

@router.post("/analyze-brief", response_model=BriefAnalysisResponse)
async def analyze_brief(request: BriefAnalysisRequest):
    """
    Phase 11A: Real-time brief analysis for the Smart Adaptive Intake form.
    
    This endpoint is called as the user types their project brief (debounced).
    It returns auto-detected project type, suggested features, pages, and cost estimates.
    Uses fast keyword-based detection (no LLM call) for quick response times.
    """
    intake_agent = IntakeAgent()
    
    try:
        analysis = await intake_agent.analyze_brief(request.brief)
        return BriefAnalysisResponse(**analysis)
    except Exception as e:
        # Return empty analysis on error
        return BriefAnalysisResponse(
            warnings=[f"Analysis failed: {str(e)}"]
        )


# ============ Project CRUD Endpoints ============

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
):
    """Create a new project and start the pipeline via the queue."""
    # Create project record
    project_id = uuid.uuid4()

    # Determine project type from requirements or explicit field
    project_type = None
    if project.project_type:
        try:
            project_type = ProjectType(project.project_type)
        except ValueError:
            pass
    elif project.requirements and project.requirements.get("project_type"):
        try:
            project_type = ProjectType(project.requirements["project_type"])
        except ValueError:
            pass

    db_project = Project(
        id=project_id,
        brief=project.brief,
        name=project.name,
        project_type=project_type,
        status=ProjectStatus.PENDING,
        cost_profile=CostProfile(project.cost_profile),
        created_at=datetime.utcnow(),
        # Phase 10: Integration fields
        figma_url=project.figma_url,
        integration_config=project.integration_config or {},
        # Phase 11A: Store structured requirements
        requirements=project.requirements or {},
        project_metadata={
            "reference_urls": project.reference_urls or [],
            "tech_stack_override": project.tech_stack_override,
        },
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # Enqueue project for processing by the queue worker
    from task_queue.manager import get_queue_manager
    queue_manager = get_queue_manager()
    queue_manager.enqueue_project(
        project_id=str(project_id),
        metadata={
            "name": project.name,
            "brief": project.brief[:200],
            "cost_profile": project.cost_profile,
        },
    )

    return ProjectResponse(
        id=str(db_project.id),
        brief=db_project.brief,
        name=db_project.name,
        project_type=db_project.project_type.value if db_project.project_type else None,
        status=db_project.status.value,
        cost_profile=db_project.cost_profile.value,
        cost_estimate=db_project.cost_estimate,
        github_repo=db_project.github_repo,
        live_url=db_project.live_url,
        figma_url=db_project.figma_url,
        integration_config=db_project.integration_config,
        created_at=db_project.created_at,
        updated_at=db_project.updated_at,
        completed_at=db_project.completed_at,
    )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[str] = None,
    project_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List all projects with optional filtering."""
    query = db.query(Project)
    
    if status:
        query = query.filter(Project.status == status)
    if project_type:
        query = query.filter(Project.project_type == project_type)
    
    projects = query.order_by(Project.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        ProjectResponse(
            id=str(p.id),
            brief=p.brief,
            name=p.name,
            project_type=p.project_type.value if p.project_type else None,
            status=p.status.value,
            cost_profile=p.cost_profile.value,
            cost_estimate=p.cost_estimate,
            github_repo=p.github_repo,
            live_url=p.live_url,
            figma_url=p.figma_url,
            integration_config=p.integration_config,
            created_at=p.created_at,
            updated_at=p.updated_at,
            completed_at=p.completed_at,
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(
        id=str(project.id),
        brief=project.brief,
        name=project.name,
        project_type=project.project_type.value if project.project_type else None,
        status=project.status.value,
        cost_profile=project.cost_profile.value,
        cost_estimate=project.cost_estimate,
        github_repo=project.github_repo,
        live_url=project.live_url,
        figma_url=project.figma_url,
        integration_config=project.integration_config,
        created_at=project.created_at,
        updated_at=project.updated_at,
        completed_at=project.completed_at,
    )


@router.get("/{project_id}/outputs")
async def get_project_outputs(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get agent outputs for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "project_id": str(project.id),
        "agent_outputs": project.agent_outputs or {},
    }


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Delete a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()


@router.post("/{project_id}/resume")
async def resume_project(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Resume a failed project from its last checkpoint.

    Looks up the latest checkpoint and re-enqueues the project for
    processing. The pipeline executor will automatically pick up
    from where it left off.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status.value not in ("failed", "paused"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume project with status '{project.status.value}'. "
                   f"Only failed or paused projects can be resumed.",
        )

    # Check that a checkpoint exists
    from orchestration.checkpointing import get_latest_checkpoint
    checkpoint = get_latest_checkpoint(db, project_id)
    if not checkpoint:
        raise HTTPException(
            status_code=400,
            detail="No checkpoint found. Project must be restarted from scratch.",
        )

    # Update status back to intake so the worker picks it up
    project.status = ProjectStatus.PENDING
    db.commit()

    # Re-enqueue
    from task_queue.manager import get_queue_manager
    queue_manager = get_queue_manager()
    queue_manager.enqueue_project(
        project_id=str(project_id),
        metadata={
            "name": project.name,
            "brief": (project.brief or "")[:200],
            "cost_profile": project.cost_profile.value if project.cost_profile else "balanced",
            "resume": True,
        },
    )

    return {
        "success": True,
        "project_id": project_id,
        "resumed_from_step": checkpoint["step_number"],
        "resumed_from_agent": checkpoint["agent_name"],
    }


@router.get("/{project_id}/checkpoints")
async def get_project_checkpoints(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get checkpoint history for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from orchestration.checkpointing import get_checkpoint_history
    history = get_checkpoint_history(db, project_id)
    return {"project_id": project_id, "checkpoints": history}


@router.get("/{project_id}/audit-log")
async def get_project_audit_log(
    project_id: str,
    event_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get structured audit log for a project."""
    from models.audit_log import AuditLog

    query = db.query(AuditLog).filter(AuditLog.project_id == project_id)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    entries = query.order_by(AuditLog.timestamp.asc()).limit(limit).all()

    return {
        "project_id": project_id,
        "entries": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "agent_name": e.agent_name,
                "message": e.message,
                "details": e.details,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "duration_ms": e.duration_ms,
            }
            for e in entries
        ],
    }


async def run_pipeline(project_id: str, brief: str, cost_profile: str, requirements: dict = None):
    """Run the pipeline directly (used by queue worker).

    This is an async function that must be called from an active event loop,
    e.g. via the QueueWorker.  Do NOT pass it to BackgroundTasks.add_task()
    because that may not properly schedule the coroutine.
    """
    from models import SessionLocal

    db = SessionLocal()
    try:
        executor = PipelineExecutor(db_session=db)
        await executor.execute(project_id, brief, cost_profile, requirements=requirements or {})
    finally:
        db.close()
