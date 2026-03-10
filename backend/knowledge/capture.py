"""Phase 11B: Knowledge Capture

Auto-capture knowledge from completed agents and projects.
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import uuid

from ..models.project import Project
from ..models.project_template import ProjectTemplate
from .types import KnowledgeEntryType
from .base import store_knowledge

logger = logging.getLogger(__name__)


async def capture_agent_knowledge(
    db: Session,
    agent_name: str,
    agent_output: Dict[str, Any],
    project_id: str,
    project_type: Optional[str] = None,
    industry: Optional[str] = None,
    tech_stack: Optional[List[str]] = None,
) -> List[str]:
    """
    Capture knowledge from an agent's output.
    
    Args:
        db: Database session
        agent_name: Name of the agent
        agent_output: Agent's output data
        project_id: Project ID
        project_type: Type of project
        industry: Industry category
        tech_stack: Technologies used
        
    Returns:
        List of created knowledge entry IDs
    """
    created_ids = []
    
    try:
        if agent_name == "research":
            entries = await _capture_research_knowledge(db, agent_output, project_id, project_type, industry)
            created_ids.extend(entries)
            
        elif agent_name == "architect":
            entries = await _capture_architect_knowledge(db, agent_output, project_id, project_type, tech_stack)
            created_ids.extend(entries)
            
        elif agent_name == "design_system":
            entries = await _capture_design_knowledge(db, agent_output, project_id, project_type)
            created_ids.extend(entries)
            
        elif agent_name == "code_generation":
            entries = await _capture_codegen_knowledge(db, agent_output, project_id, project_type, tech_stack)
            created_ids.extend(entries)
            
        elif agent_name == "qa_testing":
            entries = await _capture_qa_knowledge(db, agent_output, project_id, project_type)
            created_ids.extend(entries)
            
        elif agent_name == "security":
            entries = await _capture_security_knowledge(db, agent_output, project_id, tech_stack)
            created_ids.extend(entries)
            
        elif agent_name == "code_review":
            entries = await _capture_review_knowledge(db, agent_output, project_id, tech_stack)
            created_ids.extend(entries)
            
        elif agent_name == "deployment":
            entries = await _capture_deployment_knowledge(db, agent_output, project_id, project_type)
            created_ids.extend(entries)
            
        logger.info(f"Captured {len(created_ids)} knowledge entries from {agent_name}")
        
    except Exception as e:
        logger.error(f"Failed to capture knowledge from {agent_name}: {e}")
    
    return created_ids


async def _capture_research_knowledge(
    db: Session,
    output: Dict[str, Any],
    project_id: str,
    project_type: Optional[str],
    industry: Optional[str],
) -> List[str]:
    """Capture research findings."""
    ids = []
    
    # Capture competitor analysis
    if competitors := output.get("competitors"):
        entry = await store_knowledge(
            db=db,
            entry_type=KnowledgeEntryType.RESEARCH_OUTPUT,
            title=f"Competitor Analysis: {industry or 'General'}",
            content=str(competitors),
            project_id=project_id,
            project_type=project_type,
            industry=industry,
            agent_name="research",
            tags=["competitors", "market-research"],
        )
        ids.append(entry.id)
    
    # Capture design inspiration
    if design_refs := output.get("design_references"):
        entry = await store_knowledge(
            db=db,
            entry_type=KnowledgeEntryType.RESEARCH_OUTPUT,
            title=f"Design References: {project_type or 'General'}",
            content=str(design_refs),
            project_id=project_id,
            project_type=project_type,
            industry=industry,
            agent_name="research",
            tags=["design", "inspiration"],
        )
        ids.append(entry.id)
    
    return ids


async def _capture_architect_knowledge(
    db: Session,
    output: Dict[str, Any],
    project_id: str,
    project_type: Optional[str],
    tech_stack: Optional[List[str]],
) -> List[str]:
    """Capture architecture decisions."""
    ids = []
    
    # Capture tech stack decisions
    if stack := output.get("tech_stack") or output.get("recommended_stack"):
        entry = await store_knowledge(
            db=db,
            entry_type=KnowledgeEntryType.ARCHITECTURE_DECISION,
            title=f"Tech Stack for {project_type or 'Project'}",
            content=f"Recommended stack: {stack}\n\nRationale: {output.get('rationale', 'N/A')}",
            project_id=project_id,
            project_type=project_type,
            tech_stack=tech_stack or (stack if isinstance(stack, list) else None),
            agent_name="architect",
            tags=["tech-stack", "architecture"],
        )
        ids.append(entry.id)
    
    # Capture architecture patterns
    if patterns := output.get("patterns") or output.get("architecture_patterns"):
        entry = await store_knowledge(
            db=db,
            entry_type=KnowledgeEntryType.ARCHITECTURE_DECISION,
            title=f"Architecture Patterns: {project_type or 'General'}",
            content=str(patterns),
            project_id=project_id,
            project_type=project_type,
            tech_stack=tech_stack,
            agent_name="architect",
            tags=["patterns", "architecture"],
        )
        ids.append(entry.id)
    
    return ids


async def _capture_design_knowledge(
    db: Session,
    output: Dict[str, Any],
    project_id: str,
    project_type: Optional[str],
) -> List[str]:
    """Capture design system decisions."""
    ids = []
    
    # Capture design tokens
    if tokens := output.get("design_tokens") or output.get("tokens"):
        entry = await store_knowledge(
            db=db,
            entry_type=KnowledgeEntryType.DESIGN_TOKEN,
            title=f"Design Tokens: {project_type or 'General'}",
            content=str(tokens),
            project_id=project_id,
            project_type=project_type,
            agent_name="design_system",
            tags=["design-tokens", "colors", "typography"],
        )
        ids.append(entry.id)
    
    # Capture component patterns
    if components := output.get("components") or output.get("component_patterns"):
        entry = await store_knowledge(
            db=db,
            entry_type=KnowledgeEntryType.DESIGN_TOKEN,
            title=f"Component Patterns: {project_type or 'General'}",
            content=str(components),
            project_id=project_id,
            project_type=project_type,
            agent_name="design_system",
            tags=["components", "ui-patterns"],
        )
        ids.append(entry.id)
    
    return ids


async def _capture_codegen_knowledge(
    db: Session,
    output: Dict[str, Any],
    project_id: str,
    project_type: Optional[str],
    tech_stack: Optional[List[str]],
) -> List[str]:
    """Capture successful code generation prompts."""
    ids = []
    
    # Capture successful v0 prompts
    if prompts := output.get("v0_prompts") or output.get("successful_prompts"):
        for i, prompt in enumerate(prompts[:5] if isinstance(prompts, list) else [prompts]):
            prompt_text = prompt.get("prompt", str(prompt)) if isinstance(prompt, dict) else str(prompt)
            quality = prompt.get("quality_score", 0.8) if isinstance(prompt, dict) else 0.8
            
            entry = await store_knowledge(
                db=db,
                entry_type=KnowledgeEntryType.PROMPT_RESULT,
                title=f"v0 Prompt #{i+1}: {project_type or 'General'}",
                content=prompt_text,
                project_id=project_id,
                project_type=project_type,
                tech_stack=tech_stack,
                quality_score=quality,
                agent_name="code_generation",
                tags=["v0-prompt", "code-generation"],
            )
            ids.append(entry.id)
    
    return ids


async def _capture_qa_knowledge(
    db: Session,
    output: Dict[str, Any],
    project_id: str,
    project_type: Optional[str],
) -> List[str]:
    """Capture QA findings and fixes."""
    ids = []
    
    # Capture bugs found and fixed
    if findings := output.get("findings") or output.get("bugs_fixed"):
        for finding in findings[:10] if isinstance(findings, list) else [findings]:
            if isinstance(finding, dict):
                title = finding.get("title", finding.get("bug", "QA Finding"))
                bug = finding.get("description", finding.get("bug", str(finding)))
                fix = finding.get("fix", finding.get("resolution", "N/A"))
            else:
                title = "QA Finding"
                bug = str(finding)
                fix = "N/A"
            
            entry = await store_knowledge(
                db=db,
                entry_type=KnowledgeEntryType.QA_FINDING,
                title=title,
                content=f"Bug: {bug}\n\nFix: {fix}",
                project_id=project_id,
                project_type=project_type,
                agent_name="qa_testing",
                tags=["bug", "qa", "fix"],
            )
            ids.append(entry.id)
    
    return ids


async def _capture_security_knowledge(
    db: Session,
    output: Dict[str, Any],
    project_id: str,
    tech_stack: Optional[List[str]],
) -> List[str]:
    """Capture security findings."""
    ids = []
    
    if findings := output.get("findings") or output.get("vulnerabilities"):
        for finding in findings[:10] if isinstance(findings, list) else [findings]:
            if isinstance(finding, dict):
                title = finding.get("rule_id", finding.get("title", "Security Finding"))
                content = f"Severity: {finding.get('severity', 'unknown')}\n\n{finding.get('message', str(finding))}"
            else:
                title = "Security Finding"
                content = str(finding)
            
            entry = await store_knowledge(
                db=db,
                entry_type=KnowledgeEntryType.SECURITY_FINDING,
                title=title,
                content=content,
                project_id=project_id,
                tech_stack=tech_stack,
                agent_name="security",
                tags=["security", "vulnerability"],
            )
            ids.append(entry.id)
    
    return ids


async def _capture_review_knowledge(
    db: Session,
    output: Dict[str, Any],
    project_id: str,
    tech_stack: Optional[List[str]],
) -> List[str]:
    """Capture code review patterns."""
    ids = []
    
    if patterns := output.get("patterns") or output.get("code_patterns"):
        for pattern in patterns[:5] if isinstance(patterns, list) else [patterns]:
            if isinstance(pattern, dict):
                title = pattern.get("name", pattern.get("title", "Code Pattern"))
                content = pattern.get("code", pattern.get("pattern", str(pattern)))
            else:
                title = "Code Pattern"
                content = str(pattern)
            
            entry = await store_knowledge(
                db=db,
                entry_type=KnowledgeEntryType.CODE_PATTERN,
                title=title,
                content=content,
                project_id=project_id,
                tech_stack=tech_stack,
                agent_name="code_review",
                tags=["code-pattern", "best-practice"],
            )
            ids.append(entry.id)
    
    return ids


async def _capture_deployment_knowledge(
    db: Session,
    output: Dict[str, Any],
    project_id: str,
    project_type: Optional[str],
) -> List[str]:
    """Capture deployment configurations."""
    ids = []
    
    if config := output.get("deployment_config") or output.get("config"):
        entry = await store_knowledge(
            db=db,
            entry_type=KnowledgeEntryType.DEPLOYMENT_CONFIG,
            title=f"Deployment Config: {output.get('platform', 'General')}",
            content=str(config),
            project_id=project_id,
            project_type=project_type,
            agent_name="deployment",
            tags=["deployment", output.get("platform", "vercel")],
        )
        ids.append(entry.id)
    
    return ids


async def capture_project_knowledge(
    db: Session,
    project: Project,
) -> List[str]:
    """
    Capture all knowledge from a completed project.
    
    Args:
        db: Database session
        project: Completed project
        
    Returns:
        List of created knowledge entry IDs
    """
    created_ids = []
    
    if not project.agent_outputs:
        return created_ids
    
    # Get project metadata
    project_type = project.project_type.value if project.project_type else None
    metadata = project.project_metadata or {}
    industry = metadata.get("industry")
    tech_stack = metadata.get("tech_stack", [])
    
    # Capture knowledge from each agent's output
    for agent_name, output in project.agent_outputs.items():
        if isinstance(output, dict):
            ids = await capture_agent_knowledge(
                db=db,
                agent_name=agent_name,
                agent_output=output,
                project_id=project.id,
                project_type=project_type,
                industry=industry,
                tech_stack=tech_stack,
            )
            created_ids.extend(ids)
    
    return created_ids


async def auto_generate_template(
    db: Session,
    project: Project,
    qa_score: float,
) -> Optional[ProjectTemplate]:
    """
    Auto-generate a template from a successful project (QA score >= 0.8).
    
    Args:
        db: Database session
        project: Completed project
        qa_score: QA score (0-1)
        
    Returns:
        Created template or None
    """
    if qa_score < 0.8:
        logger.info(f"Project {project.id} QA score {qa_score} too low for template")
        return None
    
    # Extract template data from project
    metadata = project.project_metadata or {}
    requirements = project.requirements or {}
    agent_outputs = project.agent_outputs or {}
    
    # Get design tokens if available
    design_tokens = agent_outputs.get("design_system", {}).get("design_tokens")
    
    # Get tech stack from architect output
    tech_stack = agent_outputs.get("architect", {}).get("tech_stack")
    if not tech_stack:
        tech_stack = metadata.get("tech_stack")
    
    # Get features
    features = requirements.get("core_features", [])
    if not features:
        features = requirements.get("features", [])
    
    template = ProjectTemplate(
        id=str(uuid.uuid4()),
        name=f"{project.name} Template",
        description=f"Auto-generated template from successful project: {project.description or project.name}",
        project_type=project.project_type.value if project.project_type else "web_simple",
        industry=metadata.get("industry"),
        brief_template=metadata.get("brief", project.description),
        requirements=requirements,
        design_tokens=design_tokens,
        tech_stack=tech_stack if isinstance(tech_stack, list) else None,
        features=features if isinstance(features, list) else None,
        source_project_id=project.id,
        is_auto_generated=True,
        is_public=True,
        qa_score=qa_score,
        tags=[project.project_type.value if project.project_type else "general"],
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    logger.info(f"Auto-generated template {template.id} from project {project.id}")
    return template
