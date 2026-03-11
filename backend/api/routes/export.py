"""
Phase 11C: Export & Backup API Routes

Endpoints for:
- Project export/import
- System backup
- Knowledge base export
"""

import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import get_db
from models.project import Project
from config.settings import get_settings
from export.project import (
    export_project_zip,
    import_project_zip,
    list_exportable_files
)
from export.system import (
    backup_system,
    restore_system,
    export_knowledge_base,
    import_knowledge_base
)


router = APIRouter(prefix="/export", tags=["export"])


# Request/Response models
class BackupRequest(BaseModel):
    destination: str = Field(
        default="local",
        description="Backup destination: local, s3, or r2"
    )
    bucket_name: Optional[str] = Field(
        default=None,
        description="S3/R2 bucket name (required for cloud destinations)"
    )
    include_projects: bool = Field(
        default=False,
        description="Include generated project files"
    )


class RestoreRequest(BaseModel):
    backup_path: str = Field(..., description="Path to backup ZIP file")
    restore_database: bool = Field(default=True)
    restore_files: bool = Field(default=True)


class ExportableFilesResponse(BaseModel):
    project_id: str
    files: List[Dict[str, Any]]
    total_size_bytes: int
    file_count: int


class ImportResult(BaseModel):
    success: bool
    project_id: str
    message: str


class BackupResult(BaseModel):
    success: bool
    destination: str
    path: Optional[str] = None
    bucket: Optional[str] = None
    key: Optional[str] = None
    size_bytes: Optional[int] = None
    created_at: Optional[str] = None
    error: Optional[str] = None


