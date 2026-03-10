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


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "agent_name": self.agent_name,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
        }


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
            else:
                # Unexpected return type
                agent_result = AgentResult(
                    success=True,
                    agent_name=self.name,
                    data={"result": result} if result else {},
                )
            
            self.status = AgentStatus.COMPLETED if agent_result.success else AgentStatus.FAILED
            agent_result.execution_time = time.time() - start_time
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

    async def call_llm(
        self,
        prompt: str,
        model: str = "anthropic/claude-3-haiku",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Call the LLM via OpenRouter API.
        
        Returns dict with: content, prompt_tokens, completion_tokens, total_tokens, cost, duration_ms
        """
        import httpx
        import time
        
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
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        
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
                    self.logger.error(f"LLM API error: {response.status_code} - {response.text}")
                    return {
                        "content": f"Error: API returned {response.status_code}",
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost": 0.0,
                        "duration_ms": duration_ms,
                        "error": response.text,
                    }
                
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                
                return {
                    "content": content,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "cost": self._calculate_cost(model, usage),
                    "duration_ms": duration_ms,
                }
                
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return {
                "content": f"Error: {str(e)}",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "duration_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
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
