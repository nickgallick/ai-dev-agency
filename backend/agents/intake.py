"""Intake & Classification Agent - Step 1."""
import json
from typing import Any, Dict

from .base import BaseAgent


class IntakeAgent(BaseAgent):
    """Classifies project briefs and extracts key information."""
    
    name = "intake"
    description = "Intake & Classification Agent"
    step_number = 1
    
    SYSTEM_PROMPT = """You are the Intake & Classification Agent for an AI development agency.
    
Your job is to analyze project briefs and:
1. Classify the project type (web_simple or web_complex)
2. Extract key requirements
3. Identify the target audience
4. Note any special requirements or constraints
5. Estimate project complexity

Project Type Definitions:
- web_simple: Landing pages, portfolios, small business sites, blogs (1-5 pages, no complex backend)
- web_complex: Multi-page apps with authentication, databases, APIs, dashboards, e-commerce

Respond ONLY with valid JSON in this format:
{
    "project_type": "web_simple" | "web_complex",
    "project_name": "suggested name for the project",
    "summary": "2-3 sentence summary of what will be built",
    "key_features": ["feature1", "feature2", ...],
    "target_audience": "description of target users",
    "complexity_score": 1-10,
    "estimated_pages": number,
    "requires_backend": true/false,
    "requires_database": true/false,
    "requires_auth": true/false,
    "special_requirements": ["any special notes"],
    "recommended_tech_stack": {
        "frontend": "recommended framework",
        "backend": "if needed",
        "database": "if needed"
    }
}"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the project brief and classify it."""
        brief = input_data.get("brief", "")
        cost_profile = input_data.get("cost_profile", "balanced")
        
        # Select model based on cost profile
        model = self._select_model(cost_profile)
        
        prompt = f"""Analyze this project brief and classify it:

---
{brief}
---

Provide your classification as JSON."""
        
        result = await self.call_llm(
            prompt=prompt,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.3,
        )
        
        # Parse the JSON response
        try:
            classification = json.loads(result["content"])
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                classification = json.loads(content[start:end])
            else:
                classification = {"error": "Failed to parse response", "raw": content}
        
        # Log the execution
        await self.log_execution(
            input_data=input_data,
            output_data=classification,
            model=model,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            cost=result["cost"],
            duration_ms=result["duration_ms"],
        )
        
        return {
            "classification": classification,
            "model_used": model,
            "tokens": result["total_tokens"],
            "cost": result["cost"],
        }
    
    def _select_model(self, cost_profile: str) -> str:
        """Select model based on cost profile."""
        models = {
            "budget": "deepseek/deepseek-chat",
            "balanced": "anthropic/claude-sonnet-4",
            "premium": "anthropic/claude-opus-4",
        }
        return models.get(cost_profile, "anthropic/claude-sonnet-4")
