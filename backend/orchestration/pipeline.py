"""Pipeline orchestration for AI Dev Agency agents."""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type

from ..agents.base import AgentResult, BaseAgent
from ..agents.security import SecurityAgent
from ..agents.seo import SEOAgent
from ..agents.accessibility import AccessibilityAgent
from ..config.settings import Settings


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
        self._setup_default_pipeline()

    def _setup_default_pipeline(self) -> None:
        """Setup the default pipeline with all agents."""
        # Phase 1: Code Generation (placeholder for future implementation)
        self.add_node(PipelineNode(
            id="code_generation",
            name="Code Generation",
            agent_class=BaseAgent,  # Placeholder
            dependencies=[],
        ))

        # Phase 2: Documentation (placeholder)
        self.add_node(PipelineNode(
            id="documentation",
            name="Documentation",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["code_generation"],
        ))

        # Phase 3: Testing (placeholder)
        self.add_node(PipelineNode(
            id="testing",
            name="Testing",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["code_generation"],
        ))

        # Phase 4: Quality & Compliance - Run in parallel after Code Generation
        self.add_node(PipelineNode(
            id="security",
            name="Security Scan",
            agent_class=SecurityAgent,
            dependencies=["code_generation"],
            parallel_group="quality",
        ))

        self.add_node(PipelineNode(
            id="seo",
            name="SEO Audit",
            agent_class=SEOAgent,
            dependencies=["code_generation"],
            parallel_group="quality",
        ))

        self.add_node(PipelineNode(
            id="accessibility",
            name="Accessibility Audit",
            agent_class=AccessibilityAgent,
            dependencies=["code_generation"],
            parallel_group="quality",
        ))

        # QA Agent - runs after all quality checks complete
        self.add_node(PipelineNode(
            id="qa",
            name="QA Review",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["security", "seo", "accessibility", "testing"],
        ))

        # Phase 5: Deployment (placeholder)
        self.add_node(PipelineNode(
            id="deployment",
            name="Deployment",
            agent_class=BaseAgent,  # Placeholder
            dependencies=["qa"],
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
