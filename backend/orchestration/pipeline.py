"""Pipeline orchestration for AI Dev Agency agents.

Enhanced with:
- Project Manager checkpoints (coherence and completeness)
- Code Review agent
- Post-Deploy Verification agent
- Dynamic agent pooling for parallel code generation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type

from agents.base import AgentResult, BaseAgent
from agents.security import SecurityAgent
from agents.seo import SEOAgent
from agents.accessibility import AccessibilityAgent
from agents.qa_testing import QATestingAgent
from agents.deployment import DeploymentAgent
from agents.analytics_monitoring import AnalyticsMonitoringAgent
from agents.coding_standards import CodingStandardsAgent
from agents.revision_handler import RevisionHandlerAgent
from agents.project_manager import ProjectManagerAgent, COMPLEX_PROJECT_TYPES
from agents.code_review import CodeReviewAgent
from agents.post_deploy_verification import PostDeployVerificationAgent
from config.settings import Settings
from utils.cost_optimizer import get_cost_optimizer, CostProfile


class NodeStatus(Enum):
    """Pipeline node execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineNode:
    """Represents a node in the pipeline DAG."""
    id: str
    name: str
    agent_class: Type[BaseAgent]
    dependencies: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[AgentResult] = None
    parallel_group: Optional[str] = None  # Nodes with same group run in parallel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "parallel_group": self.parallel_group,
        }


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    max_parallel: int = 4
    timeout_per_node: int = 600
    continue_on_failure: bool = True
    skip_on_dependency_failure: bool = True
    cost_profile: str = "balanced"
    revision_mode: bool = False
    revision_scope: str = "medium_feature"  # small_tweak, medium_feature, major_addition
    project_type: str = "web_simple"
    cost_alert_threshold: float = 50.0
    # Dynamic pooling settings
    enable_dynamic_pooling: bool = True
    max_parallel_code_gen: int = 5  # Max concurrent v0 API sessions
    pooling_batch_threshold: int = 10  # Activate pooling when 10+ prompts


# Project type configurations
PROJECT_TYPE_CONFIGS = {
    # Web projects - full pipeline
    "web_simple": {
        "skip_agents": [],
        "required_agents": ["intake", "code_generation", "deployment"],
    },
    "web_complex": {
        "skip_agents": [],
        "required_agents": ["intake", "architect", "code_generation", "security", "deployment"],
    },
    # Mobile projects - skip web-specific agents
    "mobile_native_ios": {
        "skip_agents": ["seo"],  # SEO not relevant for native apps
        "required_agents": ["intake", "architect", "code_generation", "security", "deployment"],
    },
    "mobile_cross_platform": {
        "skip_agents": ["seo"],
        "required_agents": ["intake", "architect", "code_generation", "security", "deployment"],
    },
    "mobile_pwa": {
        "skip_agents": [],  # PWA benefits from SEO
        "required_agents": ["intake", "code_generation", "seo", "deployment"],
    },
    # Desktop apps
    "desktop_app": {
        "skip_agents": ["seo"],
        "required_agents": ["intake", "architect", "code_generation", "security", "deployment"],
    },
    # Chrome extensions
    "chrome_extension": {
        "skip_agents": ["seo"],
        "required_agents": ["intake", "code_generation", "security", "deployment"],
    },
    # CLI tools
    "cli_tool": {
        "skip_agents": ["seo", "accessibility", "design_system"],
        "required_agents": ["intake", "code_generation", "deployment"],
    },
    # Python projects
    "python_api": {
        "skip_agents": ["seo", "accessibility", "design_system"],
        "required_agents": ["intake", "architect", "code_generation", "security", "deployment"],
    },
    "python_saas": {
        "skip_agents": [],
        "required_agents": ["intake", "architect", "code_generation", "security", "deployment"],
    },
}


# Revision scope agent mapping
REVISION_AGENT_MAPPING = {
    "small_tweak": ["code_generation"],
    "medium_feature": ["architect", "code_generation", "qa"],
    "major_addition": ["intake", "architect", "design_system", "code_generation", "security", "qa", "deployment"],
}


