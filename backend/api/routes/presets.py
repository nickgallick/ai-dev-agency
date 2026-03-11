"""Phase 11A: Project Presets API Routes."""
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import get_db, ProjectPreset

router = APIRouter(prefix="/presets", tags=["presets"])


# ============ Request/Response Models ============

class PresetConfig(BaseModel):
    """Preset configuration structure (subset of ProjectRequirements)."""
    project_type: Optional[str] = None
    cost_profile: str = "balanced"
    industry: Optional[str] = None
    design_preferences: Optional[dict] = None
    tech_stack: Optional[dict] = None
    deployment: Optional[dict] = None
    web_complex_options: Optional[dict] = None
    web_simple_options: Optional[dict] = None
    mobile_options: Optional[dict] = None
    cli_options: Optional[dict] = None
    desktop_options: Optional[dict] = None
    build_mode: str = "full_auto"
    integration_config: Optional[dict] = None


class PresetCreate(BaseModel):
    """Request model for creating a preset."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, description="Lucide icon name")
    config: PresetConfig


class PresetUpdate(BaseModel):
    """Request model for updating a preset."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = None
    config: Optional[PresetConfig] = None


class PresetResponse(BaseModel):
    """Response model for preset data."""
    id: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    config: dict
    use_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Default Presets ============

DEFAULT_PRESETS = [
    {
        "name": "SaaS Starter",
        "description": "Full-stack SaaS with auth, billing, and dashboard",
        "icon": "Sparkles",
        "config": {
            "project_type": "python_saas",
            "cost_profile": "balanced",
            "design_preferences": {
                "color_scheme": "system",
                "design_style": "minimal",
                "glassmorphism": True
            },
            "web_complex_options": {
                "key_features": ["authentication", "dashboard", "payments"],
                "include_auth": True,
                "include_dashboard": True,
                "include_billing": True
            }
        }
    },
    {
        "name": "Landing Page",
        "description": "Simple, beautiful landing page",
        "icon": "Globe",
        "config": {
            "project_type": "web_simple",
            "cost_profile": "budget",
            "design_preferences": {
                "color_scheme": "light",
                "design_style": "elegant"
            },
            "web_simple_options": {
                "num_pages": 1,
                "sections": ["hero", "features", "testimonials", "cta"],
                "include_contact_form": True
            }
        }
    },
    {
        "name": "Mobile App",
        "description": "Cross-platform mobile app with Expo",
        "icon": "Smartphone",
        "config": {
            "project_type": "mobile_cross_platform",
            "cost_profile": "balanced",
            "mobile_options": {
                "platforms": ["ios", "android"],
                "framework": "expo"
            }
        }
    },
    {
        "name": "REST API",
        "description": "FastAPI backend with PostgreSQL",
        "icon": "Server",
        "config": {
            "project_type": "python_api",
            "cost_profile": "budget",
            "tech_stack": {
                "backend_framework": "FastAPI",
                "database": "PostgreSQL"
            }
        }
    },
    {
        "name": "Chrome Extension",
        "description": "Browser extension with manifest v3",
        "icon": "Chrome",
        "config": {
            "project_type": "chrome_extension",
            "cost_profile": "budget"
        }
    }
]


# ============ Endpoints ============

@router.get("/", response_model=List[PresetResponse])
async def list_presets(
    include_defaults: bool = True,
    db: Session = Depends(get_db)
):
    """List all presets including default ones."""
    presets = []
    
    # Add default presets if requested
    if include_defaults:
        for i, default in enumerate(DEFAULT_PRESETS):
            presets.append(PresetResponse(
                id=f"default_{i}",
                name=default["name"],
                description=default["description"],
                icon=default["icon"],
                config=default["config"],
                use_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ))
    
    # Add user presets from database
    db_presets = db.query(ProjectPreset).order_by(ProjectPreset.created_at.desc()).all()
    for p in db_presets:
        presets.append(PresetResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            icon=p.icon,
            config=p.config or {},
            use_count=int(p.use_count) if p.use_count else 0,
            created_at=p.created_at,
            updated_at=p.updated_at
        ))
    
    return presets


