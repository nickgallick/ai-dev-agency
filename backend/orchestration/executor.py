"""Pipeline executor for running projects through the agent workflow.

Enhanced with real-time activity streaming via SSE and actual agent execution.
"""
import asyncio
import uuid
import logging
import traceback
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from .pipeline import Pipeline, PipelineConfig, NodeStatus

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """Executes the pipeline with real agent execution and activity streaming."""

    def __init__(self, db_session=None):
        self.db = db_session
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
        requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute the full pipeline for a project."""

        logger.info(f"Starting pipeline execution for project {project_id}")

        # Emit pipeline start
        self._emit_activity(
            project_id, "pipeline_start",
            "🚀 Pipeline started - building your project!",
            progress=0
        )

        # Create pipeline instance with config
        config = PipelineConfig(
            cost_profile=cost_profile,
            continue_on_failure=True,
        )
        pipeline = Pipeline(config=config, db=self.db)

        # Set up context for the pipeline — include structured requirements
        context = {
            "project_id": project_id,
            "brief": brief,
            "cost_profile": cost_profile,
            "requirements": requirements or {},
        }

        # Update project status in database
        if self.db:
            await self._update_project_status(project_id, "intake")

        try:
            # Run the pipeline with activity emissions
            results = await self._run_pipeline_with_activity(
                project_id, pipeline, context
            )

            # Update project with results
            if self.db:
                await self._save_project_results(
                    project_id,
                    results,
                    pipeline.total_cost,
                    pipeline.cost_breakdown
                )

            # Emit completion
            self._emit_activity(
                project_id, "pipeline_complete",
                "✅ Project build completed successfully!",
                progress=100
            )

            # Get delivery info
            delivery_result = results.get("delivery")
            delivery_data = delivery_result.data if delivery_result and delivery_result.success else {}

            return {
                "success": True,
                "project_id": project_id,
                "status": "completed",
                "total_cost": pipeline.total_cost,
                "cost_breakdown": pipeline.cost_breakdown,
                "delivery": delivery_data,
                "github_repo": delivery_data.get("github_repo"),
            }

        except Exception as e:
            logger.error(f"Pipeline failed: {e}\n{traceback.format_exc()}")

            # Emit failure
            self._emit_activity(
                project_id, "pipeline_error",
                f"❌ Pipeline failed: {str(e)}",
                details={"error": str(e), "traceback": traceback.format_exc()}
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

    async def _run_pipeline_with_activity(
        self,
        project_id: str,
        pipeline: Pipeline,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run pipeline with activity emissions for each step."""

        # Define agent steps with their progress percentages
        agent_progress = {
            "intake": (5, 10, "Analyzing project requirements..."),
            "research": (10, 18, "Researching design inspiration & best practices..."),
            "architect": (18, 28, "Planning application structure..."),
            "design_system": (28, 35, "Creating design tokens & theme..."),
            "asset_generation": (35, 42, "Generating visual assets..."),
            "content_generation": (42, 48, "Creating copy & content..."),
            "pm_checkpoint_1": (48, 52, "Validating design coherence..."),
            "code_generation": (52, 68, "Generating application code..."),
            "integration_wiring": (68, 72, "Wiring integrations and APIs..."),
            "pm_checkpoint_2": (72, 76, "Validating code completeness..."),
            "code_review": (76, 80, "Reviewing code quality..."),
            "security": (80, 84, "Scanning for security vulnerabilities..."),
            "seo": (84, 86, "Optimizing for search engines..."),
            "accessibility": (86, 88, "Checking accessibility compliance..."),
            "qa": (88, 92, "Running automated tests..."),
            "deployment": (92, 96, "Deploying to production..."),
            "post_deploy_verification": (96, 98, "Verifying deployment..."),
            "analytics_monitoring": (98, 99, "Setting up analytics..."),
            "coding_standards": (99, 100, "Generating documentation..."),
            "delivery": (100, 100, "Preparing delivery package..."),
        }

        results = {}
        pipeline.context = context

        # QA retry tracking (max 3 attempts)
        qa_retry_count = 0
        MAX_QA_RETRIES = 3
        QA_RETRY_NODES = [
            "code_generation", "integration_wiring", "pm_checkpoint_2", "code_review",
            "security", "seo", "accessibility", "qa"
        ]

        # Run agents in proper order respecting dependencies
        while True:
            ready_nodes = pipeline.get_ready_nodes()
            if not ready_nodes:
                # Check if QA failed and we should retry code generation
                qa_node = pipeline.nodes.get("qa")
                if (
                    qa_node
                    and qa_node.status == NodeStatus.FAILED
                    and qa_retry_count < MAX_QA_RETRIES
                ):
                    qa_retry_count += 1
                    logger.warning(
                        f"QA failed — retrying code generation "
                        f"(attempt {qa_retry_count}/{MAX_QA_RETRIES})"
                    )
                    self._emit_activity(
                        project_id, "agent_retry",
                        f"🔄 QA found issues — retrying code generation "
                        f"(attempt {qa_retry_count}/{MAX_QA_RETRIES})",
                        progress=52
                    )
                    # Reset the code-gen → QA nodes back to PENDING
                    for node_id in QA_RETRY_NODES:
                        node = pipeline.nodes.get(node_id)
                        if node:
                            node.status = NodeStatus.PENDING
                            node.result = None
                    pipeline.context["qa_retry_count"] = qa_retry_count
                    continue

                # Truly done or stuck
                pending = [n for n in pipeline.nodes.values()
                          if n.status == NodeStatus.PENDING]
                if pending:
                    logger.warning(f"Pipeline stuck with pending nodes: {[n.name for n in pending]}")
                break

            # Group by parallel execution
            groups = pipeline.get_parallel_groups(ready_nodes)

            for group_name, group_nodes in groups.items():
                if group_name is not None:
                    # Execute parallel group
                    await self._execute_parallel_with_activity(
                        project_id, pipeline, group_nodes, agent_progress, results
                    )
                else:
                    # Execute sequentially
                    for node in group_nodes:
                        await self._execute_node_with_activity(
                            project_id, pipeline, node, agent_progress, results
                        )

        return results

    async def _execute_node_with_activity(
        self,
        project_id: str,
        pipeline: Pipeline,
        node,
        agent_progress: Dict,
        results: Dict
    ):
        """Execute a single node with activity streaming."""
        agent_name = node.id
        progress_info = agent_progress.get(agent_name, (50, 60, f"Running {agent_name}..."))
        start_progress, end_progress, message = progress_info

        # Emit agent start
        self._emit_activity(
            project_id, "agent_start",
            message,
            agent_name=agent_name,
            progress=start_progress
        )

        # Emit thinking message
        await asyncio.sleep(0.1)
        self._emit_activity(
            project_id, "agent_thinking",
            self._get_thinking_message(agent_name),
            agent_name=agent_name,
            progress=(start_progress + end_progress) / 2
        )

        try:
            # Actually execute the node
            logger.info(f"Executing agent: {agent_name}")
            result = await pipeline.execute_node(node)
            results[node.id] = result

            # Capture knowledge from successful agent outputs
            if result and result.success and self.db:
                await self._capture_knowledge(project_id, agent_name, result, pipeline.context)

            # Emit completion
            status = "complete" if result and result.success else "failed"
            self._emit_activity(
                project_id, f"agent_{status}",
                f"{'✅ Completed' if result and result.success else '⚠️ Completed with issues'} {agent_name.replace('_', ' ').title()}",
                agent_name=agent_name,
                progress=end_progress,
                details={"success": result.success if result else False}
            )

        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")
            self._emit_activity(
                project_id, "agent_error",
                f"❌ Error in {agent_name}: {str(e)}",
                agent_name=agent_name,
                details={"error": str(e)}
            )
            # Continue with next agents instead of raising
            results[node.id] = None

    async def _execute_parallel_with_activity(
        self,
        project_id: str,
        pipeline: Pipeline,
        nodes,
        agent_progress: Dict,
        results: Dict
    ):
        """Execute parallel nodes with activity streaming."""
        tasks = []
        for node in nodes:
            tasks.append(
                self._execute_node_with_activity(
                    project_id, pipeline, node, agent_progress, results
                )
            )
        await asyncio.gather(*tasks, return_exceptions=True)

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
            "integration_wiring": "Wiring third-party integrations and generating .env.example...",
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

    async def _capture_knowledge(
        self, project_id: str, agent_name: str, result, context: Dict[str, Any]
    ):
        """Capture knowledge from a completed agent into the knowledge base."""
        try:
            from knowledge.capture import capture_agent_knowledge

            output_data = result.data if hasattr(result, "data") else {}
            if not isinstance(output_data, dict):
                return

            project_type = context.get("requirements", {}).get("project_type")
            industry = context.get("requirements", {}).get("industry")
            tech_stack = context.get("requirements", {}).get("tech_stack")

            await capture_agent_knowledge(
                db=self.db,
                agent_name=agent_name,
                agent_output=output_data,
                project_id=project_id,
                project_type=project_type,
                industry=industry,
                tech_stack=tech_stack if isinstance(tech_stack, list) else None,
            )
        except Exception as e:
            logger.warning(f"Knowledge capture failed for {agent_name}: {e}")

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

    async def _save_project_results(
        self,
        project_id: str,
        results: Dict[str, Any],
        total_cost: float,
        cost_breakdown: Dict[str, float]
    ):
        """Save final results to database."""
        from models import Project, CostTracking
        from sqlalchemy import update
        import uuid as uuid_module

        # Extract agent outputs from results
        agent_outputs = {}
        for agent_name, result in results.items():
            if result and hasattr(result, 'data'):
                agent_outputs[agent_name] = result.data
            elif result:
                agent_outputs[agent_name] = {"success": result.success if hasattr(result, 'success') else False}

        # Get delivery info
        delivery_result = results.get("delivery")
        delivery_data = delivery_result.data if delivery_result and hasattr(delivery_result, 'data') else {}
        github_repo = delivery_data.get("github_repo") if isinstance(delivery_data, dict) else None

        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(
                status="completed",
                agent_outputs=agent_outputs,
                github_repo=github_repo,
                updated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
        )
        self.db.execute(stmt)

        # Create cost tracking record
        cost_record = CostTracking(
            id=uuid_module.uuid4(),
            project_id=project_id,
            total_cost=total_cost,
            breakdown={
                "by_agent": cost_breakdown,
            },
            timestamp=datetime.utcnow(),
        )
        self.db.add(cost_record)
        self.db.commit()
