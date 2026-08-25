"""
Vector indexing service

Orchestrates embedding generation and Qdrant indexing for document chunks.
"""
from typing import List
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from qdrant_client.models import PointStruct, Distance

from app.schemas.ingestion import DocumentChunk, IngestionResult
from app.schemas.indexing import IndexingResult
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.qdrant_service import QdrantService, get_qdrant_service
from app.repositories.document_repository import DocumentRepository
from app.core.config import settings
from app.core.errors import VectorDBError, EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorIndexingService:
    """
    Service for indexing document chunks into Qdrant vector database.
    
    Pipeline:
        Phase 6 chunks
            ↓
        EmbeddingService
            ↓
        LocalEmbeddingProvider
            ↓
        all-MiniLM-L6-v2
            ↓
        384-dimensional vectors
            ↓
        Qdrant
    
    Responsibilities:
        - Generate embeddings for document chunks
        - Create Qdrant points with complete metadata
        - Upsert vectors (idempotent)
        - Handle re-indexing (delete old, insert new)
        - Update document indexing status in PostgreSQL
    
    Security:
        - department_id comes from trusted PostgreSQL metadata
        - All chunk metadata is preserved in Qdrant payload
        - No client-supplied authorization metadata
    """
    
    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService = None,
        qdrant_service: QdrantService = None
    ):
        """
        Initialize vector indexing service.
        
        Args:
            db: Database session
            embedding_service: Embedding service (uses default if None)
            qdrant_service: Qdrant service (uses default if None)
        """
        self.db = db
        self.embedding_service = embedding_service or get_embedding_service()
        self.qdrant_service = qdrant_service or get_qdrant_service()
        self.document_repository = DocumentRepository(db)
        
        # Ensure collection exists
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """
        Ensure Qdrant collection exists with correct configuration.
        
        Collection config:
            - name: knowledge_chunks
            - vector_size: 384 (all-MiniLM-L6-v2)
            - distance: COSINE
        """
        try:
            self.qdrant_service.ensure_collection(
                collection_name=settings.qdrant_collection_name,
                vector_size=settings.embedding_dimension,
                distance=Distance.COSINE
            )
        except VectorDBError:
            logger.error("Failed to ensure Qdrant collection")
            raise
    
    def index_document(
        self,
        ingestion_result: IngestionResult
    ) -> IndexingResult:
        """
        Index a document's chunks into Qdrant.
        
        Process:
            1. Check if document already indexed (re-indexing)
            2. If re-indexing, delete old vectors
            3. Generate embeddings for all chunks (batch)
            4. Create Qdrant points with metadata
            5. Upsert points (idempotent)
            6. Update document.indexed_at in PostgreSQL
            7. Return indexing result
        
        Args:
            ingestion_result: Result from Phase 6 ingestion
            
        Returns:
            IndexingResult with indexing metadata
            
        Raises:
            EmbeddingError: If embedding generation fails
            VectorDBError: If Qdrant operations fail
        """
        document_id = ingestion_result.document_id
        chunks = ingestion_result.chunks
        
        logger.info(
            f"Starting vector indexing: document_id={document_id}, "
            f"chunks={len(chunks)}"
        )
        
        # Check if document was previously indexed
        document = self.document_repository.get_by_id(document_id)
        if document and document.indexed_at:
            logger.info(
                f"Document {document_id} was previously indexed at "
                f"{document.indexed_at}, re-indexing..."
            )
            # Delete old vectors
            self._delete_document_vectors(document_id)
        
        # Generate embeddings
        embeddings = self._generate_embeddings(chunks)
        
        # Create Qdrant points
        points = self._create_points(chunks, embeddings)
        
        # Upsert points
        self._upsert_points(points)
        
        # Update document indexing status
        self._update_indexing_status(document_id)
        
        logger.info(
            f"Vector indexing complete: document_id={document_id}, "
            f"indexed={len(points)} vectors"
        )
        
        return IndexingResult(
            document_id=document_id,
            document_name=ingestion_result.document_name,
            department_name=ingestion_result.department_name,
            chunk_count=len(chunks),
            embedded_count=len(embeddings),
            indexed_count=len(points),
            embedding_model=self.embedding_service.get_model_name(),
            vector_dimension=self.embedding_service.get_dimension(),
            collection=settings.qdrant_collection_name,
            status="indexed"
        )
    
    def _delete_document_vectors(self, document_id: int) -> None:
        """
        Delete all vectors for a document.
        
        Used during re-indexing to remove stale chunks.
        
        Args:
            document_id: Document ID to delete vectors for
        """
        try:
            self.qdrant_service.delete_document_vectors(
                collection_name=settings.qdrant_collection_name,
                document_id=document_id
            )
        except VectorDBError:
            logger.error(f"Failed to delete vectors for document {document_id}")
            raise
    
    def _generate_embeddings(
        self,
        chunks: List[DocumentChunk]
    ) -> List[List[float]]:
        """
        Generate embeddings for all chunks.
        
        Uses batch embedding for efficiency.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            # Extract chunk texts
            texts = [chunk.text for chunk in chunks]
            
            logger.info(f"Generating embeddings for {len(texts)} chunks")
            
            # Batch embed
            embeddings = self.embedding_service.embed_texts(texts)
            
            logger.info(
                f"Generated {len(embeddings)} embeddings "
                f"(dimension={self.embedding_service.get_dimension()})"
            )
            
            return embeddings
            
        except EmbeddingError:
            logger.error("Failed to generate embeddings")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during embedding generation: {e}")
            raise EmbeddingError(f"Failed to generate embeddings: {e}")
    
    def _create_points(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ) -> List[PointStruct]:
        """
        Create Qdrant points from chunks and embeddings.
        
        Each point contains:
            - id: Deterministic chunk_id
            - vector: Embedding
            - payload: Complete chunk metadata (for ACL and display)
        
        Payload structure:
            {
                "document_id": int,          # For deletion
                "chunk_id": str,             # Deterministic ID
                "document_name": str,        # For display
                "department_id": int,        # CRITICAL: For ACL filtering
                "department_name": str,      # For display
                "sensitivity": str,          # For future filtering
                "page_start": int,           # For source attribution
                "page_end": int,             # For source attribution
                "chunk_index": int,          # For ordering
                "chunk_text": str            # For display/context
            }
        
        Args:
            chunks: List of document chunks
            embeddings: List of embedding vectors
            
        Returns:
            List of Qdrant points
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunk count ({len(chunks)}) != embedding count ({len(embeddings)})"
            )
        
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            # Convert string chunk_id to UUID for Qdrant compatibility
            # Use UUID v5 for deterministic generation from chunk_id
            point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, chunk.chunk_id))
            
            point = PointStruct(
                id=point_id,  # UUID string
                vector=embedding,
                payload={
                    # Document reference
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "document_name": chunk.document_name,
                    
                    # Authorization metadata (CRITICAL for Phase 8 ACL)
                    "department_id": chunk.department_id,
                    "department_name": chunk.department_name,
                    "sensitivity": chunk.sensitivity,
                    
                    # Source attribution
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    
                    # Position
                    "chunk_index": chunk.chunk_index,
                    
                    # Content
                    "chunk_text": chunk.text
                }
            )
            points.append(point)
        
        logger.debug(f"Created {len(points)} Qdrant points")
        return points
    
    def _upsert_points(self, points: List[PointStruct]) -> None:
        """
        Upsert points to Qdrant.
        
        Uses upsert semantics for idempotent indexing.
        
        Args:
            points: List of Qdrant points
        """
        try:
            self.qdrant_service.upsert_points(
                collection_name=settings.qdrant_collection_name,
                points=points
            )
        except VectorDBError:
            logger.error("Failed to upsert points to Qdrant")
            raise
    
    def _update_indexing_status(self, document_id: int) -> None:
        """
        Update document indexing status in PostgreSQL.
        
        Sets indexed_at to current timestamp.
        
        Args:
            document_id: Document ID to update
        """
        try:
            document = self.document_repository.get_by_id(document_id)
            if document:
                document.indexed_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Updated indexed_at for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to update indexing status: {e}")
            # Don't raise - indexing succeeded, status update is secondary
    
    def get_collection_info(self):
        """
        Get information about the Qdrant collection.
        
        Returns:
            Collection information dict
        """
        return self.qdrant_service.get_collection_info(
            settings.qdrant_collection_name
        )
