"""Agent logs API routes."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import get_db, AgentLog

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentLogResponse(BaseModel):
    """Response model for agent log data."""
    id: str
    project_id: str
    agent_name: str
    agent_step: Optional[int]
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    duration_ms: int
    timestamp: datetime
    status: str
    error_message: Optional[str]

    class Config:
        from_attributes = True


@router.get("/logs", response_model=List[AgentLogResponse])
async def list_agent_logs(
    project_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    model: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List agent logs with filtering."""
    query = db.query(AgentLog)
    
    if project_id:
        query = query.filter(AgentLog.project_id == project_id)
    if agent_name:
        query = query.filter(AgentLog.agent_name == agent_name)
    if model:
        query = query.filter(AgentLog.model_used == model)
    if start_date:
        query = query.filter(AgentLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AgentLog.timestamp <= end_date)
    
    logs = query.order_by(AgentLog.timestamp.desc()).offset(offset).limit(limit).all()
    
    return [
        AgentLogResponse(
            id=str(log.id),
            project_id=str(log.project_id),
            agent_name=log.agent_name,
            agent_step=log.agent_step,
            model_used=log.model_used,
            prompt_tokens=log.prompt_tokens,
            completion_tokens=log.completion_tokens,
            total_tokens=log.total_tokens,
            cost=log.cost,
            duration_ms=log.duration_ms,
            timestamp=log.timestamp,
            status=log.status,
            error_message=log.error_message,
        )
        for log in logs
    ]


@router.get("/logs/{log_id}")
async def get_agent_log_detail(
    log_id: str,
    db: Session = Depends(get_db),
):
    """Get detailed agent log including input/output data."""
    log = db.query(AgentLog).filter(AgentLog.id == log_id).first()
    
    if not log:
        return {"error": "Log not found"}
    
    return {
        "id": str(log.id),
        "project_id": str(log.project_id),
        "agent_name": log.agent_name,
        "agent_step": log.agent_step,
        "model_used": log.model_used,
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "total_tokens": log.total_tokens,
        "cost": log.cost,
        "duration_ms": log.duration_ms,
        "timestamp": log.timestamp.isoformat(),
        "status": log.status,
        "error_message": log.error_message,
        "input_data": log.input_data,
        "output_data": log.output_data,
    }


@router.get("/stats")
async def get_agent_stats(
    db: Session = Depends(get_db),
):
    """Get aggregated agent statistics."""
    from sqlalchemy import func
    
    # Get stats by agent
    agent_stats = (
        db.query(
            AgentLog.agent_name,
            func.count(AgentLog.id).label("call_count"),
            func.sum(AgentLog.cost).label("total_cost"),
            func.avg(AgentLog.duration_ms).label("avg_duration_ms"),
            func.sum(AgentLog.total_tokens).label("total_tokens"),
        )
        .group_by(AgentLog.agent_name)
        .all()
    )
    
    # Get stats by model
    model_stats = (
        db.query(
            AgentLog.model_used,
            func.count(AgentLog.id).label("call_count"),
            func.sum(AgentLog.cost).label("total_cost"),
            func.sum(AgentLog.total_tokens).label("total_tokens"),
        )
        .group_by(AgentLog.model_used)
        .all()
    )
    
    return {
        "by_agent": [
            {
                "agent_name": s.agent_name,
                "call_count": s.call_count,
                "total_cost": float(s.total_cost or 0),
                "avg_duration_ms": float(s.avg_duration_ms or 0),
                "total_tokens": int(s.total_tokens or 0),
            }
            for s in agent_stats
        ],
        "by_model": [
            {
                "model": s.model_used,
                "call_count": s.call_count,
                "total_cost": float(s.total_cost or 0),
                "total_tokens": int(s.total_tokens or 0),
            }
            for s in model_stats
        ],
    }
