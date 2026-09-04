"""
Qdrant vector database service
"""
from typing import List, Optional, Dict, Any
import socket
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)

from app.core.config import settings
from app.core.errors import VectorDBError
from app.core.logging import get_logger

logger = get_logger(__name__)


class QdrantService:
    """
    Service for interacting with Qdrant vector database.
    
    This service provides vector storage and retrieval operations
    with ACL filtering support.
    
    Phase 7: Collection management, vector indexing
    Phase 8: Similarity search with department ACL filtering
    """
    
    def __init__(self):
        """Initialize Qdrant client."""
        try:
            # Support both local Qdrant and Qdrant Cloud
            # Local: url="http://localhost:6333", api_key=""
            # Cloud: url="https://...", api_key="xxxxxxxx-xxxx-xxxx..."
            kwargs = {
                "url": settings.qdrant_url,
                "timeout": settings.qdrant_timeout
            }
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key
            
            self.client = QdrantClient(**kwargs)
            logger.info(f"Qdrant client initialized: {settings.qdrant_url} (timeout={settings.qdrant_timeout}s)")
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
        except (socket.timeout, TimeoutError):
            logger.error(f"Qdrant health check timed out after {settings.qdrant_timeout}s")
            return False
        except ResponseHandlingException as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
    
    def ensure_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE
    ) -> None:
        """
        Ensure collection exists with correct configuration.
        
        If collection doesn't exist, creates it.
        If it exists, verifies configuration matches.
        
        Args:
            collection_name: Name of the collection
            vector_size: Vector dimension (384 for all-MiniLM-L6-v2)
            distance: Distance metric (COSINE for semantic similarity)
            
        Raises:
            VectorDBError: If collection creation fails or config mismatch
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if collection_name in collection_names:
                # Verify configuration
                collection_info = self.client.get_collection(collection_name)
                
                existing_size = collection_info.config.params.vectors.size
                existing_distance = collection_info.config.params.vectors.distance
                
                if existing_size != vector_size:
                    raise VectorDBError(
                        f"Collection '{collection_name}' exists with "
                        f"vector_size={existing_size}, expected {vector_size}"
                    )
                
                if existing_distance != distance:
                    raise VectorDBError(
                        f"Collection '{collection_name}' exists with "
                        f"distance={existing_distance}, expected {distance}"
                    )
                
                logger.info(
                    f"Collection '{collection_name}' exists with correct config: "
                    f"size={vector_size}, distance={distance}"
                )
                
                # Ensure payload indexes exist on existing collection
                # (required for Qdrant Cloud, even if collection already exists)
                try:
                    self.client.create_payload_index(
                        collection_name=collection_name,
                        field_name="department_id",
                        field_schema="integer"
                    )
                    logger.info(
                        f"Created payload index for 'department_id' "
                        f"in collection '{collection_name}'"
                    )
                except Exception as index_error:
                    # Index may already exist - this is OK
                    logger.debug(
                        f"Payload index for 'department_id' creation result: {index_error}"
                    )
                
                try:
                    self.client.create_payload_index(
                        collection_name=collection_name,
                        field_name="document_id",
                        field_schema="integer"
                    )
                    logger.info(
                        f"Created payload index for 'document_id' "
                        f"in collection '{collection_name}'"
                    )
                except Exception as index_error:
                    # Index may already exist - this is OK
                    logger.debug(
                        f"Payload index for 'document_id' creation result: {index_error}"
                    )
            else:
                # Create collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=distance
                    )
                )
                logger.info(
                    f"Created collection '{collection_name}': "
                    f"size={vector_size}, distance={distance}"
                )
                
                # Create payload indexes for filtering (required for Qdrant Cloud)
                # These indexes are necessary for filtering by department_id
                try:
                    self.client.create_payload_index(
                        collection_name=collection_name,
                        field_name="department_id",
                        field_schema="integer"
                    )
                    logger.info(
                        f"Created payload index for 'department_id' "
                        f"in collection '{collection_name}'"
                    )
                except Exception as index_error:
                    logger.warning(
                        f"Failed to create payload index for 'department_id': "
                        f"{index_error}. Filtering may be slow or fail in Qdrant Cloud."
                    )
                
                # Also index document_id for deletion operations
                try:
                    self.client.create_payload_index(
                        collection_name=collection_name,
                        field_name="document_id",
                        field_schema="integer"
                    )
                    logger.info(
                        f"Created payload index for 'document_id' "
                        f"in collection '{collection_name}'"
                    )
                except Exception as index_error:
                    logger.warning(
                        f"Failed to create payload index for 'document_id': "
                        f"{index_error}"
                    )
                
        except VectorDBError:
            raise
        except (socket.timeout, TimeoutError) as e:
            logger.error(f"Qdrant operation timed out while ensuring collection '{collection_name}': {e}")
            raise VectorDBError(f"Qdrant operation timed out: {e}")
        except Exception as e:
            logger.error(f"Failed to ensure collection '{collection_name}': {e}")
            raise VectorDBError(
                f"Failed to ensure collection '{collection_name}': {e}"
            )
    
    def upsert_points(
        self,
        collection_name: str,
        points: List[PointStruct]
    ) -> None:
        """
        Upsert points into collection.
        
        Uses upsert semantics - if point ID exists, it's updated,
        otherwise it's inserted. This ensures idempotent indexing.
        
        Args:
            collection_name: Name of the collection
            points: List of points to upsert
            
        Raises:
            VectorDBError: If upsert fails
        """
        if not points:
            logger.warning("No points to upsert")
            return
        
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(
                f"Upserted {len(points)} points to '{collection_name}'"
            )
        except Exception as e:
            logger.error(f"Failed to upsert points: {e}")
            raise VectorDBError(f"Failed to upsert points: {e}")
    
    def delete_document_vectors(
        self,
        collection_name: str,
        document_id: int
    ) -> None:
        """
        Delete all vectors for a document.
        
        Used for re-indexing when document content changes.
        Removes all chunks associated with the document ID.
        
        Args:
            collection_name: Name of the collection
            document_id: Document ID to delete vectors for
            
        Raises:
            VectorDBError: If deletion fails
        """
        try:
            # Delete all points where document_id matches
            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
            logger.info(
                f"Deleted vectors for document_id={document_id} "
                f"from '{collection_name}'"
            )
        except Exception as e:
            logger.error(
                f"Failed to delete vectors for document_id={document_id}: {e}"
            )
            raise VectorDBError(
                f"Failed to delete vectors for document_id={document_id}: {e}"
            )
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get collection information.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection information including point count, config, etc.
            
        Raises:
            VectorDBError: If collection doesn't exist or query fails
        """
        try:
            collection = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "points_count": collection.points_count,
                "vector_size": collection.config.params.vectors.size,
                "distance": collection.config.params.vectors.distance.name,
                "status": collection.status.name
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise VectorDBError(f"Failed to get collection info: {e}")
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        department_filter: Filter,
        top_k: int,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search vectors with ACL filtering.
        
        SECURITY CRITICAL: This method implements retrieval-time ACL filtering.
        The department_filter MUST be applied during the Qdrant search operation,
        NOT after retrieving results.
        
        Process:
            1. Ensure collection exists (with indexes for Qdrant Cloud)
            2. Qdrant searches for similar vectors
            3. AND applies department_filter DURING search
            4. Returns only authorized results
        
        Args:
            collection_name: Name of the collection to search
            query_vector: Query embedding vector (384-dim for all-MiniLM-L6-v2)
            department_filter: Filter restricting results to user's department
            top_k: Maximum number of results to return
            score_threshold: Optional minimum similarity score
            
        Returns:
            List of search results with payload and score:
            [
                {
                    "id": "doc1_chunk0",
                    "score": 0.85,
                    "payload": {
                        "document_id": 1,
                        "chunk_id": "doc1_chunk0",
                        "document_name": "...",
                        "department_id": 10,
                        "chunk_text": "...",
                        ...
                    }
                },
                ...
            ]
            
        Raises:
            VectorDBError: If search fails
            
        Security:
            - Collection must exist with proper indexes
            - ACL filter is mandatory and applied during search
            - Client cannot bypass department restriction
            - Unauthorized chunks are NEVER retrieved
        """
        try:
            # Ensure collection exists with proper indexes (idempotent)
            # This is necessary for Qdrant Cloud which was deleted during debugging
            self.ensure_collection(
                collection_name=collection_name,
                vector_size=384,  # all-MiniLM-L6-v2 dimension
                distance=Distance.COSINE
            )
            
            # Search with ACL filter using query_points
            search_result = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=department_filter,  # ← SECURITY BOUNDARY
                limit=top_k,
                score_threshold=score_threshold
            )
            
            # Convert to dict format
            results = []
            for scored_point in search_result.points:
                results.append({
                    "id": scored_point.id,
                    "score": scored_point.score,
                    "payload": scored_point.payload
                })
            
            logger.info(
                f"Search completed: collection={collection_name}, "
                f"top_k={top_k}, threshold={score_threshold}, "
                f"results={len(results)}"
            )
            
            return results
            
        except (socket.timeout, TimeoutError) as e:
            logger.error(f"Qdrant request timed out after {settings.qdrant_timeout}s: {e}")
            raise VectorDBError(f"Qdrant request timed out: {e}")
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise VectorDBError(f"Vector search failed: {e}")


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
