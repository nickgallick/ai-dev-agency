"""Real-time activity streaming API for pipeline progress.

This module provides Server-Sent Events (SSE) for real-time updates during
pipeline execution, so users can see exactly what's happening:
- Current agent and action ("Intake Agent: Analyzing requirements...")
- Sub-steps and progress
- Logs as they happen
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional, List
from collections import defaultdict
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activity", tags=["activity"])


# ============ In-Memory Activity Store ============
# In production, use Redis for multi-instance support

class ActivityEvent(BaseModel):
    """A single activity event."""
    id: str
    project_id: str
    timestamp: datetime
    event_type: str  # "agent_start", "agent_thinking", "agent_progress", "agent_complete", "agent_error", "log"
    agent_name: Optional[str] = None
    agent_display_name: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    progress: Optional[float] = None  # 0-100


# Store activity events per project (in-memory, last 100 events)
_activity_store: Dict[str, List[ActivityEvent]] = defaultdict(list)
_activity_subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)

# Agent display names and emojis
AGENT_INFO = {
    "intake": ("🎯 Intake Agent", "Analyzing project requirements"),
    "research": ("🔍 Research Agent", "Researching design inspiration & best practices"),
    "architect": ("🏗️ Architect Agent", "Planning application structure"),
    "design_system": ("🎨 Design System Agent", "Creating design tokens & theme"),
    "asset_generation": ("🖼️ Asset Generator", "Creating visual assets"),
    "content_generation": ("✍️ Content Agent", "Generating copy & content"),
    "pm_checkpoint_1": ("📋 PM Checkpoint 1", "Validating coherence"),
    "code_generation": ("💻 Code Generator", "Generating application code"),
    "pm_checkpoint_2": ("📋 PM Checkpoint 2", "Validating completeness"),
    "code_review": ("🔎 Code Review Agent", "Reviewing code quality"),
    "security": ("🔒 Security Agent", "Scanning for vulnerabilities"),
    "seo": ("📈 SEO Agent", "Optimizing for search engines"),
    "accessibility": ("♿ Accessibility Agent", "Checking WCAG compliance"),
    "qa": ("🧪 QA Agent", "Running automated tests"),
    "deployment": ("🚀 Deployment Agent", "Deploying to production"),
    "post_deploy_verification": ("✅ Verification Agent", "Verifying deployment"),
    "analytics_monitoring": ("📊 Analytics Agent", "Setting up monitoring"),
    "coding_standards": ("📝 Standards Agent", "Generating documentation"),
    "delivery": ("📦 Delivery Agent", "Preparing delivery package"),
}


def emit_activity(
    project_id: str,
    event_type: str,
    message: str,
    agent_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    progress: Optional[float] = None,
):
    """Emit an activity event to all subscribers."""
    agent_info = AGENT_INFO.get(agent_name, (agent_name, "")) if agent_name else (None, "")
    
    event = ActivityEvent(
        id=str(uuid.uuid4()),
        project_id=project_id,
        timestamp=datetime.utcnow(),
        event_type=event_type,
        agent_name=agent_name,
        agent_display_name=agent_info[0] if agent_name else None,
        message=message,
        details=details,
        progress=progress,
    )
    
    # Store event (keep last 100)
    _activity_store[project_id].append(event)
    if len(_activity_store[project_id]) > 100:
        _activity_store[project_id] = _activity_store[project_id][-100:]
    
    # Notify all subscribers
    for queue in _activity_subscribers.get(project_id, []):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # Skip if queue is full
    
    logger.info(f"Activity [{project_id[:8]}]: {message}")


def get_recent_activity(project_id: str, limit: int = 50) -> List[ActivityEvent]:
    """Get recent activity events for a project."""
    return _activity_store.get(project_id, [])[-limit:]


async def subscribe_to_activity(project_id: str) -> asyncio.Queue:
    """Subscribe to activity updates for a project."""
    queue = asyncio.Queue(maxsize=100)
    _activity_subscribers[project_id].append(queue)
    return queue


def unsubscribe_from_activity(project_id: str, queue: asyncio.Queue):
    """Unsubscribe from activity updates."""
    if queue in _activity_subscribers.get(project_id, []):
        _activity_subscribers[project_id].remove(queue)


# ============ API Endpoints ============

@router.get("/{project_id}/stream")
async def stream_activity(project_id: str, request: Request):
    """
    Server-Sent Events endpoint for real-time activity streaming.
    
    Connect with EventSource in browser:
    ```javascript
    const evtSource = new EventSource('/api/activity/{project_id}/stream');
    evtSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data);
    };
    ```
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        queue = await subscribe_to_activity(project_id)
        
        try:
            # Send recent events first
            recent = get_recent_activity(project_id, 20)
            for event in recent:
                yield f"data: {event.model_dump_json()}\n\n"
            
            # Stream new events
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                try:
                    # Wait for new event with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
                    
        finally:
            unsubscribe_from_activity(project_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/{project_id}/recent")
async def get_activity(project_id: str, limit: int = 50) -> List[dict]:
    """Get recent activity events for a project."""
    events = get_recent_activity(project_id, limit)
    return [e.model_dump() for e in events]


@router.post("/{project_id}/test-emit")
async def test_emit_activity(project_id: str) -> Dict[str, Any]:
    """Test endpoint to emit sample activity events."""
    emit_activity(
        project_id, "pipeline_start",
        "🚀 Pipeline started - building your project!",
        progress=0
    )
    await asyncio.sleep(0.3)
    emit_activity(
        project_id, "agent_start",
        "Analyzing project requirements...",
        agent_name="intake",
        progress=5
    )
    await asyncio.sleep(0.3)
    emit_activity(
        project_id, "agent_thinking",
        "Understanding project scope and requirements...",
        agent_name="intake",
        progress=7
    )
    return {"success": True, "message": "Test events emitted"}


@router.get("/{project_id}/status")
async def get_pipeline_status(project_id: str) -> Dict[str, Any]:
    """Get current pipeline status summary."""
    from models import SessionLocal, Project, AgentLog
    
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": "Project not found"}
        
        # Get agent logs for status
        logs = db.query(AgentLog).filter(
            AgentLog.project_id == project_id
        ).order_by(AgentLog.timestamp.desc()).limit(20).all()
        
        # Determine current agent from logs
        current_agent = None
        completed_agents = set()
        for log in logs:
            if log.status == "completed":
                completed_agents.add(log.agent_name)
            elif log.status == "running" and not current_agent:
                current_agent = log.agent_name
        
        return {
            "project_id": project_id,
            "status": project.status.value if hasattr(project.status, 'value') else str(project.status),
            "current_agent": current_agent,
            "completed_agents": list(completed_agents),
            "total_agents": len(AGENT_INFO),
            "progress": len(completed_agents) / len(AGENT_INFO) * 100 if AGENT_INFO else 0,
        }
    finally:
        db.close()
