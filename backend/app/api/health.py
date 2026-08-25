"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db.session import check_db_connection
from app.services.qdrant_service import get_qdrant_service, QdrantService

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    services: dict


@router.get("/health", response_model=HealthResponse)
async def health_check(
    qdrant: QdrantService = Depends(get_qdrant_service)
) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the health status of the API and its dependencies.
    
    Returns:
        HealthResponse with status and service availability
    """
    # Check database connection
    db_healthy = check_db_connection()
    
    # Check Qdrant connection
    qdrant_healthy = qdrant.health_check()
    
    # Determine overall status
    overall_status = "healthy" if (db_healthy and qdrant_healthy) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        services={
            "database": "ok" if db_healthy else "unavailable",
            "vector_db": "ok" if qdrant_healthy else "unavailable"
        }
    )
