"""
Tests for vector indexing service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from app.services.vector_indexing_service import VectorIndexingService
from app.schemas.ingestion import IngestionResult, DocumentChunk
from app.schemas.indexing import IndexingResult
from app.core.errors import VectorDBError, EmbeddingError


class TestVectorIndexingService:
    """Test suite for vector indexing service."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        service = Mock()
        service.embed_texts.return_value = [
            [0.1] * 384,
            [0.2] * 384,
            [0.3] * 384
        ]
        service.get_dimension.return_value = 384
        service.get_model_name.return_value = "sentence-transformers/all-MiniLM-L6-v2"
        return service
    
    @pytest.fixture
    def mock_qdrant_service(self):
        """Create mock Qdrant service."""
        service = Mock()
        service.collection_exists.return_value = False
        service.get_collection_info.return_value = {
            'points_count': 10,
            'vector_size': 384,
            'distance': 'Cosine',
            'status': 'green'
        }
        return service
    
    @pytest.fixture
    def indexing_service(self, mock_db, mock_embedding_service, mock_qdrant_service):
        """Create vector indexing service with mocks."""
        with patch('app.services.vector_indexing_service.get_embedding_service') as mock_get_emb:
            mock_get_emb.return_value = mock_embedding_service
            
            with patch('app.services.vector_indexing_service.get_qdrant_service') as mock_get_qd:
                mock_get_qd.return_value = mock_qdrant_service
                
                service = VectorIndexingService(mock_db)
                service.embedding_service = mock_embedding_service
                service.qdrant_service = mock_qdrant_service
                
                return service
    
    @pytest.fixture
    def sample_ingestion_result(self):
        """Create sample ingestion result."""
        return IngestionResult(
            document_id=1,
            document_name="Test Document",
            department_name="engineering",
            sensitivity="internal",
            page_count=5,
            character_count=1000,
            chunk_count=3,
            content_hash="abc123",
            status="NEW_DOCUMENT_INGESTED",
            chunks=[
                DocumentChunk(
                    chunk_id="doc1_chunk0",
                    document_id=1,
                    document_name="Test Document",
                    department_id=10,
                    department_name="engineering",
                    sensitivity="internal",
                    page_start=1,
                    page_end=2,
                    chunk_index=0,
                    text="This is the first chunk of text."
                ),
                DocumentChunk(
                    chunk_id="doc1_chunk1",
                    document_id=1,
                    document_name="Test Document",
                    department_id=10,
                    department_name="engineering",
                    sensitivity="internal",
                    page_start=2,
                    page_end=3,
                    chunk_index=1,
                    text="This is the second chunk of text."
                ),
                DocumentChunk(
                    chunk_id="doc1_chunk2",
                    document_id=1,
                    document_name="Test Document",
                    department_id=10,
                    department_name="engineering",
                    sensitivity="internal",
                    page_start=3,
                    page_end=5,
                    chunk_index=2,
                    text="This is the third chunk of text."
                )
            ]
        )
    
    def test_initialization_creates_collection(self, mock_db, mock_embedding_service, mock_qdrant_service):
        """Test that initialization creates Qdrant collection."""
        with patch('app.services.vector_indexing_service.get_embedding_service') as mock_get_emb:
            mock_get_emb.return_value = mock_embedding_service
            
            with patch('app.services.vector_indexing_service.get_qdrant_service') as mock_get_qd:
                mock_get_qd.return_value = mock_qdrant_service
                
                service = VectorIndexingService(mock_db)
                
                # Should create collection
                mock_qdrant_service.ensure_collection.assert_called_once()
    
    def test_index_document_success(self, indexing_service, sample_ingestion_result, mock_db):
        """Test successful document indexing."""
        # Mock document repository
        mock_doc_repo = Mock()
        mock_document = Mock()
        mock_document.indexed_at = None  # Not previously indexed
        mock_doc_repo.get_by_id.return_value = mock_document
        
        with patch('app.services.vector_indexing_service.DocumentRepository') as MockDocRepo:
            MockDocRepo.return_value = mock_doc_repo
            
            result = indexing_service.index_document(sample_ingestion_result)
            
            # Verify result
            assert isinstance(result, IndexingResult)
            assert result.document_id == 1
            assert result.document_name == "Test Document"
            assert result.department_name == "engineering"
            assert result.chunk_count == 3
            assert result.embedded_count == 3
            assert result.indexed_count == 3
            assert result.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
            assert result.vector_dimension == 384
            assert result.collection == "knowledge_chunks"
            assert result.status == "indexed"
            
            # Verify embeddings were generated
            indexing_service.embedding_service.embed_texts.assert_called_once()
            call_args = indexing_service.embedding_service.embed_texts.call_args[0][0]
            assert len(call_args) == 3
            
            # Verify vectors were upserted
            indexing_service.qdrant_service.upsert_points.assert_called_once()
            
            # Verify document was updated
            assert mock_document.indexed_at is not None
            mock_db.commit.assert_called()
    
    def test_index_document_reindexing(self, indexing_service, sample_ingestion_result, mock_db):
        """Test re-indexing existing document."""
        # Mock document repository
        mock_doc_repo = Mock()
        mock_document = Mock()
        mock_document.indexed_at = datetime.utcnow()  # Previously indexed
        mock_doc_repo.get_by_id.return_value = mock_document
        
        with patch('app.services.vector_indexing_service.DocumentRepository') as MockDocRepo:
            MockDocRepo.return_value = mock_doc_repo
            
            result = indexing_service.index_document(sample_ingestion_result)
            
            # Should delete old vectors first
            indexing_service.qdrant_service.delete_document_vectors.assert_called_once_with(
                "knowledge_chunks", 1
            )
            
            # Then index new vectors
            indexing_service.qdrant_service.upsert_points.assert_called_once()
            
            assert result.status == "re-indexed"
    
    def test_index_document_creates_correct_points(self, indexing_service, sample_ingestion_result, mock_db):
        """Test that Qdrant points are created with correct structure."""
        # Mock document repository
        mock_doc_repo = Mock()
        mock_document = Mock()
        mock_document.indexed_at = None
        mock_doc_repo.get_by_id.return_value = mock_document
        
        with patch('app.services.vector_indexing_service.DocumentRepository') as MockDocRepo:
            MockDocRepo.return_value = mock_doc_repo
            
            result = indexing_service.index_document(sample_ingestion_result)
            
            # Get the points that were created
            call_args = indexing_service.qdrant_service.upsert_points.call_args
            collection_name = call_args[0][0]
            points = call_args[0][1]
            
            assert collection_name == "knowledge_chunks"
            assert len(points) == 3
            
            # Verify first point structure
            point = points[0]
            assert point.id == "doc1_chunk0"
            assert len(point.vector) == 384
            
            # Verify payload structure (ACL critical!)
            payload = point.payload
            assert payload['document_id'] == 1
            assert payload['chunk_id'] == "doc1_chunk0"
            assert payload['document_name'] == "Test Document"
            assert payload['department_id'] == 10  # ACL critical!
            assert payload['department_name'] == "engineering"
            assert payload['sensitivity'] == "internal"
            assert payload['page_start'] == 1
            assert payload['page_end'] == 2
            assert payload['chunk_index'] == 0
            assert payload['chunk_text'] == "This is the first chunk of text."
    
    def test_index_document_embedding_error(self, indexing_service, sample_ingestion_result, mock_db):
        """Test handling of embedding error."""
        # Mock document repository
        mock_doc_repo = Mock()
        mock_document = Mock()
        mock_document.indexed_at = None
        mock_doc_repo.get_by_id.return_value = mock_document
        
        # Make embedding service raise error
        indexing_service.embedding_service.embed_texts.side_effect = EmbeddingError("Model failed")
        
        with patch('app.services.vector_indexing_service.DocumentRepository') as MockDocRepo:
            MockDocRepo.return_value = mock_doc_repo
            
            with pytest.raises(EmbeddingError, match="Model failed"):
                indexing_service.index_document(sample_ingestion_result)
            
            # Should not have updated database
            assert not mock_db.commit.called
    
    def test_index_document_vector_db_error(self, indexing_service, sample_ingestion_result, mock_db):
        """Test handling of vector database error."""
        # Mock document repository
        mock_doc_repo = Mock()
        mock_document = Mock()
        mock_document.indexed_at = None
        mock_doc_repo.get_by_id.return_value = mock_document
        
        # Make Qdrant service raise error
        indexing_service.qdrant_service.upsert_points.side_effect = VectorDBError("Qdrant failed")
        
        with patch('app.services.vector_indexing_service.DocumentRepository') as MockDocRepo:
            MockDocRepo.return_value = mock_doc_repo
            
            with pytest.raises(VectorDBError, match="Qdrant failed"):
                indexing_service.index_document(sample_ingestion_result)
            
            # Should not have updated database
            assert not mock_db.commit.called
    
    def test_index_document_no_chunks(self, indexing_service, mock_db):
        """Test indexing document with no chunks."""
        # Mock document repository
        mock_doc_repo = Mock()
        
        # Empty ingestion result
        empty_result = IngestionResult(
            document_id=1,
            document_name="Empty Doc",
            department_name="engineering",
            sensitivity="internal",
            page_count=0,
            character_count=0,
            chunk_count=0,
            content_hash="empty",
            status="NEW_DOCUMENT_INGESTED",
            chunks=[]
        )
        
        with patch('app.services.vector_indexing_service.DocumentRepository') as MockDocRepo:
            MockDocRepo.return_value = mock_doc_repo
            
            with pytest.raises(ValueError, match="No chunks to index"):
                indexing_service.index_document(empty_result)
    
    def test_get_collection_info(self, indexing_service):
        """Test getting collection info."""
        info = indexing_service.get_collection_info()
        
        assert info['points_count'] == 10
        assert info['vector_size'] == 384
        assert info['distance'] == 'Cosine'
        assert info['status'] == 'green'
        
        indexing_service.qdrant_service.get_collection_info.assert_called_once_with("knowledge_chunks")
    
    def test_department_id_comes_from_chunk(self, indexing_service, sample_ingestion_result, mock_db):
        """
        CRITICAL: Test that department_id comes from chunk (PostgreSQL metadata).
        
        department_id MUST come from trusted database, never from client input.
        This is the ACL foundation for Phase 8.
        """
        # Mock document repository
        mock_doc_repo = Mock()
        mock_document = Mock()
        mock_document.indexed_at = None
        mock_doc_repo.get_by_id.return_value = mock_document
        
        with patch('app.services.vector_indexing_service.DocumentRepository') as MockDocRepo:
            MockDocRepo.return_value = mock_doc_repo
            
            result = indexing_service.index_document(sample_ingestion_result)
            
            # Verify points have department_id from chunk
            call_args = indexing_service.qdrant_service.upsert_points.call_args
            points = call_args[0][1]
            
            for point, chunk in zip(points, sample_ingestion_result.chunks):
                assert point.payload['department_id'] == chunk.department_id
                assert point.payload['department_id'] == 10  # From PostgreSQL
                
                # Verify chunk has department_id (Phase 6 contract)
                assert hasattr(chunk, 'department_id')
                assert chunk.department_id is not None


