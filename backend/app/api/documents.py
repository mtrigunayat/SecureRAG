"""
Document API endpoints

Protected test endpoints for Phase 5 authorization verification.

IMPORTANT:
    These are test/verification endpoints for Phase 5.
    They are NOT the final document retrieval/ingestion API.
    Future phases will add RAG, embeddings, and Qdrant integration.

Purpose:
    - Verify authentication works
    - Verify user identity is resolved
    - Verify document is loaded from PostgreSQL
    - Verify department authorization is enforced
    - Verify authorized users can access metadata
    - Verify unauthorized users receive 403

Security:
    - Returns only safe document metadata
    - Does NOT return actual document content
    - Does NOT involve Qdrant (future phase)
    - Department authorization enforced via AuthorizationService
"""
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.services.authorization_service import authorization_service
from app.schemas.document import DocumentMetadataResponse
from app.core.errors import NotFoundError, ForbiddenError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}", response_model=DocumentMetadataResponse)
async def get_document_metadata(
    document_id: Annotated[int, Path(description="Document ID", ge=1)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
) -> DocumentMetadataResponse:
    """
    Get document metadata (test endpoint for Phase 5 authorization).
    
    This endpoint verifies department-based authorization:
    1. User must be authenticated (JWT validation)
    2. User identity loaded from PostgreSQL
    3. Document loaded from PostgreSQL
    4. Authorization checks: user.department_id == document.department_id
    5. If authorized: return safe metadata
    6. If unauthorized: return 403 Forbidden
    
    Args:
        document_id: Document ID
        current_user: Authenticated user (from JWT)
        db: Database session
        
    Returns:
        Document metadata for authorized users
        
    Raises:
        NotFoundError: Document does not exist (404)
        ForbiddenError: User does not have access (403)
        
    Security:
        - Authentication required (401 if missing)
        - Authorization enforced (403 if denied)
        - Department comes from PostgreSQL (trusted)
        - Client cannot influence authorization scope
        - Generic error messages (no information leakage)
        
    Example:
        GET /api/documents/1
        Authorization: Bearer <token>
        
        Response (if authorized):
        {
            "id": 1,
            "name": "Deployment Guidelines",
            "department": {
                "id": 1,
                "name": "engineering"
            },
            "sensitivity": "internal",
            ...
        }
        
        Response (if unauthorized):
        403 Forbidden
        {
            "detail": "You do not have permission to access this resource"
        }
    """
    # Load document from PostgreSQL
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_id(document_id)
    
    if not document:
        logger.warning(f"Document {document_id} not found")
        raise NotFoundError(f"Document not found")
    
    # Authorization check: department-based access control
    # User's department comes from PostgreSQL (trusted source)
    # Document's department comes from PostgreSQL (trusted source)
    # Client cannot influence this check
    try:
        authorization_service.authorize_document_access(current_user, document)
    except ForbiddenError:
        # Log the authorization failure
        logger.warning(
            f"Authorization denied: user {current_user.id} "
            f"({current_user.department.name}) attempted to access "
            f"document {document.id} ({document.department.name})"
        )
        raise
    
    # Authorization successful
    logger.info(
        f"Document access granted: user {current_user.id} "
        f"({current_user.department.name}) accessing document {document.id}"
    )
    
    # Return safe metadata (not actual content)
    return DocumentMetadataResponse.model_validate(document)
