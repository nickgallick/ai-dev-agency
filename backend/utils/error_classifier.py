"""Self-healing error classification and routing.

Replaces blunt keyword matching with structured error classification.
Each error is classified into a category with a specific resolution
strategy, preventing wasted tokens on non-transient failures.

Error categories:
- TRANSIENT: Network/timeout/rate-limit → retry with backoff
- AUTH: API key invalid/expired → fail fast, notify user
- QUOTA: Account quota exceeded → fail fast, suggest upgrade
- VALIDATION: Bad input/prompt → rewrite prompt, don't retry same call
- MODEL: Model unavailable/deprecated → fallback to alternate model
- CONTENT: Safety filter / content policy → rewrite prompt
- UPSTREAM: External API failure (v0, GitHub) → retry or skip
- LOGIC: Code/logic bug in agent → fail, log for debugging
- UNKNOWN: Unclassified → conservative retry (1x), then fail
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Structured error classification categories."""
    TRANSIENT = "transient"       # Network, timeout, 502/503/504
    RATE_LIMIT = "rate_limit"     # 429, quota per-minute
    AUTH = "auth"                 # 401, 403, invalid API key
    QUOTA = "quota"              # Account-level quota/billing
    VALIDATION = "validation"    # 400, bad request, invalid prompt
    MODEL = "model"              # Model not found, deprecated
    CONTENT = "content"          # Content policy, safety filter
    UPSTREAM = "upstream"        # External API (v0, GitHub, etc.)
    LOGIC = "logic"              # Internal code error / bug
    UNKNOWN = "unknown"          # Unclassified


class ResolutionStrategy(str, Enum):
    """What to do after classifying an error."""
    RETRY_BACKOFF = "retry_backoff"           # Exponential backoff retry
    RETRY_IMMEDIATE = "retry_immediate"       # Retry immediately (no delay)
    FALLBACK_MODEL = "fallback_model"         # Try a different model
    REWRITE_PROMPT = "rewrite_prompt"         # Shorten/rewrite the prompt
    FAIL_FAST = "fail_fast"                   # Don't retry, fail immediately
    SKIP_AGENT = "skip_agent"                 # Skip this agent, continue pipeline
    NOTIFY_USER = "notify_user"               # Fail + surface to user for action
    WAIT_AND_RETRY = "wait_and_retry"         # Long wait (rate limit cooldown)


@dataclass
class ClassifiedError:
    """A classified error with resolution strategy."""
    category: ErrorCategory
    strategy: ResolutionStrategy
    message: str                              # Original error message
    should_retry: bool                        # Quick check: should we retry?
    max_retries: int = 0                      # How many retries for this type
    retry_delay: float = 0.0                  # Base delay in seconds
    fallback_model: Optional[str] = None      # Alternate model to try
    user_message: Optional[str] = None        # Human-readable explanation
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "strategy": self.strategy.value,
            "message": self.message,
            "should_retry": self.should_retry,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "fallback_model": self.fallback_model,
            "user_message": self.user_message,
        }


# ── Classification rules ─────────────────────────────────────────────────

