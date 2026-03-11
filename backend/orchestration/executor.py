"""Pipeline executor for running projects through the agent workflow.

Enhanced with:
- Real-time activity streaming via SSE
- PostgreSQL checkpointing for crash recovery / resume
- Structured audit logging for every pipeline decision
- LangSmith tracing integration (when configured)
"""
import asyncio
import os
import time
import uuid
import logging
import traceback
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from .pipeline import Pipeline, PipelineConfig, NodeStatus
from .checkpointing import save_checkpoint, get_latest_checkpoint, delete_checkpoints
from .checkpoints import CheckpointManager, get_checkpoint_manager
from .audit import (
    audit_pipeline_start, audit_pipeline_complete, audit_pipeline_failed,
    audit_agent_start, audit_agent_complete, audit_agent_failed,
    audit_agent_skipped, audit_agent_retry,
    audit_checkpoint_save, audit_checkpoint_resume,
)

logger = logging.getLogger(__name__)

# Prometheus metrics (graceful no-op if prometheus_client not installed)
from utils.metrics import (
    record_pipeline_start,
    record_pipeline_complete,
    record_pipeline_failure,
    record_agent_run,
    record_checkpoint_pause,
)

# ── LangSmith tracing setup ─────────────────────────────────────────────

_langsmith_enabled = False

try:
    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
        from langsmith import traceable
        _langsmith_enabled = True
        logger.info("LangSmith tracing enabled")
except ImportError:
    traceable = None


def _trace(name: str):
    """Decorator that applies LangSmith tracing when available, otherwise no-op."""
    if _langsmith_enabled and traceable:
        return traceable(name=name)
    return lambda fn: fn


