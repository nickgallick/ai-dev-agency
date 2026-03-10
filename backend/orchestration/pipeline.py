"""LangGraph pipeline definition for the 6-agent workflow."""
from typing import TypedDict, Annotated, Any, Dict, List, Optional
from langgraph.graph import StateGraph, END
import operator


class PipelineState(TypedDict):
    """State object passed through the pipeline."""
    # Input
    project_id: str
    brief: str
    cost_profile: str  # budget, balanced, premium
    
    # Agent outputs
    classification: Optional[Dict[str, Any]]
    research: Optional[Dict[str, Any]]
    architecture: Optional[Dict[str, Any]]
    design_system: Optional[Dict[str, Any]]
    generated_code: Optional[Dict[str, Any]]
    delivery: Optional[Dict[str, Any]]
    
    # Tracking
    current_step: int
    status: str  # pending, running, completed, failed
    errors: Annotated[List[str], operator.add]
    cost_breakdown: Dict[str, float]
    total_cost: float


def create_pipeline() -> StateGraph:
    """Create the LangGraph pipeline with all 6 agents."""
    
    workflow = StateGraph(PipelineState)
    
    # Define nodes (agent functions will be bound at runtime)
    workflow.add_node("intake", intake_node)
    workflow.add_node("research", research_node)
    workflow.add_node("architect", architect_node)
    workflow.add_node("design_system", design_system_node)
    workflow.add_node("code_generation", code_generation_node)
    workflow.add_node("delivery", delivery_node)
    
    # Define edges (linear flow for Phase 1)
    workflow.add_edge("intake", "research")
    workflow.add_edge("research", "architect")
    workflow.add_edge("architect", "design_system")
    workflow.add_edge("design_system", "code_generation")
    workflow.add_edge("code_generation", "delivery")
    workflow.add_edge("delivery", END)
    
    # Set entry point
    workflow.set_entry_point("intake")
    
    return workflow.compile()


async def intake_node(state: PipelineState) -> PipelineState:
    """Execute intake agent."""
    from agents import IntakeAgent
    
    agent = IntakeAgent(project_id=state["project_id"])
    result = await agent.execute({
        "brief": state["brief"],
        "cost_profile": state["cost_profile"],
    })
    
    state["classification"] = result.get("classification")
    state["current_step"] = 1
    state["cost_breakdown"]["intake"] = result.get("cost", 0)
    state["total_cost"] += result.get("cost", 0)
    
    return state


async def research_node(state: PipelineState) -> PipelineState:
    """Execute research agent."""
    from agents import ResearchAgent
    
    agent = ResearchAgent(project_id=state["project_id"])
    result = await agent.execute({
        "brief": state["brief"],
        "classification": state["classification"],
        "cost_profile": state["cost_profile"],
    })
    
    state["research"] = result.get("research")
    state["current_step"] = 2
    state["cost_breakdown"]["research"] = result.get("cost", 0)
    state["total_cost"] += result.get("cost", 0)
    
    return state


async def architect_node(state: PipelineState) -> PipelineState:
    """Execute architect agent."""
    from agents import ArchitectAgent
    
    agent = ArchitectAgent(project_id=state["project_id"])
    result = await agent.execute({
        "brief": state["brief"],
        "classification": state["classification"],
        "research": state["research"],
        "cost_profile": state["cost_profile"],
    })
    
    state["architecture"] = result.get("architecture")
    state["current_step"] = 3
    state["cost_breakdown"]["architect"] = result.get("cost", 0)
    state["total_cost"] += result.get("cost", 0)
    
    return state


async def design_system_node(state: PipelineState) -> PipelineState:
    """Execute design system agent."""
    from agents import DesignSystemAgent
    
    agent = DesignSystemAgent(project_id=state["project_id"])
    result = await agent.execute({
        "brief": state["brief"],
        "classification": state["classification"],
        "research": state["research"],
        "architecture": state["architecture"],
        "cost_profile": state["cost_profile"],
    })
    
    state["design_system"] = result.get("design_system")
    state["current_step"] = 4
    state["cost_breakdown"]["design_system"] = result.get("cost", 0)
    state["total_cost"] += result.get("cost", 0)
    
    return state


async def code_generation_node(state: PipelineState) -> PipelineState:
    """Execute code generation agent."""
    from agents import CodeGenerationAgent
    
    agent = CodeGenerationAgent(project_id=state["project_id"])
    result = await agent.execute({
        "brief": state["brief"],
        "architecture": state["architecture"],
        "design_system": state["design_system"],
    })
    
    state["generated_code"] = result
    state["current_step"] = 5
    state["cost_breakdown"]["code_generation"] = result.get("cost", 0)
    state["total_cost"] += result.get("cost", 0)
    
    return state


async def delivery_node(state: PipelineState) -> PipelineState:
    """Execute delivery agent."""
    from agents import DeliveryAgent
    
    agent = DeliveryAgent(project_id=state["project_id"])
    result = await agent.execute({
        "project_name": state["classification"].get("project_name", "generated-project"),
        "files": state["generated_code"].get("files", []),
        "classification": state["classification"],
        "architecture": state["architecture"],
        "cost_breakdown": state["cost_breakdown"],
    })
    
    state["delivery"] = result
    state["current_step"] = 6
    state["status"] = "completed"
    
    return state