# (pattern, category, strategy) — first match wins
_CLASSIFICATION_RULES: List[Tuple[str, ErrorCategory, ResolutionStrategy]] = [
    # Auth / API key errors — fail fast
    (r"(401|unauthorized|invalid.*api.?key|authentication.*failed|invalid.*token)", ErrorCategory.AUTH, ResolutionStrategy.FAIL_FAST),
    (r"(403|forbidden|access.*denied|permission.*denied)", ErrorCategory.AUTH, ResolutionStrategy.FAIL_FAST),

    # Quota / billing — fail fast, notify user
    (r"(quota.*exceeded|billing|payment.*required|insufficient.*credits|account.*limit)", ErrorCategory.QUOTA, ResolutionStrategy.NOTIFY_USER),
    (r"(usage.*limit|spending.*limit|budget.*exceeded)", ErrorCategory.QUOTA, ResolutionStrategy.NOTIFY_USER),

    # Rate limit — wait and retry with longer delay
    (r"(429|rate.?limit|too.?many.?requests|throttl)", ErrorCategory.RATE_LIMIT, ResolutionStrategy.WAIT_AND_RETRY),
    (r"(retry.?after|slow.*down|requests.*per.*minute)", ErrorCategory.RATE_LIMIT, ResolutionStrategy.WAIT_AND_RETRY),

    # Model errors — fallback to alternate model
    (r"(model.*not.*found|model.*deprecated|model.*unavailable|no.*such.*model)", ErrorCategory.MODEL, ResolutionStrategy.FALLBACK_MODEL),
    (r"(model.*overloaded|model.*capacity|model.*busy)", ErrorCategory.MODEL, ResolutionStrategy.FALLBACK_MODEL),

    # Content policy — rewrite prompt
    (r"(content.*policy|safety.*filter|flagged.*content|harmful|unsafe)", ErrorCategory.CONTENT, ResolutionStrategy.REWRITE_PROMPT),
    (r"(blocked.*by.*filter|moderation|content.*violation)", ErrorCategory.CONTENT, ResolutionStrategy.REWRITE_PROMPT),

    # Validation — don't retry with same input
    (r"(400|bad.*request|invalid.*parameter|validation.*error)", ErrorCategory.VALIDATION, ResolutionStrategy.FAIL_FAST),
    (r"(context.*length|too.*long|max.*tokens.*exceeded|token.*limit)", ErrorCategory.VALIDATION, ResolutionStrategy.REWRITE_PROMPT),
    (r"(invalid.*json|malformed|parse.*error)", ErrorCategory.VALIDATION, ResolutionStrategy.FAIL_FAST),

    # Transient network / server errors — retry with backoff
    (r"(timeout|timed?\s*out|deadline.*exceeded)", ErrorCategory.TRANSIENT, ResolutionStrategy.RETRY_BACKOFF),
    (r"(connection.*(?:refused|reset|error|closed))", ErrorCategory.TRANSIENT, ResolutionStrategy.RETRY_BACKOFF),
    (r"(502|503|504|bad.*gateway|service.*unavailable|gateway.*timeout)", ErrorCategory.TRANSIENT, ResolutionStrategy.RETRY_BACKOFF),
    (r"(500|internal.*server.*error)", ErrorCategory.TRANSIENT, ResolutionStrategy.RETRY_BACKOFF),
    (r"(network|dns|socket|ssl|tls|certificate)", ErrorCategory.TRANSIENT, ResolutionStrategy.RETRY_BACKOFF),
    (r"(econnrefused|econnreset|epipe|enetunreach)", ErrorCategory.TRANSIENT, ResolutionStrategy.RETRY_BACKOFF),

    # Upstream external API errors
    (r"(vercel|v0.*api|deployment.*failed)", ErrorCategory.UPSTREAM, ResolutionStrategy.RETRY_BACKOFF),
    (r"(github.*api|git.*push.*failed|repository)", ErrorCategory.UPSTREAM, ResolutionStrategy.RETRY_BACKOFF),
    (r"(openai.*api|dall.?e|stability)", ErrorCategory.UPSTREAM, ResolutionStrategy.RETRY_BACKOFF),

    # Circuit breaker / retry exhaustion
    (r"(circuit.?breaker.*open)", ErrorCategory.TRANSIENT, ResolutionStrategy.WAIT_AND_RETRY),
    (r"(retries.*exhausted|max.*retries)", ErrorCategory.TRANSIENT, ResolutionStrategy.FAIL_FAST),
]

# Compiled patterns for performance
_COMPILED_RULES = [
    (re.compile(pattern, re.IGNORECASE), category, strategy)
    for pattern, category, strategy in _CLASSIFICATION_RULES
]

# Model fallback chain — if a model fails, try the next one
_MODEL_FALLBACKS: Dict[str, str] = {
    "anthropic/claude-opus-4": "anthropic/claude-sonnet-4",
    "anthropic/claude-sonnet-4": "deepseek/deepseek-chat",
    "openai/gpt-4o": "openai/gpt-4o-mini",
    "openai/gpt-4o-mini": "deepseek/deepseek-chat",
    "deepseek/deepseek-chat": "anthropic/claude-3-haiku",
    "deepseek/deepseek-coder": "deepseek/deepseek-chat",
}

