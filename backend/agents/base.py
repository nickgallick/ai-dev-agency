"""Base Agent class for all AI Dev Agency agents."""

import asyncio
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

try:
    import docker
    DOCKER_SDK_AVAILABLE = True
except ImportError:
    DOCKER_SDK_AVAILABLE = False

from ..config.settings import Settings


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
            self.status = AgentStatus.COMPLETED if result.success else AgentStatus.FAILED
            result.execution_time = time.time() - start_time
            self.logger.info(
                f"{self.name} agent completed in {result.execution_time:.2f}s"
            )
            return result
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
