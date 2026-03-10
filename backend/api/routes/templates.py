"""Phase 11B: Project Templates API

API routes for managing project templates.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid

from models.database import get_db
from models.project import Project
from models.project_template import ProjectTemplate
from knowledge.capture import auto_generate_template

router = APIRouter(prefix="/api/templates", tags=["templates"])


# Pydantic models for request/response

class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_type: str
    industry: Optional[str] = None
    brief_template: Optional[str] = None
    requirements: Optional[dict] = None
    design_tokens: Optional[dict] = None
    tech_stack: Optional[list] = None
    features: Optional[list] = None
    tags: Optional[List[str]] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    brief_template: Optional[str] = None
    requirements: Optional[dict] = None
    design_tokens: Optional[dict] = None
    tech_stack: Optional[list] = None
    features: Optional[list] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    project_type: str
    industry: Optional[str]
    thumbnail_url: Optional[str]
    brief_template: Optional[str]
    requirements: Optional[dict]
    design_tokens: Optional[dict]
    tech_stack: Optional[list]
    features: Optional[list]
    source_project_id: Optional[str]
    is_auto_generated: bool
    is_public: bool
    qa_score: Optional[float]
    build_success_count: int
    total_usage_count: int
    created_at: Optional[str]
    is_active: bool
    tags: Optional[List[str]]
    
    class Config:
        from_attributes = True


class UseTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    customizations: Optional[dict] = None  # Override specific fields


# API Routes

@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    is_public: bool = Query(True, description="Filter by public visibility"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all templates with optional filtering."""
    query = db.query(ProjectTemplate).filter(ProjectTemplate.is_active == True)
    
    if project_type:
        query = query.filter(ProjectTemplate.project_type == project_type)
    if industry:
        query = query.filter(ProjectTemplate.industry == industry)
    if is_public is not None:
        query = query.filter(ProjectTemplate.is_public == is_public)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (ProjectTemplate.name.ilike(search_term)) |
            (ProjectTemplate.description.ilike(search_term))
        )
    
    # Order by usage count (most popular first)
    query = query.order_by(ProjectTemplate.total_usage_count.desc())
    
    templates = query.offset(offset).limit(limit).all()
    
    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            project_type=t.project_type,
            industry=t.industry,
            thumbnail_url=t.thumbnail_url,
            brief_template=t.brief_template,
            requirements=t.requirements,
            design_tokens=t.design_tokens,
            tech_stack=t.tech_stack,
            features=t.features,
            source_project_id=t.source_project_id,
            is_auto_generated=t.is_auto_generated,
            is_public=t.is_public,
            qa_score=t.qa_score,
            build_success_count=t.build_success_count,
            total_usage_count=t.total_usage_count,
            created_at=t.created_at.isoformat() if t.created_at else None,
            is_active=t.is_active,
            tags=t.tags,
        )
        for t in templates
    ]


@router.post("", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db),
):
    """Create a new template manually."""
    template = ProjectTemplate(
        id=str(uuid.uuid4()),
        name=template_data.name,
        description=template_data.description,
        project_type=template_data.project_type,
        industry=template_data.industry,
        brief_template=template_data.brief_template,
        requirements=template_data.requirements,
        design_tokens=template_data.design_tokens,
        tech_stack=template_data.tech_stack,
        features=template_data.features,
        is_auto_generated=False,
        is_public=True,
        tags=template_data.tags,
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        project_type=template.project_type,
        industry=template.industry,
        thumbnail_url=template.thumbnail_url,
        brief_template=template.brief_template,
        requirements=template.requirements,
        design_tokens=template.design_tokens,
        tech_stack=template.tech_stack,
        features=template.features,
        source_project_id=template.source_project_id,
        is_auto_generated=template.is_auto_generated,
        is_public=template.is_public,
        qa_score=template.qa_score,
        build_success_count=template.build_success_count,
        total_usage_count=template.total_usage_count,
        created_at=template.created_at.isoformat() if template.created_at else None,
        is_active=template.is_active,
        tags=template.tags,
    )


