"""
Chat API endpoints

Phase 9: RAG-based chat completion with LLM generation.
"""
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.services.rag_service import RAGService
from app.schemas.chat import ChatRequest, ChatResponse
from app.core.errors import LLMError, AuthorizationError, VectorDBError, EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
) -> ChatResponse:
    """
    RAG-based chat completion.
    
    COMPLETE SECURE RAG PIPELINE:
    
    1. **Authentication** (JWT - mandatory)
       - User loaded from PostgreSQL
       - Department relationship included
    
    2. **Authorization** (Department-based)
       - Department resolved from PostgreSQL (TRUSTED)
       - Client CANNOT specify department
    
    3. **Retrieval** (Phase 8)
       - Query embedding (local, $0 cost)
       - Qdrant search WITH department ACL filter
       - Only authorized chunks returned
       - Relevance threshold: score >= 0.7
    
    4. **Generation** (Phase 9 - THIS ENDPOINT)
       - Secure prompt construction
       - Retrieved documents treated as UNTRUSTED DATA
       - System instructions backend-controlled
       - LLM generates answer from authorized context
       - Sources backend-controlled (not LLM-generated)
    
    SECURITY ARCHITECTURE:
    
        User Question (client)
            ↓
        JWT Authentication (required)
            ↓
        PostgreSQL User.department_id (TRUSTED)
            ↓
        Local Query Embedding ($0)
            ↓
        Qdrant Search + ACL Filter (department_id)
            ↓
        Authorized Chunks ONLY (score >= 0.7)
            ↓
        Secure Prompt Construction
            ├─ System: Trusted instructions
            ├─ Context: Untrusted data (documents)
            └─ User: Question
            ↓
        Azure GPT-4.1-mini
            ↓
        Grounded Answer
            ↓
        Backend-Controlled Sources
            ↓
        API Response
    
    CRITICAL SECURITY GUARANTEES:
    
    1. ✅ LLM receives ONLY authorized chunks
    2. ✅ Authorization happens BEFORE LLM generation
    3. ✅ Department from PostgreSQL (never from client)
    4. ✅ ACL filtering happens INSIDE Qdrant (not post-retrieval)
    5. ✅ System prompt is backend-controlled
    6. ✅ Retrieved documents treated as untrusted data
    7. ✅ Sources are backend-controlled (not LLM-generated)
    8. ✅ Empty retrieval does NOT call LLM
    9. ✅ Relevance threshold enforced (0.7)
    10. ✅ Same embedding model as indexing (consistency)
    
    Request Example:
        {
            "question": "What is our leave policy?"
        }
    
    Response Example:
        {
            "answer": "Full-time employees receive 20 days of PTO annually...",
            "sources": [
                {
                    "document_id": 5,
                    "document_name": "HR Policies 2024",
                    "department_name": "hr",
                    "sensitivity": "internal",
                    "page_start": 12,
                    "page_end": 13,
                    "score": 0.87
                }
            ],
            "retrieved_count": 1,
            "user_department_name": "hr",
            "model": "gpt-4.1-mini"
        }
    
    Security Notes:
        - Client provides ONLY the question
        - department_id is server-resolved
        - system_prompt is backend-controlled
        - context is backend-controlled
        - sources are backend-controlled
        - Client CANNOT inject arbitrary context
        - Client CANNOT modify system instructions
        - Client CANNOT access unauthorized departments
    
    Args:
        request: Chat request with question only
        current_user: Authenticated user (from JWT + PostgreSQL)
        db: Database session
    
    Returns:
        ChatResponse with answer and sources
    
    Raises:
        AuthenticationError: If JWT is invalid (401)
        AuthorizationError: If user has no department (403)
        EmbeddingError: If query embedding fails (500)
        VectorDBError: If Qdrant search fails (503)
        LLMError: If LLM generation fails (503)
    """
    logger.info(
        "Chat request received",
        extra={
            "user_id": current_user.id,
            "department_id": current_user.department_id,
            "question_length": len(request.question)
        }
    )
    
    try:
        # Create RAG service
        rag_service = RAGService(db)
        
        # Generate RAG-based response
        response = rag_service.generate(
            question=request.question,
            authenticated_user=current_user
        )
        
        logger.info(
            "Chat request completed",
            extra={
                "user_id": current_user.id,
                "retrieved_count": response.retrieved_count,
                "source_count": len(response.sources),
                "model": response.model
            }
        )
        
        return response
        
    except (EmbeddingError, VectorDBError, LLMError) as e:
        logger.error(
            f"Chat request failed: {str(e)}",
            extra={"user_id": current_user.id, "error_type": type(e).__name__}
        )
        raise