# Resolution parameters per category
_RESOLUTION_PARAMS: Dict[ErrorCategory, Dict[str, Any]] = {
    ErrorCategory.TRANSIENT: {"max_retries": 3, "retry_delay": 2.0},
    ErrorCategory.RATE_LIMIT: {"max_retries": 3, "retry_delay": 10.0},
    ErrorCategory.AUTH: {"max_retries": 0, "retry_delay": 0},
    ErrorCategory.QUOTA: {"max_retries": 0, "retry_delay": 0},
    ErrorCategory.VALIDATION: {"max_retries": 0, "retry_delay": 0},
    ErrorCategory.MODEL: {"max_retries": 1, "retry_delay": 1.0},
    ErrorCategory.CONTENT: {"max_retries": 1, "retry_delay": 0},
    ErrorCategory.UPSTREAM: {"max_retries": 2, "retry_delay": 5.0},
    ErrorCategory.LOGIC: {"max_retries": 0, "retry_delay": 0},
    ErrorCategory.UNKNOWN: {"max_retries": 1, "retry_delay": 3.0},
}

# User-facing messages per category
_USER_MESSAGES: Dict[ErrorCategory, str] = {
    ErrorCategory.TRANSIENT: "Temporary server issue. Retrying automatically.",
    ErrorCategory.RATE_LIMIT: "API rate limit reached. Waiting before retrying.",
    ErrorCategory.AUTH: "API authentication failed. Check your API keys in Settings.",
    ErrorCategory.QUOTA: "API quota exceeded. Check billing or upgrade your plan.",
    ErrorCategory.VALIDATION: "Invalid request. The agent will adjust and retry.",
    ErrorCategory.MODEL: "Model unavailable. Switching to an alternate model.",
    ErrorCategory.CONTENT: "Content filtered. Adjusting the prompt.",
    ErrorCategory.UPSTREAM: "External service error. Retrying.",
    ErrorCategory.LOGIC: "Internal error. This has been logged for investigation.",
    ErrorCategory.UNKNOWN: "Unexpected error occurred. Attempting recovery.",
}


# ── Main classification function ─────────────────────────────────────────

def classify_error(
    error: str,
    status_code: Optional[int] = None,
    exception_type: Optional[str] = None,
    model: Optional[str] = None,
) -> ClassifiedError:
    """Classify an error into a category with resolution strategy.

    Uses regex pattern matching against known error patterns.
    Falls back to UNKNOWN if no pattern matches.

    Args:
        error: Error message string
        status_code: HTTP status code if available
        exception_type: Python exception class name if available
        model: Model that was being called (for fallback lookup)

    Returns:
        ClassifiedError with category, strategy, and resolution params
    """
    # Combine all signals into a single searchable string
    search_text = error.lower()
    if status_code:
        search_text += f" {status_code}"
    if exception_type:
        search_text += f" {exception_type.lower()}"

    # Match against rules (first match wins)
    category = ErrorCategory.UNKNOWN
    strategy = ResolutionStrategy.FAIL_FAST

    for pattern, cat, strat in _COMPILED_RULES:
        if pattern.search(search_text):
            category = cat
            strategy = strat
            break

    # Look up resolution parameters
    params = _RESOLUTION_PARAMS.get(category, _RESOLUTION_PARAMS[ErrorCategory.UNKNOWN])
    user_message = _USER_MESSAGES.get(category, _USER_MESSAGES[ErrorCategory.UNKNOWN])

    # Find fallback model if strategy calls for it
    fallback_model = None
    if strategy == ResolutionStrategy.FALLBACK_MODEL and model:
        fallback_model = _MODEL_FALLBACKS.get(model)
        if fallback_model:
            user_message = f"Switching from {model.split('/')[-1]} to {fallback_model.split('/')[-1]}."

    # For REWRITE_PROMPT on context length, truncation is the fix
    if strategy == ResolutionStrategy.REWRITE_PROMPT and "context" in error.lower():
        user_message = "Prompt too long. Truncating and retrying."

    classified = ClassifiedError(
        category=category,
        strategy=strategy,
        message=error,
        should_retry=params["max_retries"] > 0,
        max_retries=params["max_retries"],
        retry_delay=params["retry_delay"],
        fallback_model=fallback_model,
        user_message=user_message,
        details={
            "status_code": status_code,
            "exception_type": exception_type,
            "model": model,
        },
    )

    logger.info(
        f"Error classified: {category.value}/{strategy.value} "
        f"(retry={classified.should_retry}, model={model}) — {error[:100]}"
    )

    return classified


def is_retryable(error: str, status_code: Optional[int] = None) -> bool:
    """Quick check: is this error retryable?

    Drop-in replacement for the old _is_transient_error_message().
    """
    classified = classify_error(error, status_code=status_code)
    return classified.should_retry


def get_fallback_model(model: str) -> Optional[str]:
    """Get the fallback model for a given model."""
    return _MODEL_FALLBACKS.get(model)
