"""
Phase 11C: Project Export/Import

Export projects as ZIP files containing:
- Generated code
- Assets (images, icons)
- Configuration files
- Agent reports
- Database records (JSON)
"""

import json
import os
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, BinaryIO

from sqlalchemy.orm import Session

from models.project import Project, ProjectStatus, ProjectType, CostProfile
from models.agent_log import AgentLog
from models.cost_tracking import CostTracking


# Directories to include in export
EXPORT_DIRS = [
    "src",
    "public",
    "components",
    "pages",
    "styles",
    "assets",
    "config",
    "tests",
    "docs",
]

# Files to include in export
EXPORT_FILES = [
    "package.json",
    "tsconfig.json",
    "tailwind.config.js",
    "next.config.js",
    "vite.config.ts",
    ".env.example",
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
]

# Report files to include
REPORT_FILES = [
    "security_report.json",
    "seo_report.json",
    "accessibility_report.json",
    "qa_report.json",
    "lighthouse_report.json",
]


def list_exportable_files(project_path: str) -> List[Dict[str, Any]]:
    """
    List all files that would be included in an export.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        List of file info dicts
    """
    files = []
    base_path = Path(project_path)
    
    if not base_path.exists():
        return files
    
    # Check directories
    for dir_name in EXPORT_DIRS:
        dir_path = base_path / dir_name
        if dir_path.exists() and dir_path.is_dir():
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    files.append({
                        "path": str(file_path.relative_to(base_path)),
                        "size": file_path.stat().st_size,
                        "type": "code"
                    })
    
    # Check individual files
    for file_name in EXPORT_FILES:
        file_path = base_path / file_name
        if file_path.exists() and file_path.is_file():
            files.append({
                "path": file_name,
                "size": file_path.stat().st_size,
                "type": "config"
            })
    
    # Check reports
    for report_name in REPORT_FILES:
        report_path = base_path / report_name
        if report_path.exists() and report_path.is_file():
            files.append({
                "path": report_name,
                "size": report_path.stat().st_size,
                "type": "report"
            })
    
    return files


