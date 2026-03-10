"""Cost calculation utilities for LLM API calls."""
from typing import Dict, Tuple

# Pricing per 1M tokens (input, output)
PRICING: Dict[str, Tuple[float, float]] = {
    # Anthropic
    "anthropic/claude-opus-4": (15.0, 75.0),
    "anthropic/claude-sonnet-4": (3.0, 15.0),
    "anthropic/claude-haiku": (0.25, 1.25),
    
    # OpenAI
    "openai/gpt-4o": (5.0, 15.0),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4-turbo": (10.0, 30.0),
    
    # DeepSeek
    "deepseek/deepseek-chat": (0.14, 0.28),
    "deepseek/deepseek-coder": (0.14, 0.28),
    
    # Google
    "google/gemini-pro-1.5": (3.5, 10.5),
    "google/gemini-flash-1.5": (0.075, 0.30),
    
    # Default fallback
    "default": (1.0, 2.0),
}


def calculate_model_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calculate cost for an LLM API call.
    
    Args:
        model: Model identifier
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        
    Returns:
        Cost in USD
    """
    input_rate, output_rate = PRICING.get(model, PRICING["default"])
    cost = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000
    return round(cost, 6)


def estimate_project_cost(project_type: str, cost_profile: str) -> Dict[str, float]:
    """Estimate total project cost based on type and profile.
    
    Args:
        project_type: web_simple or web_complex
        cost_profile: budget, balanced, or premium
        
    Returns:
        Dict with min, max, and average estimates
    """
    estimates = {
        "web_simple": {
            "budget": {"min": 1.0, "max": 3.0, "avg": 2.0},
            "balanced": {"min": 5.0, "max": 10.0, "avg": 7.5},
            "premium": {"min": 15.0, "max": 30.0, "avg": 22.5},
        },
        "web_complex": {
            "budget": {"min": 5.0, "max": 15.0, "avg": 10.0},
            "balanced": {"min": 15.0, "max": 40.0, "avg": 27.5},
            "premium": {"min": 40.0, "max": 100.0, "avg": 70.0},
        },
    }
    
    return estimates.get(project_type, estimates["web_simple"]).get(
        cost_profile, estimates["web_simple"]["balanced"]
    )
