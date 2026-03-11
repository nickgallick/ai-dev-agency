"""Iterative refinement loops with quality scoring.

Agents re-run with feedback until output meets a quality threshold.
LangGraph natively supports cycles — this module provides the scoring
and feedback loop that drives them.

Quality scoring is based on:
1. **Completeness** — Did the agent produce all expected output fields?
2. **Content quality** — Is the output non-trivial (not just placeholders)?
3. **Error-free** — Did the agent complete without errors?
4. **Agent-specific checks** — Custom validators per agent type

Usage in pipeline::

    from orchestration.refinement import (
        score_agent_output,
        should_refine,
        build_refinement_feedback,
        RefinementConfig,
    )

    result = await agent.run(context)
    score = score_agent_output(node_id, result)

    if should_refine(score, config):
        context["refinement_feedback"] = build_refinement_feedback(node_id, result, score)
        result = await agent.run(context)  # Re-run with feedback
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────────────────

@dataclass
class RefinementConfig:
    """Configuration for the iterative refinement loop."""

    # Quality threshold (0.0-1.0). Outputs scoring below this trigger a re-run.
    quality_threshold: float = 0.7

    # Maximum refinement iterations per agent (prevents infinite loops)
    max_iterations: int = 2

    # Agents that should NEVER be refined (fast/simple agents)
    skip_agents: Set[str] = field(default_factory=lambda: {
        "intake",               # Classification only — always passes
        "asset_generation",     # External API call — refinement won't help
        "deploy",               # Deployment is pass/fail
        "delivery",             # Packaging is mechanical
        "post_deploy_verification",  # Verification is pass/fail
        "analytics",            # Setup is mechanical
        "coding_standards",     # Lint config is pass/fail
    })

    # Agents that benefit most from refinement (complex output)
    priority_agents: Set[str] = field(default_factory=lambda: {
        "architect",
        "code_generation",
        "code_generation_openhands",
        "integration_wiring",
        "code_review",
        "design_system",
    })


# Default global config
DEFAULT_REFINEMENT_CONFIG = RefinementConfig()


# ── Quality scoring ──────────────────────────────────────────────────────

@dataclass
class QualityScore:
    """Detailed quality assessment of an agent's output."""
    overall: float                           # 0.0-1.0 composite score
    completeness: float = 1.0               # Did it produce expected fields?
    content_quality: float = 1.0            # Is content non-trivial?
    error_free: float = 1.0                 # No errors in result?
    details: Dict[str, Any] = field(default_factory=dict)  # Agent-specific
    issues: List[str] = field(default_factory=list)         # What went wrong

    @property
    def passed(self) -> bool:
        return self.overall >= DEFAULT_REFINEMENT_CONFIG.quality_threshold


# Expected output fields per agent type.  If an agent's result.data is
# missing these keys, completeness score drops.
_EXPECTED_FIELDS: Dict[str, List[str]] = {
    "intake": ["classification", "project_type"],
    "research": ["findings", "recommendations"],
    "architect": ["architecture", "tech_stack"],
    "design_system": ["design_tokens", "components"],
    "content_generation": ["content"],
    "project_manager": ["status", "assessment"],
    "code_generation": ["code", "files"],
    "code_generation_openhands": ["code", "files"],
    "integration_wiring": ["integrations", "wiring"],
    "code_review": ["issues", "summary"],
    "security": ["vulnerabilities", "recommendations"],
    "seo": ["recommendations"],
    "accessibility": ["issues", "recommendations"],
    "qa": ["test_results", "quality_score"],
}

# Minimum content length thresholds (characters) for non-trivial output
_MIN_CONTENT_LENGTH: Dict[str, int] = {
    "architect": 200,
    "design_system": 150,
    "code_generation": 100,
    "code_generation_openhands": 100,
    "integration_wiring": 100,
    "code_review": 100,
    "research": 150,
}


