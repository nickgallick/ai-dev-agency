"""Multi-layer retry with circuit breakers for LLM API fault tolerance.

Three layers of protection:

1. **LLM call retries** — Exponential backoff with jitter for transient HTTP
   errors (429 rate-limit, 502/503/504 server errors, connection timeouts).
   Applied to every ``call_llm()`` invocation via the ``llm_retry`` decorator.

2. **Agent-level retries** — If an entire agent fails (timeout, crash),
   ``retry_agent_execution`` wraps the call and retries up to N times with
   exponential backoff.  Only retries on transient errors, not logic failures.

3. **Circuit breaker** — Tracks failure rate per provider endpoint.  When the
   failure threshold is exceeded the circuit *opens* and calls fail-fast for a
   cooldown period, preventing cascading failures and wasted spend.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, Set, Type, Tuple

logger = logging.getLogger(__name__)

# ── Retryable error detection ────────────────────────────────────────────

# HTTP status codes that are safe to retry (transient / rate-limit)
RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}

# Exception types that indicate a transient network issue
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError,  # covers socket errors
)

# Try to include httpx exceptions if available
try:
    import httpx
    RETRYABLE_EXCEPTIONS = RETRYABLE_EXCEPTIONS + (
        httpx.ConnectError,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
        httpx.ConnectTimeout,
    )
except ImportError:
    pass


def is_retryable_error(exc: Exception) -> bool:
    """Return True if the exception represents a transient/retryable error."""
    if isinstance(exc, RETRYABLE_EXCEPTIONS):
        return True
    # httpx.HTTPStatusError carries a status code
    try:
        import httpx as _httpx
        if isinstance(exc, _httpx.HTTPStatusError):
            return exc.response.status_code in RETRYABLE_STATUS_CODES
    except ImportError:
        pass
    return False


def is_retryable_status(status_code: int) -> bool:
    """Return True if the HTTP status code is retryable."""
    return status_code in RETRYABLE_STATUS_CODES


# ── Exponential backoff helpers ──────────────────────────────────────────

def _backoff_delay(attempt: int, base: float = 1.0, max_delay: float = 60.0, jitter: bool = True) -> float:
    """Calculate exponential backoff delay with optional jitter.

    delay = min(base * 2^attempt, max_delay) + random_jitter
    """
    import random
    delay = min(base * (2 ** attempt), max_delay)
    if jitter:
        delay += random.uniform(0, delay * 0.25)
    return delay


# ── Layer 1: LLM call retry decorator ───────────────────────────────────

def llm_retry(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    circuit_breaker: Optional["CircuitBreaker"] = None,
):
    """Decorator for retrying async LLM API calls with exponential backoff.

    Wraps ``call_llm``-style async functions.  On transient failures it
    retries up to ``max_retries`` times.  If a ``circuit_breaker`` is
    provided, it checks / updates its state before and after each call.

    Usage::

        @llm_retry(max_retries=3, circuit_breaker=openrouter_breaker)
        async def call_llm(self, prompt, ...):
            ...
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs) -> Any:
            provider = kwargs.get("model", "unknown").split("/")[0] if kwargs.get("model") else "unknown"

            # Check circuit breaker first
            if circuit_breaker and circuit_breaker.is_open(provider):
                logger.warning(f"Circuit breaker OPEN for {provider} — failing fast")
                return {
                    "content": f"Error: Circuit breaker open for {provider}. Service temporarily unavailable.",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0,
                    "duration_ms": 0,
                    "error": f"circuit_breaker_open:{provider}",
                }

            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    result = await fn(*args, **kwargs)

                    # Check if the result dict indicates a retryable HTTP error
                    if isinstance(result, dict) and result.get("error"):
                        error_text = str(result["error"])
                        # Extract status code from error text patterns
                        for code in RETRYABLE_STATUS_CODES:
                            if str(code) in error_text:
                                if attempt < max_retries:
                                    delay = _backoff_delay(attempt, base_delay, max_delay)
                                    logger.warning(
                                        f"LLM call returned {code}, retrying in {delay:.1f}s "
                                        f"(attempt {attempt + 1}/{max_retries + 1})"
                                    )
                                    if circuit_breaker:
                                        circuit_breaker.record_failure(provider)
                                    await asyncio.sleep(delay)
                                    last_error = error_text
                                    break
                        else:
                            # No retryable status code found — success or non-retryable error
                            if circuit_breaker and not result.get("error"):
                                circuit_breaker.record_success(provider)
                            return result
                        continue  # retry

                    # Successful result
                    if circuit_breaker:
                        circuit_breaker.record_success(provider)
                    return result

                except RETRYABLE_EXCEPTIONS as exc:
                    last_error = exc
                    if circuit_breaker:
                        circuit_breaker.record_failure(provider)
                    if attempt < max_retries:
                        delay = _backoff_delay(attempt, base_delay, max_delay)
                        logger.warning(
                            f"LLM call failed ({type(exc).__name__}), retrying in {delay:.1f}s "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"LLM call failed after {max_retries + 1} attempts: {exc}")
                        raise

                except Exception:
                    # Non-retryable exception — propagate immediately
                    if circuit_breaker:
                        circuit_breaker.record_failure(provider)
                    raise

            # Exhausted retries — return last error result
            logger.error(f"LLM call exhausted {max_retries + 1} attempts, last error: {last_error}")
            return {
                "content": f"Error: Exhausted retries. Last error: {last_error}",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "duration_ms": 0,
                "error": f"retries_exhausted:{last_error}",
            }

        return wrapper
    return decorator


