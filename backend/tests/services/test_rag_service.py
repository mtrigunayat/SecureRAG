"""
Unit tests for RAGService

Tests RAG orchestration with mocked dependencies.
"""
import pytest
from unittest.mock import Mock, MagicMock

from app.services.rag_service import RAGService
from app.services.llm_service import LLMResponse, LLMMessage
from app.schemas.retrieval import RetrievalResult, RetrievalChunk
from app.schemas.chat import ChatResponse
from app.models.user import User
from app.models.department import Department


class TestRAGService:
    """Test RAGService orchestration."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "mohit"
        user.department_id = 1
        user.department = Mock(spec=Department)
        user.department.id = 1
        user.department.name = "engineering"
        return user
    
    @pytest.fixture
    def mock_retrieval_service(self):
        """Create mock retrieval service."""
        return Mock()
    
    @pytest.fixture
    def mock_prompt_builder(self):
        """Create mock prompt builder."""
        return Mock()
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        return Mock()
    
    @pytest.fixture
    def rag_service(self, mock_db, mock_retrieval_service, mock_prompt_builder, mock_llm_service):
        """Create RAGService with mocked dependencies."""
        return RAGService(
            db=mock_db,
            retrieval_service=mock_retrieval_service,
            prompt_builder=mock_prompt_builder,
            llm_service=mock_llm_service
        )
    
    def test_generate_success(
        self,
        rag_service,
        mock_user,
        mock_retrieval_service,
        mock_prompt_builder,
        mock_llm_service
    ):
        """Test successful RAG generation."""
        # Setup retrieval result
        retrieval_result = RetrievalResult(
            question="What is our deployment process?",
            chunks=[
                RetrievalChunk(
                    chunk_id="chunk1",
                    document_id=1,
                    document_name="Engineering Handbook",
                    department_id=1,
                    department_name="engineering",
                    sensitivity="internal",
                    page_start=5,
                    page_end=6,
                    chunk_index=0,
                    chunk_text="The deployment process involves three stages...",
                    score=0.87
                )
            ],
            retrieved_count=1,
            user_department_id=1,
            user_department_name="engineering"
        )
        mock_retrieval_service.retrieve.return_value = retrieval_result
        
        # Setup prompt builder
        messages = [
            LLMMessage(role="system", content="System instructions"),
            LLMMessage(role="user", content="Context + question")
        ]
        mock_prompt_builder.build_messages.return_value = messages
        
        # Setup LLM response
        llm_response = LLMResponse(
            content="The deployment process has three stages: build, test, and release...",
            model="gpt-4.1-mini",
            finish_reason="stop",
            prompt_tokens=500,
            completion_tokens=100,
            total_tokens=600
        )
        mock_llm_service.generate.return_value = llm_response
        
        # Execute
        response = rag_service.generate(
            question="What is our deployment process?",
            authenticated_user=mock_user
        )
        
        # Verify retrieval was called
        mock_retrieval_service.retrieve.assert_called_once_with(
            question="What is our deployment process?",
            authenticated_user=mock_user
        )
        
        # Verify prompt builder was called
        mock_prompt_builder.build_messages.assert_called_once()
        
        # Verify LLM was called
        mock_llm_service.generate.assert_called_once()
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert response.answer == llm_response.content
        assert response.retrieved_count == 1
        assert response.user_department_name == "engineering"
        assert response.model == "gpt-4.1-mini"
        assert len(response.sources) == 1
        assert response.sources[0].document_name == "Engineering Handbook"
    
    def test_generate_empty_retrieval_no_llm_call(
        self,
        rag_service,
        mock_user,
        mock_retrieval_service,
        mock_prompt_builder,
        mock_llm_service
    ):
        """Test that empty retrieval does NOT call LLM."""
        # Setup empty retrieval result
        retrieval_result = RetrievalResult(
            question="What is quantum physics?",
            chunks=[],
            retrieved_count=0,
            user_department_id=1,
            user_department_name="engineering"
        )
        mock_retrieval_service.retrieve.return_value = retrieval_result
        
        # Execute
        response = rag_service.generate(
            question="What is quantum physics?",
            authenticated_user=mock_user
        )
        
        # Verify LLM was NOT called
        mock_llm_service.generate.assert_not_called()
        mock_prompt_builder.build_messages.assert_not_called()
        
        # Verify controlled response
        assert "don't have enough information" in response.answer.lower() or \
               "do not have enough information" in response.answer.lower()
        assert response.retrieved_count == 0
        assert response.sources == []
        assert response.model == "none"
    
    def test_sources_are_backend_controlled(
        self,
        rag_service,
        mock_user,
        mock_retrieval_service,
        mock_prompt_builder,
        mock_llm_service
    ):
        """Test that sources come from retrieval, not LLM output."""
        # Setup retrieval with multiple chunks
        retrieval_result = RetrievalResult(
            question="What is our leave policy?",
            chunks=[
                RetrievalChunk(
                    chunk_id="chunk1",
                    document_id=1,
                    document_name="HR Handbook",
                    department_id=2,
                    department_name="hr",
                    sensitivity="internal",
                    page_start=12,
                    page_end=13,
                    chunk_index=0,
                    chunk_text="Leave policy text...",
                    score=0.90
                ),
                RetrievalChunk(
                    chunk_id="chunk2",
                    document_id=1,  # Same document
                    document_name="HR Handbook",
                    department_id=2,
                    department_name="hr",
                    sensitivity="internal",
                    page_start=13,
                    page_end=14,
                    chunk_index=1,
                    chunk_text="More leave policy text...",
                    score=0.85
                ),
                RetrievalChunk(
                    chunk_id="chunk3",
                    document_id=2,  # Different document
                    document_name="Employee Guide",
                    department_id=2,
                    department_name="hr",
                    sensitivity="internal",
                    page_start=5,
                    page_end=6,
                    chunk_index=0,
                    chunk_text="PTO accrual...",
                    score=0.82
                )
            ],
            retrieved_count=3,
            user_department_id=2,
            user_department_name="hr"
        )
        mock_retrieval_service.retrieve.return_value = retrieval_result
        
        # Setup LLM response (without source references)
        llm_response = LLMResponse(
            content="Employees receive PTO...",
            model="gpt-4.1-mini"
        )
        mock_llm_service.generate.return_value = llm_response
        mock_prompt_builder.build_messages.return_value = []
        
        # Execute
        response = rag_service.generate(
            question="What is our leave policy?",
            authenticated_user=mock_user
        )
        
        # Verify sources are from retrieval (deduplicated by document_id)
        assert len(response.sources) == 2  # 2 unique documents
        
        # Verify source metadata comes from retrieval
        source_docs = {s.document_id for s in response.sources}
        assert 1 in source_docs  # HR Handbook
        assert 2 in source_docs  # Employee Guide
    
    def test_department_from_authenticated_user(
        self,
        rag_service,
        mock_user,
        mock_retrieval_service,
        mock_prompt_builder,
        mock_llm_service
    ):
        """Test that department comes from authenticated user object."""
        # Setup
        retrieval_result = RetrievalResult(
            question="test",
            chunks=[],
            retrieved_count=0,
            user_department_id=1,
            user_department_name="engineering"
        )
        mock_retrieval_service.retrieve.return_value = retrieval_result
        
        # Execute
        rag_service.generate(
            question="test",
            authenticated_user=mock_user
        )
        
        # Verify retrieval service was called with authenticated user
        call_args = mock_retrieval_service.retrieve.call_args
        assert call_args.kwargs["authenticated_user"] == mock_user


class TestRAGServiceSecurity:
    """Test RAG service security properties."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.department_id = 1
        user.department = Mock(spec=Department)
        user.department.id = 1
        user.department.name = "engineering"
        return user
    
    @pytest.fixture
    def rag_service(self, mock_db):
        """Create RAGService with mocked dependencies."""
        retrieval_service = Mock()
        prompt_builder = Mock()
        llm_service = Mock()
        
        return RAGService(
            db=mock_db,
            retrieval_service=retrieval_service,
            prompt_builder=prompt_builder,
            llm_service=llm_service
        )
    
    def test_no_unauthorized_context_reaches_llm(self, rag_service, mock_user):
        """
        CRITICAL SECURITY TEST: LLM only receives authorized chunks.
        
        This test verifies that the prompt builder receives ONLY
        chunks from the retrieval service (which are already ACL-filtered).
        """
        # Setup retrieval with authorized chunks
        authorized_chunks = [
            RetrievalChunk(
                chunk_id="chunk1",
                document_id=1,
                document_name="Engineering Doc",
                department_id=1,
                department_name="engineering",
                sensitivity="internal",
                page_start=1,
                page_end=1,
                chunk_index=0,
                chunk_text="Engineering content",
                score=0.9
            )
        ]
        
        retrieval_result = RetrievalResult(
            question="test",
            chunks=authorized_chunks,
            retrieved_count=1,
            user_department_id=1,
            user_department_name="engineering"
        )
        
        rag_service.retrieval_service.retrieve.return_value = retrieval_result
        rag_service.llm_service.generate.return_value = LLMResponse(
            content="answer",
            model="gpt-4.1-mini"
        )
        rag_service.prompt_builder.build_messages.return_value = []
        
        # Execute
        rag_service.generate(question="test", authenticated_user=mock_user)
        
        # Verify prompt builder received ONLY authorized chunks
        call_args = rag_service.prompt_builder.build_messages.call_args
        received_chunks = call_args.kwargs["chunks"]
        
        assert len(received_chunks) == 1
        assert received_chunks[0].department_id == 1
        assert received_chunks[0].department_name == "engineering"
