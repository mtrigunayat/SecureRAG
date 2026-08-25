"""
FastAPI application entry point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    generic_exception_handler
)
from app.db.session import init_db
from app.services.qdrant_service import init_qdrant
from app.api.health import router as health_router

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    
    Handles startup and shutdown logic.
    """
    # Startup
    logger.info("Starting Secure RAG Knowledge Assistant")
    logger.info(f"Environment: {settings.app_env}")
    
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Initialize Qdrant
        init_qdrant()
        logger.info("Qdrant initialized")
        
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title="Secure RAG Knowledge Assistant",
    description="Document-level access control with RAG",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware (for frontend in later phases)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Register routers
app.include_router(health_router, prefix="/api", tags=["health"])

# Phase 4: Authentication
from app.api.auth import router as auth_router
app.include_router(auth_router)

# Phase 5: Authorization (test endpoints)
from app.api.documents import router as documents_router
app.include_router(documents_router, prefix="/api")

# Future routers (to be added in later phases):
# app.include_router(chat_router, prefix="/api/chat", tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Secure RAG Knowledge Assistant API",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development"
    )