class PipelineExecutor:
    """Executes the pipeline with real agent execution and activity streaming."""

    def __init__(self, db_session=None):
        self.db = db_session
        self._progress_callback: Optional[Callable] = None
        self._step_counter = 0  # tracks which step we're on for checkpointing
        self._checkpoint_manager: Optional[CheckpointManager] = None

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
        resume: bool = True,
    ) -> Dict[str, Any]:
        """Execute the full pipeline for a project.

        If `resume=True` (default), checks for an existing checkpoint and
        resumes from where the pipeline left off instead of starting over.
        """
        pipeline_start = time.time()

        logger.info(f"Starting pipeline execution for project {project_id}")

        # Create pipeline instance with config
        config = PipelineConfig(
            cost_profile=cost_profile,
            continue_on_failure=True,
        )
        pipeline = Pipeline(config=config, db=self.db)

        # Set up context for the pipeline
        context = {
            "project_id": project_id,
            "brief": brief,
            "cost_profile": cost_profile,
            "requirements": requirements or {},
        }

        # ── Check for existing checkpoint to resume from ─────────────
        checkpoint = None
        if resume and self.db:
            checkpoint = get_latest_checkpoint(self.db, project_id)

        if checkpoint:
            # Resume from checkpoint
            self._step_counter = checkpoint["step_number"]
            pipeline.total_cost = checkpoint.get("total_cost", 0.0)
            pipeline.cost_breakdown = checkpoint.get("cost_breakdown", {})

            # Restore node states from checkpoint
            saved_states = checkpoint.get("node_states", {})
            for node_id, state in saved_states.items():
                if node_id in pipeline.nodes:
                    status_str = state.get("status", "pending")
                    try:
                        pipeline.nodes[node_id].status = NodeStatus(status_str)
                    except ValueError:
                        pipeline.nodes[node_id].status = NodeStatus.PENDING

            # Restore context (merge saved context with fresh context)
            saved_context = checkpoint.get("pipeline_context", {})
            # Keep fresh brief/requirements but merge accumulated results
            for key, val in saved_context.items():
                if key.endswith("_result") or key.startswith("qa_retry"):
                    context[key] = val

            completed_agents = [
                nid for nid, s in saved_states.items()
                if s.get("status") in ("completed", "skipped")
            ]

            audit_checkpoint_resume(
                self.db, project_id,
                from_step=checkpoint["step_number"],
                from_agent=checkpoint["agent_name"],
                skipped_agents=completed_agents,
            )

            self._emit_activity(
                project_id, "pipeline_resume",
                f"Resuming from checkpoint (step {checkpoint['step_number']}, "
                f"after {checkpoint['agent_name']})",
                progress=self._estimate_progress(checkpoint["agent_name"])
            )

            logger.info(
                f"Resumed from checkpoint step {checkpoint['step_number']} "
                f"(after {checkpoint['agent_name']})"
            )
        else:
            # Fresh start
            self._step_counter = 0
            self._emit_activity(
                project_id, "pipeline_start",
                "Pipeline started - building your project!",
                progress=0
            )

        # ── Initialize HITL checkpoint manager ─────────────────────
        if self.db:
            self._checkpoint_manager = get_checkpoint_manager(self.db, project_id)

        project_type = (requirements or {}).get("project_type", "unknown")
        audit_pipeline_start(self.db, project_id, cost_profile, project_type)
        record_pipeline_start(cost_profile, project_type)

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
                # Clean up checkpoints on success
                delete_checkpoints(self.db, project_id)

            duration_ms = int((time.time() - pipeline_start) * 1000)
            audit_pipeline_complete(self.db, project_id, pipeline.total_cost, duration_ms)
            record_pipeline_complete(cost_profile, project_type, duration_ms / 1000.0)

            # Emit completion
            self._emit_activity(
                project_id, "pipeline_complete",
                "Project build completed successfully!",
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

            duration_ms = int((time.time() - pipeline_start) * 1000)
            audit_pipeline_failed(self.db, project_id, str(e), duration_ms)
            record_pipeline_failure(cost_profile, project_type, duration_ms / 1000.0)

            # Emit failure
            self._emit_activity(
                project_id, "pipeline_error",
                f"Pipeline failed: {str(e)}",
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

    def _estimate_progress(self, agent_name: str) -> float:
        """Estimate progress percentage from agent name."""
        progress_map = {
            "intake": 10, "research": 18, "architect": 28,
            "design_system": 35, "asset_generation": 42, "content_generation": 48,
            "pm_checkpoint_1": 52, "code_generation": 68, "integration_wiring": 72,
            "pm_checkpoint_2": 76, "code_review": 80, "security": 84,
            "seo": 86, "accessibility": 88, "qa": 92, "deployment": 96,
            "post_deploy_verification": 98, "analytics_monitoring": 99,
            "coding_standards": 100, "delivery": 100,
        }
        return progress_map.get(agent_name, 50)

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
        qa_retry_count = context.get("qa_retry_count", 0)
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

                    audit_agent_retry(
                        self.db, project_id,
                        qa_retry_count, MAX_QA_RETRIES, QA_RETRY_NODES,
                    )

                    self._emit_activity(
                        project_id, "agent_retry",
                        f"QA found issues — retrying code generation "
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
        """Execute a single node with activity streaming, checkpointing, and audit logging."""
        agent_name = node.id
        progress_info = agent_progress.get(agent_name, (50, 60, f"Running {agent_name}..."))
        start_progress, end_progress, message = progress_info

        self._step_counter += 1
        step = self._step_counter

        # Audit + activity: agent start
        audit_agent_start(self.db, project_id, agent_name, step)
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

        agent_start = time.time()

        try:
            # Actually execute the node
            logger.info(f"Executing agent: {agent_name}")
            result = await pipeline.execute_node(node)
            results[node.id] = result

            duration_ms = int((time.time() - agent_start) * 1000)
            cost = 0.0
            if result and hasattr(result, 'data') and isinstance(result.data, dict):
                cost = result.data.get('cost', 0.0)

            # Capture knowledge from successful agent outputs
            if result and result.success and self.db:
                await self._capture_knowledge(project_id, agent_name, result, pipeline.context)

            # Audit + metrics: agent complete or failed
            if result and result.success:
                audit_agent_complete(self.db, project_id, agent_name, duration_ms, cost)
                record_agent_run(agent_name, "success", duration_ms / 1000.0, cost)
            else:
                err = (result.errors[0] if result and result.errors else "unknown")
                audit_agent_failed(self.db, project_id, agent_name, str(err), duration_ms)
                record_agent_run(agent_name, "failure", duration_ms / 1000.0)

            # Emit completion
            status = "complete" if result and result.success else "failed"
            self._emit_activity(
                project_id, f"agent_{status}",
                f"{'Completed' if result and result.success else 'Completed with issues'} {agent_name.replace('_', ' ').title()}",
                agent_name=agent_name,
                progress=end_progress,
                details={"success": result.success if result else False}
            )

        except Exception as e:
            duration_ms = int((time.time() - agent_start) * 1000)
            logger.error(f"Agent {agent_name} failed: {e}")

            audit_agent_failed(self.db, project_id, agent_name, str(e), duration_ms)

            self._emit_activity(
                project_id, "agent_error",
                f"Error in {agent_name}: {str(e)}",
                agent_name=agent_name,
                details={"error": str(e)}
            )
            # Continue with next agents instead of raising
            results[node.id] = None

        # ── HITL: Check if we should pause at this checkpoint ────────
        if self._checkpoint_manager and self._checkpoint_manager.should_pause_at(agent_name):
            agent_output = {}
            if results.get(node.id) and hasattr(results[node.id], 'data'):
                agent_output = results[node.id].data or {}

            self._emit_activity(
                project_id, "checkpoint_pause",
                f"Paused at checkpoint: {agent_name.replace('_', ' ').title()} — waiting for approval",
                agent_name=agent_name,
                details={
                    "checkpoint_agent": agent_name,
                    "requires_approval": True,
                    "output_summary": str(agent_output)[:500] if agent_output else None,
                },
            )

            logger.info(f"HITL: Pausing at checkpoint after {agent_name}")
            record_checkpoint_pause(
                self._checkpoint_manager.get_autonomy_tier(), agent_name
            )

            # Build pipeline state snapshot for checkpoint
            pipeline_state = {
                nid: n.status.value for nid, n in pipeline.nodes.items()
            }

            # This blocks until the user resumes via the API
            await self._checkpoint_manager.pause_at_checkpoint(
                agent_name=agent_name,
                agent_output=agent_output,
                pipeline_state=pipeline_state,
            )

            # Check if user edited the output
            state = self._checkpoint_manager.project.checkpoint_state or {}
            cp_data = state.get("checkpoint_data", {})
            if cp_data.get("edited") and cp_data.get("output_data"):
                # Replace agent result with edited output
                from agents.base import AgentResult
                edited = cp_data["output_data"]
                results[node.id] = AgentResult(
                    success=True,
                    agent_name=agent_name,
                    data=edited,
                )
                # Also update the node result in the pipeline
                if node.id in pipeline.nodes:
                    pipeline.nodes[node.id].result = results[node.id]
                # Store edited result in context for downstream agents
                pipeline.context[f"{agent_name}_result"] = edited

            self._emit_activity(
                project_id, "checkpoint_resume",
                f"Resumed from checkpoint: {agent_name.replace('_', ' ').title()}",
                agent_name=agent_name,
            )

            logger.info(f"HITL: Resumed from checkpoint after {agent_name}")

        # ── Save checkpoint after every agent ────────────────────────
        if self.db:
            self._save_pipeline_checkpoint(project_id, pipeline, agent_name, step)

    def _save_pipeline_checkpoint(
        self, project_id: str, pipeline: Pipeline, agent_name: str, step: int
    ):
        """Snapshot full pipeline state to PostgreSQL."""
        try:
            # Build node_states dict
            node_states = {}
            for nid, node in pipeline.nodes.items():
                node_states[nid] = {
                    "status": node.status.value,
                    "has_result": node.result is not None,
                }

            # Build config dict
            config_dict = {
                "cost_profile": pipeline.config.cost_profile,
                "max_parallel": pipeline.config.max_parallel,
                "timeout_per_node": pipeline.config.timeout_per_node,
                "continue_on_failure": pipeline.config.continue_on_failure,
                "project_type": pipeline.config.project_type,
            }

            agent_status = "completed"
            node = pipeline.nodes.get(agent_name)
            if node:
                agent_status = node.status.value

            cp_id = save_checkpoint(
                db=self.db,
                project_id=project_id,
                agent_name=agent_name,
                agent_status=agent_status,
                node_states=node_states,
                pipeline_context=pipeline.context,
                pipeline_config=config_dict,
                total_cost=pipeline.total_cost,
                cost_breakdown=pipeline.cost_breakdown,
                step_number=step,
            )

            if cp_id:
                audit_checkpoint_save(self.db, project_id, agent_name, step, cp_id)

        except Exception as e:
            logger.warning(f"Checkpoint save failed for {agent_name}: {e}")

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
