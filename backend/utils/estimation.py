"""Pre-execution cost and time estimation engine.

Estimates token usage, dollar cost, and wall-clock time for a full pipeline
run *before* the user starts it.  Users approve spend before it happens.

Token estimation uses a lightweight heuristic based on:
- Brief length (longer briefs → more prompt tokens per agent)
- Project type complexity multipliers
- Per-agent typical input/output token ratios
- Model pricing from the cost optimizer

No external dependencies (tiktoken optional for accuracy boost).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config.model_routing import get_model_for_agent, AGENT_COMPLEXITY
from utils.cost_optimizer import MODEL_PRICING, ModelCostInfo

logger = logging.getLogger(__name__)


# ── Token estimation profiles per agent ──────────────────────────────────

# Each agent has a typical (input_tokens, output_tokens) range.
# These are based on prompt structure analysis:
#   - input = system prompt + brief + upstream context
#   - output = agent's generated content
# Values are (base_input, base_output) — scaled by brief length multiplier.

_AGENT_TOKEN_PROFILES: Dict[str, Dict[str, int]] = {
    "intake":                   {"input": 1200,  "output": 800},
    "research":                 {"input": 2000,  "output": 3000},
    "architect":                {"input": 3000,  "output": 4000},
    "design_system":            {"input": 2500,  "output": 3500},
    "asset_generation":         {"input": 1000,  "output": 500},
    "content_generation":       {"input": 1500,  "output": 2500},
    "project_manager":          {"input": 2500,  "output": 1500},
    "code_generation":          {"input": 4000,  "output": 8000},
    "code_generation_openhands": {"input": 3000, "output": 6000},
    "integration_wiring":       {"input": 3500,  "output": 5000},
    "code_review":              {"input": 4000,  "output": 3000},
    "security":                 {"input": 2000,  "output": 2000},
    "seo":                      {"input": 1500,  "output": 1500},
    "accessibility":            {"input": 1500,  "output": 1500},
    "qa":                       {"input": 3000,  "output": 3000},
    "deploy":                   {"input": 1000,  "output": 800},
    "analytics":                {"input": 1000,  "output": 800},
    "coding_standards":         {"input": 1000,  "output": 800},
    "post_deploy_verification": {"input": 800,   "output": 500},
    "delivery":                 {"input": 800,   "output": 500},
}

# Project type complexity multipliers — more complex projects need more tokens
_PROJECT_TYPE_MULTIPLIERS: Dict[str, float] = {
    "web_simple":           1.0,
    "web_complex":          1.8,
    "mobile_native_ios":    1.6,
    "mobile_cross_platform": 1.7,
    "mobile_pwa":           1.3,
    "desktop_app":          1.5,
    "chrome_extension":     0.8,
    "cli_tool":             0.6,
    "python_api":           1.2,
    "python_saas":          2.0,
}

# Average wall-clock time per agent (seconds), including LLM latency
_AGENT_TIME_ESTIMATES: Dict[str, float] = {
    "intake":                   15,
    "research":                 45,
    "architect":                60,
    "design_system":            45,
    "asset_generation":         30,
    "content_generation":       30,
    "project_manager":          20,
    "code_generation":          120,
    "code_generation_openhands": 90,
    "integration_wiring":       60,
    "code_review":              45,
    "security":                 30,
    "seo":                      20,
    "accessibility":            20,
    "qa":                       60,
    "deploy":                   30,
    "analytics":                15,
    "coding_standards":         15,
    "post_deploy_verification": 10,
    "delivery":                 15,
}

# Agents that run in parallel (same group runs concurrently)
_PARALLEL_GROUPS: List[List[str]] = [
    ["asset_generation", "content_generation"],
    ["security", "seo", "accessibility"],
    ["analytics", "coding_standards"],
]


# ── Data classes ─────────────────────────────────────────────────────────

@dataclass
class AgentEstimate:
    """Cost and time estimate for a single agent."""
    agent_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    time_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost": round(self.cost, 4),
            "time_seconds": round(self.time_seconds, 1),
        }


@dataclass
class PipelineEstimate:
    """Full pipeline cost and time estimate."""
    total_cost: float
    min_cost: float
    max_cost: float
    total_time_seconds: float
    total_input_tokens: int
    total_output_tokens: int
    agents: List[AgentEstimate]
    cost_profile: str
    project_type: str
    brief_tokens: int
    confidence: float  # 0-1, how confident we are in this estimate

    def to_dict(self) -> Dict[str, Any]:
        minutes = math.ceil(self.total_time_seconds / 60)
        return {
            "total_cost": round(self.total_cost, 2),
            "min_cost": round(self.min_cost, 2),
            "max_cost": round(self.max_cost, 2),
            "total_time_seconds": round(self.total_time_seconds),
            "total_time_display": f"{minutes} min" if minutes < 60 else f"{minutes // 60}h {minutes % 60}m",
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "confidence": round(self.confidence, 2),
            "cost_profile": self.cost_profile,
            "project_type": self.project_type,
            "brief_tokens": self.brief_tokens,
            "agents": [a.to_dict() for a in self.agents],
        }


# ── Token counting ───────────────────────────────────────────────────────

def _estimate_brief_tokens(brief: str) -> int:
    """Estimate token count for a brief string.

    Uses tiktoken if available, otherwise a word-based heuristic.
    English text averages ~1.3 tokens per word / ~4 chars per token.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(brief))
    except Exception:
        # Heuristic: ~4 characters per token for English
        return max(1, len(brief) // 4)


def _get_model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for a model call using MODEL_PRICING."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        # Fallback: assume mid-range pricing
        return (input_tokens * 0.003 + output_tokens * 0.015) / 1000

    input_cost = (input_tokens / 1000) * pricing.input_cost_per_1k
    output_cost = (output_tokens / 1000) * pricing.output_cost_per_1k
    return input_cost + output_cost


# ── Main estimation function ─────────────────────────────────────────────

def estimate_pipeline_cost(
    brief: str,
    project_type: str = "web_simple",
    cost_profile: str = "balanced",
    num_features: int = 0,
    num_pages: int = 0,
    complexity_score: Optional[int] = None,
) -> PipelineEstimate:
    """Estimate total cost and time for a full pipeline run.

    This is called *before* the pipeline starts so the user can
    approve the estimated spend.

    Args:
        brief: The project description text
        project_type: e.g. "web_simple", "web_complex", "python_saas"
        cost_profile: "budget", "balanced", or "premium"
        num_features: Number of requested features (increases code gen tokens)
        num_pages: Number of requested pages (increases code gen tokens)
        complexity_score: 1-10 override; auto-detected from brief if None

    Returns:
        PipelineEstimate with per-agent breakdown
    """
    brief_tokens = _estimate_brief_tokens(brief)

    # Auto-detect complexity from brief length + features
    if complexity_score is None:
        # Heuristic: longer briefs with more features = more complex
        length_factor = min(10, max(1, brief_tokens // 100))
        feature_factor = min(5, num_features)
        complexity_score = min(10, max(1, (length_factor + feature_factor) // 2 + 3))

    # Project type multiplier
    type_multiplier = _PROJECT_TYPE_MULTIPLIERS.get(project_type, 1.0)

    # Complexity multiplier (1-10 → 0.7x-1.5x)
    complexity_multiplier = 0.7 + (complexity_score / 10) * 0.8

    # Brief contribution: longer briefs add more input tokens to each agent
    brief_multiplier = 1.0 + (brief_tokens / 500) * 0.3  # +30% per 500 tokens of brief

    # Feature/page contribution to code generation
    code_gen_extra = (num_features * 500) + (num_pages * 800)

    agent_estimates: List[AgentEstimate] = []
    total_cost = 0.0

    for agent_id, profile in _AGENT_TOKEN_PROFILES.items():
        model = get_model_for_agent(agent_id, cost_profile=cost_profile)

        # Scale tokens by multipliers
        input_tokens = int(
            profile["input"]
            * type_multiplier
            * complexity_multiplier
            * brief_multiplier
        )
        output_tokens = int(
            profile["output"]
            * type_multiplier
            * complexity_multiplier
        )

        # Extra tokens for code generation agents based on features/pages
        if agent_id in ("code_generation", "code_generation_openhands", "integration_wiring"):
            output_tokens += code_gen_extra

        cost = _get_model_cost(model, input_tokens, output_tokens)
        time_seconds = _AGENT_TIME_ESTIMATES.get(agent_id, 30) * complexity_multiplier

        agent_estimates.append(AgentEstimate(
            agent_id=agent_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            time_seconds=time_seconds,
        ))
        total_cost += cost

    # Calculate wall-clock time accounting for parallelism
    total_time = _calculate_parallel_time(agent_estimates)

    # Confidence: higher with more specific inputs
    confidence = 0.6
    if brief_tokens > 50:
        confidence += 0.1
    if num_features > 0 or num_pages > 0:
        confidence += 0.1
    if complexity_score is not None:
        confidence += 0.05
    confidence = min(0.95, confidence)

    # Min/max range: ±30% of expected
    min_cost = total_cost * 0.7
    max_cost = total_cost * 1.3

    estimate = PipelineEstimate(
        total_cost=total_cost,
        min_cost=min_cost,
        max_cost=max_cost,
        total_time_seconds=total_time,
        total_input_tokens=sum(a.input_tokens for a in agent_estimates),
        total_output_tokens=sum(a.output_tokens for a in agent_estimates),
        agents=agent_estimates,
        cost_profile=cost_profile,
        project_type=project_type,
        brief_tokens=brief_tokens,
        confidence=confidence,
    )

    logger.info(
        f"Pipeline estimate: ${estimate.total_cost:.2f} "
        f"({estimate.total_input_tokens + estimate.total_output_tokens} tokens, "
        f"{math.ceil(estimate.total_time_seconds / 60)} min, "
        f"confidence={estimate.confidence:.0%})"
    )

    return estimate


def _calculate_parallel_time(agents: List[AgentEstimate]) -> float:
    """Calculate wall-clock time accounting for parallel agent groups.

    Sequential agents add their time linearly.
    Parallel groups only count the slowest agent in the group.
    """
    # Build a set of agents in parallel groups
    parallel_agents: Dict[str, int] = {}  # agent_id → group_index
    for i, group in enumerate(_PARALLEL_GROUPS):
        for agent_id in group:
            parallel_agents[agent_id] = i

    # Track time per parallel group (max of group members)
    group_times: Dict[int, float] = {}
    sequential_time = 0.0

    for agent in agents:
        if agent.agent_id in parallel_agents:
            group_idx = parallel_agents[agent.agent_id]
            group_times[group_idx] = max(
                group_times.get(group_idx, 0),
                agent.time_seconds,
            )
        else:
            sequential_time += agent.time_seconds

    return sequential_time + sum(group_times.values())
