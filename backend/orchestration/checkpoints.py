"""
Phase 11C: Mid-Build Intervention - Checkpoint System

Allows pausing, resuming, editing, and replaying agent execution
at configurable checkpoints during the build process.

Modes:
- auto: No checkpoints, runs to completion
- supervised: Pauses at key points (Research, Architect, CodeGen)
- manual: User-defined checkpoints
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum
import asyncio
import json

from sqlalchemy.orm import Session
from models.project import Project
from config.settings import get_settings


class CheckpointMode(str, Enum):
    AUTO = "auto"
    SUPERVISED = "supervised"
    MANUAL = "manual"


class CheckpointState(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_USER = "waiting_user"
    EDITING = "editing"
    RESUMING = "resuming"


# Default checkpoint agents for supervised mode
DEFAULT_CHECKPOINTS = [
    "research",
    "architect",
    "code_generation",  # After v0 or OpenHands
]

# Auto-continue timeout in seconds (5 minutes)
AUTO_CONTINUE_TIMEOUT = 300


class CheckpointData:
    """Represents a checkpoint's state at a specific point"""
    
    def __init__(
        self,
        agent_name: str,
        output_data: Dict[str, Any],
        timestamp: datetime,
        pipeline_state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.agent_name = agent_name
        self.output_data = output_data
        self.timestamp = timestamp
        self.pipeline_state = pipeline_state
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "output_data": self.output_data,
            "timestamp": self.timestamp.isoformat(),
            "pipeline_state": self.pipeline_state,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointData":
        return cls(
            agent_name=data["agent_name"],
            output_data=data["output_data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            pipeline_state=data["pipeline_state"],
            metadata=data.get("metadata", {})
        )


class CheckpointManager:
    """
    Manages checkpoint creation, storage, and resume functionality
    for project builds.
    """
    
    def __init__(self, db: Session, project_id: str):
        self.db = db
        self.project_id = project_id
        self._project: Optional[Project] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start in non-paused state
        self._auto_continue_task: Optional[asyncio.Task] = None
    
    @property
    def project(self) -> Project:
        if self._project is None:
            self._project = self.db.query(Project).filter(
                Project.id == self.project_id
            ).first()
        return self._project
    
    def get_mode(self) -> CheckpointMode:
        """Get the checkpoint mode for this project"""
        mode = self.project.checkpoint_mode if self.project else "auto"
        return CheckpointMode(mode) if mode else CheckpointMode.AUTO
    
    def get_state(self) -> CheckpointState:
        """Get current checkpoint state"""
        state = self.project.checkpoint_state or {}
        return CheckpointState(state.get("status", "running"))
    
    def should_pause_at(self, agent_name: str) -> bool:
        """
        Determine if execution should pause at this agent.
        
        Args:
            agent_name: Name of the agent that just completed
            
        Returns:
            True if should pause, False otherwise
        """
        mode = self.get_mode()
        
        if mode == CheckpointMode.AUTO:
            return False
        
        if mode == CheckpointMode.SUPERVISED:
            return agent_name.lower() in [cp.lower() for cp in DEFAULT_CHECKPOINTS]
        
        if mode == CheckpointMode.MANUAL:
            # Check user-defined checkpoints
            state = self.project.checkpoint_state or {}
            custom_checkpoints = state.get("custom_checkpoints", [])
            return agent_name.lower() in [cp.lower() for cp in custom_checkpoints]
        
        return False
    
    async def pause_at_checkpoint(
        self,
        agent_name: str,
        agent_output: Dict[str, Any],
        pipeline_state: Dict[str, Any]
    ) -> CheckpointData:
        """
        Pause execution at a checkpoint.
        
        Args:
            agent_name: Name of the agent that triggered checkpoint
            agent_output: The output from the agent
            pipeline_state: Current state of the entire pipeline
            
        Returns:
            CheckpointData object representing this checkpoint
        """
        checkpoint = CheckpointData(
            agent_name=agent_name,
            output_data=agent_output,
            timestamp=datetime.utcnow(),
            pipeline_state=pipeline_state,
            metadata={
                "project_id": self.project_id,
                "mode": self.get_mode().value
            }
        )
        
        # Save checkpoint to project
        self._save_checkpoint(checkpoint)
        
        # Update project state
        self.project.checkpoint_state = {
            "status": CheckpointState.PAUSED.value,
            "paused_at_agent": agent_name,
            "paused_timestamp": datetime.utcnow().isoformat(),
            "checkpoint_data": checkpoint.to_dict(),
            "custom_checkpoints": self.project.checkpoint_state.get("custom_checkpoints", []) if self.project.checkpoint_state else []
        }
        self.project.paused_at = datetime.utcnow()
        self.db.commit()
        
        # Clear the event (pause execution)
        self._pause_event.clear()
        
        # Start auto-continue timer
        self._start_auto_continue_timer()
        
        # Wait until resumed
        await self._pause_event.wait()
        
        return checkpoint
    
    def _save_checkpoint(self, checkpoint: CheckpointData):
        """Save checkpoint to history"""
        state = self.project.checkpoint_state or {}
        history = state.get("checkpoint_history", [])
        history.append(checkpoint.to_dict())
        
        # Keep only last 10 checkpoints
        if len(history) > 10:
            history = history[-10:]
        
        state["checkpoint_history"] = history
        self.project.checkpoint_state = state
        self.db.commit()
    
    def _start_auto_continue_timer(self):
        """Start timer for auto-continue after timeout"""
        if self._auto_continue_task:
            self._auto_continue_task.cancel()
        
        async def auto_continue():
            await asyncio.sleep(AUTO_CONTINUE_TIMEOUT)
            if not self._pause_event.is_set():
                self.resume_from_checkpoint()
        
        self._auto_continue_task = asyncio.create_task(auto_continue())
    
    def resume_from_checkpoint(self, edited_output: Optional[Dict[str, Any]] = None):
        """
        Resume execution from the current checkpoint.
        
        Args:
            edited_output: Optional modified agent output to use instead of original
        """
        if self._auto_continue_task:
            self._auto_continue_task.cancel()
            self._auto_continue_task = None
        
        state = self.project.checkpoint_state or {}
        
        if edited_output:
            # Store edited output for the pipeline to use
            checkpoint_data = state.get("checkpoint_data", {})
            checkpoint_data["output_data"] = edited_output
            checkpoint_data["edited"] = True
            checkpoint_data["edited_at"] = datetime.utcnow().isoformat()
            state["checkpoint_data"] = checkpoint_data
        
        state["status"] = CheckpointState.RESUMING.value
        state["resumed_at"] = datetime.utcnow().isoformat()
        
        self.project.checkpoint_state = state
        self.project.paused_at = None
        self.db.commit()
        
        # Set the event (resume execution)
        self._pause_event.set()
    
    def edit_and_replay(
        self,
        edited_output: Dict[str, Any],
        replay_from_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Edit checkpoint output and optionally replay from a different agent.
        
        Args:
            edited_output: Modified agent output
            replay_from_agent: Agent to restart from (defaults to current checkpoint)
            
        Returns:
            Updated pipeline configuration
        """
        state = self.project.checkpoint_state or {}
        
        # Mark as editing
        state["status"] = CheckpointState.EDITING.value
        state["editing_started"] = datetime.utcnow().isoformat()
        
        checkpoint_data = state.get("checkpoint_data", {})
        original_agent = checkpoint_data.get("agent_name")
        
        # If replaying from a different agent, clear downstream results
        if replay_from_agent and replay_from_agent != original_agent:
            state["replay_from"] = replay_from_agent
            state["clear_downstream"] = True
        
        # Store edited output
        checkpoint_data["edited_output"] = edited_output
        checkpoint_data["original_output"] = checkpoint_data.get("output_data")
        state["checkpoint_data"] = checkpoint_data
        
        self.project.checkpoint_state = state
        self.db.commit()
        
        return {
            "status": "editing",
            "replay_from": replay_from_agent or original_agent,
            "edited": True
        }
    
    def restart_from_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Abort current execution and restart from a specific agent.
        
        Args:
            agent_name: Agent to restart from
            
        Returns:
            Restart configuration
        """
        state = self.project.checkpoint_state or {}
        
        # Get checkpoint history to find state before this agent
        history = state.get("checkpoint_history", [])
        restart_state = None
        
        for checkpoint in reversed(history):
            if checkpoint["agent_name"].lower() == agent_name.lower():
                restart_state = checkpoint["pipeline_state"]
                break
        
        # Update project state
        state["status"] = CheckpointState.RESUMING.value
        state["restart_from"] = agent_name
        state["restart_timestamp"] = datetime.utcnow().isoformat()
        
        if restart_state:
            state["restart_pipeline_state"] = restart_state
        
        self.project.checkpoint_state = state
        self.project.paused_at = None
        self.db.commit()
        
        # Resume execution
        self._pause_event.set()
        
        return {
            "status": "restarting",
            "restart_from": agent_name,
            "has_previous_state": restart_state is not None
        }
    
    def get_checkpoint_history(self) -> List[Dict[str, Any]]:
        """Get all checkpoint history for this project"""
        state = self.project.checkpoint_state or {}
        return state.get("checkpoint_history", [])
    
    def get_current_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Get current checkpoint data if paused"""
        if self.get_state() != CheckpointState.PAUSED:
            return None
        
        state = self.project.checkpoint_state or {}
        return state.get("checkpoint_data")
    
    def set_custom_checkpoints(self, agent_names: List[str]):
        """Set custom checkpoint agents for manual mode"""
        state = self.project.checkpoint_state or {}
        state["custom_checkpoints"] = agent_names
        self.project.checkpoint_state = state
        self.db.commit()
    
    def clear_checkpoints(self):
        """Clear all checkpoint data"""
        self.project.checkpoint_state = {
            "status": CheckpointState.RUNNING.value,
            "checkpoint_history": [],
            "custom_checkpoints": []
        }
        self.project.paused_at = None
        self.db.commit()
        self._pause_event.set()


def get_checkpoint_manager(db: Session, project_id: str) -> CheckpointManager:
    """Factory function to get a CheckpointManager instance"""
    return CheckpointManager(db, project_id)
