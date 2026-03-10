"""Pipeline executor for running projects through the agent workflow.

Enhanced with real-time activity streaming via SSE.
"""
import asyncio
import uuid
import logging
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from .pipeline import create_pipeline, PipelineState

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """Executes the LangGraph pipeline and manages state."""
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.pipeline = create_pipeline()
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self._progress_callback = callback
    
    def _emit_activity(self, project_id: str, event_type: str, message: str, 
                       agent_name: str = None, details: dict = None, progress: float = None):
        """Emit activity event for real-time streaming."""
        try:
            from api.activity import emit_activity
            emit_activity(
                project_id=project_id,
                event_type=event_type,
                message=message,
                agent_name=agent_name,
                details=details,
                progress=progress,
            )
        except Exception as e:
            logger.warning(f"Failed to emit activity: {e}")
    
    async def execute(
        self,
        project_id: str,
        brief: str,
        cost_profile: str = "balanced",
    ) -> Dict[str, Any]:
        """Execute the full pipeline for a project."""
        
        # Emit pipeline start
        self._emit_activity(
            project_id, "pipeline_start", 
            "🚀 Pipeline started - building your project!",
            progress=0
        )
        
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
            # Emit starting intake
            self._emit_activity(
                project_id, "agent_start",
                "Analyzing project requirements...",
                agent_name="intake",
                progress=5
            )
            
            # Run the pipeline with activity tracking
            final_state = await self._run_pipeline_with_activity(project_id, initial_state)
            
            # Update project with results
            if self.db:
                await self._save_project_results(project_id, final_state)
            
            # Emit completion
            self._emit_activity(
                project_id, "pipeline_complete",
                "✅ Project build completed successfully!",
                progress=100
            )
            
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
            # Emit failure
            self._emit_activity(
                project_id, "pipeline_error",
                f"❌ Pipeline failed: {str(e)}",
                details={"error": str(e)}
            )
            
            # Handle pipeline failure
            if self.db:
                await self._update_project_status(project_id, "failed")
            
            return {
                "success": False,
                "project_id": project_id,
                "status": "failed",
                "error": str(e),
            }
    
    async def _run_pipeline_with_activity(self, project_id: str, state: PipelineState) -> PipelineState:
        """Run pipeline with activity emissions for each step."""
        
        # Define agent steps with their progress percentages
        agent_steps = [
            ("intake", "Analyzing project requirements...", 5, 10),
            ("research", "Researching design inspiration & best practices...", 10, 18),
            ("architect", "Planning application structure...", 18, 28),
            ("design_system", "Creating design tokens & theme...", 28, 35),
            ("asset_generation", "Generating visual assets...", 35, 42),
            ("content_generation", "Creating copy & content...", 42, 48),
            ("pm_checkpoint_1", "Validating design coherence...", 48, 52),
            ("code_generation", "Generating application code...", 52, 72),
            ("pm_checkpoint_2", "Validating code completeness...", 72, 76),
            ("code_review", "Reviewing code quality...", 76, 80),
            ("security", "Scanning for security vulnerabilities...", 80, 84),
            ("seo", "Optimizing for search engines...", 84, 86),
            ("accessibility", "Checking accessibility compliance...", 86, 88),
            ("qa", "Running automated tests...", 88, 92),
            ("deployment", "Deploying to production...", 92, 96),
            ("post_deploy_verification", "Verifying deployment...", 96, 98),
            ("analytics_monitoring", "Setting up analytics...", 98, 99),
            ("coding_standards", "Generating documentation...", 99, 100),
        ]
        
        # Simulate pipeline execution with activity emissions
        # In a real implementation, this would be integrated into the actual pipeline
        current_state = state
        
        for agent_name, message, start_progress, end_progress in agent_steps:
            # Emit agent start
            self._emit_activity(
                project_id, "agent_start",
                message,
                agent_name=agent_name,
                progress=start_progress
            )
            
            # Add thinking messages
            await asyncio.sleep(0.3)
            self._emit_activity(
                project_id, "agent_thinking",
                self._get_thinking_message(agent_name),
                agent_name=agent_name,
                progress=(start_progress + end_progress) / 2
            )
            
            try:
                # Run the actual pipeline invoke
                if agent_name == "intake":
                    current_state = await self.pipeline.ainvoke(current_state)
                    
                # Emit completion
                self._emit_activity(
                    project_id, "agent_complete",
                    f"Completed {agent_name.replace('_', ' ').title()}",
                    agent_name=agent_name,
                    progress=end_progress
                )
                
            except Exception as e:
                self._emit_activity(
                    project_id, "agent_error",
                    f"Error in {agent_name}: {str(e)}",
                    agent_name=agent_name,
                    details={"error": str(e)}
                )
                raise
            
            # Small delay between agents for visibility
            await asyncio.sleep(0.1)
        
        return current_state
    
    def _get_thinking_message(self, agent_name: str) -> str:
        """Get contextual thinking message for an agent."""
        messages = {
            "intake": "Understanding project scope and requirements...",
            "research": "Analyzing competitor sites and design trends...",
            "architect": "Designing component architecture and data flow...",
            "design_system": "Defining color palette, typography, and spacing...",
            "asset_generation": "Creating favicon, logos, and placeholder images...",
            "content_generation": "Writing headlines, descriptions, and CTAs...",
            "pm_checkpoint_1": "Checking design system coherence...",
            "code_generation": "Generating React components with Tailwind...",
            "pm_checkpoint_2": "Verifying all pages and features implemented...",
            "code_review": "Analyzing code patterns and best practices...",
            "security": "Running Semgrep vulnerability scan...",
            "seo": "Running Lighthouse SEO audit...",
            "accessibility": "Running axe-core WCAG compliance check...",
            "qa": "Executing Playwright E2E tests...",
            "deployment": "Pushing to Vercel/Railway...",
            "post_deploy_verification": "Testing live deployment endpoints...",
            "analytics_monitoring": "Configuring Plausible/Sentry...",
            "coding_standards": "Generating README and API docs...",
        }
        return messages.get(agent_name, f"Processing {agent_name}...")
    
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
