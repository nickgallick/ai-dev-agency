"""AI Dev Agency Agents - All Phases"""

# Phase 1: Core Agents
from .base import BaseAgent
from .intake import IntakeAgent
from .research import ResearchAgent
from .architect import ArchitectAgent
from .design_system import DesignSystemAgent
from .code_generation import CodeGenerationAgent
from .delivery import DeliveryAgent

# Phase 2: Content & Asset Agents
from .asset_generation import AssetGenerationAgent
from .content_generation import ContentGenerationAgent

# Phase 4: Quality & Security Agents
from .security import SecurityAgent
from .seo import SEOAgent
from .accessibility import AccessibilityAgent

# Phase 5: QA & Deployment Agents
from .qa_testing import QATestingAgent
from .deployment import DeploymentAgent

# Phase 6: Monitoring & Standards Agents
from .analytics_monitoring import AnalyticsMonitoringAgent
from .coding_standards import CodingStandardsAgent

# Phase 7: Revision Handler
from .revision_handler import RevisionHandlerAgent

# Phase 8: Project Manager, Code Review, Post-Deploy Verification
from .project_manager import ProjectManagerAgent
from .code_review import CodeReviewAgent
from .post_deploy_verification import PostDeployVerificationAgent

__all__ = [
    # Base
    "BaseAgent",
    # Phase 1
    "IntakeAgent",
    "ResearchAgent",
    "ArchitectAgent",
    "DesignSystemAgent",
    "CodeGenerationAgent",
    "DeliveryAgent",
    # Phase 2
    "AssetGenerationAgent",
    "ContentGenerationAgent",
    # Phase 4
    "SecurityAgent",
    "SEOAgent",
    "AccessibilityAgent",
    # Phase 5
    "QATestingAgent",
    "DeploymentAgent",
    # Phase 6
    "AnalyticsMonitoringAgent",
    "CodingStandardsAgent",
    # Phase 7
    "RevisionHandlerAgent",
    # Phase 8
    "ProjectManagerAgent",
    "CodeReviewAgent",
    "PostDeployVerificationAgent",
]
