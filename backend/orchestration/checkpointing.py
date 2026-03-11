"""PostgreSQL-based pipeline checkpointing for crash recovery.

After each agent completes, a checkpoint is written to the database containing
the full DAG state (which nodes are completed/failed/skipped, their results,
the shared context, and cost tracking). On resume, the pipeline rebuilds from
the latest checkpoint and only re-runs pending agents.

This gives us:
  - Crash recovery without re-running finished agents
  - Human-in-the-loop pause/resume
  - Time-travel debugging (inspect state at any step)
  - Branch-from-checkpoint for A/B agent experiments
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def save_checkpoint(
    db: Session,
    project_id: str,
    agent_name: str,
    agent_status: str,
    node_states: Dict[str, Dict[str, Any]],
    pipeline_context: Dict[str, Any],
    pipeline_config: Dict[str, Any],
    total_cost: float,
    cost_breakdown: Dict[str, float],
    step_number: int,
) -> Optional[str]:
    """Save a pipeline checkpoint after an agent completes.

    Returns the checkpoint ID on success, None on failure.
    """
    try:
        from models.pipeline_checkpoint import PipelineCheckpoint

        # Sanitize context — remove non-serializable objects
        safe_context = _sanitize_for_json(pipeline_context)

        checkpoint = PipelineCheckpoint(
            id=uuid.uuid4(),
            project_id=project_id,
            agent_name=agent_name,
            agent_status=agent_status,
            node_states=node_states,
            pipeline_context=safe_context,
            pipeline_config=pipeline_config,
            total_cost=total_cost,
            cost_breakdown=cost_breakdown,
            step_number=step_number,
            created_at=datetime.utcnow(),
        )
        db.add(checkpoint)
        db.commit()

        logger.info(
            f"Checkpoint saved: project={project_id} step={step_number} "
            f"agent={agent_name} status={agent_status}"
        )
        return str(checkpoint.id)

    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return None


def get_latest_checkpoint(
    db: Session, project_id: str
) -> Optional[Dict[str, Any]]:
    """Get the most recent checkpoint for a project.

    Returns a dict with all checkpoint fields, or None if no checkpoint exists.
    """
    try:
        from models.pipeline_checkpoint import PipelineCheckpoint

        checkpoint = (
            db.query(PipelineCheckpoint)
            .filter(PipelineCheckpoint.project_id == project_id)
            .order_by(PipelineCheckpoint.step_number.desc())
            .first()
        )

        if not checkpoint:
            return None

        return {
            "id": str(checkpoint.id),
            "project_id": str(checkpoint.project_id),
            "agent_name": checkpoint.agent_name,
            "agent_status": checkpoint.agent_status,
            "node_states": checkpoint.node_states,
            "pipeline_context": checkpoint.pipeline_context,
            "pipeline_config": checkpoint.pipeline_config,
            "total_cost": checkpoint.total_cost,
            "cost_breakdown": checkpoint.cost_breakdown,
            "step_number": checkpoint.step_number,
            "created_at": checkpoint.created_at.isoformat() if checkpoint.created_at else None,
        }

    except Exception as e:
        logger.error(f"Failed to load checkpoint: {e}")
        return None


def get_checkpoint_history(
    db: Session, project_id: str
) -> List[Dict[str, Any]]:
    """Get all checkpoints for a project, ordered by step number."""
    try:
        from models.pipeline_checkpoint import PipelineCheckpoint

        checkpoints = (
            db.query(PipelineCheckpoint)
            .filter(PipelineCheckpoint.project_id == project_id)
            .order_by(PipelineCheckpoint.step_number.asc())
            .all()
        )

        return [
            {
                "id": str(cp.id),
                "agent_name": cp.agent_name,
                "agent_status": cp.agent_status,
                "step_number": cp.step_number,
                "total_cost": cp.total_cost,
                "created_at": cp.created_at.isoformat() if cp.created_at else None,
            }
            for cp in checkpoints
        ]

    except Exception as e:
        logger.error(f"Failed to get checkpoint history: {e}")
        return []


def delete_checkpoints(db: Session, project_id: str) -> int:
    """Delete all checkpoints for a project (e.g. after successful completion)."""
    try:
        from models.pipeline_checkpoint import PipelineCheckpoint

        count = (
            db.query(PipelineCheckpoint)
            .filter(PipelineCheckpoint.project_id == project_id)
            .delete()
        )
        db.commit()
        logger.info(f"Deleted {count} checkpoints for project {project_id}")
        return count

    except Exception as e:
        logger.error(f"Failed to delete checkpoints: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return 0


def _sanitize_for_json(data: Any, depth: int = 0) -> Any:
    """Recursively sanitize data for JSON serialization.

    Strips non-serializable objects and truncates very large strings.
    """
    if depth > 10:
        return "<truncated>"

    if data is None or isinstance(data, (bool, int, float)):
        return data

    if isinstance(data, str):
        # Truncate very long strings (e.g. full code outputs)
        if len(data) > 50_000:
            return data[:50_000] + "... <truncated>"
        return data

    if isinstance(data, dict):
        return {
            str(k): _sanitize_for_json(v, depth + 1)
            for k, v in data.items()
        }

    if isinstance(data, (list, tuple)):
        return [_sanitize_for_json(item, depth + 1) for item in data]

    # For anything else (UUID, datetime, custom objects) — stringify
    try:
        return str(data)
    except Exception:
        return "<non-serializable>"
