"""Shareable Preview Links for Stakeholder Review (#22)

Read-only signed URLs to share project output without requiring login.
Links are time-limited (default 7 days) and can be revoked.
"""
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from models.project import Project

logger = logging.getLogger(__name__)

router = APIRouter(tags=["share"])

# Signing secret — derived from SECRET_KEY
_SECRET = os.getenv("SECRET_KEY", "default-secret-key-change-in-production").encode()


# ── Models ─────────────────────────────────────────────────────────

class CreateShareLinkRequest(BaseModel):
    expires_in_days: int = Field(7, ge=1, le=90, description="Link expiry in days")
    include_outputs: bool = Field(True, description="Include agent outputs")
    include_code: bool = Field(True, description="Include generated code")
    include_qa: bool = Field(True, description="Include QA report")
    label: Optional[str] = Field(None, max_length=200, description="Optional label for this link")


class ShareLink(BaseModel):
    id: str
    project_id: str
    share_url: str
    token: str
    label: Optional[str]
    created_at: str
    expires_at: str
    include_outputs: bool
    include_code: bool
    include_qa: bool
    is_active: bool
    view_count: int


class ShareLinkList(BaseModel):
    project_id: str
    links: List[ShareLink]


# ── Token signing ──────────────────────────────────────────────────

def _sign_token(project_id: str, share_id: str, expires_at: float) -> str:
    """Create an HMAC-signed share token."""
    payload = f"{project_id}:{share_id}:{expires_at}"
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{share_id}.{sig}"


def _verify_token(project_id: str, token: str, share_data: dict) -> bool:
    """Verify share token is valid and not expired."""
    if not token or "." not in token:
        return False
    share_id, sig = token.split(".", 1)
    if share_id != share_data.get("id"):
        return False
    expires_at = share_data.get("expires_at_ts", 0)
    if time.time() > expires_at:
        return False
    expected = _sign_token(project_id, share_id, expires_at)
    return hmac.compare_digest(token, expected)


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/api/projects/{project_id}/share", response_model=ShareLink)
async def create_share_link(
    project_id: str,
    body: CreateShareLinkRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a shareable preview link for stakeholder review."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    share_id = str(uuid.uuid4())[:12]
    now = datetime.utcnow()
    expires_at = now + timedelta(days=body.expires_in_days)
    expires_ts = expires_at.timestamp()

    token = _sign_token(project_id, share_id, expires_ts)

    # Build the share URL
    base_url = str(request.base_url).rstrip("/")
    share_url = f"{base_url}/share/{project_id}?token={token}"

    share_data = {
        "id": share_id,
        "token": token,
        "label": body.label,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "expires_at_ts": expires_ts,
        "include_outputs": body.include_outputs,
        "include_code": body.include_code,
        "include_qa": body.include_qa,
        "is_active": True,
        "view_count": 0,
    }

    # Store share links in project_metadata
    metadata = dict(project.project_metadata or {})
    links = metadata.get("share_links", [])
    if not isinstance(links, list):
        links = []
    links.append(share_data)
    metadata["share_links"] = links
    project.project_metadata = metadata
    db.commit()

    return ShareLink(
        id=share_id,
        project_id=project_id,
        share_url=share_url,
        token=token,
        label=body.label,
        created_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
        include_outputs=body.include_outputs,
        include_code=body.include_code,
        include_qa=body.include_qa,
        is_active=True,
        view_count=0,
    )


@router.get("/api/projects/{project_id}/share", response_model=ShareLinkList)
async def list_share_links(
    project_id: str,
    db: Session = Depends(get_db),
):
    """List all share links for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.project_metadata or {}
    links_data = metadata.get("share_links", [])
    if not isinstance(links_data, list):
        links_data = []

    links = []
    for ld in links_data:
        links.append(ShareLink(
            id=ld["id"],
            project_id=project_id,
            share_url="",  # Not reconstructable without request
            token=ld["token"],
            label=ld.get("label"),
            created_at=ld["created_at"],
            expires_at=ld["expires_at"],
            include_outputs=ld.get("include_outputs", True),
            include_code=ld.get("include_code", True),
            include_qa=ld.get("include_qa", True),
            is_active=ld.get("is_active", True),
            view_count=ld.get("view_count", 0),
        ))

    return ShareLinkList(project_id=project_id, links=links)


@router.delete("/api/projects/{project_id}/share/{share_id}")
async def revoke_share_link(
    project_id: str,
    share_id: str,
    db: Session = Depends(get_db),
):
    """Revoke a share link."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = dict(project.project_metadata or {})
    links = metadata.get("share_links", [])
    found = False
    for link in links:
        if link["id"] == share_id:
            link["is_active"] = False
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Share link not found")

    metadata["share_links"] = links
    project.project_metadata = metadata
    db.commit()

    return {"status": "revoked", "id": share_id}


@router.get("/share/{project_id}")
async def view_shared_project(
    project_id: str,
    token: str = Query(..., description="Share token"),
    db: Session = Depends(get_db),
):
    """Public endpoint — view a shared project preview (no auth required)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = project.project_metadata or {}
    links = metadata.get("share_links", [])
    share_data = None
    for link in links:
        if link.get("token") == token:
            share_data = link
            break

    if not share_data:
        raise HTTPException(status_code=404, detail="Invalid share link")

    if not share_data.get("is_active", True):
        raise HTTPException(status_code=410, detail="Share link has been revoked")

    if not _verify_token(project_id, token, share_data):
        raise HTTPException(status_code=403, detail="Share link expired or invalid")

    # Increment view count
    share_data["view_count"] = share_data.get("view_count", 0) + 1
    project.project_metadata = metadata
    db.commit()

    # Build the shared data (read-only)
    outputs = project.agent_outputs or {}
    result: Dict[str, Any] = {
        "project_id": str(project.id),
        "name": project.name,
        "project_type": project.project_type.value if project.project_type else None,
        "status": project.status.value if project.status else None,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "live_url": project.live_url,
        "github_repo": project.github_repo,
    }

    if share_data.get("include_outputs", True):
        # Include design system, architecture, etc. (strip reasoning)
        safe_outputs = {}
        for agent, data in outputs.items():
            if agent == "browser_tests":
                continue  # Skip raw test data
            if isinstance(data, dict):
                safe = {k: v for k, v in data.items() if not k.startswith("_")}
                safe_outputs[agent] = safe
            else:
                safe_outputs[agent] = data
        result["outputs"] = safe_outputs

    if share_data.get("include_code", True):
        code_gen = outputs.get("code_generation", {})
        if isinstance(code_gen, dict):
            result["code_files"] = {
                k: v for k, v in code_gen.items()
                if k not in ("_reasoning", "cost", "model_used", "tokens")
            }

    if share_data.get("include_qa", True):
        qa_data = outputs.get("qa_testing") or outputs.get("qa", {})
        if isinstance(qa_data, dict):
            result["qa_report"] = qa_data.get("report") or qa_data.get("summary", {})

    return result
