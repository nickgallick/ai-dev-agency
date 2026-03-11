"""Centralized model routing configuration for per-agent optimization.

Instead of each agent hardcoding its own model, this module provides a
single registry that maps (agent_id, cost_profile) → model.  This enables:

- **40-50% cost reduction** by routing simple agents to cheap models
- **Central control** — change routing without touching agent code
- **Per-agent optimization** — complex agents get powerful models,
  simple agents get fast/cheap ones
- **Easy A/B testing** — swap models per agent without code changes

Usage::

    from config.model_routing import get_model_for_agent

    model = get_model_for_agent("intake", cost_profile="balanced")
    result = await self.call_llm(prompt, model=model)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ── Model tiers ──────────────────────────────────────────────────────────

# Ordered cheapest → most expensive
MODELS = {
    "deepseek_chat": "deepseek/deepseek-chat",           # $0.14/$0.28 per 1M tokens
    "deepseek_coder": "deepseek/deepseek-coder",         # $0.10/$0.20 per 1M tokens
    "haiku": "anthropic/claude-3-haiku",                  # $0.25/$1.25 per 1M tokens
    "gpt35": "openai/gpt-3.5-turbo",                     # $0.50/$1.50 per 1M tokens
    "sonnet": "anthropic/claude-sonnet-4",                # $3.00/$15.00 per 1M tokens
    "gpt4o": "openai/gpt-4o",                            # $5.00/$15.00 per 1M tokens
    "opus": "anthropic/claude-opus-4",                    # $15.00/$75.00 per 1M tokens
}

# ── Agent complexity classification ──────────────────────────────────────

# Each agent is classified by the complexity of reasoning required:
#   - "low"    → classification, extraction, simple formatting
#   - "medium" → analysis, synthesis, moderate reasoning
#   - "high"   → architecture, code generation, complex reasoning

AGENT_COMPLEXITY: Dict[str, str] = {
    "intake":               "low",      # Classify project type, extract requirements
    "research":             "medium",   # Synthesize research findings
    "architect":            "high",     # System design, tech stack decisions
    "design_system":        "medium",   # Design tokens, component specs
    "asset_generation":     "low",      # Prompt generation for image APIs
    "content_generation":   "low",      # Copy, placeholder text
    "project_manager":      "medium",   # Checkpoint review, coherence checks
    "code_generation":      "high",     # Write actual code
    "code_generation_openhands": "high",
    "integration_wiring":   "high",     # Wire components together
    "code_review":          "high",     # Find bugs, assess quality
    "security":             "medium",   # Security scanning prompts
    "seo":                  "low",      # SEO meta tags, performance hints
    "accessibility":        "low",      # a11y checks
    "qa":                   "medium",   # Test generation, quality scoring
    "deploy":               "low",      # Deployment config generation
    "analytics":            "low",      # Monitoring setup
    "coding_standards":     "low",      # Lint rules, formatting
    "post_deploy_verification": "low",  # Verify deployment status
    "delivery":             "low",      # Package and deliver artifacts
}


# ── Routing table ────────────────────────────────────────────────────────

# (complexity, cost_profile) → model alias
# This is the core optimization: cheap agents use cheap models.

_ROUTING_TABLE: Dict[tuple, str] = {
    # Budget profile — maximize cost savings
    ("low",    "budget"):    "deepseek_chat",
    ("medium", "budget"):    "deepseek_chat",
    ("high",   "budget"):    "sonnet",

    # Balanced profile — good quality at reasonable cost
    ("low",    "balanced"):  "deepseek_chat",
    ("medium", "balanced"):  "sonnet",
    ("high",   "balanced"):  "sonnet",

    # Premium profile — best quality regardless of cost
    ("low",    "premium"):   "sonnet",
    ("medium", "premium"):   "sonnet",
    ("high",   "premium"):   "opus",
}

# Per-agent overrides (when an agent needs a specific model regardless of
# cost profile).  These take precedence over the routing table.
_AGENT_OVERRIDES: Dict[str, Dict[str, str]] = {
    # Architect always needs strong reasoning
    "architect": {
        "budget":    "sonnet",
        "balanced":  "sonnet",
        "premium":   "opus",
    },
    # Code generation needs strong coding ability
    "code_generation": {
        "budget":    "sonnet",
        "balanced":  "sonnet",
        "premium":   "opus",
    },
    "code_generation_openhands": {
        "budget":    "sonnet",
        "balanced":  "sonnet",
        "premium":   "opus",
    },
    # Code review should match code generation quality
    "code_review": {
        "budget":    "sonnet",
        "balanced":  "sonnet",
        "premium":   "opus",
    },
}


# ── Public API ───────────────────────────────────────────────────────────

def get_model_for_agent(
    agent_id: str,
    cost_profile: str = "balanced",
    fallback: str = "anthropic/claude-sonnet-4",
) -> str:
    """Get the optimal model for an agent given the cost profile.

    Lookup order:
    1. Per-agent override (if exists)
    2. Routing table (complexity × cost_profile)
    3. Fallback model

    Args:
        agent_id: Pipeline node ID (e.g., "intake", "code_generation")
        cost_profile: One of "budget", "balanced", "premium"
        fallback: Default model if no routing rule matches

    Returns:
        OpenRouter model string (e.g., "anthropic/claude-sonnet-4")
    """
    # 1. Check per-agent overrides
    if agent_id in _AGENT_OVERRIDES:
        alias = _AGENT_OVERRIDES[agent_id].get(cost_profile)
        if alias and alias in MODELS:
            model = MODELS[alias]
            logger.debug(f"Model routing: {agent_id} → {model} (override, {cost_profile})")
            return model

    # 2. Check routing table by complexity
    complexity = AGENT_COMPLEXITY.get(agent_id, "medium")
    alias = _ROUTING_TABLE.get((complexity, cost_profile))
    if alias and alias in MODELS:
        model = MODELS[alias]
        logger.debug(f"Model routing: {agent_id} → {model} ({complexity}, {cost_profile})")
        return model

    # 3. Fallback
    logger.debug(f"Model routing: {agent_id} → {fallback} (fallback)")
    return fallback


def get_routing_summary() -> Dict[str, Dict[str, str]]:
    """Return the full routing table for all agents across all profiles.

    Useful for the settings UI and debugging.

    Returns:
        Dict mapping agent_id → {cost_profile → model_string}
    """
    profiles = ["budget", "balanced", "premium"]
    summary = {}
    for agent_id in AGENT_COMPLEXITY:
        summary[agent_id] = {
            profile: get_model_for_agent(agent_id, profile)
            for profile in profiles
        }
    return summary


@dataclass
class ModelRoutingStats:
    """Tracks model usage across agents for cost analysis."""
    calls_by_model: Dict[str, int]
    cost_by_model: Dict[str, float]
    calls_by_agent: Dict[str, int]

    @classmethod
    def empty(cls) -> "ModelRoutingStats":
        return cls(
            calls_by_model={},
            cost_by_model={},
            calls_by_agent={},
        )

    def record(self, agent_id: str, model: str, cost: float) -> None:
        self.calls_by_model[model] = self.calls_by_model.get(model, 0) + 1
        self.cost_by_model[model] = self.cost_by_model.get(model, 0.0) + cost
        self.calls_by_agent[agent_id] = self.calls_by_agent.get(agent_id, 0) + 1
