"""Research Agent - Step 2."""
import json
from typing import Any, Dict

from .base import BaseAgent


class ResearchAgent(BaseAgent):
    """Conducts research on competitors, design trends, and best practices."""
    
    name = "research"
    description = "Research Agent"
    step_number = 2
    
    SYSTEM_PROMPT = """You are the Research Agent for an AI development agency.

Your job is to:
1. Research competitor websites and apps in the same industry
2. Identify current design trends and best practices
3. Recommend UI/UX patterns that work well for this type of project
4. Suggest color schemes, typography, and layout approaches
5. Note any technical considerations or integrations to consider

Respond ONLY with valid JSON in this format:
{
    "competitor_analysis": [
        {
            "name": "competitor name",
            "url": "url if known",
            "strengths": ["what they do well"],
            "weaknesses": ["what could be improved"]
        }
    ],
    "design_trends": ["trend1", "trend2", ...],
    "recommended_patterns": [
        {
            "pattern": "pattern name",
            "use_case": "where to use it",
            "rationale": "why it works"
        }
    ],
    "color_recommendations": {
        "primary": "#hex",
        "secondary": "#hex",
        "accent": "#hex",
        "background": "#hex",
        "text": "#hex",
        "rationale": "why these colors"
    },
    "typography_recommendations": {
        "heading_font": "font name",
        "body_font": "font name",
        "rationale": "why these fonts"
    },
    "technical_considerations": ["consideration1", "consideration2"],
    "key_integrations": ["integration1", "integration2"]
}"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct research based on project classification."""
        classification = input_data.get("classification", {})
        brief = input_data.get("brief", "")
        cost_profile = input_data.get("cost_profile", "balanced")
        
        model = self._select_model(cost_profile)
        
        prompt = f"""Conduct research for this project:

Original Brief:
{brief}

Project Classification:
{json.dumps(classification, indent=2)}

Research competitors, design trends, and provide recommendations."""
        
        result = await self.call_llm(
            prompt=prompt,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.5,
            max_tokens=4096,
        )
        
        try:
            research = json.loads(result["content"])
        except json.JSONDecodeError:
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                research = json.loads(content[start:end])
            else:
                research = {"error": "Failed to parse response", "raw": content}
        
        await self.log_execution(
            input_data=input_data,
            output_data=research,
            model=model,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            cost=result["cost"],
            duration_ms=result["duration_ms"],
        )
        
        return {
            "research": research,
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
