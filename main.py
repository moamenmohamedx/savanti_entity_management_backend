"""Entity Management API - Main Application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from config import get_settings
from entities import router as entities_router
# from entities.debug_routes import router as debug_router  # Empty file, disabled for now
from chat import router as chat_router

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("starting_entity_management_api", environment=settings.environment)
    yield
    logger.info("shutting_down_entity_management_api")


app = FastAPI(
    title="Entity Management API",
    version="1.0.0",
    description="Backend API for managing legal entities with AI-powered assistance",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(entities_router, prefix="/api/entities", tags=["Entities"])
# app.include_router(debug_router, prefix="/api", tags=["Debug"])  # Disabled - empty file
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "entity-management-backend"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Entity Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes (dev mode)
    )