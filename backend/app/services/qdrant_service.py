"""
Qdrant vector database service
"""
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException

from app.core.config import settings
from app.core.errors import VectorDBError
from app.core.logging import get_logger

logger = get_logger(__name__)


class QdrantService:
    """
    Service for interacting with Qdrant vector database.
    
    This service provides a clean abstraction for vector operations.
    Actual vector search and ACL filtering will be implemented in later phases.
    """
    
    def __init__(self):
        """Initialize Qdrant client."""
        try:
            self.client = QdrantClient(url=settings.qdrant_url)
            logger.info(f"Qdrant client initialized: {settings.qdrant_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise VectorDBError(f"Failed to initialize Qdrant client: {e}")
    
    def health_check(self) -> bool:
        """
        Check if Qdrant is healthy and reachable.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to get collections (basic connectivity test)
            self.client.get_collections()
            return True
        except ResponseHandlingException as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
    
    # Future methods for later phases:
    # - create_collection()
    # - insert_vectors()
    # - search_with_filter()
    # - delete_by_filter()


# Global Qdrant service instance
qdrant_service: Optional[QdrantService] = None


def get_qdrant_service() -> QdrantService:
    """
    Dependency for getting Qdrant service in FastAPI endpoints.
    
    Returns:
        Qdrant service instance
    """
    global qdrant_service
    if qdrant_service is None:
        qdrant_service = QdrantService()
    return qdrant_service


def init_qdrant() -> None:
    """
    Initialize Qdrant service.
    
    Called during application startup.
    """
    global qdrant_service
    try:
        qdrant_service = QdrantService()
        logger.info("Qdrant service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant service: {e}")
        raise VectorDBError(f"Failed to initialize Qdrant service: {e}")
