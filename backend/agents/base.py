"""Base agent class with common functionality."""
import os
import time
import httpx
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
import uuid


class BaseAgent(ABC):
    """Base class for all agents in the pipeline."""
    
    name: str = "base"
    description: str = "Base agent"
    step_number: int = 0
    
    def __init__(self, project_id: str, db_session=None):
        self.project_id = project_id
        self.db = db_session
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main task."""
        pass
    
    async def call_llm(
        self,
        prompt: str,
        model: str = "anthropic/claude-sonnet-4",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Call OpenRouter API for LLM inference."""
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-dev-agency.local",
            "X-Title": "AI Dev Agency"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Extract token usage
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # Calculate cost (rough estimates per model)
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
        
        return {
            "content": result["choices"][0]["message"]["content"],
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost": cost,
            "duration_ms": duration_ms,
        }
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on model pricing."""
        # Pricing per 1M tokens (input/output)
        pricing = {
            "anthropic/claude-sonnet-4": (3.0, 15.0),
            "anthropic/claude-opus-4": (15.0, 75.0),
            "openai/gpt-4o": (5.0, 15.0),
            "openai/gpt-4o-mini": (0.15, 0.60),
            "deepseek/deepseek-chat": (0.14, 0.28),
            "deepseek/deepseek-coder": (0.14, 0.28),
        }
        
        input_rate, output_rate = pricing.get(model, (1.0, 2.0))
        cost = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000
        return round(cost, 6)
    
    async def log_execution(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        duration_ms: int,
        status: str = "completed",
        error_message: Optional[str] = None,
    ):
        """Log agent execution to database."""
        if not self.db:
            return
        
        from models import AgentLog
        
        log = AgentLog(
            id=uuid.uuid4(),
            project_id=self.project_id,
            agent_name=self.name,
            agent_step=self.step_number,
            model_used=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            input_data=input_data,
            output_data=output_data,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        self.db.commit()
