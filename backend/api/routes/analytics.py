"""Analytics API Routes for Phase 9A - Enhanced Analytics.

Provides endpoints for:
- Agent success rate leaderboard
- Model performance comparison
- Build time waterfall analysis
- QA failure patterns
- Cost accuracy tracking
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.database import get_db
from utils.agent_analytics import get_agent_analytics, AgentAnalytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ============ Response Models ============

class AgentSuccessRateResponse(BaseModel):
    """Agent success rate data."""
    agent_name: str
    total_executions: int
    successful_executions: int
    success_rate: float
    avg_execution_time_ms: float
    avg_revision_count: float
    avg_quality_score: float
    total_cost: float


class ModelComparisonResponse(BaseModel):
    """Model comparison data."""
    agent_name: str
    model_used: str
    execution_count: int
    success_rate: float
    avg_execution_time_ms: float
    avg_revision_count: float
    avg_quality_score: float
    avg_cost: float


class BuildTimeWaterfallResponse(BaseModel):
    """Build time waterfall data."""
    agent_name: str
    total_time_ms: int
    avg_time_ms: float
    percentage_of_total: float
    execution_count: int


class QAFailurePatternResponse(BaseModel):
    """QA failure pattern data."""
    id: str
    pattern_hash: str
    pattern_type: str
    description: str
    sample_error: Optional[str]
    causing_agent: Optional[str]
    occurrence_count: int
    last_occurred: str
    first_occurred: str
    affected_projects: List[str]
    is_resolved: bool
    resolution_notes: Optional[str]


class CostAccuracyStatsResponse(BaseModel):
    """Cost accuracy statistics."""
    total_projects: int
    avg_accuracy: Optional[float]
    avg_estimation_error: Optional[float]
    underestimates: int
    overestimates: int
    by_project_type: dict
    by_cost_profile: dict


class CostAccuracyRecordResponse(BaseModel):
    """Individual cost accuracy record."""
    id: str
    project_id: str
    project_type: str
    cost_profile: str
    complexity_score: int
    estimated_cost: float
    actual_cost: Optional[float]
    accuracy_percentage: Optional[float]
    estimation_error: Optional[float]
    estimated_at: str
    completed_at: Optional[str]


# ============ Endpoints ============

@router.get("/agent-success-rates", response_model=List[AgentSuccessRateResponse])
async def get_agent_success_rates(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of agents"),
    db: Session = Depends(get_db)
):
    """Get agent success rate leaderboard.
    
    Returns agents ranked by success rate, showing:
    - Total and successful executions
    - Success rate percentage
    - Average execution time
    - Average revision count
    - Average quality score
    - Total cost
    """
    analytics = get_agent_analytics(db)
    rates = analytics.get_agent_success_rates(days=days, limit=limit)
    
    return [
        AgentSuccessRateResponse(
            agent_name=r.agent_name,
            total_executions=r.total_executions,
            successful_executions=r.successful_executions,
            success_rate=r.success_rate,
            avg_execution_time_ms=r.avg_execution_time_ms,
            avg_revision_count=r.avg_revision_count,
            avg_quality_score=r.avg_quality_score,
            total_cost=r.total_cost,
        )
        for r in rates
    ]


@router.get("/model-comparison", response_model=List[ModelComparisonResponse])
async def get_model_comparison(
    agent_name: Optional[str] = Query(None, description="Filter by specific agent"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Compare model performance across agents.
    
    Shows how different models perform for the same agent:
    - Success rate comparison
    - Execution time differences
    - Revision count (fewer = better)
    - Quality scores
    - Cost comparison
    """
    analytics = get_agent_analytics(db)
    comparisons = analytics.compare_model_performance(
        agent_name=agent_name,
        days=days
    )
    
    return [
        ModelComparisonResponse(
            agent_name=c.agent_name,
            model_used=c.model_used,
            execution_count=c.execution_count,
            success_rate=c.success_rate,
            avg_execution_time_ms=c.avg_execution_time_ms,
            avg_revision_count=c.avg_revision_count,
            avg_quality_score=c.avg_quality_score,
            avg_cost=c.avg_cost,
        )
        for c in comparisons
    ]


