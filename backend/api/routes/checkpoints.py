"""
Phase 11C: Checkpoint API Routes

Endpoints for mid-build intervention:
- Pause at checkpoint
- Resume from checkpoint
- Edit and replay
- Restart from agent
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from models.project import Project, ProjectStatus
from orchestration.checkpoints import (
    CheckpointManager,
    CheckpointMode,
    CheckpointState,
    get_checkpoint_manager,
    DEFAULT_CHECKPOINTS
)


router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


# Request/Response models
class SetCheckpointModeRequest(BaseModel):
    mode: str = Field(..., description="Checkpoint mode: auto, supervised, manual")
    custom_checkpoints: Optional[List[str]] = Field(
        default=None,
        description="Custom checkpoint agents (for manual mode)"
    )


class ResumeRequest(BaseModel):
    edited_output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Modified agent output to use"
    )


class EditAndReplayRequest(BaseModel):
    edited_output: Dict[str, Any] = Field(..., description="Modified agent output")
    replay_from_agent: Optional[str] = Field(
        default=None,
        description="Agent to restart from (defaults to current checkpoint)"
    )


class RestartFromAgentRequest(BaseModel):
    agent_name: str = Field(..., description="Agent to restart from")


class CheckpointStatusResponse(BaseModel):
    project_id: str
    mode: str
    state: str
    paused_at: Optional[str]
    paused_at_agent: Optional[str]
    current_checkpoint: Optional[Dict[str, Any]]
    checkpoint_history: List[Dict[str, Any]]
    custom_checkpoints: List[str]
    available_checkpoints: List[str]


# Endpoints
@router.get("/{project_id}/status", response_model=CheckpointStatusResponse)
async def get_checkpoint_status(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get checkpoint status for a project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    manager = get_checkpoint_manager(db, str(project_id))
    state_data = project.checkpoint_state or {}
    
    return CheckpointStatusResponse(
        project_id=str(project_id),
        mode=manager.get_mode().value,
        state=manager.get_state().value,
        paused_at=project.paused_at.isoformat() if project.paused_at else None,
        paused_at_agent=state_data.get("paused_at_agent"),
        current_checkpoint=manager.get_current_checkpoint(),
        checkpoint_history=manager.get_checkpoint_history(),
        custom_checkpoints=state_data.get("custom_checkpoints", []),
        available_checkpoints=DEFAULT_CHECKPOINTS
    )


@router.post("/{project_id}/mode")
async def set_checkpoint_mode(
    project_id: UUID,
    request: SetCheckpointModeRequest,
    db: Session = Depends(get_db)
):
    """
    Set checkpoint mode for a project.
    
    Modes:
    - auto: No checkpoints, runs to completion
    - supervised: Pauses at default checkpoints (research, architect, code_generation)
    - manual: User-defined checkpoints
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Validate mode
    try:
        mode = CheckpointMode(request.mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode. Must be one of: {[m.value for m in CheckpointMode]}"
        )
    
    # Update project
    project.checkpoint_mode = mode.value
    
    # Set custom checkpoints if manual mode
    if mode == CheckpointMode.MANUAL and request.custom_checkpoints:
        manager = get_checkpoint_manager(db, str(project_id))
        manager.set_custom_checkpoints(request.custom_checkpoints)
    
    db.commit()
    
    return {
        "success": True,
        "mode": mode.value,
        "custom_checkpoints": request.custom_checkpoints if mode == CheckpointMode.MANUAL else None
    }


@router.post("/{project_id}/pause")
async def pause_project(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Manually pause a running project.
    
    The project will pause at the next checkpoint opportunity.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.status not in [ProjectStatus.INTAKE, ProjectStatus.RESEARCH, 
                               ProjectStatus.ARCHITECT, ProjectStatus.DESIGN,
                               ProjectStatus.CODE_GENERATION, ProjectStatus.QA]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project cannot be paused in current state"
        )
    
    # Mark project for pausing
    project.status = ProjectStatus.PAUSED
    project.paused_at = datetime.utcnow()
    
    state = project.checkpoint_state or {}
    state["status"] = CheckpointState.PAUSED.value
    state["manual_pause"] = True
    state["paused_timestamp"] = datetime.utcnow().isoformat()
    project.checkpoint_state = state
    
    db.commit()
    
    return {
        "success": True,
        "message": "Project marked for pause",
        "status": "paused"
    }


@router.post("/{project_id}/resume")
async def resume_project(
    project_id: UUID,
    request: ResumeRequest,
    db: Session = Depends(get_db)
):
    """
    Resume a paused project.
    
    Optionally provide edited output to use instead of the original.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.status != ProjectStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not paused"
        )
    
    manager = get_checkpoint_manager(db, str(project_id))
    manager.resume_from_checkpoint(request.edited_output)
    
    # Update project status
    state = project.checkpoint_state or {}
    previous_status = state.get("status_before_pause", ProjectStatus.INTAKE.value)
    project.status = ProjectStatus(previous_status)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Project resumed",
        "edited": request.edited_output is not None
    }


@router.post("/{project_id}/edit-and-replay")
async def edit_and_replay(
    project_id: UUID,
    request: EditAndReplayRequest,
    db: Session = Depends(get_db)
):
    """
    Edit checkpoint output and replay from that point.
    
    Use this to modify agent output and re-run downstream agents
    with the modified data.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.status != ProjectStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project must be paused to edit and replay"
        )
    
    manager = get_checkpoint_manager(db, str(project_id))
    result = manager.edit_and_replay(
        edited_output=request.edited_output,
        replay_from_agent=request.replay_from_agent
    )
    
    db.commit()
    
    return {
        "success": True,
        **result
    }


@router.post("/{project_id}/restart-from/{agent_name}")
async def restart_from_agent(
    project_id: UUID,
    agent_name: str,
    db: Session = Depends(get_db)
):
    """
    Abort current execution and restart from a specific agent.
    
    This will use the pipeline state from before that agent ran.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Validate agent name
    valid_agents = [
        "intake", "research", "architect", "design_system",
        "asset_generation", "content_generation", "code_generation",
        "security", "seo", "accessibility", "qa_testing",
        "deployment", "analytics_monitoring", "coding_standards"
    ]
    
    if agent_name.lower() not in valid_agents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent name. Must be one of: {valid_agents}"
        )
    
    manager = get_checkpoint_manager(db, str(project_id))
    result = manager.restart_from_agent(agent_name)
    
    db.commit()
    
    return {
        "success": True,
        **result
    }


@router.delete("/{project_id}/checkpoints")
async def clear_checkpoints(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Clear all checkpoint data for a project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    manager = get_checkpoint_manager(db, str(project_id))
    manager.clear_checkpoints()
    
    return {
        "success": True,
        "message": "Checkpoints cleared"
    }
