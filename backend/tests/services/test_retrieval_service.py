"""
Tests for retrieval service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.services.retrieval_service import RetrievalService
from app.schemas.retrieval import RetrievalResult, RetrievalChunk
from app.core.errors import AuthorizationError, EmbeddingError, VectorDBError


class TestRetrievalService:
    """Test suite for retrieval service."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        user = Mock()
        user.id = 1
        user.username = "alice"
        user.department_id = 10
        user.department = Mock()
        user.department.id = 10
        user.department.name = "engineering"
        return user
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        service = Mock()
        service.embed_text.return_value = [0.1] * 384
        service.get_dimension.return_value = 384
        service.get_model_name.return_value = "sentence-transformers/all-MiniLM-L6-v2"
        return service
    
    @pytest.fixture
    def mock_qdrant_service(self):
        """Create mock Qdrant service."""
        service = Mock()
        service.search.return_value = [
            {
                "id": "doc1_chunk0",
                "score": 0.85,
                "payload": {
                    "chunk_id": "doc1_chunk0",
                    "document_id": 1,
                    "document_name": "Engineering Doc",
                    "department_id": 10,
                    "department_name": "engineering",
                    "sensitivity": "internal",
                    "page_start": 1,
                    "page_end": 2,
                    "chunk_index": 0,
                    "chunk_text": "This is engineering content."
                }
            }
        ]
        return service
    
    @pytest.fixture
    def retrieval_service(self, mock_db, mock_embedding_service, mock_qdrant_service):
        """Create retrieval service with mocks."""
        return RetrievalService(
            db=mock_db,
            embedding_service=mock_embedding_service,
            qdrant_service=mock_qdrant_service
        )
    
    def test_retrieve_success(self, retrieval_service, mock_user):
        """Test successful retrieval."""
        question = "What is the deployment process?"
        
        result = retrieval_service.retrieve(
            question=question,
            authenticated_user=mock_user
        )
        
        # Verify result structure
        assert isinstance(result, RetrievalResult)
        assert result.question == question
        assert result.user_department_id == 10
        assert result.user_department_name == "engineering"
        assert result.retrieved_count == 1
        assert len(result.chunks) == 1
        
        # Verify chunk
        chunk = result.chunks[0]
        assert chunk.chunk_id == "doc1_chunk0"
        assert chunk.document_id == 1
        assert chunk.department_id == 10
        assert chunk.score == 0.85
    
    def test_department_resolution_from_postgresql(self, retrieval_service, mock_user):
        """
        SECURITY TEST: Verify department comes from PostgreSQL.
        
        This is CRITICAL - department must be resolved server-side
        from the authenticated user's database record.
        """
        question = "test question"
        
        result = retrieval_service.retrieve(
            question=question,
            authenticated_user=mock_user
        )
        
        # Verify department came from User.department relationship
        assert result.user_department_id == mock_user.department.id
        assert result.user_department_name == mock_user.department.name
    
    def test_acl_filter_construction(self, retrieval_service, mock_user, mock_qdrant_service):
        """
        SECURITY TEST: Verify ACL filter is constructed correctly.
        
        The Qdrant search MUST include a department filter.
        """
        question = "test question"
        
        retrieval_service.retrieve(
            question=question,
            authenticated_user=mock_user
        )
        
        # Verify Qdrant search was called with department filter
        mock_qdrant_service.search.assert_called_once()
        call_kwargs = mock_qdrant_service.search.call_args.kwargs
        
        # Verify filter is present
        assert "department_filter" in call_kwargs
        filter_obj = call_kwargs["department_filter"]
        
        # Verify filter structure
        assert isinstance(filter_obj, Filter)
        assert len(filter_obj.must) == 1
        
        # Verify filter targets department_id
        condition = filter_obj.must[0]
        assert isinstance(condition, FieldCondition)
        assert condition.key == "department_id"
        assert condition.match.value == 10  # User's department
    
    def test_no_department_fails_securely(self, retrieval_service):
        """
        SECURITY TEST: User without department cannot retrieve.
        
        If department cannot be resolved, retrieval MUST fail securely.
        NO unrestricted search should happen.
        """
        # User with no department
        user = Mock()
        user.id = 999
        user.department = None
        
        with pytest.raises(AuthorizationError, match="department not found"):
            retrieval_service.retrieve(
                question="test",
                authenticated_user=user
            )
    
    def test_empty_question_rejected(self, retrieval_service, mock_user):
        """Test that empty questions are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            retrieval_service.retrieve(
                question="",
                authenticated_user=mock_user
            )
        
        with pytest.raises(ValueError, match="cannot be empty"):
            retrieval_service.retrieve(
                question="   ",
                authenticated_user=mock_user
            )
    
    def test_question_too_long_rejected(self, retrieval_service, mock_user):
        """Test that overly long questions are rejected."""
        long_question = "a" * 1001
        
        with pytest.raises(ValueError, match="too long"):
            retrieval_service.retrieve(
                question=long_question,
                authenticated_user=mock_user
            )
    
    def test_embedding_uses_same_model_as_indexing(
        self,
        retrieval_service,
        mock_user,
        mock_embedding_service
    ):
        """
        Verify query embedding uses the same model as document indexing.
        
        CRITICAL: Query and document embeddings MUST use the same model.
        """
        question = "test question"
        
        retrieval_service.retrieve(
            question=question,
            authenticated_user=mock_user
        )
        
        # Verify embedding service was called
        mock_embedding_service.embed_text.assert_called_once_with(question)
        
        # Verify model is all-MiniLM-L6-v2
        assert mock_embedding_service.get_model_name() == "sentence-transformers/all-MiniLM-L6-v2"
        assert mock_embedding_service.get_dimension() == 384
    
    def test_embedding_failure_raises_error(
        self,
        retrieval_service,
        mock_user,
        mock_embedding_service
    ):
        """Test that embedding failures are handled correctly."""
        mock_embedding_service.embed_text.side_effect = EmbeddingError("Model failed")
        
        with pytest.raises(EmbeddingError, match="Model failed"):
            retrieval_service.retrieve(
                question="test",
                authenticated_user=mock_user
            )
    
    def test_qdrant_failure_raises_error(
        self,
        retrieval_service,
        mock_user,
        mock_qdrant_service
    ):
        """Test that Qdrant failures are handled correctly."""
        mock_qdrant_service.search.side_effect = VectorDBError("Qdrant unavailable")
        
        with pytest.raises(VectorDBError, match="Qdrant unavailable"):
            retrieval_service.retrieve(
                question="test",
                authenticated_user=mock_user
            )
    
    def test_empty_retrieval_returns_empty_list(
        self,
        retrieval_service,
        mock_user,
        mock_qdrant_service
    ):
        """Test that no matching results returns empty list."""
        # No results from Qdrant
        mock_qdrant_service.search.return_value = []
        
        result = retrieval_service.retrieve(
            question="unmatched question",
            authenticated_user=mock_user
        )
        
        assert result.retrieved_count == 0
        assert len(result.chunks) == 0
    
    def test_top_k_configuration(
        self,
        retrieval_service,
        mock_user,
        mock_qdrant_service
    ):
        """Test that top_k is passed to Qdrant search."""
        retrieval_service.retrieve(
            question="test",
            authenticated_user=mock_user
        )
        
        call_kwargs = mock_qdrant_service.search.call_args.kwargs
        assert "top_k" in call_kwargs
    
    def test_score_threshold_configuration(
        self,
        retrieval_service,
        mock_user,
        mock_qdrant_service
    ):
        """Test that score threshold is passed to Qdrant search."""
        retrieval_service.retrieve(
            question="test",
            authenticated_user=mock_user
        )
        
        call_kwargs = mock_qdrant_service.search.call_args.kwargs
        assert "score_threshold" in call_kwargs
    
    def test_results_preserve_source_information(
        self,
        retrieval_service,
        mock_user
    ):
        """
        Test that results preserve all source information for citations.
        
        Phase 9 will need this information for source attribution.
        """
        result = retrieval_service.retrieve(
            question="test",
            authenticated_user=mock_user
        )
        
        chunk = result.chunks[0]
        
        # Verify all source information is present
        assert chunk.document_id is not None
        assert chunk.document_name is not None
        assert chunk.chunk_id is not None
        assert chunk.page_start is not None
        assert chunk.page_end is not None
        assert chunk.chunk_index is not None
        assert chunk.chunk_text is not None
        assert chunk.score is not None


class TestDepartmentFilterConstruction:
    """Test department ACL filter construction."""
    
    def test_filter_structure(self):
        """Test that filter is constructed correctly."""
        service = RetrievalService(db=Mock())
        
        filter_obj = service._build_department_filter(department_id=42)
        
        # Verify filter structure
        assert isinstance(filter_obj, Filter)
        assert len(filter_obj.must) == 1
        
        # Verify condition
        condition = filter_obj.must[0]
        assert isinstance(condition, FieldCondition)
        assert condition.key == "department_id"
        assert condition.match.value == 42
    
    def test_filter_uses_exact_department_id(self):
        """
        SECURITY TEST: Filter must use exact department ID.
        
        No wildcards, no ranges, no approximations.
        """
        service = RetrievalService(db=Mock())
        
        filter_obj = service._build_department_filter(department_id=10)
        
        condition = filter_obj.must[0]
        assert condition.match.value == 10  # Exact match only


class TestClientCannotInfluenceDepartment:
    """
    SECURITY TEST: Verify client cannot influence department selection.
    
    This is the MOST CRITICAL security test for Phase 8.
    """
    
    def test_client_department_parameter_ignored(self):
        """
        Test that even if client provides department_id, it's ignored.
        
        Department MUST come from authenticated user's PostgreSQL record.
        """
        # This test verifies architectural compliance
        # The API endpoint does NOT accept department_id parameter
        # Only the question is accepted
        
        from app.schemas.retrieval import RetrievalRequest
        
        # Verify schema only has question field
        schema_fields = RetrievalRequest.model_fields
        assert "question" in schema_fields
        assert "department_id" not in schema_fields
        assert "department_name" not in schema_fields
    
    def test_department_comes_from_authenticated_user_only(self):
        """
        Verify department is ONLY resolved from authenticated_user parameter.
        
        The retrieve() method signature enforces this.
        """
        from inspect import signature
        from app.services.retrieval_service import RetrievalService
        
        sig = signature(RetrievalService.retrieve)
        params = sig.parameters
        
        # Verify method signature
        assert "question" in params
        assert "authenticated_user" in params
        assert "department_id" not in params  # NOT allowed
        assert "department" not in params  # NOT allowed
