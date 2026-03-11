"""Prometheus metrics for AI Dev Agency (#19).

Exposes custom counters, histograms, and gauges for:
- Pipeline execution (start/complete/fail, duration)
- Per-agent execution (duration, cost, success/fail)
- LLM API calls (model, status, latency)
- Queue depth and processing time
- Circuit breaker state

All metrics are registered on the default Prometheus registry so they
are automatically scraped via the ``/metrics`` endpoint added by
``prometheus-fastapi-instrumentator`` in ``main.py``.
"""

import time
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Info,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.info("prometheus_client not installed — metrics disabled")

# ── Metric definitions (no-op stubs when prometheus_client missing) ──────

if PROMETHEUS_AVAILABLE:
    # -- Pipeline ----------------------------------------------------------
    PIPELINE_STARTS = Counter(
        "pipeline_starts_total",
        "Total pipeline executions started",
        ["cost_profile", "project_type"],
    )
    PIPELINE_COMPLETIONS = Counter(
        "pipeline_completions_total",
        "Total pipeline executions completed successfully",
        ["cost_profile", "project_type"],
    )
    PIPELINE_FAILURES = Counter(
        "pipeline_failures_total",
        "Total pipeline executions that failed",
        ["cost_profile", "project_type"],
    )
    PIPELINE_DURATION = Histogram(
        "pipeline_duration_seconds",
        "Pipeline execution duration in seconds",
        ["cost_profile", "project_type"],
        buckets=[30, 60, 120, 300, 600, 900, 1800, 3600],
    )

    # -- Agents ------------------------------------------------------------
    AGENT_RUNS = Counter(
        "agent_runs_total",
        "Total agent executions",
        ["agent_name", "status"],  # status: success | failure | skipped
    )
    AGENT_DURATION = Histogram(
        "agent_duration_seconds",
        "Agent execution duration in seconds",
        ["agent_name"],
        buckets=[1, 5, 10, 30, 60, 120, 300],
    )
    AGENT_COST = Histogram(
        "agent_cost_dollars",
        "Agent LLM cost in USD",
        ["agent_name", "model"],
        buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    )

    # -- LLM API -----------------------------------------------------------
    LLM_REQUESTS = Counter(
        "llm_requests_total",
        "Total LLM API requests",
        ["model", "status"],  # status: success | error
    )
    LLM_LATENCY = Histogram(
        "llm_latency_seconds",
        "LLM API call latency in seconds",
        ["model"],
        buckets=[0.5, 1, 2, 5, 10, 30, 60],
    )
    LLM_TOKENS = Counter(
        "llm_tokens_total",
        "Total LLM tokens consumed",
        ["model", "direction"],  # direction: input | output
    )

    # -- Queue -------------------------------------------------------------
    QUEUE_DEPTH = Gauge(
        "queue_depth",
        "Number of projects currently in the queue",
    )
    QUEUE_PROCESSING_TIME = Histogram(
        "queue_processing_seconds",
        "Time a project spent in queue before processing started",
        buckets=[1, 5, 15, 30, 60, 120, 300],
    )

    # -- Circuit breaker ---------------------------------------------------
    CIRCUIT_BREAKER_STATE = Gauge(
        "circuit_breaker_state",
        "Circuit breaker state per provider (0=closed, 1=open, 2=half_open)",
        ["provider"],
    )

    # -- Checkpoints / Autonomy -------------------------------------------
    CHECKPOINT_PAUSES = Counter(
        "checkpoint_pauses_total",
        "Total checkpoint pauses",
        ["autonomy_tier", "agent_name"],
    )
    CHECKPOINT_RESUMES = Counter(
        "checkpoint_resumes_total",
        "Total checkpoint resumes",
        ["autonomy_tier", "resume_type"],  # resume_type: approve | edit | reject
    )

    # -- App info -----------------------------------------------------------
    APP_INFO = Info("ai_dev_agency", "AI Dev Agency application info")
    APP_INFO.info({
        "version": "1.12.0",
        "phase": "12-metrics",
    })

# ── Helper functions ─────────────────────────────────────────────────────


def record_pipeline_start(cost_profile: str = "balanced", project_type: str = "unknown"):
    if PROMETHEUS_AVAILABLE:
        PIPELINE_STARTS.labels(cost_profile=cost_profile, project_type=project_type).inc()


def record_pipeline_complete(cost_profile: str, project_type: str, duration_seconds: float):
    if PROMETHEUS_AVAILABLE:
        PIPELINE_COMPLETIONS.labels(cost_profile=cost_profile, project_type=project_type).inc()
        PIPELINE_DURATION.labels(cost_profile=cost_profile, project_type=project_type).observe(duration_seconds)


def record_pipeline_failure(cost_profile: str, project_type: str, duration_seconds: float):
    if PROMETHEUS_AVAILABLE:
        PIPELINE_FAILURES.labels(cost_profile=cost_profile, project_type=project_type).inc()
        PIPELINE_DURATION.labels(cost_profile=cost_profile, project_type=project_type).observe(duration_seconds)


def record_agent_run(agent_name: str, status: str, duration_seconds: float,
                     cost: float = 0.0, model: str = "unknown"):
    if PROMETHEUS_AVAILABLE:
        AGENT_RUNS.labels(agent_name=agent_name, status=status).inc()
        AGENT_DURATION.labels(agent_name=agent_name).observe(duration_seconds)
        if cost > 0:
            AGENT_COST.labels(agent_name=agent_name, model=model).observe(cost)


def record_llm_request(model: str, status: str, latency_seconds: float,
                       input_tokens: int = 0, output_tokens: int = 0):
    if PROMETHEUS_AVAILABLE:
        LLM_REQUESTS.labels(model=model, status=status).inc()
        LLM_LATENCY.labels(model=model).observe(latency_seconds)
        if input_tokens:
            LLM_TOKENS.labels(model=model, direction="input").inc(input_tokens)
        if output_tokens:
            LLM_TOKENS.labels(model=model, direction="output").inc(output_tokens)


def set_queue_depth(depth: int):
    if PROMETHEUS_AVAILABLE:
        QUEUE_DEPTH.set(depth)


def record_queue_wait(seconds: float):
    if PROMETHEUS_AVAILABLE:
        QUEUE_PROCESSING_TIME.observe(seconds)


def set_circuit_breaker_state(provider: str, state: str):
    """State: closed=0, open=1, half_open=2."""
    if PROMETHEUS_AVAILABLE:
        state_map = {"closed": 0, "open": 1, "half_open": 2}
        CIRCUIT_BREAKER_STATE.labels(provider=provider).set(state_map.get(state, 0))


def record_checkpoint_pause(autonomy_tier: str, agent_name: str):
    if PROMETHEUS_AVAILABLE:
        CHECKPOINT_PAUSES.labels(autonomy_tier=autonomy_tier, agent_name=agent_name).inc()


def record_checkpoint_resume(autonomy_tier: str, resume_type: str):
    if PROMETHEUS_AVAILABLE:
        CHECKPOINT_RESUMES.labels(autonomy_tier=autonomy_tier, resume_type=resume_type).inc()


@contextmanager
def track_llm_call(model: str):
    """Context manager that times an LLM call and records metrics."""
    start = time.time()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = time.time() - start
        record_llm_request(model, status, elapsed)
