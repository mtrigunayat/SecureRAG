"""
RAG Service

Orchestrates the complete RAG (Retrieval-Augmented Generation) pipeline.

Architecture:

    User Question
        ↓
    Authentication (JWT)
        ↓
    RAGService ← THIS
        ↓
    ┌───────────────┬───────────────┐
    ↓               ↓               ↓
RetrievalService  PromptBuilder  LLMService
    ↓               ↓               ↓
Authorized      Secure         Azure GPT-4.1-mini
Chunks          Prompt
    ↓               ↓               ↓
    └───────────────┴───────────────┘
                    ↓
            Grounded Answer + Sources
"""
from typing import List
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.retrieval_service import RetrievalService
from app.services.prompt_builder import PromptBuilder
from app.services.llm_service import LLMService, LLMMessage
from app.services.providers.azure_openai_provider import get_azure_openai_provider
from app.schemas.retrieval import RetrievalChunk
from app.schemas.chat import ChatResponse, ChatSource
from app.core.config import settings
from app.core.errors import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)


class RAGService:
    """
    RAG service orchestrator.
    
    SECURITY ARCHITECTURE:
    
    1. Retrieval happens BEFORE LLM generation
    2. Authorization happens DURING retrieval (ACL filtering)
    3. Only authorized chunks reach the LLM
    4. Department resolution from PostgreSQL (never from client)
    5. System prompt is backend-controlled
    6. Context is backend-controlled
    7. Sources are backend-controlled (not LLM-generated)
    
    CRITICAL INVARIANT:
    
    NO UNAUTHORIZED DOCUMENT CONTENT MUST EVER REACH THE LLM.
    
    Flow:
    
    1. User authenticated → User object from PostgreSQL
    2. Department resolved → user.department.id (trusted)
    3. Query embedded → Local sentence-transformers (
$0)
    4. Qdrant search → ACL filter (department_id)
    5. Relevance threshold → score >= 0.7
    6. Authorized chunks → ONLY user's department
    7. Prompt construction → Secure separation
    8. LLM generation → Answer from authorized context
    9. Source attribution → Backend-controlled metadata
    
    Phase 8: Retrieval with ACL
    Phase 9: LLM generation (this service)
    """
    
    def __init__(
        self,
        db: Session,
        retrieval_service: RetrievalService = None,
        prompt_builder: PromptBuilder = None,
        llm_service: LLMService = None
    ):
        """
        Initialize RAG service.
        
        Args:
            db: Database session
            retrieval_service: Optional retrieval service (for testing)
            prompt_builder: Optional prompt builder (for testing)
            llm_service: Optional LLM service (for testing)
        """
        self.db = db
        
        # Dependencies (with dependency injection for testing)
        self.retrieval_service = retrieval_service or RetrievalService(db)
        self.prompt_builder = prompt_builder or PromptBuilder()
        
        # LLM service (with Azure provider)
        if llm_service is None:
            azure_provider = get_azure_openai_provider()
            self.llm_service = LLMService(provider=azure_provider)
        else:
            self.llm_service = llm_service
        
        logger.info("RAGService initialized")
    
    def generate(
        self,
        question: str,
        authenticated_user: User
    ) -> ChatResponse:
        """
        Generate a RAG-based answer for a user's question.
        
        Pipeline:
        
        1. Retrieve authorized chunks (Phase 8)
        2. Check if chunks are empty
           - If empty: Return controlled "no info" response (no LLM call)
           - If not empty: Continue to LLM
        3. Build secure prompt
        4. Call LLM
        5. Extract answer
        6. Attach backend-controlled sources
        7. Return response
        
        Args:
            question: User's question
            authenticated_user: Authenticated user from PostgreSQL
        
        Returns:
            ChatResponse with answer and sources
        
        Raises:
            LLMError: If LLM generation fails
        
        Security:
            - Department from authenticated_user.department (PostgreSQL)
            - ACL filtering happens in retrieval (before LLM)
            - Only authorized chunks reach LLM
            - System prompt is backend-controlled
            - Sources are backend-controlled
        """
        logger.info(
            "Starting RAG generation",
            extra={
                "user_id": authenticated_user.id,
                "department_id": authenticated_user.department_id
            }
        )
        
        # Step 1: Retrieve authorized chunks
        retrieval_result = self.retrieval_service.retrieve(
            question=question,
            authenticated_user=authenticated_user
        )
        
        logger.info(
            "Retrieval completed",
            extra={
                "retrieved_count": retrieval_result.retrieved_count,
                "user_department": retrieval_result.user_department_name
            }
        )
        
        # Step 2: Check if retrieval is empty
        if retrieval_result.retrieved_count == 0:
            logger.info("No relevant chunks retrieved - returning controlled response without LLM call")
            return self._build_empty_response(retrieval_result.user_department_name)
        
        # Step 3: Build secure prompt
        messages = self.prompt_builder.build_messages(
            question=question,
            chunks=retrieval_result.chunks
        )
        
        # Step 4: Call LLM
        try:
            llm_response = self.llm_service.generate(
                messages=messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens
            )
            
            logger.info(
                "LLM generation completed",
                extra={
                    "model": llm_response.model,
                    "finish_reason": llm_response.finish_reason,
                    "prompt_tokens": llm_response.prompt_tokens,
                    "completion_tokens": llm_response.completion_tokens
                }
            )
            
        except LLMError as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise
        
        # Step 5: Build backend-controlled sources
        sources = self._build_sources(retrieval_result.chunks)
        
        # Step 6: Return response
        response = ChatResponse(
            answer=llm_response.content,
            sources=sources,
            retrieved_count=retrieval_result.retrieved_count,
            user_department_name=retrieval_result.user_department_name,
            model=llm_response.model
        )
        
        logger.info("RAG generation completed successfully")
        
        return response
    
    def _build_empty_response(self, user_department_name: str) -> ChatResponse:
        """
        Build controlled response when no relevant chunks are retrieved.
        
        This avoids unnecessary LLM calls and prevents hallucination.
        
        Args:
            user_department_name: User's department name
        
        Returns:
            ChatResponse with controlled "no info" message
        
        Security:
            - Does NOT call LLM
            - Does NOT hallucinate an answer
            - Does NOT search unauthorized departments
            - Does NOT lower threshold automatically
        """
        return ChatResponse(
            answer="I don't have enough information in the available documents to answer that question. The information may not exist in your department's knowledge base, or it may be phrased differently than your question.",
            sources=[],
            retrieved_count=0,
            user_department_name=user_department_name,
            model="none"
        )
    
    def _build_sources(self, chunks: List[RetrievalChunk]) -> List[ChatSource]:
        """
        Build backend-controlled source citations.
        
        Sources are derived from retrieval results, NOT from LLM output.
        This prevents the LLM from inventing source metadata.
        
        Args:
            chunks: Retrieved chunks from Phase 8
        
        Returns:
            List of ChatSource objects
        
        Security:
            - Sources come from Phase 8 retrieval (authorized)
            - LLM cannot invent sources
            - Source metadata is backend-controlled
        """
        # Deduplicate by document_id to avoid repeated citations
        seen_docs = set()
        sources = []
        
        for chunk in chunks:
            if chunk.document_id not in seen_docs:
                seen_docs.add(chunk.document_id)
                
                sources.append(
                    ChatSource(
                        document_id=chunk.document_id,
                        document_name=chunk.document_name,
                        department_name=chunk.department_name,
                        sensitivity=chunk.sensitivity,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        score=chunk.score
                    )
                )
        
        return sources