@router.post("/from-project/{project_id}", response_model=TemplateResponse)
async def create_template_from_project(
    project_id: str,
    name: Optional[str] = Query(None, description="Custom template name"),
    db: Session = Depends(get_db),
):
    """Save a completed project as a template."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get QA score from agent outputs if available
    qa_score = 0.8  # Default
    if project.agent_outputs:
        qa_output = project.agent_outputs.get("qa_testing", {})
        if isinstance(qa_output, dict):
            qa_score = qa_output.get("overall_score", qa_output.get("score", 0.8))
    
    template = await auto_generate_template(db, project, qa_score)
    
    if not template:
        # If auto-generation failed (low QA score), create manually
        metadata = project.project_metadata or {}
        requirements = project.requirements or {}
        agent_outputs = project.agent_outputs or {}
        
        template = ProjectTemplate(
            id=str(uuid.uuid4()),
            name=name or f"{project.name} Template",
            description=f"Template from project: {project.description or project.name}",
            project_type=project.project_type.value if project.project_type else "web_simple",
            industry=metadata.get("industry"),
            brief_template=metadata.get("brief", project.description),
            requirements=requirements,
            design_tokens=agent_outputs.get("design_system", {}).get("design_tokens"),
            tech_stack=agent_outputs.get("architect", {}).get("tech_stack"),
            features=requirements.get("core_features", []),
            source_project_id=project.id,
            is_auto_generated=False,
            is_public=True,
            qa_score=qa_score,
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
    
    # Update name if provided
    if name and template.name != name:
        template.name = name
        db.commit()
        db.refresh(template)
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        project_type=template.project_type,
        industry=template.industry,
        thumbnail_url=template.thumbnail_url,
        brief_template=template.brief_template,
        requirements=template.requirements,
        design_tokens=template.design_tokens,
        tech_stack=template.tech_stack,
        features=template.features,
        source_project_id=template.source_project_id,
        is_auto_generated=template.is_auto_generated,
        is_public=template.is_public,
        qa_score=template.qa_score,
        build_success_count=template.build_success_count,
        total_usage_count=template.total_usage_count,
        created_at=template.created_at.isoformat() if template.created_at else None,
        is_active=template.is_active,
        tags=template.tags,
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    """Get a template by ID."""
    template = db.query(ProjectTemplate).filter(ProjectTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        project_type=template.project_type,
        industry=template.industry,
        thumbnail_url=template.thumbnail_url,
        brief_template=template.brief_template,
        requirements=template.requirements,
        design_tokens=template.design_tokens,
        tech_stack=template.tech_stack,
        features=template.features,
        source_project_id=template.source_project_id,
        is_auto_generated=template.is_auto_generated,
        is_public=template.is_public,
        qa_score=template.qa_score,
        build_success_count=template.build_success_count,
        total_usage_count=template.total_usage_count,
        created_at=template.created_at.isoformat() if template.created_at else None,
        is_active=template.is_active,
        tags=template.tags,
    )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    update_data: TemplateUpdate,
    db: Session = Depends(get_db),
):
    """Update a template."""
    template = db.query(ProjectTemplate).filter(ProjectTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(template, key, value)
    
    db.commit()
    db.refresh(template)
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        project_type=template.project_type,
        industry=template.industry,
        thumbnail_url=template.thumbnail_url,
        brief_template=template.brief_template,
        requirements=template.requirements,
        design_tokens=template.design_tokens,
        tech_stack=template.tech_stack,
        features=template.features,
        source_project_id=template.source_project_id,
        is_auto_generated=template.is_auto_generated,
        is_public=template.is_public,
        qa_score=template.qa_score,
        build_success_count=template.build_success_count,
        total_usage_count=template.total_usage_count,
        created_at=template.created_at.isoformat() if template.created_at else None,
        is_active=template.is_active,
        tags=template.tags,
    )


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    """Delete (soft delete) a template."""
    template = db.query(ProjectTemplate).filter(ProjectTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.is_active = False
    db.commit()
    
    return {"status": "deleted", "id": template_id}


@router.post("/{template_id}/use")
async def use_template(
    template_id: str,
    request: UseTemplateRequest,
    db: Session = Depends(get_db),
):
    """Create a new project from a template.
    
    Returns the pre-filled project data for the New Project form.
    """
    template = db.query(ProjectTemplate).filter(
        ProjectTemplate.id == template_id,
        ProjectTemplate.is_active == True,
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Increment usage count
    template.total_usage_count += 1
    db.commit()
    
    # Prepare project data from template
    project_data = {
        "name": request.name,
        "description": request.description or template.description,
        "project_type": template.project_type,
        "brief": template.brief_template,
        "requirements": template.requirements or {},
        "design_tokens": template.design_tokens,
        "tech_stack": template.tech_stack,
        "features": template.features,
        "industry": template.industry,
        "from_template_id": template.id,
    }
    
    # Apply customizations if provided
    if request.customizations:
        for key, value in request.customizations.items():
            if value is not None:
                project_data[key] = value
    
    return {
        "status": "ready",
        "template_id": template.id,
        "project_data": project_data,
    }
