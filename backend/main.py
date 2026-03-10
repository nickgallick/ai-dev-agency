"""FastAPI application for AI Dev Agency."""
import os
from pathlib import Path

# Load environment variables from .env file before any other imports
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import projects_router, agents_router, costs_router, health_router
from api.routes import revisions_router, analytics_router, integrations_router
from api.routes.presets import router as presets_router  # Phase 11A
from api.routes.templates import router as templates_router  # Phase 11B
from api.routes.knowledge import router as knowledge_router  # Phase 11B
from api.routes.checkpoints import router as checkpoints_router  # Phase 11C
from api.routes.queue import router as queue_router  # Phase 11C
from api.routes.export import router as export_router  # Phase 11C
from api.activity import router as activity_router  # Real-time activity streaming
from auth import auth_router
from models import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="AI Dev Agency API",
    description="Universal AI Development Agency System - Phase 11C Advanced Features",
    version="1.11.2",
    lifespan=lifespan,
)

# CORS middleware - allow all origins in production for Railway
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Add Railway and other production domains
railway_url = os.getenv("RAILWAY_STATIC_URL", "")
if railway_url:
    allowed_origins.append(railway_url)
    allowed_origins.append(railway_url.replace("http://", "https://"))

# Allow all origins if in production
if os.getenv("PRODUCTION", "").lower() == "true":
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(auth_router)  # Phase 9B: Authentication - Already has /api prefix
app.include_router(projects_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(costs_router, prefix="/api")
app.include_router(revisions_router)  # Already has /api prefix in router
app.include_router(analytics_router)  # Phase 9A: Analytics - Already has /api prefix
app.include_router(integrations_router, prefix="/api")  # Phase 10: Integrations
app.include_router(presets_router, prefix="/api")  # Phase 11A: Presets
app.include_router(templates_router)  # Phase 11B: Templates - Already has /api prefix
app.include_router(knowledge_router)  # Phase 11B: Knowledge - Already has /api prefix
app.include_router(checkpoints_router, prefix="/api")  # Phase 11C: Checkpoints
app.include_router(queue_router, prefix="/api")  # Phase 11C: Queue
app.include_router(export_router, prefix="/api")  # Phase 11C: Export
app.include_router(activity_router, prefix="/api")  # Real-time activity streaming


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AI Dev Agency API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
