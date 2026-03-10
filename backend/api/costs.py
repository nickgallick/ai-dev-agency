"""Cost tracking API routes."""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import get_db, CostTracking, AgentLog, Project

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("/summary")
async def get_cost_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get overall cost summary."""
    query = db.query(CostTracking)
    
    if start_date:
        query = query.filter(CostTracking.timestamp >= start_date)
    if end_date:
        query = query.filter(CostTracking.timestamp <= end_date)
    
    total_cost = query.with_entities(func.sum(CostTracking.total_cost)).scalar() or 0
    project_count = query.with_entities(func.count(CostTracking.project_id.distinct())).scalar() or 0
    
    return {
        "total_cost": float(total_cost),
        "project_count": project_count,
        "avg_cost_per_project": float(total_cost / project_count) if project_count > 0 else 0,
    }


@router.get("/by-project")
async def get_costs_by_project(
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    """Get costs grouped by project."""
    costs = (
        db.query(CostTracking)
        .join(Project, CostTracking.project_id == Project.id)
        .order_by(CostTracking.timestamp.desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "project_id": str(c.project_id),
            "total_cost": float(c.total_cost),
            "breakdown": c.breakdown,
            "timestamp": c.timestamp.isoformat(),
        }
        for c in costs
    ]


@router.get("/by-agent")
async def get_costs_by_agent(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get costs grouped by agent."""
    query = db.query(
        AgentLog.agent_name,
        func.sum(AgentLog.cost).label("total_cost"),
        func.count(AgentLog.id).label("call_count"),
    )
    
    if start_date:
        query = query.filter(AgentLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AgentLog.timestamp <= end_date)
    
    results = query.group_by(AgentLog.agent_name).all()
    
    return [
        {
            "agent_name": r.agent_name,
            "total_cost": float(r.total_cost or 0),
            "call_count": r.call_count,
        }
        for r in results
    ]


@router.get("/by-model")
async def get_costs_by_model(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get costs grouped by model."""
    query = db.query(
        AgentLog.model_used,
        func.sum(AgentLog.cost).label("total_cost"),
        func.sum(AgentLog.prompt_tokens).label("prompt_tokens"),
        func.sum(AgentLog.completion_tokens).label("completion_tokens"),
        func.count(AgentLog.id).label("call_count"),
    )
    
    if start_date:
        query = query.filter(AgentLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AgentLog.timestamp <= end_date)
    
    results = query.group_by(AgentLog.model_used).all()
    
    return [
        {
            "model": r.model_used,
            "total_cost": float(r.total_cost or 0),
            "prompt_tokens": int(r.prompt_tokens or 0),
            "completion_tokens": int(r.completion_tokens or 0),
            "call_count": r.call_count,
        }
        for r in results
    ]


@router.get("/trends")
async def get_cost_trends(
    days: int = Query(30, le=90),
    db: Session = Depends(get_db),
):
    """Get daily cost trends."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    results = (
        db.query(
            func.date(AgentLog.timestamp).label("date"),
            func.sum(AgentLog.cost).label("daily_cost"),
            func.count(AgentLog.id).label("call_count"),
        )
        .filter(AgentLog.timestamp >= start_date)
        .group_by(func.date(AgentLog.timestamp))
        .order_by(func.date(AgentLog.timestamp))
        .all()
    )
    
    return [
        {
            "date": str(r.date),
            "daily_cost": float(r.daily_cost or 0),
            "call_count": r.call_count,
        }
        for r in results
    ]
