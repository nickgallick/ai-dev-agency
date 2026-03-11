"""Structured audit logging for pipeline decisions.

Every significant pipeline event is recorded to both:
  1. The audit_logs PostgreSQL table (queryable, persistent)
  2. Python structured logging (for real-time log aggregation)

This makes every pipeline decision queryable — no more grepping log files.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("pipeline.audit")


def audit_log(
    db: Optional[Session],
    event_type: str,
    message: str,
    project_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
) -> None:
    """Record a structured audit event.

    Always emits a structured log line. If a DB session is available,
    also persists to the audit_logs table.
    """
    details = details or {}

    # Structured log line (always emitted, even without DB)
    log_data = {
        "event": event_type,
        "project_id": project_id,
        "agent": agent_name,
        "msg": message,
        **{k: v for k, v in details.items() if k not in ("event", "project_id", "agent", "msg")},
    }
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms

    logger.info(json.dumps(log_data, default=str))

    # Persist to DB if available
    if db:
        try:
            from models.audit_log import AuditLog

            entry = AuditLog(
                id=uuid.uuid4(),
                event_type=event_type,
                project_id=project_id,
                agent_name=agent_name,
                message=message,
                details=details,
                timestamp=datetime.utcnow(),
                duration_ms=str(duration_ms) if duration_ms is not None else None,
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist audit log: {e}")
            try:
                db.rollback()
            except Exception:
                pass


# ── Convenience helpers for common events ────────────────────────────────


def audit_pipeline_start(
    db: Optional[Session], project_id: str, cost_profile: str, project_type: str = "unknown"
) -> None:
    audit_log(
        db, "pipeline_start",
        f"Pipeline started for project {project_id}",
        project_id=project_id,
        details={
            "cost_profile": cost_profile,
            "project_type": project_type,
        },
    )


def audit_pipeline_complete(
    db: Optional[Session], project_id: str, total_cost: float, duration_ms: int
) -> None:
    audit_log(
        db, "pipeline_complete",
        f"Pipeline completed for project {project_id} (${total_cost:.4f})",
        project_id=project_id,
        details={"total_cost": total_cost},
        duration_ms=duration_ms,
    )


def audit_pipeline_failed(
    db: Optional[Session], project_id: str, error: str, duration_ms: int
) -> None:
    audit_log(
        db, "pipeline_failed",
        f"Pipeline failed: {error[:200]}",
        project_id=project_id,
        details={"error": error},
        duration_ms=duration_ms,
    )


def audit_agent_start(
    db: Optional[Session], project_id: str, agent_name: str, step: int
) -> None:
    audit_log(
        db, "agent_start",
        f"Agent {agent_name} started (step {step})",
        project_id=project_id,
        agent_name=agent_name,
        details={"step": step},
    )


def audit_agent_complete(
    db: Optional[Session], project_id: str, agent_name: str,
    duration_ms: int, cost: float = 0.0
) -> None:
    audit_log(
        db, "agent_complete",
        f"Agent {agent_name} completed in {duration_ms}ms",
        project_id=project_id,
        agent_name=agent_name,
        details={"cost": cost},
        duration_ms=duration_ms,
    )


def audit_agent_failed(
    db: Optional[Session], project_id: str, agent_name: str,
    error: str, duration_ms: int
) -> None:
    audit_log(
        db, "agent_failed",
        f"Agent {agent_name} failed: {error[:200]}",
        project_id=project_id,
        agent_name=agent_name,
        details={"error": error},
        duration_ms=duration_ms,
    )


def audit_agent_skipped(
    db: Optional[Session], project_id: str, agent_name: str, reason: str
) -> None:
    audit_log(
        db, "agent_skip",
        f"Agent {agent_name} skipped: {reason}",
        project_id=project_id,
        agent_name=agent_name,
        details={"reason": reason},
    )


def audit_agent_retry(
    db: Optional[Session], project_id: str,
    retry_count: int, max_retries: int, reset_nodes: list
) -> None:
    audit_log(
        db, "agent_retry",
        f"QA retry {retry_count}/{max_retries} — resetting {len(reset_nodes)} nodes",
        project_id=project_id,
        agent_name="qa",
        details={
            "retry_count": retry_count,
            "max_retries": max_retries,
            "reset_nodes": reset_nodes,
        },
    )


def audit_checkpoint_save(
    db: Optional[Session], project_id: str, agent_name: str,
    step: int, checkpoint_id: str
) -> None:
    audit_log(
        db, "checkpoint_save",
        f"Checkpoint saved after {agent_name} (step {step})",
        project_id=project_id,
        agent_name=agent_name,
        details={"step": step, "checkpoint_id": checkpoint_id},
    )


def audit_checkpoint_resume(
    db: Optional[Session], project_id: str, from_step: int,
    from_agent: str, skipped_agents: list
) -> None:
    audit_log(
        db, "checkpoint_resume",
        f"Resuming from step {from_step} ({from_agent}), skipping {len(skipped_agents)} agents",
        project_id=project_id,
        details={
            "resumed_from_step": from_step,
            "resumed_from_agent": from_agent,
            "skipped_agents": skipped_agents,
        },
    )


def audit_dependency_skip(
    db: Optional[Session], project_id: str, agent_name: str, failed_dep: str
) -> None:
    audit_log(
        db, "dependency_skip",
        f"Agent {agent_name} skipped due to failed dependency {failed_dep}",
        project_id=project_id,
        agent_name=agent_name,
        details={"failed_dependency": failed_dep},
    )


def audit_cost_alert(
    db: Optional[Session], project_id: str,
    current_cost: float, threshold: float
) -> None:
    pct = (current_cost / threshold * 100) if threshold > 0 else 0
    audit_log(
        db, "cost_alert",
        f"Cost alert: ${current_cost:.2f} ({pct:.0f}% of ${threshold:.2f})",
        project_id=project_id,
        details={
            "current_cost": current_cost,
            "threshold": threshold,
            "percentage": round(pct, 1),
        },
    )


def audit_queue_event(
    db: Optional[Session], project_id: str, action: str, position: int = 0
) -> None:
    audit_log(
        db, f"queue_{action}",
        f"Project {action} (position {position})",
        project_id=project_id,
        details={"position": position},
    )
