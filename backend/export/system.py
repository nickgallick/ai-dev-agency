"""
Phase 11C: System Backup & Restore

Provides:
- Full system backup to S3/R2
- Knowledge base export
- Restore from backup
"""

import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import subprocess

from sqlalchemy.orm import Session

from config.settings import get_settings
from models.database import engine
from models.knowledge_base import KnowledgeBase
from models.project_template import ProjectTemplate


# Tables to include in backup
BACKUP_TABLES = [
    "projects",
    "agent_logs",
    "cost_tracking",
    "deployment_records",
    "agent_performance",
    "cost_accuracy_tracking",
    "project_presets",
    "knowledge_base",
    "project_templates",
    "users",
]

# Project root (two levels up from this file: backend/export/ -> backend/ -> project/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# Directories to include in backup (absolute, skip if they don't exist)
BACKUP_DIRS = [
    str(_PROJECT_ROOT / "generated_assets"),
    str(_PROJECT_ROOT / "templates"),
    "/home/ubuntu/ai-dev-agency/generated_assets",  # legacy path
    "/home/ubuntu/ai-dev-agency/templates",          # legacy path
]

# Local backup destination
_LOCAL_BACKUP_DIR = _PROJECT_ROOT / "backups"


def backup_system(
    db: Session,
    destination: str = "local",
    bucket_name: Optional[str] = None,
    include_projects: bool = False
) -> Dict[str, Any]:
    """
    Create a full system backup.
    
    Args:
        db: Database session
        destination: "local", "s3", or "r2"
        bucket_name: S3/R2 bucket name (required for cloud destinations)
        include_projects: Include generated project files
        
    Returns:
        Backup result with path/URL and metadata
    """
    settings = get_settings()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"ai_dev_agency_backup_{timestamp}"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir = Path(temp_dir) / backup_name
        backup_dir.mkdir()
        
        # 1. Backup database tables
        db_backup_dir = backup_dir / "database"
        db_backup_dir.mkdir()
        
        from sqlalchemy import text as _sql_text
        for table_name in BACKUP_TABLES:
            try:
                # Export table to JSON using raw SQL
                result = db.execute(_sql_text(f"SELECT row_to_json(t) FROM {table_name} t"))
                rows = [row[0] for row in result]

                with open(db_backup_dir / f"{table_name}.json", "w") as f:
                    json.dump(rows, f, indent=2, default=str)
            except Exception as e:
                # Table might not exist
                print(f"Warning: Could not backup table {table_name}: {e}")
        
        # 2. Backup static directories
        for dir_path in BACKUP_DIRS:
            if os.path.exists(dir_path):
                dest_name = Path(dir_path).name
                dest_path = backup_dir / "files" / dest_name
                dest_path.parent.mkdir(exist_ok=True)
                
                import shutil
                shutil.copytree(dir_path, dest_path)
        
        # 3. Optionally backup generated projects
        if include_projects:
            projects_dir = backup_dir / "projects"
            projects_dir.mkdir()
            
            source_dirs = [
                "/home/ubuntu/projects",
                "/home/ubuntu/ai-dev-agency/generated"
            ]
            
            for source_dir in source_dirs:
                if os.path.exists(source_dir):
                    for project_folder in os.listdir(source_dir):
                        src = Path(source_dir) / project_folder
                        if src.is_dir():
                            import shutil
                            shutil.copytree(src, projects_dir / project_folder)
        
        # 4. Create backup metadata
        metadata = {
            "backup_version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "tables_backed_up": BACKUP_TABLES,
            "include_projects": include_projects,
            "destination": destination
        }
        
        with open(backup_dir / "backup_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # 5. Create ZIP file
        zip_path = Path(temp_dir) / f"{backup_name}.zip"
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in backup_dir.rglob("*"):
                if file_path.is_file():
                    arc_name = file_path.relative_to(backup_dir)
                    zf.write(file_path, arc_name)
        
        # 6. Upload to destination
        if destination == "local":
            # Save locally — use project-root/backups, fall back to /tmp
            local_backup_dir = _LOCAL_BACKUP_DIR
            try:
                local_backup_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                local_backup_dir = Path(tempfile.gettempdir()) / "ai_dev_agency_backups"
                local_backup_dir.mkdir(parents=True, exist_ok=True)

            final_path = local_backup_dir / f"{backup_name}.zip"
            import shutil
            shutil.copy2(zip_path, final_path)
            
            return {
                "success": True,
                "destination": "local",
                "path": str(final_path),
                "size_bytes": final_path.stat().st_size,
                "created_at": metadata["created_at"]
            }
        
        elif destination in ("s3", "r2"):
            if not bucket_name:
                raise ValueError(f"bucket_name required for {destination} destination")
            
            # Upload to S3/R2
            return _upload_to_cloud(
                zip_path,
                bucket_name,
                f"backups/{backup_name}.zip",
                destination,
                settings
            )
        
        else:
            raise ValueError(f"Unknown destination: {destination}")


def _upload_to_cloud(
    file_path: Path,
    bucket: str,
    key: str,
    provider: str,
    settings
) -> Dict[str, Any]:
    """
    Upload file to S3 or R2.
    
    Uses boto3 for both (R2 is S3-compatible).
    """
    try:
        import boto3
        from botocore.config import Config
        
        if provider == "r2":
            # Cloudflare R2
            endpoint_url = f"https://{getattr(settings, 'r2_account_id', '')}.r2.cloudflarestorage.com"
            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=getattr(settings, 'r2_access_key_id', ''),
                aws_secret_access_key=getattr(settings, 'r2_secret_access_key', ''),
                config=Config(signature_version="s3v4")
            )
        else:
            # AWS S3
            client = boto3.client(
                "s3",
                aws_access_key_id=getattr(settings, 'aws_access_key_id', ''),
                aws_secret_access_key=getattr(settings, 'aws_secret_access_key', ''),
                region_name=getattr(settings, 'aws_region', 'us-east-1')
            )
        
        # Upload file
        client.upload_file(str(file_path), bucket, key)
        
        return {
            "success": True,
            "destination": provider,
            "bucket": bucket,
            "key": key,
            "size_bytes": file_path.stat().st_size,
            "created_at": datetime.utcnow().isoformat()
        }
    
    except ImportError:
        raise ImportError("boto3 required for cloud backup. Install with: pip install boto3")
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "destination": provider
        }


