"""Agent Analytics Module for Phase 9A - Enhanced Analytics.

Provides functions to:
- Log agent performance after each agent completes
- Calculate agent success rates
- Compare model performance
- Identify common failure patterns
- Track cost accuracy
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from models.agent_performance import AgentPerformance, QAFailurePattern, CostAccuracyTracking

logger = logging.getLogger(__name__)


@dataclass
class AgentPerformanceData:
    """Data structure for logging agent performance."""
    project_id: UUID
    agent_name: str
    model_used: str
    execution_time_ms: int
    tokens_used: Dict[str, int]
    cost: float
    passed_next_stage: bool = True
    revision_count: int = 0
    qa_issues_caused: int = 0
    quality_score: float = 1.0
    error_occurred: bool = False
    error_message: Optional[str] = None


@dataclass
class AgentSuccessRate:
    """Agent success rate statistics."""
    agent_name: str
    total_executions: int
    successful_executions: int
    success_rate: float
    avg_execution_time_ms: float
    avg_revision_count: float
    avg_quality_score: float
    total_cost: float


@dataclass
class ModelComparison:
    """Model performance comparison for a specific agent."""
    agent_name: str
    model_used: str
    execution_count: int
    success_rate: float
    avg_execution_time_ms: float
    avg_revision_count: float
    avg_quality_score: float
    avg_cost: float


@dataclass
class BuildTimeWaterfall:
    """Build time breakdown by agent."""
    agent_name: str
    total_time_ms: int
    avg_time_ms: float
    percentage_of_total: float
    execution_count: int


class AgentAnalytics:
    """Agent analytics engine for tracking and analyzing agent performance."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_performance(self, data: AgentPerformanceData) -> AgentPerformance:
        """Log agent performance after execution.
        
        Args:
            data: AgentPerformanceData with all metrics
            
        Returns:
            Created AgentPerformance record
        """
        try:
            performance = AgentPerformance(
                project_id=data.project_id,
                agent_name=data.agent_name,
                model_used=data.model_used,
                execution_time_ms=data.execution_time_ms,
                output_quality={
                    "passed_next_stage": data.passed_next_stage,
                    "revision_count": data.revision_count,
                    "qa_issues_caused": data.qa_issues_caused,
                    "quality_score": data.quality_score,
                    "error_occurred": data.error_occurred,
                    "error_message": data.error_message,
                },
                tokens_used=data.tokens_used,
                cost=data.cost,
            )
            
            self.db.add(performance)
            self.db.commit()
            self.db.refresh(performance)
            
            logger.info(
                f"Logged performance for {data.agent_name} "
                f"(model={data.model_used}, time={data.execution_time_ms}ms, cost=${data.cost:.4f})"
            )
            
            return performance
            
        except Exception as e:
            logger.error(f"Failed to log agent performance: {e}")
            self.db.rollback()
            raise
    
    def get_agent_success_rates(
        self, 
        days: int = 30,
        limit: int = 20
    ) -> List[AgentSuccessRate]:
        """Calculate success rates for all agents.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of agents to return
            
        Returns:
            List of AgentSuccessRate ordered by success rate
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        results = self.db.query(
            AgentPerformance.agent_name,
            func.count(AgentPerformance.id).label('total_executions'),
            func.sum(
                func.cast(
                    AgentPerformance.output_quality['passed_next_stage'].astext == 'true',
                    type_=func.INTEGER()
                )
            ).label('successful_executions'),
            func.avg(AgentPerformance.execution_time_ms).label('avg_time'),
            func.avg(
                func.cast(
                    AgentPerformance.output_quality['revision_count'].astext,
                    type_=func.FLOAT()
                )
            ).label('avg_revisions'),
            func.avg(
                func.cast(
                    AgentPerformance.output_quality['quality_score'].astext,
                    type_=func.FLOAT()
                )
            ).label('avg_quality'),
            func.sum(AgentPerformance.cost).label('total_cost'),
        ).filter(
            AgentPerformance.created_at >= cutoff_date
        ).group_by(
            AgentPerformance.agent_name
        ).order_by(
            desc('successful_executions')
        ).limit(limit).all()
        
        success_rates = []
        for row in results:
            total = row.total_executions or 1
            successful = row.successful_executions or 0
            success_rates.append(AgentSuccessRate(
                agent_name=row.agent_name,
                total_executions=total,
                successful_executions=successful,
                success_rate=successful / total * 100 if total > 0 else 0,
                avg_execution_time_ms=row.avg_time or 0,
                avg_revision_count=row.avg_revisions or 0,
                avg_quality_score=row.avg_quality or 1.0,
                total_cost=row.total_cost or 0,
            ))
        
        # Sort by success rate descending
        success_rates.sort(key=lambda x: x.success_rate, reverse=True)
        return success_rates
    
    def compare_model_performance(
        self,
        agent_name: Optional[str] = None,
        days: int = 30
    ) -> List[ModelComparison]:
        """Compare model performance, optionally for a specific agent.
        
        Args:
            agent_name: Optional agent to filter by
            days: Number of days to look back
            
        Returns:
            List of ModelComparison data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(
            AgentPerformance.agent_name,
            AgentPerformance.model_used,
            func.count(AgentPerformance.id).label('execution_count'),
            func.avg(
                func.cast(
                    AgentPerformance.output_quality['passed_next_stage'].astext == 'true',
                    type_=func.INTEGER()
                )
            ).label('success_rate'),
            func.avg(AgentPerformance.execution_time_ms).label('avg_time'),
            func.avg(
                func.cast(
                    AgentPerformance.output_quality['revision_count'].astext,
                    type_=func.FLOAT()
                )
            ).label('avg_revisions'),
            func.avg(
                func.cast(
                    AgentPerformance.output_quality['quality_score'].astext,
                    type_=func.FLOAT()
                )
            ).label('avg_quality'),
            func.avg(AgentPerformance.cost).label('avg_cost'),
        ).filter(
            AgentPerformance.created_at >= cutoff_date
        )
        
        if agent_name:
            query = query.filter(AgentPerformance.agent_name == agent_name)
        
        results = query.group_by(
            AgentPerformance.agent_name,
            AgentPerformance.model_used
        ).order_by(
            AgentPerformance.agent_name,
            desc('success_rate')
        ).all()
        
        comparisons = []
        for row in results:
            comparisons.append(ModelComparison(
                agent_name=row.agent_name,
                model_used=row.model_used,
                execution_count=row.execution_count or 0,
                success_rate=(row.success_rate or 0) * 100,
                avg_execution_time_ms=row.avg_time or 0,
                avg_revision_count=row.avg_revisions or 0,
                avg_quality_score=row.avg_quality or 1.0,
                avg_cost=row.avg_cost or 0,
            ))
        
        return comparisons
    
    def get_build_time_waterfall(
        self,
        project_id: Optional[UUID] = None,
        days: int = 30
    ) -> List[BuildTimeWaterfall]:
        """Get build time breakdown by agent.
        
        Args:
            project_id: Optional project to get specific breakdown
            days: Number of days to aggregate
            
        Returns:
            List of BuildTimeWaterfall data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(
            AgentPerformance.agent_name,
            func.sum(AgentPerformance.execution_time_ms).label('total_time'),
            func.avg(AgentPerformance.execution_time_ms).label('avg_time'),
            func.count(AgentPerformance.id).label('execution_count'),
        ).filter(
            AgentPerformance.created_at >= cutoff_date
        )
        
        if project_id:
            query = query.filter(AgentPerformance.project_id == project_id)
        
        results = query.group_by(
            AgentPerformance.agent_name
        ).order_by(
            AgentPerformance.agent_name
        ).all()
        
        # Calculate total time for percentage
        total_time = sum(row.total_time or 0 for row in results)
        
        waterfall = []
        for row in results:
            time_ms = row.total_time or 0
            waterfall.append(BuildTimeWaterfall(
                agent_name=row.agent_name,
                total_time_ms=time_ms,
                avg_time_ms=row.avg_time or 0,
                percentage_of_total=(time_ms / total_time * 100) if total_time > 0 else 0,
                execution_count=row.execution_count or 0,
            ))
        
        # Sort by pipeline order (roughly)
        agent_order = [
            'intake', 'research', 'architect', 'design_system',
            'asset_generation', 'content_generation', 'pm_checkpoint_1',
            'code_generation', 'pm_checkpoint_2', 'code_review',
            'security', 'seo', 'accessibility', 'qa',
            'deployment', 'post_deploy_verification',
            'analytics_monitoring', 'coding_standards', 'delivery'
        ]
        
        def sort_key(item: BuildTimeWaterfall) -> int:
            try:
                return agent_order.index(item.agent_name)
            except ValueError:
                return len(agent_order)
        
        waterfall.sort(key=sort_key)
        return waterfall
    
    def record_qa_failure(
        self,
        pattern_type: str,
        description: str,
        sample_error: str,
        causing_agent: Optional[str],
        project_id: UUID
    ) -> QAFailurePattern:
        """Record or update a QA failure pattern.
        
        Args:
            pattern_type: Type of failure (security, accessibility, seo, test_failure)
            description: Human-readable description
            sample_error: Sample error message
            causing_agent: Agent that caused the issue
            project_id: Project where failure occurred
            
        Returns:
            QAFailurePattern record
        """
        # Create hash from normalized description
        pattern_hash = hashlib.sha256(
            f"{pattern_type}:{description.lower().strip()}".encode()
        ).hexdigest()
        
        # Check if pattern already exists
        existing = self.db.query(QAFailurePattern).filter(
            QAFailurePattern.pattern_hash == pattern_hash
        ).first()
        
        if existing:
            # Update existing pattern
            existing.occurrence_count += 1
            existing.last_occurred = datetime.utcnow()
            
            # Add project to affected list if not already there
            affected = existing.affected_projects or []
            project_id_str = str(project_id)
            if project_id_str not in affected:
                affected.append(project_id_str)
                existing.affected_projects = affected
            
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new pattern
            pattern = QAFailurePattern(
                pattern_hash=pattern_hash,
                pattern_type=pattern_type,
                description=description,
                sample_error=sample_error,
                causing_agent=causing_agent,
                affected_projects=[str(project_id)],
            )
            self.db.add(pattern)
            self.db.commit()
            self.db.refresh(pattern)
            return pattern
    
    def get_top_failure_patterns(
        self,
        limit: int = 10,
        include_resolved: bool = False
    ) -> List[QAFailurePattern]:
        """Get top recurring QA failure patterns.
        
        Args:
            limit: Maximum number of patterns to return
            include_resolved: Whether to include resolved patterns
            
        Returns:
            List of QAFailurePattern ordered by occurrence count
        """
        query = self.db.query(QAFailurePattern)
        
        if not include_resolved:
            query = query.filter(QAFailurePattern.is_resolved == False)
        
        patterns = query.order_by(
            desc(QAFailurePattern.occurrence_count)
        ).limit(limit).all()
        
        return patterns
    
    def record_cost_estimate(
        self,
        project_id: UUID,
        project_type: str,
        cost_profile: str,
        estimated_cost: float,
        complexity_score: int = 5
    ) -> CostAccuracyTracking:
        """Record initial cost estimate for a project.
        
        Args:
            project_id: Project ID
            project_type: Type of project
            cost_profile: Cost profile used
            estimated_cost: Estimated cost
            complexity_score: Complexity score (1-10)
            
        Returns:
            CostAccuracyTracking record
        """
        tracking = CostAccuracyTracking(
            project_id=project_id,
            project_type=project_type,
            cost_profile=cost_profile,
            estimated_cost=estimated_cost,
            complexity_score=complexity_score,
        )
        self.db.add(tracking)
        self.db.commit()
        self.db.refresh(tracking)
        return tracking
    
    def update_actual_cost(
        self,
        project_id: UUID,
        actual_cost: float
    ) -> Optional[CostAccuracyTracking]:
        """Update actual cost when project completes.
        
        Args:
            project_id: Project ID
            actual_cost: Actual cost incurred
            
        Returns:
            Updated CostAccuracyTracking record
        """
        tracking = self.db.query(CostAccuracyTracking).filter(
            CostAccuracyTracking.project_id == project_id
        ).first()
        
        if not tracking:
            logger.warning(f"No cost tracking record found for project {project_id}")
            return None
        
        tracking.actual_cost = actual_cost
        tracking.completed_at = datetime.utcnow()
        
        # Calculate accuracy metrics
        if tracking.estimated_cost > 0:
            error = actual_cost - tracking.estimated_cost
            tracking.estimation_error = error
            tracking.accuracy_percentage = max(0, (1 - abs(error) / tracking.estimated_cost) * 100)
        
        self.db.commit()
        self.db.refresh(tracking)
        return tracking
    
    def get_cost_accuracy_stats(
        self,
        project_type: Optional[str] = None,
        cost_profile: Optional[str] = None,
        days: int = 90
    ) -> Dict[str, Any]:
        """Get cost accuracy statistics.
        
        Args:
            project_type: Optional filter by project type
            cost_profile: Optional filter by cost profile
            days: Number of days to look back
            
        Returns:
            Dict with accuracy statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(CostAccuracyTracking).filter(
            CostAccuracyTracking.completed_at.isnot(None),
            CostAccuracyTracking.estimated_at >= cutoff_date
        )
        
        if project_type:
            query = query.filter(CostAccuracyTracking.project_type == project_type)
        if cost_profile:
            query = query.filter(CostAccuracyTracking.cost_profile == cost_profile)
        
        records = query.all()
        
        if not records:
            return {
                "total_projects": 0,
                "avg_accuracy": None,
                "avg_estimation_error": None,
                "underestimates": 0,
                "overestimates": 0,
                "by_project_type": {},
                "by_cost_profile": {},
            }
        
        # Calculate statistics
        total = len(records)
        accuracies = [r.accuracy_percentage for r in records if r.accuracy_percentage is not None]
        errors = [r.estimation_error for r in records if r.estimation_error is not None]
        
        underestimates = sum(1 for e in errors if e > 0)
        overestimates = sum(1 for e in errors if e < 0)
        
        # Group by project type
        by_type: Dict[str, List[float]] = {}
        by_profile: Dict[str, List[float]] = {}
        
        for r in records:
            if r.accuracy_percentage is not None:
                by_type.setdefault(r.project_type, []).append(r.accuracy_percentage)
                by_profile.setdefault(r.cost_profile, []).append(r.accuracy_percentage)
        
        return {
            "total_projects": total,
            "avg_accuracy": sum(accuracies) / len(accuracies) if accuracies else None,
            "avg_estimation_error": sum(errors) / len(errors) if errors else None,
            "underestimates": underestimates,
            "overestimates": overestimates,
            "by_project_type": {
                k: sum(v) / len(v) for k, v in by_type.items()
            },
            "by_cost_profile": {
                k: sum(v) / len(v) for k, v in by_profile.items()
            },
        }
    
    def get_cost_accuracy_data(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get cost accuracy data for charting.
        
        Args:
            limit: Maximum number of records
            
        Returns:
            List of cost accuracy records for visualization
        """
        records = self.db.query(CostAccuracyTracking).filter(
            CostAccuracyTracking.completed_at.isnot(None)
        ).order_by(
            desc(CostAccuracyTracking.completed_at)
        ).limit(limit).all()
        
        return [r.to_dict() for r in records]


# Singleton instance
_analytics_instance: Optional[AgentAnalytics] = None


def get_agent_analytics(db: Session) -> AgentAnalytics:
    """Get agent analytics instance.
    
    Args:
        db: Database session
        
    Returns:
        AgentAnalytics instance
    """
    return AgentAnalytics(db)


def log_agent_performance(
    db: Session,
    project_id: UUID,
    agent_name: str,
    model_used: str,
    execution_time_ms: int,
    tokens_used: Dict[str, int],
    cost: float,
    passed_next_stage: bool = True,
    revision_count: int = 0,
    qa_issues_caused: int = 0,
    quality_score: float = 1.0,
    error_occurred: bool = False,
    error_message: Optional[str] = None
) -> AgentPerformance:
    """Convenience function to log agent performance.
    
    This is the main entry point for logging agent performance from the pipeline.
    """
    analytics = get_agent_analytics(db)
    data = AgentPerformanceData(
        project_id=project_id,
        agent_name=agent_name,
        model_used=model_used,
        execution_time_ms=execution_time_ms,
        tokens_used=tokens_used,
        cost=cost,
        passed_next_stage=passed_next_stage,
        revision_count=revision_count,
        qa_issues_caused=qa_issues_caused,
        quality_score=quality_score,
        error_occurred=error_occurred,
        error_message=error_message,
    )
    return analytics.log_performance(data)
