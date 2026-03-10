"""Pipeline executor for running projects through the agent workflow."""
import asyncio
import uuid
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from .pipeline import create_pipeline, PipelineState


class PipelineExecutor:
    """Executes the LangGraph pipeline and manages state."""
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.pipeline = create_pipeline()
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self._progress_callback = callback
    
    async def execute(
        self,
        project_id: str,
        brief: str,
        cost_profile: str = "balanced",
    ) -> Dict[str, Any]:
        """Execute the full pipeline for a project."""
        
        # Initialize state
        initial_state: PipelineState = {
            "project_id": project_id,
            "brief": brief,
            "cost_profile": cost_profile,
            "classification": None,
            "research": None,
            "architecture": None,
            "design_system": None,
            "generated_code": None,
            "delivery": None,
            "current_step": 0,
            "status": "running",
            "errors": [],
            "cost_breakdown": {},
            "total_cost": 0.0,
        }
        
        # Update project status in database
        if self.db:
            await self._update_project_status(project_id, "intake")
        
        try:
            # Run the pipeline
            final_state = await self.pipeline.ainvoke(initial_state)
            
            # Update project with results
            if self.db:
                await self._save_project_results(project_id, final_state)
            
            return {
                "success": True,
                "project_id": project_id,
                "status": final_state["status"],
                "total_cost": final_state["total_cost"],
                "cost_breakdown": final_state["cost_breakdown"],
                "delivery": final_state["delivery"],
                "github_repo": final_state["delivery"].get("github_repo") if final_state["delivery"] else None,
            }
            
        except Exception as e:
            # Handle pipeline failure
            if self.db:
                await self._update_project_status(project_id, "failed")
            
            return {
                "success": False,
                "project_id": project_id,
                "status": "failed",
                "error": str(e),
            }
    
    async def _update_project_status(self, project_id: str, status: str):
        """Update project status in database."""
        from models import Project
        from sqlalchemy import update
        
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        self.db.execute(stmt)
        self.db.commit()
    
    async def _save_project_results(self, project_id: str, state: PipelineState):
        """Save final results to database."""
        from models import Project, CostTracking
        from sqlalchemy import update
        import uuid as uuid_module
        
        # Update project
        agent_outputs = {
            "classification": state["classification"],
            "research": state["research"],
            "architecture": state["architecture"],
            "design_system": state["design_system"],
            "generated_code": state["generated_code"],
            "delivery": state["delivery"],
        }
        
        delivery = state.get("delivery", {})
        
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(
                status="completed",
                agent_outputs=agent_outputs,
                github_repo=delivery.get("github_repo"),
                updated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
        )
        self.db.execute(stmt)
        
        # Create cost tracking record
        cost_record = CostTracking(
            id=uuid_module.uuid4(),
            project_id=project_id,
            total_cost=state["total_cost"],
            breakdown={
                "by_agent": state["cost_breakdown"],
            },
            timestamp=datetime.utcnow(),
        )
        self.db.add(cost_record)
        self.db.commit()
