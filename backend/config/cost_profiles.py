"""Cost profile configurations."""

COST_PROFILES = {
    "budget": {
        "description": "Minimize cost - use cheapest models that still work",
        "models": {
            "intake": "deepseek/deepseek-chat",
            "research": "deepseek/deepseek-chat",
            "architect": "anthropic/claude-sonnet-4",
            "design_system": "deepseek/deepseek-chat",
            "content": "deepseek/deepseek-chat",
            "seo": "deepseek/deepseek-chat",
        },
        "estimated_cost": {
            "web_simple": "$1-3",
            "web_complex": "$5-15",
        },
    },
    "balanced": {
        "description": "Default - good quality, reasonable cost",
        "models": {
            "intake": "anthropic/claude-sonnet-4",
            "research": "anthropic/claude-sonnet-4",
            "architect": "anthropic/claude-opus-4",
            "design_system": "anthropic/claude-sonnet-4",
            "content": "openai/gpt-4o",
            "seo": "anthropic/claude-sonnet-4",
        },
        "estimated_cost": {
            "web_simple": "$5-10",
            "web_complex": "$15-40",
        },
    },
    "premium": {
        "description": "Maximum quality - best models everywhere",
        "models": {
            "intake": "anthropic/claude-opus-4",
            "research": "anthropic/claude-opus-4",
            "architect": "anthropic/claude-opus-4",
            "design_system": "anthropic/claude-opus-4",
            "content": "anthropic/claude-opus-4",
            "seo": "anthropic/claude-opus-4",
        },
        "estimated_cost": {
            "web_simple": "$15-30",
            "web_complex": "$40-100",
        },
    },
}