def restore_system(
    db: Session,
    backup_path: str,
    restore_database: bool = True,
    restore_files: bool = True
) -> Dict[str, Any]:
    """
    Restore system from a backup.
    
    Args:
        db: Database session
        backup_path: Path to backup ZIP file (local) or S3/R2 URL
        restore_database: Restore database tables
        restore_files: Restore file directories
        
    Returns:
        Restore result with details
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download if cloud URL
        if backup_path.startswith("s3://") or backup_path.startswith("r2://"):
            # TODO: Implement cloud download
            raise NotImplementedError("Cloud restore not yet implemented")
        
        # Extract ZIP
        extract_dir = Path(temp_dir) / "extracted"
        with zipfile.ZipFile(backup_path, "r") as zf:
            zf.extractall(extract_dir)
        
        # Read metadata
        metadata_file = extract_dir / "backup_metadata.json"
        if not metadata_file.exists():
            raise ValueError("Invalid backup: backup_metadata.json not found")
        
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        restored = {
            "tables": [],
            "directories": [],
            "errors": []
        }
        
        # Restore database tables
        if restore_database:
            db_dir = extract_dir / "database"
            if db_dir.exists():
                for json_file in db_dir.glob("*.json"):
                    table_name = json_file.stem
                    try:
                        with open(json_file, "r") as f:
                            rows = json.load(f)
                        
                        # Clear existing data and insert
                        # Note: This is a simplified restore - production would need more care
                        for row in rows:
                            db.execute(
                                f"INSERT INTO {table_name} SELECT * FROM json_populate_record(null::{table_name}, :data) ON CONFLICT DO NOTHING",
                                {"data": json.dumps(row)}
                            )
                        
                        db.commit()
                        restored["tables"].append(table_name)
                    except Exception as e:
                        restored["errors"].append(f"Table {table_name}: {str(e)}")
        
        # Restore files
        if restore_files:
            files_dir = extract_dir / "files"
            if files_dir.exists():
                import shutil
                for item in files_dir.iterdir():
                    if item.is_dir():
                        dest = Path("/home/ubuntu/ai-dev-agency") / item.name
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                        restored["directories"].append(str(dest))
        
        return {
            "success": len(restored["errors"]) == 0,
            "backup_version": metadata.get("backup_version"),
            "backup_created_at": metadata.get("created_at"),
            "restored": restored
        }


def export_knowledge_base(
    db: Session,
    include_embeddings: bool = False
) -> bytes:
    """
    Export the knowledge base as JSON.
    
    Args:
        db: Database session
        include_embeddings: Include vector embeddings (large)
        
    Returns:
        JSON bytes
    """
    entries = db.query(KnowledgeBase).all()
    
    data = {
        "export_version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "entry_count": len(entries),
        "entries": []
    }
    
    for entry in entries:
        entry_data = {
            "id": str(entry.id),
            "knowledge_type": entry.knowledge_type,
            "project_type": entry.project_type,
            "source_project_id": str(entry.source_project_id) if entry.source_project_id else None,
            "source_agent": entry.source_agent,
            "title": entry.title,
            "content": entry.content,
            "metadata": entry.metadata,
            "quality_score": entry.quality_score,
            "usage_count": entry.usage_count,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None
        }
        
        if include_embeddings and entry.embedding:
            entry_data["embedding"] = entry.embedding.tolist() if hasattr(entry.embedding, 'tolist') else entry.embedding
        
        data["entries"].append(entry_data)
    
    return json.dumps(data, indent=2).encode("utf-8")


def import_knowledge_base(
    db: Session,
    json_data: bytes,
    merge: bool = True
) -> Dict[str, Any]:
    """
    Import knowledge base from JSON.
    
    Args:
        db: Database session
        json_data: JSON bytes
        merge: If True, merge with existing. If False, replace.
        
    Returns:
        Import result
    """
    import uuid
    
    data = json.loads(json_data.decode("utf-8"))
    
    if not merge:
        # Clear existing entries
        db.query(KnowledgeBase).delete()
        db.commit()
    
    imported = 0
    skipped = 0
    errors = []
    
    for entry_data in data.get("entries", []):
        try:
            # Check if entry already exists (by title and type)
            existing = db.query(KnowledgeBase).filter(
                KnowledgeBase.title == entry_data.get("title"),
                KnowledgeBase.knowledge_type == entry_data.get("knowledge_type")
            ).first()
            
            if existing and merge:
                skipped += 1
                continue
            
            entry = KnowledgeBase(
                id=uuid.uuid4(),
                knowledge_type=entry_data.get("knowledge_type"),
                project_type=entry_data.get("project_type"),
                source_project_id=entry_data.get("source_project_id"),
                source_agent=entry_data.get("source_agent"),
                title=entry_data.get("title"),
                content=entry_data.get("content"),
                metadata=entry_data.get("metadata", {}),
                quality_score=entry_data.get("quality_score", 0.8),
                usage_count=entry_data.get("usage_count", 0)
            )
            
            db.add(entry)
            imported += 1
        except Exception as e:
            errors.append(str(e))
    
    db.commit()
    
    return {
        "success": len(errors) == 0,
        "imported": imported,
        "skipped": skipped,
        "errors": errors
    }
