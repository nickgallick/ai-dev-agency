"""Base Agent class for all AI Dev Agency agents."""

import asyncio
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

try:
    import docker
    DOCKER_SDK_AVAILABLE = True
except ImportError:
    DOCKER_SDK_AVAILABLE = False

from config.settings import Settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from knowledge.types import KnowledgeQueryResult


class ClarificationNeeded(Exception):
    """Raised when an agent needs clarification from the user before proceeding."""
    def __init__(self, question: str, context: str = "", agent_name: str = ""):
        self.question = question
        self.context = context
        self.agent_name = agent_name
        super().__init__(question)


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentReasoning:
    """Captures the reasoning behind an agent's decisions."""
    goal: str = ""
    approach: str = ""
    key_decisions: List[Dict[str, str]] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    confidence: float = 0.0
    constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "approach": self.approach,
            "key_decisions": self.key_decisions,
            "alternatives_considered": self.alternatives_considered,
            "confidence": self.confidence,
            "constraints": self.constraints,
        }


@dataclass
class AgentResult:
    """Result from an agent execution."""
    success: bool
    agent_name: str
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    reasoning: Optional[AgentReasoning] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        result = {
            "success": self.success,
            "agent_name": self.agent_name,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
        }
        if self.reasoning:
            result["reasoning"] = self.reasoning.to_dict()
        return result


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the agent."""
        self.settings = settings or Settings()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.status = AgentStatus.IDLE
        self._docker_client: Optional[Any] = None
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging for the agent."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f"[%(asctime)s] [{self.__class__.__name__}] %(levelname)s: %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    @property
    def docker_client(self) -> Optional[Any]:
        """Get or create Docker client."""
        if self._docker_client is None and DOCKER_SDK_AVAILABLE:
            try:
                self._docker_client = docker.from_env()
                self._docker_client.ping()
            except Exception as e:
                self.logger.warning(f"Docker SDK not available: {e}")
                self._docker_client = None
        return self._docker_client

    @property
    def use_docker_sdk(self) -> bool:
        """Check if Docker SDK should be used."""
        if self.settings.docker_integration_mode == "subprocess":
            return False
        return self.docker_client is not None

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the agent name."""
        pass

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute the agent's main task."""
        pass

    def build_reasoning(
        self,
        goal: str,
        approach: str,
        key_decisions: Optional[List[Dict[str, str]]] = None,
        alternatives_considered: Optional[List[str]] = None,
        confidence: float = 0.8,
        constraints: Optional[List[str]] = None,
    ) -> AgentReasoning:
        """Build a reasoning object to attach to an AgentResult."""
        return AgentReasoning(
            goal=goal,
            approach=approach,
            key_decisions=key_decisions or [],
            alternatives_considered=alternatives_considered or [],
            confidence=confidence,
            constraints=constraints or [],
        )

    def request_clarification(self, question: str, context: str = "") -> None:
        """Interrupt the pipeline to ask the user a clarification question.

        Raises ClarificationNeeded which is caught by the executor to pause
        the pipeline, surface the question to the frontend, and wait for the
        user's answer before resuming.
        """
        raise ClarificationNeeded(
            question=question,
            context=context,
            agent_name=self.name,
        )

    def get_model(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Get the optimal model for this agent via centralized routing.

        Uses the cost_profile from context (set by PipelineConfig) and
        the agent's pipeline ID to look up the best model from the
        routing table in config/model_routing.py.

        Falls back to the agent's own _select_model() if it exists,
        or the default model if routing is unavailable.
        """
        from config.model_routing import get_model_for_agent

        # Derive agent_id from class name: "IntakeAgent" → "intake"
        agent_id = self.__class__.__name__.replace("Agent", "").lower()
        # Allow context to override with explicit agent_id
        if context and "agent_id" in context:
            agent_id = context["agent_id"]

        cost_profile = "balanced"
        if context:
            cost_profile = context.get("cost_profile", "balanced")

        return get_model_for_agent(agent_id, cost_profile=cost_profile)

    async def run(self, context: Dict[str, Any]) -> AgentResult:
        """Run the agent with status tracking and timing."""
        import time
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            self.logger.info(f"Starting {self.name} agent")
            result = await self.execute(context)
            
            # Handle both Dict and AgentResult returns from execute()
            if isinstance(result, AgentResult):
                agent_result = result
            elif isinstance(result, dict):
                # Wrap dict result in AgentResult
                agent_result = AgentResult(
                    success=not result.get("error"),
                    agent_name=self.name,
                    data=result,
                    errors=result.get("errors", []) if isinstance(result.get("errors"), list) else [],
                    warnings=result.get("warnings", []) if isinstance(result.get("warnings"), list) else [],
                )
            elif hasattr(result, 'status') and hasattr(result, 'error_message'):
                # Handle AgentOutput from models.schemas
                success = getattr(result, 'status', None) != AgentStatus.FAILED
                errors = [result.error_message] if result.error_message else []
                output_data = getattr(result, 'output_data', {}) or {}
                agent_result = AgentResult(
                    success=success,
                    agent_name=self.name,
                    data=output_data,
                    errors=errors,
                )
            else:
                # Unexpected return type
                agent_result = AgentResult(
                    success=True,
                    agent_name=self.name,
                    data={"result": result} if result else {},
                )
            
            self.status = AgentStatus.COMPLETED if agent_result.success else AgentStatus.FAILED
            agent_result.execution_time = time.time() - start_time

            # Auto-generate reasoning if the agent didn't provide one
            if agent_result.reasoning is None and agent_result.success:
                agent_result.reasoning = self._infer_reasoning(agent_result, context)

            self.logger.info(
                f"{self.name} agent completed in {agent_result.execution_time:.2f}s"
            )
            return agent_result
        except asyncio.CancelledError:
            self.status = AgentStatus.CANCELLED
            self.logger.warning(f"{self.name} agent cancelled")
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=["Agent execution cancelled"],
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.logger.error(f"{self.name} agent failed: {e}")
            return AgentResult(
                success=False,
                agent_name=self.name,
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )

    def _infer_reasoning(self, result: AgentResult, context: Dict[str, Any]) -> AgentReasoning:
        """Infer reasoning from agent result data when not explicitly provided."""
        agent_id = self.__class__.__name__.replace("Agent", "").lower()
        cost_profile = context.get("cost_profile", "balanced")
        model = self.get_model(context)

        goal = f"Execute {self.name} stage of the pipeline"
        approach = f"Used model {model} with {cost_profile} cost profile"
        decisions = []
        constraints = []

        # Extract meaningful decisions from result data
        data = result.data or {}
        if "project_type" in data or "detected_project_type" in data:
            pt = data.get("project_type") or data.get("detected_project_type")
            decisions.append({"decision": f"Classified as {pt}", "reason": "Based on brief analysis"})
        if "tech_stack" in data:
            decisions.append({"decision": "Selected tech stack", "reason": "Matched project requirements"})
        if "files" in data or "generated_files" in data:
            fc = len(data.get("files") or data.get("generated_files") or [])
            decisions.append({"decision": f"Generated {fc} files", "reason": "Based on architecture spec"})
        if data.get("auto_fixes_applied"):
            decisions.append({"decision": f"Applied {len(data['auto_fixes_applied'])} auto-fixes", "reason": "Resolved automatically fixable issues"})
        if "score" in data or "quality_score" in data:
            s = data.get("score") or data.get("quality_score")
            decisions.append({"decision": f"Quality score: {s}", "reason": "Evaluated against quality criteria"})

        if result.warnings:
            constraints = [f"Warning: {w}" for w in result.warnings[:3]]

        confidence = 0.85 if result.success and not result.warnings else 0.65

        return AgentReasoning(
            goal=goal,
            approach=approach,
            key_decisions=decisions,
            alternatives_considered=[],
            confidence=confidence,
            constraints=constraints,
        )

    async def call_llm(
        self,
        prompt: str,
        model: str = "anthropic/claude-3-haiku",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Call the LLM via OpenRouter API with automatic retry and circuit breaker.

        Three layers of fault tolerance:
        1. Exponential backoff retries for transient HTTP errors (429, 502, 503, 504)
        2. Circuit breaker that fails-fast when a provider is consistently failing
        3. Graceful error responses (never raises, always returns a dict)

        Returns dict with: content, prompt_tokens, completion_tokens, total_tokens, cost, duration_ms
        """
        import httpx
        import time
        from utils.retry import (
            llm_circuit_breaker,
            is_retryable_status,
            _backoff_delay,
            RETRYABLE_EXCEPTIONS,
        )

        MAX_RETRIES = 3
        BASE_DELAY = 2.0
        MAX_DELAY = 60.0

        api_key = self.settings.openrouter_api_key
        if not api_key:
            self.logger.warning("OpenRouter API key not configured, returning mock response")
            return {
                "content": f"Mock response for: {prompt[:100]}...",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "duration_ms": 0,
            }

        provider = model.split("/")[0] if "/" in model else "unknown"

        # Layer 3: Circuit breaker — fail fast if provider is down
        if llm_circuit_breaker.is_open(provider):
            self.logger.warning(f"Circuit breaker OPEN for {provider} — failing fast")
            return {
                "content": f"Error: Service temporarily unavailable ({provider})",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "duration_ms": 0,
                "error": f"circuit_breaker_open:{provider}",
            }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        last_error = None

        # Layer 1: Exponential backoff retries for transient errors
        for attempt in range(MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://ai-dev-agency.local",
                            "X-Title": "AI Dev Agency",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                        },
                        timeout=120.0,
                    )

                    duration_ms = int((time.time() - start_time) * 1000)

                    if response.status_code != 200:
                        from utils.error_classifier import classify_error, ResolutionStrategy

                        error_text = response.text
                        classified = classify_error(
                            error_text,
                            status_code=response.status_code,
                            model=model,
                        )
                        last_error = f"API returned {response.status_code}"

                        # Route based on classified error strategy
                        if classified.should_retry and attempt < MAX_RETRIES:
                            delay = classified.retry_delay or _backoff_delay(attempt, BASE_DELAY, MAX_DELAY)

                            # For rate limits, respect Retry-After header
                            retry_after = response.headers.get("retry-after")
                            if retry_after and response.status_code == 429:
                                try:
                                    delay = max(delay, float(retry_after))
                                except ValueError:
                                    pass

                            # Model fallback: swap to alternate model on next attempt
                            if classified.strategy == ResolutionStrategy.FALLBACK_MODEL and classified.fallback_model:
                                model = classified.fallback_model
                                provider = model.split("/")[0]
                                self.logger.warning(
                                    f"Falling back to {model} after {classified.category.value} error"
                                )
                                # Update the request payload for next attempt
                                messages  # messages already set, model var is updated

                            self.logger.warning(
                                f"LLM API {response.status_code} [{classified.category.value}], "
                                f"retrying in {delay:.1f}s "
                                f"(attempt {attempt + 1}/{MAX_RETRIES + 1}, model={model})"
                            )
                            llm_circuit_breaker.record_failure(provider)
                            await asyncio.sleep(delay)
                            continue

                        # Non-retryable or retries exhausted
                        self.logger.error(
                            f"LLM API error [{classified.category.value}]: "
                            f"{response.status_code} - {error_text[:200]}"
                        )
                        llm_circuit_breaker.record_failure(provider)
                        return {
                            "content": f"Error: {classified.user_message}",
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                            "cost": 0.0,
                            "duration_ms": duration_ms,
                            "error": error_text,
                            "error_category": classified.category.value,
                            "error_strategy": classified.strategy.value,
                        }

                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})

                    # Success — record with circuit breaker and return
                    llm_circuit_breaker.record_success(provider)

                    if attempt > 0:
                        self.logger.info(f"LLM call succeeded after {attempt + 1} attempts (model={model})")

                    return {
                        "content": content,
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                        "cost": self._calculate_cost(model, usage),
                        "duration_ms": duration_ms,
                    }

            except RETRYABLE_EXCEPTIONS as e:
                last_error = str(e)
                llm_circuit_breaker.record_failure(provider)
                if attempt < MAX_RETRIES:
                    delay = _backoff_delay(attempt, BASE_DELAY, MAX_DELAY)
                    self.logger.warning(
                        f"LLM call failed ({type(e).__name__}: {e}), retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES + 1}, model={model})"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"LLM call failed after {MAX_RETRIES + 1} attempts: {e}")

            except Exception as e:
                # Non-retryable exception — fail immediately
                self.logger.error(f"LLM call failed (non-retryable): {e}")
                llm_circuit_breaker.record_failure(provider)
                return {
                    "content": f"Error: {str(e)}",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "error": str(e),
                }

        # All retries exhausted
        return {
            "content": f"Error: Exhausted {MAX_RETRIES + 1} retries. Last error: {last_error}",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
            "duration_ms": int((time.time() - start_time) * 1000),
            "error": f"retries_exhausted:{last_error}",
        }
    
    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """Calculate cost based on model and token usage."""
        # Approximate costs per 1K tokens (input/output)
        MODEL_COSTS = {
            "anthropic/claude-3-haiku": (0.00025, 0.00125),
            "anthropic/claude-3-sonnet": (0.003, 0.015),
            "anthropic/claude-3-opus": (0.015, 0.075),
            "openai/gpt-4-turbo": (0.01, 0.03),
            "openai/gpt-4o": (0.005, 0.015),
            "openai/gpt-3.5-turbo": (0.0005, 0.0015),
            "deepseek/deepseek-coder": (0.0001, 0.0002),
            "deepseek/deepseek-chat": (0.00014, 0.00028),
        }
        
        input_cost, output_cost = MODEL_COSTS.get(model, (0.001, 0.002))
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        return (prompt_tokens * input_cost + completion_tokens * output_cost) / 1000

    async def log_execution(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
        duration_ms: int = 0,
    ) -> None:
        """Log agent execution details."""
        self.logger.info(
            f"Execution complete: model={model}, tokens={prompt_tokens+completion_tokens}, "
            f"cost=${cost:.4f}, duration={duration_ms}ms"
        )

    def run_docker_container(
        self,
        image: str,
        command: Optional[Union[str, List[str]]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        environment: Optional[Dict[str, str]] = None,
        network: Optional[str] = None,
        remove: bool = True,
        timeout: int = 300,
    ) -> tuple[int, str, str]:
        """Run a Docker container and return exit code, stdout, stderr."""
        if self.use_docker_sdk:
            return self._run_docker_sdk(
                image, command, volumes, environment, network, remove, timeout
            )
        else:
            return self._run_subprocess(
                image, command, volumes, environment, timeout
            )

    def _run_docker_sdk(
        self,
        image: str,
        command: Optional[Union[str, List[str]]],
        volumes: Optional[Dict[str, Dict[str, str]]],
        environment: Optional[Dict[str, str]],
        network: Optional[str],
        remove: bool,
        timeout: int,
    ) -> tuple[int, str, str]:
        """Run container using Docker SDK."""
        try:
            # Pull image if not available
            try:
                self.docker_client.images.get(image)
            except docker.errors.ImageNotFound:
                self.logger.info(f"Pulling image: {image}")
                self.docker_client.images.pull(image)

            # Run container
            container = self.docker_client.containers.run(
                image=image,
                command=command,
                volumes=volumes,
                environment=environment,
                network=network,
                remove=False,
                detach=True,
            )

            try:
                result = container.wait(timeout=timeout)
                exit_code = result.get("StatusCode", 1)
                logs = container.logs(stdout=True, stderr=True).decode("utf-8")
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8")
            finally:
                if remove:
                    try:
                        container.remove(force=True)
                    except:
                        pass

            return exit_code, stdout, stderr
        except Exception as e:
            self.logger.error(f"Docker SDK error: {e}")
            return 1, "", str(e)

    def _run_subprocess(
        self,
        image: str,
        command: Optional[Union[str, List[str]]],
        volumes: Optional[Dict[str, Dict[str, str]]],
        environment: Optional[Dict[str, str]],
        timeout: int,
    ) -> tuple[int, str, str]:
        """Run container using subprocess (fallback)."""
        cmd = ["docker", "run", "--rm"]

        if volumes:
            for host_path, config in volumes.items():
                bind = config.get("bind", host_path)
                mode = config.get("mode", "rw")
                cmd.extend(["-v", f"{host_path}:{bind}:{mode}"])

        if environment:
            for key, value in environment.items():
                cmd.extend(["-e", f"{key}={value}"])

        cmd.append(image)

        if command:
            if isinstance(command, str):
                cmd.extend(command.split())
            else:
                cmd.extend(command)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Container execution timed out"
        except Exception as e:
            return 1, "", str(e)

    def read_file(self, path: str) -> Optional[str]:
        """Read file contents."""
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {path}: {e}")
            return None

    def write_file(self, path: str, content: str) -> bool:
        """Write content to file."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            return True
        except Exception as e:
            self.logger.error(f"Failed to write file {path}: {e}")
            return False

    # Phase 11B: Knowledge Base Integration
    
    async def query_knowledge(
        self,
        db: "Session",
        context: Dict[str, Any],
        limit: int = 5,
    ) -> List["KnowledgeQueryResult"]:
        """
        Query the knowledge base for relevant information before starting work.
        
        Args:
            db: Database session
            context: Agent context with project info
            limit: Maximum results to return
            
        Returns:
            List of relevant knowledge entries
        """
        try:
            from knowledge.base import get_relevant_knowledge
            
            results = await get_relevant_knowledge(
                db=db,
                agent_name=self.name,
                context=context,
                limit=limit,
            )
            
            if results:
                self.logger.info(f"Found {len(results)} relevant knowledge entries")
            
            return results
        except Exception as e:
            self.logger.warning(f"Failed to query knowledge base: {e}")
            return []
    
    def format_knowledge_context(
        self,
        knowledge_results: List["KnowledgeQueryResult"],
    ) -> str:
        """
        Format knowledge results into a context string for LLM prompts.
        
        Args:
            knowledge_results: List of knowledge query results
            
        Returns:
            Formatted string with relevant knowledge
        """
        if not knowledge_results:
            return ""
        
        sections = ["## Relevant Knowledge from Past Projects\n"]
        
        for result in knowledge_results:
            entry = result.entry
            sections.append(f"### {entry.title}")
            sections.append(f"Type: {entry.entry_type.value}")
            if entry.quality_score:
                sections.append(f"Quality: {entry.quality_score:.0%}")
            sections.append(f"\n{entry.content}\n")
        
        return "\n".join(sections)

    # ── Integration Key Helpers ───────────────────────────────────────────────

    @staticmethod
    def get_integration_key(env_key: str, required: bool = False) -> Optional[str]:
        """Get an integration key, checking the UI store first then env vars.

        Args:
            env_key: The environment variable name (e.g. ``GITHUB_TOKEN``).
            required: If ``True``, log a warning when the key is missing.

        Returns:
            The key value, or ``None`` if not configured.
        """
        try:
            from api.routes.integrations import get_integration_value
            value = get_integration_value(env_key)
        except Exception:
            value = os.environ.get(env_key) or None

        if not value and required:
            logging.getLogger("agents.base").warning(
                f"Integration key {env_key} is not configured — "
                "the agent will skip features that depend on it"
            )
        return value