# ── Layer 2: Agent-level retry ───────────────────────────────────────────

async def retry_agent_execution(
    execute_fn: Callable,
    *args,
    max_retries: int = 2,
    base_delay: float = 3.0,
    max_delay: float = 30.0,
    agent_name: str = "unknown",
    **kwargs,
) -> Any:
    """Retry an agent execution function with exponential backoff.

    Only retries on transient errors (timeouts, connection issues).
    Logic errors, validation failures, etc. are NOT retried.

    Args:
        execute_fn: Async callable to execute (e.g. agent.run)
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay cap in seconds
        agent_name: For logging

    Returns:
        The result from execute_fn
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            result = await execute_fn(*args, **kwargs)

            # Check if the result indicates a transient failure worth retrying
            if hasattr(result, "success") and not result.success:
                errors = getattr(result, "errors", [])
                # Only retry if errors look transient
                is_transient = any(
                    _is_transient_error_message(str(e)) for e in errors
                )
                if is_transient and attempt < max_retries:
                    delay = _backoff_delay(attempt, base_delay, max_delay)
                    logger.warning(
                        f"Agent {agent_name} failed with transient error, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue

            return result

        except asyncio.TimeoutError:
            last_exc = asyncio.TimeoutError(f"Agent {agent_name} timed out")
            if attempt < max_retries:
                delay = _backoff_delay(attempt, base_delay, max_delay)
                logger.warning(
                    f"Agent {agent_name} timed out, retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                await asyncio.sleep(delay)
            else:
                raise last_exc

        except RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = _backoff_delay(attempt, base_delay, max_delay)
                logger.warning(
                    f"Agent {agent_name} failed ({type(exc).__name__}), "
                    f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                )
                await asyncio.sleep(delay)
            else:
                raise

        except Exception:
            # Non-retryable — propagate immediately
            raise

    # Should not reach here, but just in case
    if last_exc:
        raise last_exc
    return None


def _is_transient_error_message(error: str) -> bool:
    """Heuristic: does this error message look like a transient issue?"""
    transient_keywords = [
        "timeout", "timed out", "connection", "network",
        "rate limit", "429", "502", "503", "504",
        "server error", "unavailable", "overloaded",
        "circuit_breaker", "retries_exhausted",
    ]
    error_lower = error.lower()
    return any(kw in error_lower for kw in transient_keywords)


# ── Layer 3: Circuit Breaker ─────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation — requests pass through
    OPEN = "open"          # Failures exceeded threshold — requests fail-fast
    HALF_OPEN = "half_open"  # Cooldown expired — let one request through to test


@dataclass
class _ProviderState:
    """Per-provider circuit breaker state."""
    failures: int = 0
    successes: int = 0
    last_failure_time: float = 0.0
    state: CircuitState = CircuitState.CLOSED
    half_open_attempt: bool = False


@dataclass
class CircuitBreaker:
    """Circuit breaker that tracks failure rate per LLM provider.

    When failures exceed ``failure_threshold`` within the
    ``window_seconds`` window, the circuit opens and all requests
    fail-fast for ``cooldown_seconds``.  After cooldown the circuit
    enters half-open state and allows one test request through.

    Usage::

        breaker = CircuitBreaker(failure_threshold=5, cooldown_seconds=60)

        # In call_llm:
        if breaker.is_open("openrouter"):
            return error_response

        try:
            result = await make_api_call()
            breaker.record_success("openrouter")
        except TransientError:
            breaker.record_failure("openrouter")
    """

    failure_threshold: int = 5
    cooldown_seconds: float = 60.0
    window_seconds: float = 120.0
    half_open_max_failures: int = 1
    _providers: Dict[str, _ProviderState] = field(default_factory=dict)

    def _get_state(self, provider: str) -> _ProviderState:
        if provider not in self._providers:
            self._providers[provider] = _ProviderState()
        return self._providers[provider]

    def is_open(self, provider: str) -> bool:
        """Check if the circuit is open (should fail-fast)."""
        state = self._get_state(provider)
        now = time.time()

        if state.state == CircuitState.CLOSED:
            return False

        if state.state == CircuitState.OPEN:
            # Check if cooldown has expired
            if now - state.last_failure_time >= self.cooldown_seconds:
                state.state = CircuitState.HALF_OPEN
                state.half_open_attempt = False
                logger.info(f"Circuit breaker for {provider}: OPEN → HALF_OPEN (testing)")
                return False  # Allow one test request
            return True

        if state.state == CircuitState.HALF_OPEN:
            # Allow only if no half-open attempt is in progress
            if not state.half_open_attempt:
                state.half_open_attempt = True
                return False
            return True  # Block concurrent requests during half-open test

        return False

    def record_success(self, provider: str) -> None:
        """Record a successful call. Resets circuit if half-open."""
        state = self._get_state(provider)
        state.successes += 1

        if state.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker for {provider}: HALF_OPEN → CLOSED (success)")
            state.state = CircuitState.CLOSED
            state.failures = 0
            state.half_open_attempt = False
        elif state.state == CircuitState.CLOSED:
            # Decay failures on success (sliding window effect)
            now = time.time()
            if now - state.last_failure_time > self.window_seconds:
                state.failures = 0

    def record_failure(self, provider: str) -> None:
        """Record a failed call. May trip the circuit to OPEN."""
        state = self._get_state(provider)
        state.failures += 1
        state.last_failure_time = time.time()

        if state.state == CircuitState.HALF_OPEN:
            # Failed during half-open test → re-open
            state.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker for {provider}: HALF_OPEN → OPEN (test failed)")
            return

        if state.state == CircuitState.CLOSED:
            if state.failures >= self.failure_threshold:
                state.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker for {provider}: CLOSED → OPEN "
                    f"({state.failures} failures in {self.window_seconds}s)"
                )

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Return current circuit breaker status for all providers."""
        return {
            provider: {
                "state": state.state.value,
                "failures": state.failures,
                "successes": state.successes,
                "last_failure": state.last_failure_time,
            }
            for provider, state in self._providers.items()
        }

    def reset(self, provider: Optional[str] = None) -> None:
        """Reset circuit breaker state."""
        if provider:
            if provider in self._providers:
                self._providers[provider] = _ProviderState()
        else:
            self._providers.clear()


# ── Global circuit breaker instance ──────────────────────────────────────

# Shared across all agent instances.  Configurable thresholds:
# - 5 failures within 120s → open circuit
# - 60s cooldown before half-open test
llm_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    cooldown_seconds=60.0,
    window_seconds=120.0,
)