def score_agent_output(
    agent_id: str,
    result: Any,  # AgentResult
) -> QualityScore:
    """Score an agent's output on completeness, quality, and correctness.

    Returns a QualityScore with overall score between 0.0 and 1.0.
    """
    issues: List[str] = []

    # ── Error-free check ─────────────────────────────────────────────
    error_free = 1.0
    if not result.success:
        error_free = 0.0
        issues.append("Agent reported failure")
    elif result.errors:
        error_free = 0.3
        issues.append(f"Agent had {len(result.errors)} error(s)")

    # ── Completeness check ───────────────────────────────────────────
    completeness = 1.0
    expected = _EXPECTED_FIELDS.get(agent_id, [])
    data = getattr(result, "data", {}) or {}

    if expected:
        present = sum(1 for f in expected if f in data and data[f])
        completeness = present / len(expected) if expected else 1.0
        missing = [f for f in expected if f not in data or not data[f]]
        if missing:
            issues.append(f"Missing output fields: {', '.join(missing)}")

    # ── Content quality check ────────────────────────────────────────
    content_quality = 1.0
    min_length = _MIN_CONTENT_LENGTH.get(agent_id, 0)

    if min_length > 0:
        # Check total content length across all data values
        total_content = _extract_content_length(data)
        if total_content < min_length:
            content_quality = max(0.2, total_content / min_length)
            issues.append(
                f"Content too short ({total_content} chars, need {min_length})"
            )

    # Check for placeholder/error content
    placeholder_score = _check_for_placeholders(data)
    if placeholder_score < 1.0:
        content_quality = min(content_quality, placeholder_score)
        issues.append("Output contains placeholder or error content")

    # ── Composite score ──────────────────────────────────────────────
    # Weighted: error-free matters most, then completeness, then quality
    overall = (
        error_free * 0.4
        + completeness * 0.35
        + content_quality * 0.25
    )

    score = QualityScore(
        overall=round(overall, 3),
        completeness=round(completeness, 3),
        content_quality=round(content_quality, 3),
        error_free=round(error_free, 3),
        issues=issues,
        details={
            "agent_id": agent_id,
            "expected_fields": expected,
            "data_keys": list(data.keys()) if data else [],
        },
    )

    logger.info(
        f"Quality score for {agent_id}: {score.overall:.2f} "
        f"(completeness={score.completeness:.2f}, "
        f"quality={score.content_quality:.2f}, "
        f"error_free={score.error_free:.2f})"
    )

    return score


def _extract_content_length(data: Dict[str, Any]) -> int:
    """Recursively measure total string content length in data dict."""
    total = 0
    for v in data.values():
        if isinstance(v, str):
            total += len(v)
        elif isinstance(v, dict):
            total += _extract_content_length(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    total += len(item)
                elif isinstance(item, dict):
                    total += _extract_content_length(item)
    return total


def _check_for_placeholders(data: Dict[str, Any]) -> float:
    """Check if output contains placeholder/mock/error content. Returns 0-1."""
    placeholder_patterns = [
        "todo", "placeholder", "lorem ipsum", "mock response",
        "error:", "failed to", "not implemented",
    ]

    content_str = str(data).lower()
    hits = sum(1 for p in placeholder_patterns if p in content_str)

    if hits == 0:
        return 1.0
    elif hits <= 2:
        return 0.6
    else:
        return 0.3


# ── Refinement decisions ─────────────────────────────────────────────────

def should_refine(
    agent_id: str,
    score: QualityScore,
    iteration: int,
    config: Optional[RefinementConfig] = None,
) -> bool:
    """Decide whether an agent should be re-run with feedback.

    Returns True if:
    1. The agent is not in the skip list
    2. The quality score is below threshold
    3. We haven't exceeded max iterations
    """
    config = config or DEFAULT_REFINEMENT_CONFIG

    if agent_id in config.skip_agents:
        return False

    if iteration >= config.max_iterations:
        logger.info(
            f"Refinement: {agent_id} hit max iterations ({config.max_iterations}), "
            f"accepting score {score.overall:.2f}"
        )
        return False

    if score.overall >= config.quality_threshold:
        return False

    logger.info(
        f"Refinement: {agent_id} scored {score.overall:.2f} < {config.quality_threshold}, "
        f"triggering re-run (iteration {iteration + 1}/{config.max_iterations})"
    )
    return True


def build_refinement_feedback(
    agent_id: str,
    result: Any,  # AgentResult
    score: QualityScore,
) -> str:
    """Build a feedback prompt for the agent's next iteration.

    This is injected into the context so the agent knows what to fix.
    """
    feedback_parts = [
        f"Your previous output scored {score.overall:.0%} quality and needs improvement.",
        "",
        "Issues found:",
    ]

    for issue in score.issues:
        feedback_parts.append(f"  - {issue}")

    feedback_parts.append("")

    if score.completeness < 0.8:
        missing = score.details.get("expected_fields", [])
        feedback_parts.append(
            f"Please ensure you include all required output fields: {', '.join(missing)}"
        )

    if score.content_quality < 0.8:
        feedback_parts.append(
            "Please provide more detailed, substantive content. "
            "Avoid placeholders, TODOs, or minimal outputs."
        )

    if score.error_free < 1.0:
        feedback_parts.append(
            "Please fix the errors from your previous attempt. "
            "The output must complete without errors."
        )

    feedback_parts.append("")
    feedback_parts.append(
        "Re-run your analysis and provide an improved, complete output."
    )

    return "\n".join(feedback_parts)
