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


class EstimateRequest(BaseModel):
    """Request model for pre-execution cost/time estimation."""
    brief: str = Field(..., min_length=1)
    project_type: str = Field("web_simple")
    cost_profile: str = Field("balanced")
    num_features: int = Field(0, ge=0)
    num_pages: int = Field(0, ge=0)


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
    # Phase 13: Approved pipeline plan (user-reviewed agent skip list)
    pipeline_plan: Optional[dict] = Field(None, description="User-approved pipeline execution plan")


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


# ============ Brief Wizard: Completeness & Enhancement (#2) ============


class BriefScoreRequest(BaseModel):
    """Request for brief completeness scoring."""
    brief: str = Field(..., min_length=1)
    project_type: str = Field("web_simple")


class BriefEnhanceRequest(BaseModel):
    """Request for brief prompt enhancement."""
    brief: str = Field(..., min_length=1)
    project_type: str = Field("web_simple")
    detected_features: Optional[List[str]] = None
    detected_pages: Optional[List[str]] = None


@router.post("/score-brief")
async def score_brief_endpoint(request: BriefScoreRequest):
    """Score a project brief on completeness.

    Returns per-dimension scores, missing elements, and suggestions.
    Instant response — no LLM calls.
    """
    from utils.brief_enhancer import score_brief

    score = score_brief(request.brief, request.project_type)
    return score.to_dict()


@router.post("/enhance-brief")
async def enhance_brief_endpoint(request: BriefEnhanceRequest):
    """Enhance a project brief by filling in detected gaps.

    Returns the original brief plus sensible additions for missing
    dimensions. Does NOT rewrite the user's text.
    """
    from utils.brief_enhancer import enhance_brief

    enhanced = enhance_brief(
        request.brief,
        project_type=request.project_type,
        detected_features=request.detected_features,
        detected_pages=request.detected_pages,
    )
    return enhanced.to_dict()


# ============ Pre-Execution Estimation (#8) ============

@router.post("/estimate")
async def estimate_project_cost(request: EstimateRequest):
    """Estimate cost and time for a pipeline run before starting it.

    Returns per-agent token estimates, dollar costs, and wall-clock time.
    The user reviews this estimate and approves spend before the pipeline starts.

    No LLM calls are made — this is a fast, local calculation.
    """
    from utils.estimation import estimate_pipeline_cost

    try:
        estimate = estimate_pipeline_cost(
            brief=request.brief,
            project_type=request.project_type,
            cost_profile=request.cost_profile,
            num_features=request.num_features,
            num_pages=request.num_pages,
        )
        return estimate.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Estimation failed: {str(e)}")


# ============ Pipeline Plan Generation (#13) ============


class GeneratePlanRequest(BaseModel):
    """Request for generating a pipeline execution plan."""
    brief: str = Field(..., min_length=1)
    project_type: str = Field("web_simple")
    cost_profile: str = Field("balanced")
    num_features: int = Field(0, ge=0)
    num_pages: int = Field(0, ge=0)
    build_mode: str = Field("autonomous")


