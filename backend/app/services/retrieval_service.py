"""
Retrieval service

Orchestrates secure vector retrieval with ACL filtering.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.models.user import User
from app.services.embedding_service import get_embedding_service
from app.services.qdrant_service import get_qdrant_service
from app.schemas.retrieval import RetrievalChunk, RetrievalResult
from app.core.config import settings
from app.core.errors import VectorDBError, EmbeddingError, AuthorizationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class RetrievalService:
    """
    Secure retrieval service with retrieval-time ACL filtering.
    
    SECURITY ARCHITECTURE:
    
    User Question
          ↓
    Authenticated User (JWT)
          ↓
    PostgreSQL User.department_id (TRUSTED)
          ↓
    Query Embedding (local, $0 cost)
          ↓
    Qdrant Search + ACL Filter (department_id)
          ↓
    Authorized Chunks ONLY
          ↓
    Relevance Threshold (>= 0.7)
          ↓
    Retrieval Results
    
    CRITICAL SECURITY REQUIREMENTS:
    1. Department MUST come from PostgreSQL User (never from client)
    2. ACL filter MUST be applied INSIDE Qdrant search (not post-retrieval)
    3. Client CANNOT influence department selection
    4. Unauthorized chunks MUST NEVER be retrieved
    
    Phase 8: Retrieval only (no LLM)
    Phase 9: LLM generation using these results
    """
    
    def __init__(
        self,
        db: Session,
        embedding_service=None,
        qdrant_service=None
    ):
        """
        Initialize retrieval service.
        
        Args:
            db: Database session
            embedding_service: Optional embedding service (for testing)
            qdrant_service: Optional Qdrant service (for testing)
        """
        self.db = db
        self.embedding_service = embedding_service or get_embedding_service()
        self.qdrant_service = qdrant_service or get_qdrant_service()
        
        logger.info("RetrievalService initialized")
    
    def retrieve(
        self,
        question: str,
        authenticated_user: User
    ) -> RetrievalResult:
        """
        Retrieve relevant authorized chunks for a user's question.
        
        This is the MAIN ENTRY POINT for Phase 8 retrieval.
        
        Process:
            1. Validate question
            2. Resolve user's department (from PostgreSQL)
            3. Generate query embedding (using same model as indexing)
            4. Construct department ACL filter
            5. Execute Qdrant search WITH filter
            6. Apply relevance threshold
            7. Normalize results
        
        Args:
            question: User's question
            authenticated_user: Authenticated User object from PostgreSQL
            
        Returns:
            RetrievalResult with authorized chunks
            
        Raises:
            AuthorizationError: If user's department cannot be resolved
            EmbeddingError: If query embedding fails
            VectorDBError: If Qdrant search fails
            
        Security:
            - authenticated_user MUST be resolved by authentication middleware
            - Department comes from PostgreSQL relationship (trusted source)
            - Client cannot override department
            - ACL filtering happens inside Qdrant (not post-retrieval)
        """
        logger.info(
            f"Starting retrieval: user_id={authenticated_user.id}, "
            f"question_length={len(question)}"
        )
        
        # Step 1: Validate question
        self._validate_question(question)
        
        # Step 2: Resolve trusted department (SECURITY CRITICAL)
        department_id, department_name = self._resolve_department(authenticated_user)
        
        # Step 3: Generate query embedding
        query_vector = self._embed_question(question)
        
        # Step 4: Construct ACL filter (SECURITY BOUNDARY)
        acl_filter = self._build_department_filter(department_id)
        
        # Step 5: Execute filtered search
        raw_results = self._search_vectors(
            query_vector=query_vector,
            department_filter=acl_filter
        )
        
        # Step 6: Normalize results
        chunks = self._normalize_results(raw_results)
        
        logger.info(
            f"Retrieval complete: user_id={authenticated_user.id}, "
            f"department_id={department_id}, chunks={len(chunks)}"
        )
        
        return RetrievalResult(
            question=question,
            chunks=chunks,
            retrieved_count=len(chunks),
            user_department_id=department_id,
            user_department_name=department_name
        )
    
    def _validate_question(self, question: str) -> None:
        """
        Validate user question.
        
        Args:
            question: User's question
            
        Raises:
            ValueError: If question is invalid
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        if len(question) > 1000:
            raise ValueError("Question too long (max 1000 characters)")
    
    def _resolve_department(self, user: User) -> tuple[int, str]:
        """
        Resolve user's department from PostgreSQL.
        
        SECURITY CRITICAL: This is the ONLY trusted source for department.
        
        Args:
            user: Authenticated User object with department relationship
            
        Returns:
            Tuple of (department_id, department_name)
            
        Raises:
            AuthorizationError: If department cannot be resolved
            
        Security:
            - User object comes from PostgreSQL (authenticated)
            - Department relationship is loaded from database
            - Client cannot influence this value
        """
        if not user.department:
            logger.error(f"User {user.id} has no department")
            raise AuthorizationError(
                "User department not found. Cannot authorize retrieval."
            )
        
        department_id = user.department.id
        department_name = user.department.name
        
        logger.info(
            f"Resolved department: user_id={user.id}, "
            f"department_id={department_id}, department_name={department_name}"
        )
        
        return department_id, department_name
    
    def _embed_question(self, question: str) -> List[float]:
        """
        Generate embedding for user question.
        
        Uses the SAME model as document indexing (Phase 7):
            - Model: sentence-transformers/all-MiniLM-L6-v2
            - Dimension: 384
            - Cost: $0 (local)
        
        Args:
            question: User's question
            
        Returns:
            384-dimensional embedding vector
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            logger.info("Generating query embedding")
            
            embedding = self.embedding_service.embed_text(question)
            
            logger.info(
                f"Query embedding generated: dimension={len(embedding)}, "
                f"model={self.embedding_service.get_model_name()}"
            )
            
            return embedding
            
        except EmbeddingError:
            logger.error("Failed to generate query embedding")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during query embedding: {e}")
            raise EmbeddingError(f"Failed to generate query embedding: {e}")
    
    def _build_department_filter(self, department_id: int) -> Filter:
        """
        Build Qdrant ACL filter for department authorization.
        
        SECURITY CRITICAL: This filter enforces retrieval-time authorization.
        
        The filter restricts results to chunks where:
            payload.department_id == authenticated_user.department_id
        
        Args:
            department_id: User's department ID (from PostgreSQL)
            
        Returns:
            Qdrant Filter object
            
        Security:
            - Filter is constructed server-side ONLY
            - Client cannot modify filter expression
            - Client cannot bypass filter
            - Filter is applied DURING Qdrant search (not post-retrieval)
        """
        filter_obj = Filter(
            must=[
                FieldCondition(
                    key="department_id",
                    match=MatchValue(value=department_id)
                )
            ]
        )
        
        logger.debug(f"Built ACL filter: department_id={department_id}")
        
        return filter_obj
    
    def _search_vectors(
        self,
        query_vector: List[float],
        department_filter: Filter
    ) -> List[Dict[str, Any]]:
        """
        Execute Qdrant vector search with ACL filtering.
        
        SECURITY BOUNDARY: ACL filter is applied HERE during search.
        
        Args:
            query_vector: Query embedding
            department_filter: Department ACL filter
            
        Returns:
            Raw search results from Qdrant
            
        Raises:
            VectorDBError: If search fails
        """
        try:
            results = self.qdrant_service.search(
                collection_name=settings.qdrant_collection_name,
                query_vector=query_vector,
                department_filter=department_filter,  # ← ACL ENFORCEMENT
                top_k=settings.retrieval_top_k,
                score_threshold=settings.retrieval_score_threshold
            )
            
            logger.info(
                f"Vector search complete: results={len(results)}, "
                f"top_k={settings.retrieval_top_k}, "
                f"threshold={settings.retrieval_score_threshold}"
            )
            
            return results
            
        except VectorDBError:
            logger.error("Vector search failed")
            raise
    
    def _normalize_results(
        self,
        raw_results: List[Dict[str, Any]]
    ) -> List[RetrievalChunk]:
        """
        Normalize Qdrant results to RetrievalChunk schema.
        
        Args:
            raw_results: Raw search results from Qdrant
            
        Returns:
            List of RetrievalChunk objects
        """
        chunks = []
        
        for result in raw_results:
            payload = result["payload"]
            score = result["score"]
            
            chunk = RetrievalChunk(
                chunk_id=payload["chunk_id"],
                document_id=payload["document_id"],
                document_name=payload["document_name"],
                department_id=payload["department_id"],
                department_name=payload["department_name"],
                sensitivity=payload["sensitivity"],
                page_start=payload["page_start"],
                page_end=payload["page_end"],
                chunk_index=payload["chunk_index"],
                chunk_text=payload["chunk_text"],
                score=score
            )
            
            chunks.append(chunk)
        
        logger.debug(f"Normalized {len(chunks)} chunks")
        
        return chunks
