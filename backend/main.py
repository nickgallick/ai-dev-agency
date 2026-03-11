"""FastAPI application for AI Dev Agency."""
import os
from pathlib import Path

# Load environment variables from .env file before any other imports
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api import projects_router, agents_router, costs_router, health_router
from api.routes import revisions_router, analytics_router, integrations_router, mcp_router, api_keys_router
from api.routes.presets import router as presets_router  # Phase 11A
from api.routes.templates import router as templates_router  # Phase 11B
from api.routes.knowledge import router as knowledge_router  # Phase 11B
from api.routes.checkpoints import router as checkpoints_router  # Phase 11C
from api.routes.queue import router as queue_router  # Phase 11C
from api.routes.export import router as export_router  # Phase 11C
from api.activity import router as activity_router  # Real-time activity streaming
from auth import auth_router
from models import engine, Base


async def _run_pipeline_from_queue(project_id: str, db):
    """Execute pipeline for a project dequeued by the queue worker."""
    from orchestration.executor import PipelineExecutor
    from models.project import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return
    executor = PipelineExecutor(db_session=db)
    await executor.execute(
        project_id=str(project.id),
        brief=project.brief or "",
        cost_profile=project.cost_profile.value if project.cost_profile else "balanced",
        requirements=project.requirements or {},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # Start the queue worker background task
    queue_worker_task = None
    try:
        from task_queue.worker import QueueWorker
        worker = QueueWorker(pipeline_executor=_run_pipeline_from_queue)
        queue_worker_task = asyncio.create_task(worker.start())
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Queue worker failed to start: {e}")

    yield

    # Shutdown: stop the queue worker
    if queue_worker_task and not queue_worker_task.done():
        queue_worker_task.cancel()
        try:
            await queue_worker_task
        except asyncio.CancelledError:
            pass


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

# Prometheus metrics middleware — exposes /metrics endpoint
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health", "/health/ready"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=True)
except ImportError:
    pass  # prometheus_fastapi_instrumentator not installed — skip

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
app.include_router(mcp_router, prefix="/api")  # MCP Server management
app.include_router(api_keys_router, prefix="/api")  # Platform API key management


# Static file serving for production
static_dir = Path(__file__).parent / "static"
if static_dir.exists() and os.getenv("PRODUCTION", "").lower() == "true":
    # Mount static files (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the frontend."""
        return FileResponse(static_dir / "index.html")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Catch-all route to serve SPA for client-side routing."""
        # Don't serve static files for API routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("health"):
            return {"detail": "Not Found"}
        
        # Check if file exists in static folder
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # Return index.html for SPA routing
        return FileResponse(static_dir / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint (development mode)."""
        return {
            "name": "AI Dev Agency API",
            "version": "1.0.0",
            "docs": "/docs",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
