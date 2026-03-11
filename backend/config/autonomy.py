"""Tiered Autonomy Configuration (#26).

Defines three autonomy tiers that control how much human oversight
each project gets.  Built on top of the existing HITL checkpoint
system from Phase 11C.

Tiers
-----
- **supervised**  – Pauses after every agent for user approval.
- **guided**      – Pauses only at critical decision points
                    (research, architect, code_generation, qa, deployment).
- **autonomous**  – Runs the entire pipeline without pausing (default).

Each tier maps to checkpoint_mode + a set of checkpoint agents so
the existing CheckpointManager works unchanged.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ── Tier definitions ────────────────────────────────────────────────────

ALL_PIPELINE_AGENTS: List[str] = [
    "intake",
    "research",
    "architect",
    "design_system",
    "asset_generation",
    "content_generation",
    "pm_checkpoint_1",
    "code_generation",
    "integration_wiring",
    "pm_checkpoint_2",
    "code_review",
    "security",
    "seo",
    "accessibility",
    "qa",
    "deployment",
    "post_deploy_verification",
    "analytics_monitoring",
    "coding_standards",
    "delivery",
]

GUIDED_CHECKPOINTS: List[str] = [
    "research",
    "architect",
    "code_generation",
    "qa",
    "deployment",
]


@dataclass
class AutonomyTier:
    """Definition of a single autonomy tier."""

    id: str
    label: str
    description: str
    checkpoint_mode: str  # maps to CheckpointMode: auto | supervised | manual
    checkpoint_agents: List[str] = field(default_factory=list)
    auto_continue_timeout: int = 300  # seconds; 0 = wait forever
    allow_output_editing: bool = True
    notify_on_pause: bool = True


AUTONOMY_TIERS: Dict[str, AutonomyTier] = {
    "supervised": AutonomyTier(
        id="supervised",
        label="Supervised",
        description="Pause after every agent for your review and approval.",
        checkpoint_mode="manual",  # manual with all agents as checkpoints
        checkpoint_agents=ALL_PIPELINE_AGENTS,
        auto_continue_timeout=0,  # wait forever
        allow_output_editing=True,
        notify_on_pause=True,
    ),
    "guided": AutonomyTier(
        id="guided",
        label="Guided",
        description="Pause only at critical decision points for review.",
        checkpoint_mode="manual",  # manual with only key agents
        checkpoint_agents=GUIDED_CHECKPOINTS,
        auto_continue_timeout=300,  # 5 min auto-continue
        allow_output_editing=True,
        notify_on_pause=True,
    ),
    "autonomous": AutonomyTier(
        id="autonomous",
        label="Autonomous",
        description="Run the entire pipeline without pausing.",
        checkpoint_mode="auto",
        checkpoint_agents=[],
        auto_continue_timeout=0,
        allow_output_editing=False,
        notify_on_pause=False,
    ),
}

# Map legacy buildMode values from frontend to autonomy tiers
BUILD_MODE_TO_TIER: Dict[str, str] = {
    "full_auto": "autonomous",
    "step_approval": "supervised",
    "preview_only": "guided",  # closest match — guided gives key checkpoint review
    # Direct tier names also accepted
    "supervised": "supervised",
    "guided": "guided",
    "autonomous": "autonomous",
}


def get_tier(tier_id: str) -> AutonomyTier:
    """Return an AutonomyTier by id, falling back to autonomous."""
    return AUTONOMY_TIERS.get(tier_id, AUTONOMY_TIERS["autonomous"])


def resolve_tier(build_mode: Optional[str]) -> AutonomyTier:
    """Resolve a build_mode or tier name to an AutonomyTier.

    Accepts both legacy buildMode values (full_auto, step_approval,
    preview_only) and direct tier names (supervised, guided, autonomous).
    """
    if not build_mode:
        return AUTONOMY_TIERS["autonomous"]
    tier_id = BUILD_MODE_TO_TIER.get(build_mode, "autonomous")
    return get_tier(tier_id)


def get_tiers_summary() -> List[Dict]:
    """Return a summary list of all tiers for the API / frontend."""
    return [
        {
            "id": t.id,
            "label": t.label,
            "description": t.description,
            "checkpoint_agents": t.checkpoint_agents,
            "auto_continue_timeout": t.auto_continue_timeout,
            "allow_output_editing": t.allow_output_editing,
        }
        for t in AUTONOMY_TIERS.values()
    ]