# Project Export Endpoints
@router.get("/projects/{project_id}/files", response_model=ExportableFilesResponse)
async def list_project_files(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    List all files that would be included in a project export.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Try to find project path
    settings = get_settings()
    base_dir = settings.project_temp_dir
    project_path = None
    possible_paths = [
        f"{base_dir}/projects/{project_id}",
        f"{base_dir}/generated/{project_id}",
    ]
    if project.project_metadata:
        possible_paths.append(project.project_metadata.get("output_path"))
    
    for path in possible_paths:
        if path:
            import os
            if os.path.exists(path):
                project_path = path
                break
    
    if not project_path:
        return ExportableFilesResponse(
            project_id=str(project_id),
            files=[],
            total_size_bytes=0,
            file_count=0
        )
    
    files = list_exportable_files(project_path)
    total_size = sum(f.get("size", 0) for f in files)
    
    return ExportableFilesResponse(
        project_id=str(project_id),
        files=files,
        total_size_bytes=total_size,
        file_count=len(files)
    )


@router.get("/projects/{project_id}")
async def export_project(
    project_id: UUID,
    include_logs: bool = Query(default=True),
    include_costs: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    """
    Export a project as a ZIP file.
    
    The ZIP contains:
    - project.json: Project metadata and agent outputs
    - agent_logs.json: All agent execution logs
    - cost_tracking.json: Cost breakdown
    - code/: Generated code and assets
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    try:
        zip_bytes = export_project_zip(
            db=db,
            project_id=str(project_id),
            include_logs=include_logs,
            include_costs=include_costs
        )
        
        filename = f"{project.name or 'project'}_{project_id}.zip"
        
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.post("/projects/import", response_model=ImportResult)
async def import_project(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Import a project from a ZIP file.
    
    Creates a new project from an exported ZIP.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a ZIP archive"
        )
    
    try:
        project_id = import_project_zip(
            db=db,
            zip_file=file.file
        )
        
        return ImportResult(
            success=True,
            project_id=project_id,
            message="Project imported successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


# System Backup Endpoints
@router.post("/system/backup", response_model=BackupResult)
async def create_backup(
    request: BackupRequest,
    db: Session = Depends(get_db)
):
    """
    Create a full system backup.
    
    Backs up:
    - All database tables
    - Generated assets and templates
    - Optionally: generated project files
    
    Destinations:
    - local: Saves to /home/ubuntu/ai-dev-agency/backups/
    - s3: Uploads to AWS S3
    - r2: Uploads to Cloudflare R2
    """
    try:
        result = backup_system(
            db=db,
            destination=request.destination,
            bucket_name=request.bucket_name,
            include_projects=request.include_projects
        )
        
        return BackupResult(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup failed: {str(e)}"
        )


@router.get("/system/backups")
async def list_backups():
    """
    List available local backups.
    """
    import os
    from pathlib import Path
    
    from export.system import _LOCAL_BACKUP_DIR
    backup_dir = _LOCAL_BACKUP_DIR

    if not backup_dir.exists():
        return {"backups": []}
    
    backups = []
    for file in backup_dir.glob("*.zip"):
        stat = file.stat()
        backups.append({
            "filename": file.name,
            "path": str(file),
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
        })
    
    # Sort by creation time, newest first
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"backups": backups}


@router.post("/system/restore")
async def restore_backup(
    request: RestoreRequest,
    db: Session = Depends(get_db)
):
    """
    Restore system from a backup.
    
    WARNING: This will modify the database and file system.
    """
    import os
    
    if not os.path.exists(request.backup_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found"
        )
    
    try:
        result = restore_system(
            db=db,
            backup_path=request.backup_path,
            restore_database=request.restore_database,
            restore_files=request.restore_files
        )
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {str(e)}"
        )


# Knowledge Base Export Endpoints
@router.get("/knowledge")
async def export_knowledge(
    include_embeddings: bool = Query(default=False),
    db: Session = Depends(get_db)
):
    """
    Export the knowledge base as JSON.
    
    Set include_embeddings=true to include vector embeddings (large file).
    """
    try:
        json_bytes = export_knowledge_base(
            db=db,
            include_embeddings=include_embeddings
        )
        
        filename = f"knowledge_base_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        return Response(
            content=json_bytes,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.post("/knowledge/import")
async def import_knowledge(
    file: UploadFile = File(...),
    merge: bool = Query(default=True, description="Merge with existing or replace"),
    db: Session = Depends(get_db)
):
    """
    Import knowledge base from JSON.

    Set merge=false to replace existing knowledge base.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a JSON file"
        )

    try:
        content = await file.read()
        result = import_knowledge_base(
            db=db,
            json_data=content,
            merge=merge
        )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


# Project Artifacts Endpoint
@router.get("/projects/{project_id}/artifacts")
async def get_project_artifacts(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get artifact metadata for a completed project.

    Returns preview_url, github_repo, readme, file structure, and deployment URLs.
    """
    import os

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    settings = get_settings()
    base_dir = settings.project_temp_dir

    # Locate the project directory
    project_path = None
    possible_paths = [
        f"{base_dir}/projects/{project_id}",
        f"{base_dir}/generated/{project_id}",
    ]
    if project.project_metadata:
        output_path = project.project_metadata.get("output_path") or project.project_metadata.get("project_path")
        if output_path:
            possible_paths.insert(0, output_path)

    for path in possible_paths:
        if path and os.path.exists(path):
            project_path = path
            break

    # Try to read the README
    readme_content = None
    if project_path:
        for readme_name in ["README.md", "readme.md", "README.txt"]:
            readme_path = os.path.join(project_path, readme_name)
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        readme_content = f.read()
                    break
                except Exception:
                    pass

    # Check agent outputs for generated README
    agent_outputs = project.agent_outputs or {}
    if not readme_content:
        coding_output = agent_outputs.get("coding_standards", {})
        if isinstance(coding_output, dict):
            readme_content = coding_output.get("readme_content") or coding_output.get("readme")

    # Build file structure
    file_structure = []
    if project_path:
        try:
            for root, dirs, files in os.walk(project_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', '.git')]
                rel_root = os.path.relpath(root, project_path)
                if rel_root == '.':
                    for f in files[:20]:
                        file_structure.append(f)
                else:
                    for f in files[:10]:
                        file_structure.append(f"{rel_root}/{f}")
                if len(file_structure) > 50:
                    break
        except Exception:
            pass

    # Extract live URL from multiple sources
    delivery_output = agent_outputs.get("delivery", {})
    deployment_output = agent_outputs.get("deployment", {})

    live_url = (
        project.live_url
        or (delivery_output.get("live_url") if isinstance(delivery_output, dict) else None)
        or (deployment_output.get("live_url") if isinstance(deployment_output, dict) else None)
    )

    # Get all deployment URLs
    deployment_urls = []
    if isinstance(deployment_output, dict):
        for dep in deployment_output.get("deployments", []):
            if isinstance(dep, dict) and dep.get("url"):
                deployment_urls.append({
                    "platform": dep.get("platform", "unknown"),
                    "url": dep["url"],
                    "status": dep.get("status", "unknown"),
                })

    return {
        "project_id": str(project_id),
        "project_type": project.project_type.value if project.project_type else None,
        "project_name": project.name,
        "status": project.status.value if project.status else None,
        "live_url": live_url,
        "github_repo": project.github_repo,
        "deployment_urls": deployment_urls,
        "readme_content": readme_content,
        "file_structure": file_structure,
        "has_local_files": project_path is not None,
    }
