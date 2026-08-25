"""
Retrieval API endpoints

Phase 8: Secure vector retrieval with retrieval-time ACL filtering.
"""
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.services.retrieval_service import RetrievalService
from app.schemas.retrieval import RetrievalRequest, RetrievalResult
from app.core.errors import AuthorizationError, VectorDBError, EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


@router.post("", response_model=RetrievalResult)
def retrieve_documents(
    request: RetrievalRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
) -> RetrievalResult:
    """
    Retrieve relevant authorized documents for a question.
    
    SECURITY ARCHITECTURE:
    
    1. JWT Authentication (mandatory)
    2. User loaded from PostgreSQL
    3. Department resolved from PostgreSQL (TRUSTED)
    4. Client CANNOT specify department
    5. Query embedding generated locally ($0 cost)
    6. Qdrant search WITH department ACL filter
    7. Only authorized chunks returned
    
    Request:
        {
            "question": "What is our leave policy?"
        }
    
    Response:
        {
            "question": "...",
            "chunks": [
                {
                    "chunk_id": "...",
                    "document_name": "...",
                    "chunk_text": "...",
                    "score": 0.87,
                    ...
                }
            ],
            "retrieved_count": 3,
            "user_department_id": 10,
            "user_department_name": "engineering"
        }
    
    Security:
        - Requires valid JWT authentication
        - Department determined server-side from PostgreSQL
        - ACL filtering happens during Qdrant search
        - Unauthorized documents NEVER retrieved
        - Client cannot bypass authorization
    
    Phase 8 Scope:
        - Retrieval ONLY
        - NO LLM generation (Phase 9)
        - NO prompt construction (Phase 9)
        - Returns raw retrieved chunks for future LLM consumption
    
    Args:
        request: Retrieval request with user question
        current_user: Authenticated user (from JWT + PostgreSQL)
        db: Database session
        
    Returns:
        RetrievalResult with authorized chunks
        
    Raises:
        401 Unauthorized: If JWT is invalid or missing
        403 Forbidden: If user has no department
        500 Internal Server Error: If embedding or search fails
    """
    logger.info(
        f"Retrieval request: user_id={current_user.id}, "
        f"question_length={len(request.question)}"
    )
    
    try:
        # Create retrieval service
        retrieval_service = RetrievalService(db)
        
        # Execute retrieval with ACL enforcement
        result = retrieval_service.retrieve(
            question=request.question,
            authenticated_user=current_user  # ← Department comes from here
        )
        
        logger.info(
            f"Retrieval successful: user_id={current_user.id}, "
            f"chunks={result.retrieved_count}"
        )
        
        return result
        
    except AuthorizationError as e:
        logger.error(f"Authorization failed: user_id={current_user.id}, error={e.message}")
        raise
    except (EmbeddingError, VectorDBError) as e:
        logger.error(f"Retrieval failed: user_id={current_user.id}, error={e.message}")
        raise
    except ValueError as e:
        logger.error(f"Invalid request: user_id={current_user.id}, error={str(e)}")
        raise
