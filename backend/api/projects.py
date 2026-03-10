"""Project API routes."""
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import get_db, Project, ProjectType, ProjectStatus, CostProfile
from orchestration import PipelineExecutor

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    """Request model for creating a project."""
    brief: str = Field(..., min_length=10, description="Project description")
    name: Optional[str] = Field(None, description="Optional project name")
    cost_profile: str = Field("balanced", description="Cost profile: budget, balanced, premium")
    reference_urls: Optional[List[str]] = Field(None, description="Reference URLs for inspiration")
    tech_stack_override: Optional[dict] = Field(None, description="Override tech stack")
    # Phase 10: Integration fields
    figma_url: Optional[str] = Field(None, description="Optional Figma design file URL")
    integration_config: Optional[dict] = Field(None, description="Integration configuration")


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


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new project and start the pipeline."""
    # Create project record
    project_id = uuid.uuid4()
    
    db_project = Project(
        id=project_id,
        brief=project.brief,
        name=project.name,
        status=ProjectStatus.PENDING,
        cost_profile=CostProfile(project.cost_profile),
        created_at=datetime.utcnow(),
        # Phase 10: Integration fields
        figma_url=project.figma_url,
        integration_config=project.integration_config or {},
        project_metadata={
            "reference_urls": project.reference_urls or [],
            "tech_stack_override": project.tech_stack_override,
        },
    )
    
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Start pipeline in background
    background_tasks.add_task(
        run_pipeline,
        str(project_id),
        project.brief,
        project.cost_profile,
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


async def run_pipeline(project_id: str, brief: str, cost_profile: str):
    """Run the pipeline in background."""
    from models import SessionLocal
    
    db = SessionLocal()
    try:
        executor = PipelineExecutor(db_session=db)
        await executor.execute(project_id, brief, cost_profile)
    finally:
        db.close()
