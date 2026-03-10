from .database import Base, get_db, engine, SessionLocal
from .project import Project, ProjectType, ProjectStatus, CostProfile
from .agent_log import AgentLog
from .cost_tracking import CostTracking
from .deployment_record import DeploymentRecord
from .mcp_credentials import MCPCredential
# Phase 9A: Agent Performance Analytics
from .agent_performance import AgentPerformance, QAFailurePattern, CostAccuracyTracking
# Phase 11A: Project Presets
from .preset import ProjectPreset
# Phase 11B: Knowledge Base + Templates
from .knowledge_base import KnowledgeBase
from .project_template import ProjectTemplate

__all__ = [
    "Base",
    "get_db",
    "engine",
    "SessionLocal",
    "Project",
    "ProjectType",
    "ProjectStatus",
    "CostProfile",
    "AgentLog",
    "CostTracking",
    "DeploymentRecord",
    "MCPCredential",
    # Phase 9A
    "AgentPerformance",
    "QAFailurePattern",
    "CostAccuracyTracking",
    # Phase 11A
    "ProjectPreset",
    # Phase 11B
    "KnowledgeBase",
    "ProjectTemplate",
]

# Note: Auth models (User, RefreshToken) are in backend/auth/models.py
# and imported separately via the auth module