class Pipeline:
    """Orchestrates agent execution in a directed acyclic graph (DAG)."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        config: Optional[PipelineConfig] = None,
    ):
        self.settings = settings or Settings()
        self.config = config or PipelineConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.nodes: Dict[str, PipelineNode] = {}
        self.context: Dict[str, Any] = {}
        self.cost_optimizer = get_cost_optimizer()
        self.total_cost: float = 0.0
        self.cost_breakdown: Dict[str, float] = {}
        self._setup_default_pipeline()
    
    def configure_for_project_type(self, project_type: str) -> None:
        """Configure pipeline for a specific project type."""
        self.config.project_type = project_type
        type_config = PROJECT_TYPE_CONFIGS.get(project_type, PROJECT_TYPE_CONFIGS["web_simple"])
        
        # Skip agents that aren't relevant for this project type
        for agent_id in type_config.get("skip_agents", []):
            if agent_id in self.nodes:
                self.nodes[agent_id].status = NodeStatus.SKIPPED
                self.logger.info(f"Skipping {agent_id} for project type {project_type}")
    
    def configure_for_revision(self, revision_scope: str) -> None:
        """Configure pipeline for revision mode."""
        self.config.revision_mode = True
        self.config.revision_scope = revision_scope
        
        # Get agents needed for this revision scope
        needed_agents = REVISION_AGENT_MAPPING.get(revision_scope, ["code_generation"])
        
        # Skip agents not needed for this revision
        for node_id, node in self.nodes.items():
            if node_id not in needed_agents:
                node.status = NodeStatus.SKIPPED
                self.logger.info(f"Skipping {node_id} for revision scope {revision_scope}")
    
    def get_cost_estimate(self) -> Dict[str, Any]:
        """Get cost estimate for the pipeline execution."""
        estimate = self.cost_optimizer.estimate_project_cost(
            project_type=self.config.project_type,
            cost_profile=CostProfile(self.config.cost_profile),
            complexity_score=5,  # Default complexity
        )
        
        return {
            "min_cost": estimate.min_cost,
            "max_cost": estimate.max_cost,
            "expected_cost": estimate.expected_cost,
            "breakdown": estimate.breakdown,
            "confidence": estimate.confidence,
        }
    
    def track_agent_cost(self, agent_name: str, cost: float) -> None:
        """Track cost for an agent execution."""
        self.total_cost += cost
        self.cost_breakdown[agent_name] = self.cost_breakdown.get(agent_name, 0) + cost
        
        # Check for cost alerts
        alert = self.cost_optimizer.check_cost_alert(
            project_id=self.context.get("project_id", "unknown"),
            current_cost=self.total_cost,
            budget_limit=self.config.cost_alert_threshold,
        )
        
        if alert:
            self.logger.warning(
                f"Cost alert: Project {alert.project_id} at ${alert.current_cost:.2f} "
                f"({alert.percentage:.0f}% of ${alert.threshold:.2f} threshold)"
            )

    def _setup_default_pipeline(self) -> None:
        """Setup the default pipeline with all agents.
        
        Pipeline order:
        1-6. Intake, Research, Architect, Design System, Assets, Content (parallel)
        ★ PM Checkpoint 1 (coherence)
        7. Code Generation (with dynamic pooling)
        ★ PM Checkpoint 2 (completeness)
        ★ Code Review
        8-10. Security/SEO/Accessibility (parallel)
        11. QA & Testing
        12. Deployment
        ★ Post-Deploy Verification
        13-14. Monitoring/Standards (parallel)
        15. Delivery
        """
        # Placeholders for Phase 1-2 agents (intake, research, architect, etc.)
        self.add_node(PipelineNode(
            id="intake",
            name="Intake & Classification",
            agent_class=BaseAgent,  # Placeholder
            dependencies=[],
        ))
        
        self.add_node(PipelineNode(
            id="research",
            name="Research",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["intake"],
        ))
        
        self.add_node(PipelineNode(
            id="architect",
            name="Architect",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["research"],
        ))
        
        self.add_node(PipelineNode(
            id="design_system",
            name="Design System",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["architect"],
        ))
        
        # Asset and Content generation run in parallel
        self.add_node(PipelineNode(
            id="asset_generation",
            name="Asset Generation",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["architect"],
            parallel_group="content_assets",
        ))
        
        self.add_node(PipelineNode(
            id="content_generation",
            name="Content Generation",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["architect"],
            parallel_group="content_assets",
        ))
        
        # ★ PM Checkpoint 1: Coherence validation
        # Runs after Architect + Design System + Content + Assets, before Code Gen
        self.add_node(PipelineNode(
            id="pm_checkpoint_1",
            name="PM Checkpoint 1 (Coherence)",
            agent_class=ProjectManagerAgent,
            dependencies=["architect", "design_system", "asset_generation", "content_generation"],
        ))

        # Code Generation (with dynamic pooling support)
        self.add_node(PipelineNode(
            id="code_generation",
            name="Code Generation",
            agent_class=BaseAgent,  # Placeholder - actual implementation uses v0 API
            dependencies=["pm_checkpoint_1"],
        ))
        
        # ★ PM Checkpoint 2: Completeness validation
        # Runs after Code Gen, before Quality Gate
        self.add_node(PipelineNode(
            id="pm_checkpoint_2",
            name="PM Checkpoint 2 (Completeness)",
            agent_class=ProjectManagerAgent,
            dependencies=["code_generation"],
        ))
        
        # ★ Code Review Agent
        # Runs after PM Checkpoint 2, before Security/SEO/Accessibility
        self.add_node(PipelineNode(
            id="code_review",
            name="Code Review",
            agent_class=CodeReviewAgent,
            dependencies=["pm_checkpoint_2"],
        ))

        # Quality & Compliance - Run in parallel after Code Review
        self.add_node(PipelineNode(
            id="security",
            name="Security Scan",
            agent_class=SecurityAgent,
            dependencies=["code_review"],
            parallel_group="quality",
        ))

        self.add_node(PipelineNode(
            id="seo",
            name="SEO Audit",
            agent_class=SEOAgent,
            dependencies=["code_review"],
            parallel_group="quality",
        ))

        self.add_node(PipelineNode(
            id="accessibility",
            name="Accessibility Audit",
            agent_class=AccessibilityAgent,
            dependencies=["code_review"],
            parallel_group="quality",
        ))

        # QA Testing Agent - runs after all quality checks complete
        self.add_node(PipelineNode(
            id="qa",
            name="QA Testing",
            agent_class=QATestingAgent,
            dependencies=["security", "seo", "accessibility"],
        ))

        # Deployment Agent - runs after QA passes
        self.add_node(PipelineNode(
            id="deployment",
            name="Deployment",
            agent_class=DeploymentAgent,
            dependencies=["qa"],
        ))
        
        # ★ Post-Deploy Verification Agent
        # Runs after Deployment, before Delivery
        self.add_node(PipelineNode(
            id="post_deploy_verification",
            name="Post-Deploy Verification",
            agent_class=PostDeployVerificationAgent,
            dependencies=["deployment"],
        ))

        # Monitoring & Standards - Run in parallel after Post-Deploy Verification
        self.add_node(PipelineNode(
            id="analytics_monitoring",
            name="Analytics & Monitoring",
            agent_class=AnalyticsMonitoringAgent,
            dependencies=["post_deploy_verification"],
            parallel_group="phase6",
        ))

        self.add_node(PipelineNode(
            id="coding_standards",
            name="Coding Standards",
            agent_class=CodingStandardsAgent,
            dependencies=["post_deploy_verification"],
            parallel_group="phase6",
        ))
        
        # Delivery Agent (placeholder)
        self.add_node(PipelineNode(
            id="delivery",
            name="Delivery",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["analytics_monitoring", "coding_standards"],
        ))
        
        # Revision Handler (only activated in revision mode)
        self.add_node(PipelineNode(
            id="revision_handler",
            name="Revision Handler",
            agent_class=RevisionHandlerAgent,
            dependencies=[],  # Entry point for revisions
            status=NodeStatus.SKIPPED,  # Skipped by default, enabled in revision mode
        ))

    def add_node(self, node: PipelineNode) -> None:
        """Add a node to the pipeline."""
        self.nodes[node.id] = node

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the pipeline."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            # Remove from dependencies of other nodes
            for node in self.nodes.values():
                if node_id in node.dependencies:
                    node.dependencies.remove(node_id)

    def get_ready_nodes(self) -> List[PipelineNode]:
        """Get nodes that are ready to execute (all dependencies completed)."""
        ready = []
        for node in self.nodes.values():
            if node.status != NodeStatus.PENDING:
                continue

            # Check if all dependencies are completed
            deps_completed = all(
                self.nodes[dep].status == NodeStatus.COMPLETED
                for dep in node.dependencies
                if dep in self.nodes
            )

            # Check if any dependency failed
            deps_failed = any(
                self.nodes[dep].status == NodeStatus.FAILED
                for dep in node.dependencies
                if dep in self.nodes
            )

            if deps_failed and self.config.skip_on_dependency_failure:
                node.status = NodeStatus.SKIPPED
                continue

            if deps_completed:
                ready.append(node)

        return ready

    def get_parallel_groups(
        self, nodes: List[PipelineNode]
    ) -> Dict[Optional[str], List[PipelineNode]]:
        """Group nodes by their parallel group."""
        groups: Dict[Optional[str], List[PipelineNode]] = {}
        for node in nodes:
            group = node.parallel_group
            if group not in groups:
                groups[group] = []
            groups[group].append(node)
        return groups

    async def execute_node(self, node: PipelineNode) -> AgentResult:
        """Execute a single pipeline node."""
        self.logger.info(f"Executing node: {node.name}")
        node.status = NodeStatus.RUNNING

        try:
            # Skip placeholder agents
            if node.agent_class == BaseAgent:
                self.logger.info(f"Skipping placeholder node: {node.name}")
                node.status = NodeStatus.COMPLETED
                node.result = AgentResult(
                    success=True,
                    agent_name=node.name,
                    data={"placeholder": True},
                )
                return node.result

            # Create and run agent
            agent = node.agent_class(settings=self.settings)
            result = await asyncio.wait_for(
                agent.run(self.context),
                timeout=self.config.timeout_per_node,
            )

            node.result = result
            node.status = (
                NodeStatus.COMPLETED if result.success else NodeStatus.FAILED
            )

            # Store result in context for downstream nodes
            self.context[f"{node.id}_result"] = result.data

            return result

        except asyncio.TimeoutError:
            self.logger.error(f"Node {node.name} timed out")
            node.status = NodeStatus.FAILED
            node.result = AgentResult(
                success=False,
                agent_name=node.name,
                errors=["Execution timed out"],
            )
            return node.result

        except Exception as e:
            self.logger.error(f"Node {node.name} failed: {e}")
            node.status = NodeStatus.FAILED
            node.result = AgentResult(
                success=False,
                agent_name=node.name,
                errors=[str(e)],
            )
            return node.result

    async def execute_parallel_group(
        self, nodes: List[PipelineNode]
    ) -> List[AgentResult]:
        """Execute a group of nodes in parallel."""
        self.logger.info(
            f"Executing parallel group: {[n.name for n in nodes]}"
        )
        
        tasks = [self.execute_node(node) for node in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                nodes[i].status = NodeStatus.FAILED
                nodes[i].result = AgentResult(
                    success=False,
                    agent_name=nodes[i].name,
                    errors=[str(result)],
                )
                processed_results.append(nodes[i].result)
            else:
                processed_results.append(result)

        return processed_results

    async def run(
        self,
        context: Optional[Dict[str, Any]] = None,
        start_from: Optional[str] = None,
        only_nodes: Optional[List[str]] = None,
    ) -> Dict[str, AgentResult]:
        """Execute the pipeline."""
        self.context = context or {}
        results: Dict[str, AgentResult] = {}

        # Reset node statuses
        for node in self.nodes.values():
            if only_nodes and node.id not in only_nodes:
                node.status = NodeStatus.SKIPPED
            elif start_from and node.id != start_from:
                # Mark nodes before start_from as completed
                if self._is_upstream_of(node.id, start_from):
                    node.status = NodeStatus.COMPLETED
            else:
                node.status = NodeStatus.PENDING

        self.logger.info("Starting pipeline execution")

        while True:
            ready_nodes = self.get_ready_nodes()
            if not ready_nodes:
                # Check if we're done or stuck
                pending = [n for n in self.nodes.values() 
                          if n.status == NodeStatus.PENDING]
                if pending:
                    self.logger.warning(
                        f"Pipeline stuck with pending nodes: {[n.name for n in pending]}"
                    )
                break

            # Group by parallel execution
            groups = self.get_parallel_groups(ready_nodes)

            for group_name, group_nodes in groups.items():
                if group_name is not None:
                    # Execute parallel group
                    group_results = await self.execute_parallel_group(group_nodes)
                    for node, result in zip(group_nodes, group_results):
                        results[node.id] = result
                else:
                    # Execute sequentially
                    for node in group_nodes:
                        result = await self.execute_node(node)
                        results[node.id] = result

        self.logger.info("Pipeline execution completed")
        return results

    def _is_upstream_of(self, node_id: str, target_id: str) -> bool:
        """Check if node_id is upstream of target_id in the DAG."""
        if node_id == target_id:
            return False

        target_node = self.nodes.get(target_id)
        if not target_node:
            return False

        # BFS to find if node_id is an ancestor of target_id
        visited: Set[str] = set()
        queue = list(target_node.dependencies)

        while queue:
            current = queue.pop(0)
            if current == node_id:
                return True
            if current in visited:
                continue
            visited.add(current)

            current_node = self.nodes.get(current)
            if current_node:
                queue.extend(current_node.dependencies)

        return False

    async def run_quality_checks(
        self, context: Dict[str, Any]
    ) -> Dict[str, AgentResult]:
        """Run only the Phase 4 quality check agents in parallel."""
        self.context = context
        quality_nodes = ["security", "seo", "accessibility"]
        
        # Get the quality nodes
        nodes_to_run = [
            self.nodes[node_id] for node_id in quality_nodes
            if node_id in self.nodes
        ]

        # Execute all in parallel
        results_list = await self.execute_parallel_group(nodes_to_run)
        
        return {
            node.id: result 
            for node, result in zip(nodes_to_run, results_list)
        }
    
    async def execute_code_gen_with_pooling(
        self,
        code_gen_prompts: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[AgentResult]:
        """Execute code generation with dynamic pooling.
        
        When Architect produces 10+ prompts, groups into batches:
        - Batch 1 (foundation): sequential, single agent
        - Batch 2+ (pages): parallel, max 5 agents
        - Batch 3 (integration): sequential, single agent
        
        Only activates for balanced and premium cost profiles.
        """
        if not self.config.enable_dynamic_pooling:
            return await self._execute_code_gen_sequential(code_gen_prompts, context)
        
        # Check if pooling should be activated
        if len(code_gen_prompts) < self.config.pooling_batch_threshold:
            self.logger.info(f"Only {len(code_gen_prompts)} prompts - using sequential execution")
            return await self._execute_code_gen_sequential(code_gen_prompts, context)
        
        # Only use pooling for balanced and premium profiles
        if self.config.cost_profile == "budget":
            self.logger.info("Budget profile - using sequential execution")
            return await self._execute_code_gen_sequential(code_gen_prompts, context)
        
        self.logger.info(f"Dynamic pooling activated for {len(code_gen_prompts)} prompts")
        
        # Categorize prompts into batches
        batches = self._categorize_prompts(code_gen_prompts)
        
        all_results = []
        
        # Batch 1: Foundation (sequential)
        if batches["foundation"]:
            self.logger.info(f"Executing foundation batch: {len(batches['foundation'])} prompts")
            for prompt in batches["foundation"]:
                result = await self._execute_single_code_gen(prompt, context)
                all_results.append(result)
        
        # Batch 2: Pages (parallel, max 5 concurrent)
        if batches["pages"]:
            self.logger.info(f"Executing pages batch: {len(batches['pages'])} prompts in parallel")
            page_results = await self._execute_code_gen_parallel(
                batches["pages"],
                context,
                max_concurrent=self.config.max_parallel_code_gen,
            )
            all_results.extend(page_results)
        
        # Batch 3: Integration (sequential)
        if batches["integration"]:
            self.logger.info(f"Executing integration batch: {len(batches['integration'])} prompts")
            for prompt in batches["integration"]:
                result = await self._execute_single_code_gen(prompt, context)
                all_results.append(result)
        
        return all_results
    
    def _categorize_prompts(
        self,
        prompts: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize prompts into foundation, pages, and integration batches."""
        batches = {
            "foundation": [],
            "pages": [],
            "integration": [],
        }
        
        foundation_keywords = ["layout", "config", "setup", "base", "root", "provider", "context"]
        integration_keywords = ["api", "integration", "connection", "routing", "navigation"]
        
        for prompt in prompts:
            prompt_text = prompt.get("prompt", "").lower()
            name = prompt.get("name", "").lower()
            category = prompt.get("category", "")
            
            if category:
                # Use explicit category if provided
                if category in batches:
                    batches[category].append(prompt)
                    continue
            
            # Auto-categorize based on keywords
            if any(kw in prompt_text or kw in name for kw in foundation_keywords):
                batches["foundation"].append(prompt)
            elif any(kw in prompt_text or kw in name for kw in integration_keywords):
                batches["integration"].append(prompt)
            else:
                batches["pages"].append(prompt)
        
        return batches
    
    async def _execute_code_gen_sequential(
        self,
        prompts: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[AgentResult]:
        """Execute code generation prompts sequentially."""
        results = []
        for prompt in prompts:
            result = await self._execute_single_code_gen(prompt, context)
            results.append(result)
        return results
    
    async def _execute_code_gen_parallel(
        self,
        prompts: List[Dict[str, Any]],
        context: Dict[str, Any],
        max_concurrent: int = 5,
    ) -> List[AgentResult]:
        """Execute code generation prompts in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_limit(prompt: Dict[str, Any]) -> AgentResult:
            async with semaphore:
                return await self._execute_single_code_gen(prompt, context)
        
        tasks = [execute_with_limit(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(AgentResult(
                    success=False,
                    agent_name="code_generation",
                    errors=[str(result)],
                    data={"prompt": prompts[i].get("name", f"prompt_{i}")},
                ))
            else:
                processed.append(result)
        
        return processed
    
    async def _execute_single_code_gen(
        self,
        prompt: Dict[str, Any],
        context: Dict[str, Any],
    ) -> AgentResult:
        """Execute a single code generation prompt.
        
        This is a placeholder - actual implementation would use v0 API.
        """
        prompt_name = prompt.get("name", "unknown")
        self.logger.info(f"Executing code gen prompt: {prompt_name}")
        
        # Placeholder implementation
        # In real implementation, this would call the v0 API
        return AgentResult(
            success=True,
            agent_name="code_generation",
            data={
                "prompt_name": prompt_name,
                "generated": True,
            },
        )
    
    def configure_pm_checkpoints(self, project_type: str) -> None:
        """Configure PM checkpoints based on project type.
        
        PM checkpoints only activate for complex project types:
        - web_complex
        - python_saas
        - mobile_cross_platform
        - desktop_app
        """
        if project_type not in COMPLEX_PROJECT_TYPES:
            # Skip PM checkpoints for simple projects
            if "pm_checkpoint_1" in self.nodes:
                self.nodes["pm_checkpoint_1"].status = NodeStatus.SKIPPED
            if "pm_checkpoint_2" in self.nodes:
                self.nodes["pm_checkpoint_2"].status = NodeStatus.SKIPPED
            self.logger.info(f"PM checkpoints skipped for project type: {project_type}")
        else:
            self.logger.info(f"PM checkpoints enabled for complex project: {project_type}")

    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "nodes": {
                node_id: node.to_dict()
                for node_id, node in self.nodes.items()
            },
            "summary": {
                "total": len(self.nodes),
                "completed": sum(
                    1 for n in self.nodes.values()
                    if n.status == NodeStatus.COMPLETED
                ),
                "failed": sum(
                    1 for n in self.nodes.values()
                    if n.status == NodeStatus.FAILED
                ),
                "pending": sum(
                    1 for n in self.nodes.values()
                    if n.status == NodeStatus.PENDING
                ),
                "running": sum(
                    1 for n in self.nodes.values()
                    if n.status == NodeStatus.RUNNING
                ),
                "skipped": sum(
                    1 for n in self.nodes.values()
                    if n.status == NodeStatus.SKIPPED
                ),
            },
            "cost": {
                "total": round(self.total_cost, 4),
                "breakdown": self.cost_breakdown,
                "profile": self.config.cost_profile,
            },
            "config": {
                "project_type": self.config.project_type,
                "revision_mode": self.config.revision_mode,
                "revision_scope": self.config.revision_scope if self.config.revision_mode else None,
            },
        }

    def visualize(self) -> str:
        """Generate a text visualization of the pipeline DAG."""
        lines = ["Pipeline DAG:", "=" * 40]

        # Group nodes by level (distance from root)
        levels: Dict[int, List[str]] = {}
        
        def get_level(node_id: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()
            if node_id in visited:
                return 0
            visited.add(node_id)
            
            node = self.nodes.get(node_id)
            if not node or not node.dependencies:
                return 0
            return 1 + max(
                get_level(dep, visited.copy())
                for dep in node.dependencies
                if dep in self.nodes
            )

        for node_id in self.nodes:
            level = get_level(node_id)
            if level not in levels:
                levels[level] = []
            levels[level].append(node_id)

        for level in sorted(levels.keys()):
            nodes_at_level = levels[level]
            indent = "  " * level
            for node_id in nodes_at_level:
                node = self.nodes[node_id]
                status_icon = {
                    NodeStatus.PENDING: "⏳",
                    NodeStatus.RUNNING: "🔄",
                    NodeStatus.COMPLETED: "✅",
                    NodeStatus.FAILED: "❌",
                    NodeStatus.SKIPPED: "⏭️",
                }.get(node.status, "?")
                
                parallel_tag = f" [{node.parallel_group}]" if node.parallel_group else ""
                lines.append(f"{indent}{status_icon} {node.name}{parallel_tag}")
                
                if node.dependencies:
                    deps = ", ".join(node.dependencies)
                    lines.append(f"{indent}   └─ depends on: {deps}")

        return "\n".join(lines)


# Factory function and state class for backwards compatibility
class PipelineState:
    """State object for pipeline execution tracking."""
    
    def __init__(self, project_id: str = ""):
        self.project_id = project_id
        self.current_node: Optional[str] = None
        self.completed_nodes: List[str] = []
        self.failed_nodes: List[str] = []
        self.context: Dict[str, Any] = {}
        self.errors: List[str] = []
        # Phase 6 additions
        self.monitoring_config: Dict[str, Any] = {}
        self.documentation_links: Dict[str, str] = {}
        # Phase 8 additions - new agent outputs
        self.build_manifest: Optional[Dict[str, Any]] = None
        self.code_review_report: Optional[Dict[str, Any]] = None
        self.deploy_verification: Optional[Dict[str, Any]] = None
    
    def update_monitoring_config(self, config: Dict[str, Any]) -> None:
        """Update monitoring configuration from Analytics & Monitoring agent."""
        self.monitoring_config.update(config)
    
    def update_documentation_links(self, links: Dict[str, str]) -> None:
        """Update documentation links from Coding Standards agent."""
        self.documentation_links.update(links)
    
    def update_build_manifest(self, manifest: Dict[str, Any]) -> None:
        """Update build manifest from PM Checkpoint 1."""
        self.build_manifest = manifest
    
    def update_code_review_report(self, report: Dict[str, Any]) -> None:
        """Update code review report from Code Review agent."""
        self.code_review_report = report
    
    def update_deploy_verification(self, verification: Dict[str, Any]) -> None:
        """Update deployment verification from Post-Deploy Verification agent."""
        self.deploy_verification = verification
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "project_id": self.project_id,
            "current_node": self.current_node,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "errors": self.errors,
            "monitoring_config": self.monitoring_config,
            "documentation_links": self.documentation_links,
            "build_manifest": self.build_manifest,
            "code_review_report": self.code_review_report,
            "deploy_verification": self.deploy_verification,
        }


def create_pipeline(settings: Optional[Settings] = None, config: Optional[PipelineConfig] = None) -> Pipeline:
    """Factory function to create a configured pipeline instance."""
    pipeline = Pipeline(settings=settings, config=config)
    return pipeline
