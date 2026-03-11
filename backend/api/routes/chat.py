"""Conversational Clarification System — Pre-Build Chat & Mid-Pipeline Interrupts.

Endpoints:
- POST /api/chat              — Send a message in a pre-build conversation
- POST /api/chat/start-build  — Convert conversation into structured brief and start pipeline
- GET  /api/chat/{conv_id}    — Get conversation history
- POST /api/chat/interrupt/{project_id}/answer — Answer a mid-pipeline clarification question
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import get_db, PreBuildConversation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Request / Response models ─────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    conversation_id: str
    role: str
    message: str
    ready_to_build: bool
    suggestions: List[str] = []


class StartBuildRequest(BaseModel):
    conversation_id: str
    project_type: Optional[str] = None
    cost_profile: str = "balanced"
    name: Optional[str] = None


class StartBuildResponse(BaseModel):
    project_id: str
    brief: str
    name: Optional[str] = None


class InterruptAnswerRequest(BaseModel):
    answer: str


# ── System prompt for pre-build chat ──────────────────────────────────

PRE_BUILD_SYSTEM_PROMPT = """You are an expert software project requirements analyst for an AI development agency.
Your role is to have a brief, focused conversation with the user to clarify their project idea
before an automated 20-agent pipeline builds it.

Guidelines:
- Be concise. Ask 1-3 targeted clarifying questions per response.
- Focus on the most impactful gaps: what the app does, who uses it, core features, design preferences.
- Don't ask about things that can be reasonably inferred or defaulted.
- After 2-4 exchanges (or sooner if the brief is already clear), indicate you have enough to proceed.
- Always respond with valid JSON in this format:
{
  "response": "Your conversational message to the user",
  "ready_to_build": true/false,
  "missing_dimensions": ["list of still-unclear aspects"],
  "detected": {
    "project_type": "web_simple|web_complex|mobile_cross_platform|...|null",
    "features": ["detected features"],
    "pages": ["detected pages"],
    "industry": "detected industry or null"
  }
}

