"""Smart Cost Optimization Engine for AI Dev Agency.

Implements intelligent model selection based on:
- Quality outcomes per agent per model
- Cost profiles (budget, balanced, premium)
- Project complexity and type
- Real-time cost tracking and alerts
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class CostProfile(str, Enum):
    """Cost profile presets."""
    BUDGET = "budget"
    BALANCED = "balanced"
    PREMIUM = "premium"


@dataclass
class ModelCostInfo:
    """Cost information for a model."""
    model_id: str
    input_cost_per_1k: float  # Cost per 1K input tokens
    output_cost_per_1k: float  # Cost per 1K output tokens
    quality_score: float = 0.0  # 0-1, based on historical outcomes
    success_rate: float = 1.0  # Rate of first-try success
    avg_revision_count: float = 0.0  # Average revisions needed


@dataclass
class CostEstimate:
    """Cost estimate for a project or agent."""
    min_cost: float
    max_cost: float
    expected_cost: float
    breakdown: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.8  # Confidence level of estimate


@dataclass
class CostAlert:
    """Cost alert when threshold is exceeded."""
    project_id: str
    current_cost: float
    threshold: float
    percentage: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# Model pricing (as of March 2026 - OpenRouter rates)
MODEL_PRICING = {
    # Anthropic models
    "anthropic/claude-opus-4": ModelCostInfo(
        model_id="anthropic/claude-opus-4",
        input_cost_per_1k=0.015,
        output_cost_per_1k=0.075,
        quality_score=0.98,
    ),
    "anthropic/claude-sonnet-4": ModelCostInfo(
        model_id="anthropic/claude-sonnet-4",
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.015,
        quality_score=0.92,
    ),
    "anthropic/claude-haiku-3": ModelCostInfo(
        model_id="anthropic/claude-haiku-3",
        input_cost_per_1k=0.00025,
        output_cost_per_1k=0.00125,
        quality_score=0.75,
    ),
    # OpenAI models
    "openai/gpt-4o": ModelCostInfo(
        model_id="openai/gpt-4o",
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        quality_score=0.90,
    ),
    "openai/gpt-4o-mini": ModelCostInfo(
        model_id="openai/gpt-4o-mini",
        input_cost_per_1k=0.00015,
        output_cost_per_1k=0.0006,
        quality_score=0.78,
    ),
    # DeepSeek models
    "deepseek/deepseek-chat": ModelCostInfo(
        model_id="deepseek/deepseek-chat",
        input_cost_per_1k=0.00014,
        output_cost_per_1k=0.00028,
        quality_score=0.82,
    ),
    "deepseek/deepseek-coder": ModelCostInfo(
        model_id="deepseek/deepseek-coder",
        input_cost_per_1k=0.00014,
        output_cost_per_1k=0.00028,
        quality_score=0.85,
    ),
}

# Cost profiles with model assignments per agent
COST_PROFILES = {
    CostProfile.BUDGET: {
        "description": "Minimize cost - use cheapest models that still work",
        "models": {
            "intake": "deepseek/deepseek-chat",
            "research": "deepseek/deepseek-chat",
            "architect": "anthropic/claude-sonnet-4",
            "design_system": "deepseek/deepseek-chat",
            "asset_generation": "openai/gpt-4o-mini",
            "content_generation": "deepseek/deepseek-chat",
            "code_generation": "deepseek/deepseek-coder",
            # Phase 8 new agents
            "project_manager": "anthropic/claude-sonnet-4",  # PM needs good reasoning
            "code_review": "anthropic/claude-sonnet-4",      # Code review needs accuracy
            "post_deploy_verification": "deepseek/deepseek-chat",  # Just HTTP requests
            # Quality agents
            "security": "deepseek/deepseek-coder",
            "seo": "deepseek/deepseek-chat",
            "accessibility": "deepseek/deepseek-chat",
            "qa_testing": "deepseek/deepseek-coder",
            "deployment": "deepseek/deepseek-chat",
            "coding_standards": "deepseek/deepseek-chat",
            "analytics_monitoring": "deepseek/deepseek-chat",
            "delivery": "deepseek/deepseek-chat",
        },
        "estimated_cost_range": {
            "web_simple": (1.0, 3.0),
            "web_complex": (3.0, 8.0),
            "mobile_native_ios": (4.0, 10.0),
            "mobile_cross_platform": (3.0, 8.0),
            "mobile_pwa": (2.0, 5.0),
            "desktop_app": (3.0, 8.0),
            "chrome_extension": (1.0, 3.0),
            "cli_tool": (0.5, 2.0),
            "python_api": (1.0, 4.0),
            "python_saas": (4.0, 12.0),
        },
    },
    CostProfile.BALANCED: {
        "description": "Default - good quality, reasonable cost",
        "models": {
            "intake": "anthropic/claude-sonnet-4",
            "research": "anthropic/claude-sonnet-4",
            "architect": "anthropic/claude-opus-4",
            "design_system": "anthropic/claude-sonnet-4",
            "asset_generation": "openai/gpt-4o",
            "content_generation": "openai/gpt-4o",
            "code_generation": "anthropic/claude-sonnet-4",
            # Phase 8 new agents
            "project_manager": "anthropic/claude-sonnet-4",  # PM uses Sonnet
            "code_review": "anthropic/claude-sonnet-4",      # Code review uses Sonnet
            "post_deploy_verification": "deepseek/deepseek-chat",  # Just HTTP requests
            # Quality agents
            "security": "anthropic/claude-sonnet-4",
            "seo": "anthropic/claude-sonnet-4",
            "accessibility": "anthropic/claude-sonnet-4",
            "qa_testing": "anthropic/claude-sonnet-4",
            "deployment": "anthropic/claude-sonnet-4",
            "coding_standards": "anthropic/claude-sonnet-4",
            "analytics_monitoring": "anthropic/claude-sonnet-4",
            "delivery": "anthropic/claude-sonnet-4",
        },
        "estimated_cost_range": {
            "web_simple": (5.0, 10.0),
            "web_complex": (10.0, 20.0),
            "mobile_native_ios": (12.0, 25.0),
            "mobile_cross_platform": (10.0, 20.0),
            "mobile_pwa": (6.0, 12.0),
            "desktop_app": (8.0, 18.0),
            "chrome_extension": (4.0, 8.0),
            "cli_tool": (2.0, 5.0),
            "python_api": (5.0, 12.0),
            "python_saas": (15.0, 30.0),
        },
    },
    CostProfile.PREMIUM: {
        "description": "Maximum quality - best models everywhere",
        "models": {
            "intake": "anthropic/claude-opus-4",
            "research": "anthropic/claude-opus-4",
            "architect": "anthropic/claude-opus-4",
            "design_system": "anthropic/claude-opus-4",
            "asset_generation": "openai/gpt-4o",
            "content_generation": "anthropic/claude-opus-4",
            "code_generation": "anthropic/claude-opus-4",
            # Phase 8 new agents
            "project_manager": "anthropic/claude-opus-4",  # Premium uses Opus
            "code_review": "anthropic/claude-opus-4",      # Premium uses Opus
            "post_deploy_verification": "anthropic/claude-sonnet-4",  # Sonnet for HTTP requests
            # Quality agents
            "security": "anthropic/claude-opus-4",
            "seo": "anthropic/claude-opus-4",
            "accessibility": "anthropic/claude-opus-4",
            "qa_testing": "anthropic/claude-opus-4",
            "deployment": "anthropic/claude-opus-4",
            "coding_standards": "anthropic/claude-opus-4",
            "analytics_monitoring": "anthropic/claude-opus-4",
            "delivery": "anthropic/claude-opus-4",
        },
        "estimated_cost_range": {
            "web_simple": (15.0, 30.0),
            "web_complex": (30.0, 60.0),
            "mobile_native_ios": (40.0, 80.0),
            "mobile_cross_platform": (35.0, 70.0),
            "mobile_pwa": (20.0, 40.0),
            "desktop_app": (30.0, 60.0),
            "chrome_extension": (12.0, 25.0),
            "cli_tool": (8.0, 15.0),
            "python_api": (15.0, 35.0),
            "python_saas": (50.0, 100.0),
        },
    },
}


class CostOptimizer:
    """Smart cost optimization engine."""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.quality_history: Dict[str, Dict[str, List[float]]] = {}
        self.cost_alerts: List[CostAlert] = []
        self.alert_threshold: float = float(os.getenv("COST_ALERT_THRESHOLD", "50.0"))
    
    def get_model_for_agent(
        self,
        agent_name: str,
        cost_profile: CostProfile = CostProfile.BALANCED,
        project_type: str = "web_simple",
        complexity_score: int = 5,
    ) -> str:
        """Select the optimal model for an agent based on profile and history."""
        profile = COST_PROFILES.get(cost_profile, COST_PROFILES[CostProfile.BALANCED])
        base_model = profile["models"].get(agent_name, "anthropic/claude-sonnet-4")
        
        # For complex projects, consider upgrading budget models
        if cost_profile == CostProfile.BUDGET and complexity_score >= 8:
            # Upgrade critical agents for complex projects
            if agent_name in ["architect", "code_generation", "security"]:
                return "anthropic/claude-sonnet-4"
        
        # Check quality history - if a cheaper model consistently works, use it
        if agent_name in self.quality_history:
            model_history = self.quality_history[agent_name]
            for model_id, scores in model_history.items():
                if len(scores) >= 5:  # Need at least 5 data points
                    avg_score = sum(scores) / len(scores)
                    model_info = MODEL_PRICING.get(model_id)
                    base_info = MODEL_PRICING.get(base_model)
                    
                    # If cheaper model has good quality, use it
                    if model_info and base_info:
                        if (avg_score >= 0.85 and 
                            model_info.input_cost_per_1k < base_info.input_cost_per_1k):
                            return model_id
        
        return base_model
    
    def estimate_project_cost(
        self,
        project_type: str,
        cost_profile: CostProfile = CostProfile.BALANCED,
        complexity_score: int = 5,
    ) -> CostEstimate:
        """Estimate total cost for a project before starting."""
        profile = COST_PROFILES.get(cost_profile, COST_PROFILES[CostProfile.BALANCED])
        cost_range = profile["estimated_cost_range"].get(
            project_type, 
            (5.0, 20.0)  # Default range
        )
        
        # Adjust based on complexity
        complexity_multiplier = 0.5 + (complexity_score / 10) * 1.0  # 0.5x to 1.5x
        
        min_cost = cost_range[0] * complexity_multiplier
        max_cost = cost_range[1] * complexity_multiplier
        expected_cost = (min_cost + max_cost) / 2
        
        # Build breakdown by agent
        breakdown = {}
        agents = [
            "intake", "research", "architect", "design_system",
            "code_generation", "security", "seo", "accessibility",
            "qa_testing", "deployment", "delivery"
        ]
        
        # Rough distribution (percentages)
        distribution = {
            "intake": 0.02,
            "research": 0.08,
            "architect": 0.12,
            "design_system": 0.08,
            "code_generation": 0.30,
            "security": 0.05,
            "seo": 0.05,
            "accessibility": 0.05,
            "qa_testing": 0.10,
            "deployment": 0.05,
            "delivery": 0.10,
        }
        
        for agent in agents:
            breakdown[agent] = expected_cost * distribution.get(agent, 0.05)
        
        return CostEstimate(
            min_cost=round(min_cost, 2),
            max_cost=round(max_cost, 2),
            expected_cost=round(expected_cost, 2),
            breakdown={k: round(v, 2) for k, v in breakdown.items()},
            confidence=0.8 if len(self.quality_history) > 10 else 0.6,
        )
    
    def calculate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate actual cost for a model call."""
        model_info = MODEL_PRICING.get(model_id)
        if not model_info:
            # Default pricing for unknown models
            return (input_tokens * 0.001 + output_tokens * 0.002) / 1000
        
        input_cost = (input_tokens / 1000) * model_info.input_cost_per_1k
        output_cost = (output_tokens / 1000) * model_info.output_cost_per_1k
        
        return round(input_cost + output_cost, 6)
    
    def track_agent_quality(
        self,
        agent_name: str,
        model_id: str,
        success: bool,
        revision_needed: bool = False,
    ) -> None:
        """Track quality outcomes per agent per model."""
        if agent_name not in self.quality_history:
            self.quality_history[agent_name] = {}
        
        if model_id not in self.quality_history[agent_name]:
            self.quality_history[agent_name][model_id] = []
        
        # Score: 1.0 for success first try, 0.7 for success with revision, 0.0 for failure
        score = 0.0
        if success:
            score = 0.7 if revision_needed else 1.0
        
        self.quality_history[agent_name][model_id].append(score)
        
        # Keep only last 100 scores per model
        if len(self.quality_history[agent_name][model_id]) > 100:
            self.quality_history[agent_name][model_id] = \
                self.quality_history[agent_name][model_id][-100:]
    
    def check_cost_alert(
        self,
        project_id: str,
        current_cost: float,
        budget_limit: Optional[float] = None,
    ) -> Optional[CostAlert]:
        """Check if cost threshold is exceeded and return alert."""
        threshold = budget_limit or self.alert_threshold
        
        if current_cost >= threshold:
            percentage = (current_cost / threshold) * 100
            alert = CostAlert(
                project_id=project_id,
                current_cost=current_cost,
                threshold=threshold,
                percentage=percentage,
            )
            self.cost_alerts.append(alert)
            return alert
        
        return None
    
    def get_cost_breakdown_by_agent(
        self,
        project_costs: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Get cost breakdown grouped by agent."""
        breakdown = {}
        for record in project_costs:
            agent = record.get("agent_name", "unknown")
            cost = record.get("cost", 0)
            breakdown[agent] = breakdown.get(agent, 0) + cost
        
        return {k: round(v, 4) for k, v in breakdown.items()}
    
    def get_cost_breakdown_by_model(
        self,
        project_costs: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Get cost breakdown grouped by model."""
        breakdown = {}
        for record in project_costs:
            model = record.get("model_used", "unknown")
            cost = record.get("cost", 0)
            breakdown[model] = breakdown.get(model, 0) + cost
        
        return {k: round(v, 4) for k, v in breakdown.items()}
    
    def get_model_quality_stats(self) -> Dict[str, Dict[str, float]]:
        """Get quality statistics for all tracked agent/model combinations."""
        stats = {}
        
        for agent_name, models in self.quality_history.items():
            stats[agent_name] = {}
            for model_id, scores in models.items():
                if scores:
                    stats[agent_name][model_id] = {
                        "avg_quality": round(sum(scores) / len(scores), 3),
                        "sample_count": len(scores),
                        "success_rate": round(len([s for s in scores if s > 0]) / len(scores), 3),
                    }
        
        return stats
    
    def suggest_cost_savings(
        self,
        project_costs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Analyze project costs and suggest potential savings."""
        suggestions = []
        
        agent_costs = self.get_cost_breakdown_by_agent(project_costs)
        
        for agent, cost in agent_costs.items():
            # Check if a cheaper model could have been used based on quality history
            if agent in self.quality_history:
                current_scores = []
                cheaper_alternatives = []
                
                for model_id, scores in self.quality_history[agent].items():
                    model_info = MODEL_PRICING.get(model_id)
                    if model_info and len(scores) >= 5:
                        avg_score = sum(scores) / len(scores)
                        if avg_score >= 0.85:
                            cheaper_alternatives.append({
                                "model": model_id,
                                "quality": avg_score,
                                "cost_per_1k": model_info.input_cost_per_1k + model_info.output_cost_per_1k,
                            })
                
                if cheaper_alternatives:
                    cheapest = min(cheaper_alternatives, key=lambda x: x["cost_per_1k"])
                    suggestions.append({
                        "agent": agent,
                        "current_cost": cost,
                        "suggested_model": cheapest["model"],
                        "potential_savings": f"Up to {round((1 - cheapest['cost_per_1k'] / 0.02) * 100)}%",
                    })
        
        return suggestions


# Global instance
_cost_optimizer: Optional[CostOptimizer] = None


def get_cost_optimizer(db_session=None) -> CostOptimizer:
    """Get or create the global cost optimizer instance."""
    global _cost_optimizer
    if _cost_optimizer is None:
        _cost_optimizer = CostOptimizer(db_session)
    return _cost_optimizer