@router.get("/{preset_id}", response_model=PresetResponse)
async def get_preset(
    preset_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific preset by ID."""
    # Check if it's a default preset
    if preset_id.startswith("default_"):
        try:
            idx = int(preset_id.replace("default_", ""))
            if 0 <= idx < len(DEFAULT_PRESETS):
                default = DEFAULT_PRESETS[idx]
                return PresetResponse(
                    id=preset_id,
                    name=default["name"],
                    description=default["description"],
                    icon=default["icon"],
                    config=default["config"],
                    use_count=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
        except (ValueError, IndexError):
            pass
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # Query database
    preset = db.query(ProjectPreset).filter(ProjectPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    return PresetResponse(
        id=str(preset.id),
        name=preset.name,
        description=preset.description,
        icon=preset.icon,
        config=preset.config or {},
        use_count=int(preset.use_count) if preset.use_count else 0,
        created_at=preset.created_at,
        updated_at=preset.updated_at
    )


@router.post("/", response_model=PresetResponse, status_code=201)
async def create_preset(
    preset: PresetCreate,
    db: Session = Depends(get_db)
):
    """Create a new preset."""
    db_preset = ProjectPreset(
        id=uuid.uuid4(),
        name=preset.name,
        description=preset.description,
        icon=preset.icon,
        config=preset.config.model_dump() if preset.config else {},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        use_count=0
    )
    
    db.add(db_preset)
    db.commit()
    db.refresh(db_preset)
    
    return PresetResponse(
        id=str(db_preset.id),
        name=db_preset.name,
        description=db_preset.description,
        icon=db_preset.icon,
        config=db_preset.config or {},
        use_count=0,
        created_at=db_preset.created_at,
        updated_at=db_preset.updated_at
    )


@router.put("/{preset_id}", response_model=PresetResponse)
async def update_preset(
    preset_id: str,
    preset: PresetUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing preset."""
    # Can't update default presets
    if preset_id.startswith("default_"):
        raise HTTPException(status_code=400, detail="Cannot update default presets")
    
    db_preset = db.query(ProjectPreset).filter(ProjectPreset.id == preset_id).first()
    if not db_preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # Update fields
    if preset.name is not None:
        db_preset.name = preset.name
    if preset.description is not None:
        db_preset.description = preset.description
    if preset.icon is not None:
        db_preset.icon = preset.icon
    if preset.config is not None:
        db_preset.config = preset.config.model_dump()
    
    db_preset.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_preset)
    
    return PresetResponse(
        id=str(db_preset.id),
        name=db_preset.name,
        description=db_preset.description,
        icon=db_preset.icon,
        config=db_preset.config or {},
        use_count=int(db_preset.use_count) if db_preset.use_count else 0,
        created_at=db_preset.created_at,
        updated_at=db_preset.updated_at
    )


@router.delete("/{preset_id}", status_code=204)
async def delete_preset(
    preset_id: str,
    db: Session = Depends(get_db)
):
    """Delete a preset."""
    # Can't delete default presets
    if preset_id.startswith("default_"):
        raise HTTPException(status_code=400, detail="Cannot delete default presets")
    
    db_preset = db.query(ProjectPreset).filter(ProjectPreset.id == preset_id).first()
    if not db_preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    db.delete(db_preset)
    db.commit()


@router.post("/{preset_id}/use", response_model=PresetResponse)
async def increment_preset_usage(
    preset_id: str,
    db: Session = Depends(get_db)
):
    """Increment the usage count for a preset."""
    # Skip for default presets
    if preset_id.startswith("default_"):
        try:
            idx = int(preset_id.replace("default_", ""))
            if 0 <= idx < len(DEFAULT_PRESETS):
                default = DEFAULT_PRESETS[idx]
                return PresetResponse(
                    id=preset_id,
                    name=default["name"],
                    description=default["description"],
                    icon=default["icon"],
                    config=default["config"],
                    use_count=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
        except (ValueError, IndexError):
            pass
        raise HTTPException(status_code=404, detail="Preset not found")
    
    db_preset = db.query(ProjectPreset).filter(ProjectPreset.id == preset_id).first()
    if not db_preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    current_count = int(db_preset.use_count) if db_preset.use_count else 0
    db_preset.use_count = str(current_count + 1)
    db.commit()
    db.refresh(db_preset)
    
    return PresetResponse(
        id=str(db_preset.id),
        name=db_preset.name,
        description=db_preset.description,
        icon=db_preset.icon,
        config=db_preset.config or {},
        use_count=current_count + 1,
        created_at=db_preset.created_at,
        updated_at=db_preset.updated_at
    )