class TestVectorIDStrategy:
    """Test vector ID generation strategy."""
    
    def test_vector_id_is_deterministic(self):
        """
        Test that vector IDs are deterministic.
        
        Using chunk_id as vector ID ensures:
        1. Deterministic IDs (same chunk = same ID)
        2. Idempotent indexing (re-indexing updates, doesn't duplicate)
        3. Easy deletion by document (filter by document_id)
        """
        from app.schemas.ingestion import DocumentChunk
        
        chunk = DocumentChunk(
            chunk_id="doc1_chunk0",
            document_id=1,
            document_name="Test Document",
            department_id=10,
            department_name="engineering",
            sensitivity="internal",
            page_start=1,
            page_end=2,
            chunk_index=0,
            text="Test text"
        )
        
        # Vector ID should be chunk_id
        assert chunk.chunk_id == "doc1_chunk0"
        
        # Re-processing same chunk should have same ID
        chunk2 = DocumentChunk(
            chunk_id="doc1_chunk0",  # Same ID
            document_id=1,
            document_name="Test Document",
            department_id=10,
            department_name="engineering",
            sensitivity="internal",
            page_start=1,
            page_end=2,
            chunk_index=0,
            text="Test text"
        )
        
        assert chunk.chunk_id == chunk2.chunk_id