@router.get("/build-time-waterfall/{project_id}", response_model=List[BuildTimeWaterfallResponse])
async def get_build_time_waterfall_for_project(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """Get build time breakdown for a specific project.
    
    Shows how much time each agent took, useful for:
    - Identifying bottlenecks
    - Optimizing slow agents
    - Understanding project timeline
    """
    analytics = get_agent_analytics(db)
    waterfall = analytics.get_build_time_waterfall(project_id=project_id)
    
    if not waterfall:
        raise HTTPException(status_code=404, detail="No performance data found for this project")
    
    return [
        BuildTimeWaterfallResponse(
            agent_name=w.agent_name,
            total_time_ms=w.total_time_ms,
            avg_time_ms=w.avg_time_ms,
            percentage_of_total=w.percentage_of_total,
            execution_count=w.execution_count,
        )
        for w in waterfall
    ]


@router.get("/build-time-waterfall", response_model=List[BuildTimeWaterfallResponse])
async def get_aggregated_build_time_waterfall(
    days: int = Query(30, ge=1, le=365, description="Number of days to aggregate"),
    db: Session = Depends(get_db)
):
    """Get aggregated build time breakdown across all projects.
    
    Shows average time distribution across the pipeline.
    """
    analytics = get_agent_analytics(db)
    waterfall = analytics.get_build_time_waterfall(days=days)
    
    return [
        BuildTimeWaterfallResponse(
            agent_name=w.agent_name,
            total_time_ms=w.total_time_ms,
            avg_time_ms=w.avg_time_ms,
            percentage_of_total=w.percentage_of_total,
            execution_count=w.execution_count,
        )
        for w in waterfall
    ]


@router.get("/qa-failure-patterns", response_model=List[QAFailurePatternResponse])
async def get_qa_failure_patterns(
    limit: int = Query(10, ge=1, le=50, description="Maximum patterns to return"),
    include_resolved: bool = Query(False, description="Include resolved patterns"),
    db: Session = Depends(get_db)
):
    """Get top recurring QA failure patterns.
    
    Returns the most common issues that cause QA failures:
    - Pattern type (security, accessibility, SEO, test failures)
    - Occurrence count
    - Affected projects
    - Causing agent (if known)
    """
    analytics = get_agent_analytics(db)
    patterns = analytics.get_top_failure_patterns(
        limit=limit,
        include_resolved=include_resolved
    )
    
    return [
        QAFailurePatternResponse(
            id=str(p.id),
            pattern_hash=p.pattern_hash,
            pattern_type=p.pattern_type,
            description=p.description,
            sample_error=p.sample_error,
            causing_agent=p.causing_agent,
            occurrence_count=p.occurrence_count,
            last_occurred=p.last_occurred.isoformat() if p.last_occurred else "",
            first_occurred=p.first_occurred.isoformat() if p.first_occurred else "",
            affected_projects=p.affected_projects or [],
            is_resolved=p.is_resolved,
            resolution_notes=p.resolution_notes,
        )
        for p in patterns
    ]


@router.patch("/qa-failure-patterns/{pattern_id}/resolve")
async def resolve_qa_failure_pattern(
    pattern_id: UUID,
    resolution_notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Mark a QA failure pattern as resolved.
    
    Optionally add notes about the resolution.
    """
    from models.agent_performance import QAFailurePattern
    
    pattern = db.query(QAFailurePattern).filter(
        QAFailurePattern.id == pattern_id
    ).first()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    pattern.is_resolved = True
    if resolution_notes:
        pattern.resolution_notes = resolution_notes
    
    db.commit()
    
    return {"status": "resolved", "pattern_id": str(pattern_id)}


@router.get("/cost-accuracy", response_model=CostAccuracyStatsResponse)
async def get_cost_accuracy_stats(
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    cost_profile: Optional[str] = Query(None, description="Filter by cost profile"),
    days: int = Query(90, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Get cost estimation accuracy statistics.
    
    Shows how accurate cost estimates have been:
    - Average accuracy percentage
    - Under/over estimate counts
    - Breakdown by project type
    - Breakdown by cost profile
    """
    analytics = get_agent_analytics(db)
    stats = analytics.get_cost_accuracy_stats(
        project_type=project_type,
        cost_profile=cost_profile,
        days=days
    )
    
    return CostAccuracyStatsResponse(**stats)


@router.get("/cost-accuracy/data", response_model=List[CostAccuracyRecordResponse])
async def get_cost_accuracy_data(
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    db: Session = Depends(get_db)
):
    """Get cost accuracy data points for charting.
    
    Returns individual project cost estimates vs actuals
    for visualization in charts.
    """
    analytics = get_agent_analytics(db)
    data = analytics.get_cost_accuracy_data(limit=limit)
    
    return [
        CostAccuracyRecordResponse(**record)
        for record in data
    ]


@router.get("/summary")
async def get_analytics_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Get overall analytics summary.
    
    Returns high-level metrics for the dashboard:
    - Total agent executions
    - Overall success rate
    - Average build time
    - Top performing agent
    - Most common failure pattern
    """
    analytics = get_agent_analytics(db)
    
    # Get success rates
    success_rates = analytics.get_agent_success_rates(days=days, limit=1)
    
    # Get build time waterfall
    waterfall = analytics.get_build_time_waterfall(days=days)
    
    # Get top failure pattern
    patterns = analytics.get_top_failure_patterns(limit=1)
    
    # Get cost accuracy
    cost_stats = analytics.get_cost_accuracy_stats(days=days)
    
    # Calculate totals
    total_executions = sum(r.total_executions for r in success_rates) if success_rates else 0
    total_successful = sum(r.successful_executions for r in success_rates) if success_rates else 0
    overall_success_rate = (total_successful / total_executions * 100) if total_executions > 0 else 0
    
    total_build_time = sum(w.total_time_ms for w in waterfall) if waterfall else 0
    avg_build_time = (total_build_time / len(waterfall)) if waterfall else 0
    
    return {
        "total_agent_executions": total_executions,
        "overall_success_rate": overall_success_rate,
        "total_build_time_ms": total_build_time,
        "avg_build_time_ms": avg_build_time,
        "top_performing_agent": success_rates[0].agent_name if success_rates else None,
        "top_failure_pattern": patterns[0].description if patterns else None,
        "cost_accuracy_avg": cost_stats.get("avg_accuracy"),
        "projects_tracked": cost_stats.get("total_projects", 0),
    }