def export_project_zip(
    db: Session,
    project_id: str,
    project_path: Optional[str] = None,
    include_logs: bool = True,
    include_costs: bool = True
) -> bytes:
    """
    Export a project as a ZIP file.
    
    Args:
        db: Database session
        project_id: UUID of the project
        project_path: Path to project files (auto-detected if None)
        include_logs: Include agent logs in export
        include_costs: Include cost tracking data
        
    Returns:
        ZIP file contents as bytes
    """
    # Get project from database
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project {project_id} not found")
    
    # Determine project path
    if project_path is None:
        # Try to find project files
        possible_paths = [
            f"/home/ubuntu/projects/{project_id}",
            f"/home/ubuntu/ai-dev-agency/generated/{project_id}",
            project.project_metadata.get("output_path") if project.project_metadata else None
        ]
        for path in possible_paths:
            if path and os.path.exists(path):
                project_path = path
                break
    
    # Create temporary directory for export
    with tempfile.TemporaryDirectory() as temp_dir:
        export_dir = Path(temp_dir) / "export"
        export_dir.mkdir()
        
        # 1. Export project metadata
        metadata = {
            "id": str(project.id),
            "name": project.name,
            "brief": project.brief,
            "project_type": project.project_type.value if project.project_type else None,
            "status": project.status.value if project.status else None,
            "cost_profile": project.cost_profile.value if project.cost_profile else None,
            "cost_estimate": project.cost_estimate,
            "github_repo": project.github_repo,
            "live_url": project.live_url,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "completed_at": project.completed_at.isoformat() if project.completed_at else None,
            "agent_outputs": project.agent_outputs,
            "project_metadata": project.project_metadata,
            "revision_history": project.revision_history,
            "cost_breakdown": project.cost_breakdown,
            "requirements": project.requirements,
            "exported_at": datetime.utcnow().isoformat(),
            "export_version": "1.0"
        }
        
        with open(export_dir / "project.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # 2. Export agent logs
        if include_logs:
            logs = db.query(AgentLog).filter(AgentLog.project_id == project_id).all()
            logs_data = [
                {
                    "id": str(log.id),
                    "agent_name": log.agent_name,
                    "model_used": log.model_used,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "token_usage": log.token_usage,
                    "cost": log.cost,
                    "status": log.status,
                    "input_data": log.input_data,
                    "output_data": log.output_data
                }
                for log in logs
            ]
            
            with open(export_dir / "agent_logs.json", "w") as f:
                json.dump(logs_data, f, indent=2)
        
        # 3. Export cost tracking
        if include_costs:
            costs = db.query(CostTracking).filter(
                CostTracking.project_id == project_id
            ).all()
            costs_data = [
                {
                    "id": str(cost.id),
                    "agent_name": cost.agent_name,
                    "model_used": cost.model_used,
                    "token_count": cost.token_count,
                    "cost": cost.cost,
                    "timestamp": cost.timestamp.isoformat() if cost.timestamp else None,
                    "details": cost.details
                }
                for cost in costs
            ]
            
            with open(export_dir / "cost_tracking.json", "w") as f:
                json.dump(costs_data, f, indent=2)
        
        # 4. Copy project files if path exists
        if project_path and os.path.exists(project_path):
            code_dir = export_dir / "code"
            code_dir.mkdir()
            
            base_path = Path(project_path)
            
            # Copy directories
            for dir_name in EXPORT_DIRS:
                src_dir = base_path / dir_name
                if src_dir.exists():
                    shutil.copytree(src_dir, code_dir / dir_name)
            
            # Copy files
            for file_name in EXPORT_FILES:
                src_file = base_path / file_name
                if src_file.exists():
                    shutil.copy2(src_file, code_dir / file_name)
            
            # Copy reports
            for report_name in REPORT_FILES:
                src_report = base_path / report_name
                if src_report.exists():
                    shutil.copy2(src_report, code_dir / report_name)
        
        # 5. Create ZIP file
        zip_path = Path(temp_dir) / f"project_{project_id}.zip"
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in export_dir.rglob("*"):
                if file_path.is_file():
                    arc_name = file_path.relative_to(export_dir)
                    zf.write(file_path, arc_name)
        
        # Read and return ZIP contents
        with open(zip_path, "rb") as f:
            return f.read()


def import_project_zip(
    db: Session,
    zip_file: BinaryIO,
    override_id: Optional[str] = None
) -> str:
    """
    Import a project from a ZIP file.
    
    Args:
        db: Database session
        zip_file: ZIP file binary stream
        override_id: Optional project ID to use (generates new if None)
        
    Returns:
        ID of the imported project
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract ZIP
        zip_path = Path(temp_dir) / "import.zip"
        with open(zip_path, "wb") as f:
            f.write(zip_file.read())
        
        extract_dir = Path(temp_dir) / "extracted"
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        
        # Read project metadata
        project_json = extract_dir / "project.json"
        if not project_json.exists():
            raise ValueError("Invalid export: project.json not found")
        
        with open(project_json, "r") as f:
            metadata = json.load(f)
        
        # Generate new ID or use override
        project_id = override_id or str(uuid.uuid4())
        
        # Create project in database
        project = Project(
            id=project_id,
            name=metadata.get("name", "Imported Project"),
            brief=metadata.get("brief", ""),
            project_type=ProjectType(metadata["project_type"]) if metadata.get("project_type") else None,
            status=ProjectStatus(metadata.get("status", "completed")),
            cost_profile=CostProfile(metadata.get("cost_profile", "balanced")),
            cost_estimate=metadata.get("cost_estimate"),
            github_repo=metadata.get("github_repo"),
            live_url=metadata.get("live_url"),
            agent_outputs=metadata.get("agent_outputs", {}),
            project_metadata={
                **metadata.get("project_metadata", {}),
                "imported_from": metadata.get("id"),
                "imported_at": datetime.utcnow().isoformat()
            },
            revision_history=metadata.get("revision_history", []),
            cost_breakdown=metadata.get("cost_breakdown", {}),
            requirements=metadata.get("requirements", {})
        )
        
        db.add(project)
        
        # Import agent logs
        logs_json = extract_dir / "agent_logs.json"
        if logs_json.exists():
            with open(logs_json, "r") as f:
                logs_data = json.load(f)
            
            for log_data in logs_data:
                log = AgentLog(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    agent_name=log_data.get("agent_name"),
                    model_used=log_data.get("model_used"),
                    timestamp=datetime.fromisoformat(log_data["timestamp"]) if log_data.get("timestamp") else None,
                    token_usage=log_data.get("token_usage"),
                    cost=log_data.get("cost"),
                    status=log_data.get("status"),
                    input_data=log_data.get("input_data"),
                    output_data=log_data.get("output_data")
                )
                db.add(log)
        
        # Import cost tracking
        costs_json = extract_dir / "cost_tracking.json"
        if costs_json.exists():
            with open(costs_json, "r") as f:
                costs_data = json.load(f)
            
            for cost_data in costs_data:
                cost = CostTracking(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    agent_name=cost_data.get("agent_name"),
                    model_used=cost_data.get("model_used"),
                    token_count=cost_data.get("token_count"),
                    cost=cost_data.get("cost"),
                    timestamp=datetime.fromisoformat(cost_data["timestamp"]) if cost_data.get("timestamp") else None,
                    details=cost_data.get("details")
                )
                db.add(cost)
        
        # Copy code files to project directory
        code_dir = extract_dir / "code"
        if code_dir.exists():
            output_path = f"/home/ubuntu/projects/{project_id}"
            os.makedirs(output_path, exist_ok=True)
            
            for item in code_dir.iterdir():
                if item.is_dir():
                    shutil.copytree(item, Path(output_path) / item.name)
                else:
                    shutil.copy2(item, Path(output_path) / item.name)
            
            # Update project metadata with output path
            project.project_metadata["output_path"] = output_path
        
        db.commit()
        
        return project_id
