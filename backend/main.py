"""FastAPI application for AI Dev Agency."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import projects_router, agents_router, costs_router, health_router
from api.routes import revisions_router, analytics_router, integrations_router
from api.routes.presets import router as presets_router  # Phase 11A
from api.routes.templates import router as templates_router  # Phase 11B
from api.routes.knowledge import router as knowledge_router  # Phase 11B
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
    description="Universal AI Development Agency System - Phase 11B Knowledge Base + Templates",
    version="1.11.1",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
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