@router.post("/generate-plan")
async def generate_pipeline_plan(request: GeneratePlanRequest):
    """Generate a granular pipeline execution plan for user review.

    Returns the full DAG of agents with per-agent cost/time estimates,
    skip status (based on project type), checkpoint status (based on
    autonomy tier), and dependency information. The user reviews and
    optionally customizes this plan before starting the build.
    """
    from utils.estimation import estimate_pipeline_cost
    from config.autonomy import resolve_tier, ALL_PIPELINE_AGENTS
    from orchestration.pipeline import PROJECT_TYPE_CONFIGS

    # Get cost/time estimates
    try:
        estimate = estimate_pipeline_cost(
            brief=request.brief,
            project_type=request.project_type,
            cost_profile=request.cost_profile,
            num_features=request.num_features,
            num_pages=request.num_pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Estimation failed: {str(e)}")

    # Get project type skip config
    type_config = PROJECT_TYPE_CONFIGS.get(
        request.project_type, PROJECT_TYPE_CONFIGS.get("web_simple", {})
    )
    skip_agents = set(type_config.get("skip_agents", []))
    required_agents = set(type_config.get("required_agents", []))

    # Get autonomy tier checkpoint info
    tier = resolve_tier(request.build_mode)
    checkpoint_agents = set(tier.checkpoint_agents)

    # Agent descriptions for the plan UI
    agent_descriptions = {
        "intake": "Classifies the project, extracts key requirements",
        "research": "Researches similar projects, best practices, and technology options",
        "architect": "Designs system architecture, data models, and API structure",
        "design_system": "Creates design tokens, color palette, typography, spacing",
        "asset_generation": "Generates images, icons, and visual assets",
        "content_generation": "Writes copy, placeholder content, and microcopy",
        "pm_checkpoint_1": "Validates coherence between architecture and design",
        "code_generation": "Generates the application source code",
        "integration_wiring": "Wires third-party integrations and APIs",
        "pm_checkpoint_2": "Validates completeness of code and integrations",
        "code_review": "Reviews code for quality, patterns, and best practices",
        "security": "Scans for security vulnerabilities and OWASP issues",
        "seo": "Optimizes for search engines and web performance",
        "accessibility": "Audits for WCAG compliance and accessibility",
        "qa": "Runs tests, identifies bugs, and validates functionality",
        "deployment": "Deploys the application to hosting infrastructure",
        "post_deploy_verification": "Verifies the deployed app is working correctly",
        "analytics_monitoring": "Sets up analytics, monitoring, and alerting",
        "coding_standards": "Enforces coding standards and documentation",
        "delivery": "Creates GitHub repo and delivers final artifacts",
    }

    # Agent dependencies (mirrors Pipeline._setup_default_pipeline)
    agent_dependencies = {
        "intake": [],
        "research": ["intake"],
        "architect": ["research"],
        "design_system": ["architect"],
        "asset_generation": ["architect"],
        "content_generation": ["architect"],
        "pm_checkpoint_1": ["design_system", "asset_generation", "content_generation"],
        "code_generation": ["pm_checkpoint_1"],
        "integration_wiring": ["code_generation"],
        "pm_checkpoint_2": ["integration_wiring"],
        "code_review": ["pm_checkpoint_2"],
        "security": ["code_review"],
        "seo": ["code_review"],
        "accessibility": ["code_review"],
        "qa": ["security", "seo", "accessibility"],
        "deployment": ["qa"],
        "post_deploy_verification": ["deployment"],
        "analytics_monitoring": ["post_deploy_verification"],
        "coding_standards": ["post_deploy_verification"],
        "delivery": ["analytics_monitoring", "coding_standards"],
    }

    # Parallel groups
    parallel_groups = {
        "asset_generation": "content_assets",
        "content_generation": "content_assets",
        "design_system": None,
        "security": "quality",
        "seo": "quality",
        "accessibility": "quality",
        "analytics_monitoring": "post_deploy",
        "coding_standards": "post_deploy",
    }

    # Build the plan: one entry per agent with all metadata
    estimate_by_agent = {a.agent_id: a.to_dict() for a in estimate.agents}
    plan_agents = []

    for agent_id in ALL_PIPELINE_AGENTS:
        is_skipped = agent_id in skip_agents
        is_required = agent_id in required_agents
        is_checkpoint = agent_id in checkpoint_agents
        est = estimate_by_agent.get(agent_id, {})

        plan_agents.append({
            "agent_id": agent_id,
            "description": agent_descriptions.get(agent_id, ""),
            "dependencies": agent_dependencies.get(agent_id, []),
            "parallel_group": parallel_groups.get(agent_id),
            "skipped": is_skipped,
            "required": is_required,
            "is_checkpoint": is_checkpoint,
            "model": est.get("model", ""),
            "estimated_cost": est.get("cost", 0),
            "estimated_time_seconds": est.get("time_seconds", 0),
            "estimated_input_tokens": est.get("input_tokens", 0),
            "estimated_output_tokens": est.get("output_tokens", 0),
        })

    # Calculate active (non-skipped) summary
    active_agents = [a for a in plan_agents if not a["skipped"]]
    active_cost = sum(a["estimated_cost"] for a in active_agents)

    return {
        "project_type": request.project_type,
        "cost_profile": request.cost_profile,
        "autonomy_tier": tier.id,
        "agents": plan_agents,
        "summary": {
            "total_agents": len(plan_agents),
            "active_agents": len(active_agents),
            "skipped_agents": len(plan_agents) - len(active_agents),
            "checkpoint_count": len([a for a in plan_agents if a["is_checkpoint"] and not a["skipped"]]),
            "total_cost": round(estimate.total_cost, 2),
            "active_cost": round(active_cost, 2),
            "min_cost": round(estimate.min_cost, 2),
            "max_cost": round(estimate.max_cost, 2),
            "total_time_display": estimate.to_dict()["total_time_display"],
            "total_time_seconds": round(estimate.total_time_seconds),
            "total_tokens": estimate.total_input_tokens + estimate.total_output_tokens,
            "confidence": round(estimate.confidence, 2),
        },
    }


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

    # Phase 12: Resolve autonomy tier from build_mode in requirements
    from config.autonomy import resolve_tier
    build_mode = (project.requirements or {}).get("build_mode")
    tier = resolve_tier(build_mode)

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
        requirements={
            **(project.requirements or {}),
            # Phase 13: Store user-approved pipeline plan (skip customizations)
            **({"pipeline_plan": project.pipeline_plan} if project.pipeline_plan else {}),
        },
        project_metadata={
            "reference_urls": project.reference_urls or [],
            "tech_stack_override": project.tech_stack_override,
        },
        # Phase 12: Autonomy tier → checkpoint config
        checkpoint_mode=tier.checkpoint_mode,
        checkpoint_state={
            "custom_checkpoints": tier.checkpoint_agents,
            "autonomy_tier": tier.id,
            "auto_continue_timeout": tier.auto_continue_timeout,
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


@router.get("/{project_id}/diagnose")
async def diagnose_project(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Diagnose why a project build may have failed or produced no artifacts."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    outputs = project.agent_outputs or {}
    diagnosis = {
        "project_id": str(project.id),
        "status": project.status,
        "project_type": (project.requirements or {}).get("project_type", "unknown"),
        "cost_profile": project.cost_profile,
        "agents_ran": list(outputs.keys()),
        "agents_missing": [],
        "code_generation": None,
        "issues": [],
    }

    # Check which agents have output
    expected_agents = [
        "intake", "research", "architect", "design_system",
        "asset_generation", "content_generation", "pm_checkpoint_1",
        "code_generation", "integration_wiring",
    ]
    for a in expected_agents:
        if a not in outputs:
            diagnosis["agents_missing"].append(a)

    # Check code_generation specifically
    cg = outputs.get("code_generation")
    if cg:
        files = cg.get("files", cg.get("generated_files", []))
        diagnosis["code_generation"] = {
            "success": cg.get("success"),
            "files_count": len(files) if isinstance(files, list) else 0,
            "error": cg.get("error"),
            "strategy_used": cg.get("strategy_used"),
            "has_content": any(
                bool(f.get("content")) for f in files
            ) if isinstance(files, list) else False,
        }
    else:
        diagnosis["issues"].append(
            "code_generation agent produced no output — likely skipped due to upstream failure"
        )

    # Check for upstream failures
    for agent_name in expected_agents:
        agent_out = outputs.get(agent_name, {})
        if isinstance(agent_out, dict):
            if agent_out.get("error"):
                diagnosis["issues"].append(
                    f"{agent_name} failed: {agent_out.get('error', '')[:200]}"
                )
            elif agent_out.get("skipped"):
                diagnosis["issues"].append(f"{agent_name} was skipped")

    # Check audit log for failures
    try:
        from models.audit_log import AuditLog
        failures = db.query(AuditLog).filter(
            AuditLog.project_id == project_id,
            AuditLog.event_type.in_(["agent_failed", "pipeline_failed"]),
        ).all()
        for f in failures:
            diagnosis["issues"].append(
                f"[audit] {f.event_type}: {f.agent_name or 'pipeline'} — {(f.message or '')[:200]}"
            )
    except Exception:
        pass

    return diagnosis


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