If ready_to_build is true, include a "structured_brief" field with a comprehensive summary
that can be passed directly to the pipeline as the project brief.
"""


# ── Helpers ───────────────────────────────────────────────────────────

def _build_llm_messages(history: List[PreBuildConversation]) -> List[Dict[str, str]]:
    """Convert conversation history into LLM message format."""
    messages = []
    for msg in history:
        messages.append({"role": msg.role, "content": msg.message})
    return messages


async def _call_chat_llm(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Call LLM for pre-build chat using a cheap model via OpenRouter."""
    import httpx
    from config.settings import get_settings

    settings = get_settings()
    api_key = settings.openrouter_api_key

    if not api_key:
        # Return a mock response when no API key is configured
        return {
            "response": "I'd love to help clarify your project! Could you tell me more about: 1) Who will use this? 2) What are the 3 most important features? 3) Any design preferences?",
            "ready_to_build": False,
            "missing_dimensions": ["audience", "features", "design"],
            "detected": {"project_type": None, "features": [], "pages": [], "industry": None},
        }

    llm_messages = [{"role": "system", "content": PRE_BUILD_SYSTEM_PROMPT}] + messages

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://ai-dev-agency.local",
                    "X-Title": "AI Dev Agency - Pre-Build Chat",
                },
                json={
                    "model": "anthropic/claude-3-haiku",
                    "messages": llm_messages,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                },
                timeout=60.0,
            )
            if resp.status_code != 200:
                logger.error(f"Chat LLM error: {resp.status_code} {resp.text[:200]}")
                return {
                    "response": "I'm having trouble connecting right now. Please try again or click 'Start Build' to proceed with what you have.",
                    "ready_to_build": False,
                    "missing_dimensions": [],
                    "detected": {},
                }

            content = resp.json()["choices"][0]["message"]["content"]

            # Parse JSON from response (handle markdown code blocks)
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            return json.loads(content)
    except json.JSONDecodeError:
        # If LLM didn't return valid JSON, wrap the raw text
        return {
            "response": content if 'content' in dir() else "Could you tell me more about your project?",
            "ready_to_build": False,
            "missing_dimensions": [],
            "detected": {},
        }
    except Exception as e:
        logger.error(f"Chat LLM call failed: {e}")
        return {
            "response": "I'm having trouble connecting. You can click 'Start Build' to proceed with your current description.",
            "ready_to_build": False,
            "missing_dimensions": [],
            "detected": {},
        }


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/", response_model=ChatMessageResponse)
async def send_chat_message(req: ChatMessageRequest, db: Session = Depends(get_db)):
    """Send a message in a pre-build clarification conversation."""

    conv_id = req.conversation_id or str(uuid.uuid4())[:12]

    # Save user message
    user_msg = PreBuildConversation(
        conversation_id=conv_id,
        role="user",
        message=req.message,
    )
    db.add(user_msg)
    db.commit()

    # Get full conversation history
    history = (
        db.query(PreBuildConversation)
        .filter(PreBuildConversation.conversation_id == conv_id)
        .order_by(PreBuildConversation.timestamp)
        .all()
    )

    # Build messages and call LLM
    llm_messages = _build_llm_messages(history)
    ai_result = await _call_chat_llm(llm_messages)

    response_text = ai_result.get("response", "Could you tell me more?")
    ready = ai_result.get("ready_to_build", False)
    missing = ai_result.get("missing_dimensions", [])

    # Save assistant message
    ai_msg = PreBuildConversation(
        conversation_id=conv_id,
        role="assistant",
        message=response_text,
        ready_to_build=ready,
        metadata_=ai_result.get("detected"),
    )
    db.add(ai_msg)
    db.commit()

    return ChatMessageResponse(
        conversation_id=conv_id,
        role="assistant",
        message=response_text,
        ready_to_build=ready,
        suggestions=missing,
    )


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get the full conversation history."""
    messages = (
        db.query(PreBuildConversation)
        .filter(PreBuildConversation.conversation_id == conversation_id)
        .order_by(PreBuildConversation.timestamp)
        .all()
    )
    return [
        {
            "role": m.role,
            "message": m.message,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            "ready_to_build": m.ready_to_build,
        }
        for m in messages
    ]


@router.post("/start-build", response_model=StartBuildResponse)
async def start_build_from_conversation(req: StartBuildRequest, db: Session = Depends(get_db)):
    """Convert a pre-build conversation into a structured brief and create a project."""
    from api.projects import _create_project_record

    # Get all conversation messages
    messages = (
        db.query(PreBuildConversation)
        .filter(PreBuildConversation.conversation_id == req.conversation_id)
        .order_by(PreBuildConversation.timestamp)
        .all()
    )

    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Build the brief from conversation
    # Use the last assistant message's structured_brief if available, or synthesize
    brief_parts = []
    detected_type = req.project_type
    detected_features = []
    detected_pages = []
    detected_industry = None

    for msg in messages:
        if msg.role == "user":
            brief_parts.append(msg.message)
        if msg.metadata_:
            meta = msg.metadata_
            if meta.get("project_type") and not detected_type:
                detected_type = meta["project_type"]
            if meta.get("features"):
                detected_features = meta["features"]
            if meta.get("pages"):
                detected_pages = meta["pages"]
            if meta.get("industry"):
                detected_industry = meta["industry"]

    # Check if the last assistant message had a structured_brief
    last_ai = [m for m in messages if m.role == "assistant"]
    structured_brief = None
    if last_ai and last_ai[-1].metadata_:
        structured_brief = last_ai[-1].metadata_.get("structured_brief")

    # Use structured brief if available, otherwise combine user messages
    final_brief = structured_brief or "\n\n".join(brief_parts)

    # Build requirements
    requirements = {
        "project_type": detected_type or "web_simple",
        "features": detected_features,
        "pages": detected_pages,
        "industry": detected_industry,
        "conversation_id": req.conversation_id,
    }

    # Create project via the existing project creation logic
    from models.project import Project, ProjectStatus, CostProfile
    import uuid as uuid_module

    project_name = req.name or f"Project from chat {req.conversation_id[:8]}"

    project = Project(
        id=uuid_module.uuid4(),
        brief=final_brief,
        name=project_name,
        status=ProjectStatus.QUEUED,
        cost_profile=CostProfile(req.cost_profile) if req.cost_profile in [e.value for e in CostProfile] else CostProfile.BALANCED,
        project_type=detected_type or "web_simple",
        requirements=requirements,
    )
    db.add(project)
    db.commit()

    # Enqueue the project
    try:
        from task_queue.manager import enqueue_project
        enqueue_project(str(project.id))
    except Exception as e:
        logger.warning(f"Failed to enqueue project: {e}")

    return StartBuildResponse(
        project_id=str(project.id),
        brief=final_brief,
        name=project_name,
    )


@router.post("/interrupt/{project_id}/answer")
async def answer_interrupt(
    project_id: str,
    req: InterruptAnswerRequest,
    db: Session = Depends(get_db),
):
    """Answer a mid-pipeline clarification question from an agent."""
    from models.project import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    state = project.checkpoint_state or {}
    if state.get("status") != "waiting_clarification":
        raise HTTPException(status_code=400, detail="No pending clarification question")

    # Store the answer and mark as answered
    state["clarification_answer"] = req.answer
    state["clarification_answered_at"] = datetime.utcnow().isoformat()
    state["status"] = "resuming"

    project.checkpoint_state = state
    project.paused_at = None
    db.commit()

    # Emit activity event so frontend knows
    try:
        from api.activity import emit_activity
        agent_name = state.get("clarification_agent", "unknown")
        emit_activity(
            project_id=project_id,
            event_type="clarification_answered",
            message=f"Clarification answered — resuming {agent_name.replace('_', ' ').title()}",
            agent_name=agent_name,
            details={"answer": req.answer},
        )
    except Exception:
        pass

    return {"status": "resumed", "project_id": project_id}


@router.get("/interrupt/{project_id}/status")
async def get_interrupt_status(project_id: str, db: Session = Depends(get_db)):
    """Check if a project has a pending clarification question."""
    from models.project import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    state = project.checkpoint_state or {}
    if state.get("status") == "waiting_clarification":
        return {
            "has_question": True,
            "question": state.get("clarification_question", ""),
            "context": state.get("clarification_context", ""),
            "agent_name": state.get("clarification_agent", ""),
            "asked_at": state.get("clarification_asked_at"),
        }

    return {"has_question": False}
