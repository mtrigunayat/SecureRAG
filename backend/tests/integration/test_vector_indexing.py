"""
Integration tests for Phase 7 vector indexing

These tests verify the complete flow:
1. Document ingestion (Phase 6)
2. Local embedding generation (Phase 7)
3. Vector indexing to Qdrant (Phase 7)
4. Re-indexing behavior
"""
import pytest
import os
from pathlib import Path
from datetime import datetime

from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService
from app.services.vector_indexing_service import VectorIndexingService
from app.services.qdrant_service import QdrantService
from app.repositories.document_repository import DocumentRepository
from app.core.config import settings


@pytest.mark.integration
@pytest.mark.slow
class TestVectorIndexingIntegration:
    """Integration tests for vector indexing."""
    
    @pytest.fixture(scope="class")
    def db(self):
        """Create database session."""
        session = SessionLocal()
        yield session
        session.close()
    
    @pytest.fixture(scope="class")
    def sample_pdf(self, tmp_path_factory):
        """
        Create a sample PDF for testing.
        
        In production tests, you would use a real PDF.
        For now, we'll skip if no sample is available.
        """
        # Check if sample PDF exists
        sample_path = Path(__file__).parent.parent.parent / "test_data" / "sample.pdf"
        
        if not sample_path.exists():
            pytest.skip("Sample PDF not available")
        
        return str(sample_path)
    
    def test_full_indexing_flow(self, db, sample_pdf):
        """
        Test complete indexing flow.
        
        Steps:
        1. Ingest document
        2. Generate embeddings locally
        3. Index to Qdrant
        4. Verify vectors
        """
        # Step 1: Ingest document
        ingestion_service = IngestionService(db)
        
        ingestion_result = ingestion_service.ingest_document(
            file_path=sample_pdf,
            document_name="Integration Test Document",
            department_name="engineering",
            sensitivity="internal"
        )
        
        assert ingestion_result.document_id is not None
        assert ingestion_result.chunk_count > 0
        assert len(ingestion_result.chunks) > 0
        
        # Verify chunks have department_id (ACL critical!)
        for chunk in ingestion_result.chunks:
            assert chunk.department_id is not None
            assert chunk.department_name == "engineering"
        
        # Step 2 & 3: Index document
        indexing_service = VectorIndexingService(db)
        
        indexing_result = indexing_service.index_document(ingestion_result)
        
        assert indexing_result.document_id == ingestion_result.document_id
        assert indexing_result.chunk_count == ingestion_result.chunk_count
        assert indexing_result.embedded_count == ingestion_result.chunk_count
        assert indexing_result.indexed_count == ingestion_result.chunk_count
        assert indexing_result.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert indexing_result.vector_dimension == 384
        assert indexing_result.collection == "knowledge_chunks"
        assert indexing_result.status == "indexed"
        
        # Step 4: Verify vectors in Qdrant
        qdrant_service = QdrantService()
        
        collection_info = qdrant_service.get_collection_info("knowledge_chunks")
        assert collection_info['vector_size'] == 384
        assert collection_info['distance'] == 'Cosine'
        assert collection_info['points_count'] >= indexing_result.indexed_count
        
        # Verify document was marked as indexed
        doc_repo = DocumentRepository(db)
        document = doc_repo.get_by_id(ingestion_result.document_id)
        assert document.indexed_at is not None
        
        # Clean up
        qdrant_service.delete_document_vectors("knowledge_chunks", ingestion_result.document_id)
        doc_repo.delete(document)
        db.commit()
    
    def test_reindexing_behavior(self, db, sample_pdf):
        """
        Test re-indexing behavior.
        
        Verifies:
        1. Initial indexing creates vectors
        2. Re-indexing deletes old vectors
        3. Re-indexing creates new vectors
        4. No duplicates
        """
        # Initial ingestion and indexing
        ingestion_service = IngestionService(db)
        indexing_service = VectorIndexingService(db)
        qdrant_service = QdrantService()
        
        ingestion_result = ingestion_service.ingest_document(
            file_path=sample_pdf,
            document_name="Reindex Test Document",
            department_name="engineering",
            sensitivity="internal"
        )
        
        # First indexing
        indexing_result_1 = indexing_service.index_document(ingestion_result)
        assert indexing_result_1.status == "indexed"
        
        # Get initial count
        collection_info_1 = qdrant_service.get_collection_info("knowledge_chunks")
        initial_count = collection_info_1['points_count']
        
        # Re-index (simulate document update)
        indexing_result_2 = indexing_service.index_document(ingestion_result)
        assert indexing_result_2.status == "re-indexed"
        
        # Verify count is same (no duplicates)
        collection_info_2 = qdrant_service.get_collection_info("knowledge_chunks")
        
        # Count should be same (old vectors deleted, new ones added)
        assert collection_info_2['points_count'] == initial_count
        
        # Clean up
        qdrant_service.delete_document_vectors("knowledge_chunks", ingestion_result.document_id)
        doc_repo = DocumentRepository(db)
        document = doc_repo.get_by_id(ingestion_result.document_id)
        doc_repo.delete(document)
        db.commit()
    
    def test_no_external_api_calls(self, db, sample_pdf):
        """
        CRITICAL: Test that no external API calls are made.
        
        Verifies:
        1. No OpenAI API key required
        2. Embedding cost is $0
        3. All processing is local
        """
        # Remove API key if present
        original_key = os.environ.get('OPENAI_API_KEY')
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        
        try:
            ingestion_service = IngestionService(db)
            indexing_service = VectorIndexingService(db)
            
            # Should work without API key
            ingestion_result = ingestion_service.ingest_document(
                file_path=sample_pdf,
                document_name="No API Test Document",
                department_name="engineering",
                sensitivity="internal"
            )
            
            indexing_result = indexing_service.index_document(ingestion_result)
            
            assert indexing_result.indexed_count > 0
            assert indexing_result.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
            
            # Clean up
            qdrant_service = QdrantService()
            qdrant_service.delete_document_vectors("knowledge_chunks", ingestion_result.document_id)
            doc_repo = DocumentRepository(db)
            document = doc_repo.get_by_id(ingestion_result.document_id)
            doc_repo.delete(document)
            db.commit()
            
        finally:
            # Restore API key
            if original_key:
                os.environ['OPENAI_API_KEY'] = original_key
    
    def test_vector_payload_structure(self, db, sample_pdf):
        """
        Test that vector payloads have correct structure.
        
        Verifies all required metadata is stored for Phase 8 ACL.
        """
        ingestion_service = IngestionService(db)
        indexing_service = VectorIndexingService(db)
        qdrant_service = QdrantService()
        
        ingestion_result = ingestion_service.ingest_document(
            file_path=sample_pdf,
            document_name="Payload Test Document",
            department_name="engineering",
            sensitivity="confidential"
        )
        
        indexing_result = indexing_service.index_document(ingestion_result)
        
        # Retrieve one vector to check payload
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        # Search for document vectors
        points = qdrant_service.client.scroll(
            collection_name="knowledge_chunks",
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=ingestion_result.document_id)
                    )
                ]
            ),
            limit=1
        )[0]
        
        assert len(points) > 0
        
        point = points[0]
        payload = point.payload
        
        # Verify all required fields
        assert 'document_id' in payload
        assert 'chunk_id' in payload
        assert 'document_name' in payload
        assert 'department_id' in payload  # ACL critical!
        assert 'department_name' in payload
        assert 'sensitivity' in payload
        assert 'page_start' in payload
        assert 'page_end' in payload
        assert 'chunk_index' in payload
        assert 'chunk_text' in payload
        
        # Verify values
        assert payload['document_id'] == ingestion_result.document_id
        assert payload['department_name'] == "engineering"
        assert payload['sensitivity'] == "confidential"
        assert payload['department_id'] is not None
        
        # Verify department_id is integer (for ACL filtering)
        assert isinstance(payload['department_id'], int)
        
        # Clean up
        qdrant_service.delete_document_vectors("knowledge_chunks", ingestion_result.document_id)
        doc_repo = DocumentRepository(db)
        document = doc_repo.get_by_id(ingestion_result.document_id)
        doc_repo.delete(document)
        db.commit()


@pytest.mark.integration
class TestQdrantCollectionSetup:
    """Test Qdrant collection setup."""
    
    def test_collection_has_correct_configuration(self):
        """Test that collection is configured correctly."""
        qdrant_service = QdrantService()
        
        # Ensure collection exists
        qdrant_service.ensure_collection(
            collection_name="knowledge_chunks",
            vector_size=384
        )
        
        # Get collection info
        info = qdrant_service.get_collection_info("knowledge_chunks")
        
        assert info['vector_size'] == 384
        assert info['distance'] == 'Cosine'
        assert info['status'] in ['green', 'yellow']  # Healthy
    
    def test_collection_idempotent_creation(self):
        """Test that collection creation is idempotent."""
        qdrant_service = QdrantService()
        
        # Create collection twice
        qdrant_service.ensure_collection(
            collection_name="knowledge_chunks",
            vector_size=384
        )
        
        qdrant_service.ensure_collection(
            collection_name="knowledge_chunks",
            vector_size=384
        )
        
        # Should not raise error
        info = qdrant_service.get_collection_info("knowledge_chunks")
        assert info['vector_size'] == 384


@pytest.mark.integration
class TestEmbeddingQuality:
    """Test embedding quality and consistency."""
    
    def test_embeddings_are_normalized(self):
        """Test that embeddings are properly normalized."""
        from app.services.embedding_service import get_embedding_service
        import numpy as np
        
        embedding_service = get_embedding_service()
        
        text = "This is a test document for embedding quality."
        embedding = embedding_service.embed_text(text)
        
        # Calculate L2 norm
        norm = np.linalg.norm(embedding)
        
        # Sentence-transformers embeddings are normalized
        assert 0.9 <= norm <= 1.1  # Should be close to 1
    
    def test_embeddings_are_deterministic(self):
        """Test that embeddings are deterministic."""
        from app.services.embedding_service import get_embedding_service
        
        embedding_service = get_embedding_service()
        
        text = "Deterministic embedding test"
        
        embedding1 = embedding_service.embed_text(text)
        embedding2 = embedding_service.embed_text(text)
        
        assert embedding1 == embedding2
    
    def test_batch_embeddings_match_individual(self):
        """Test that batch embeddings match individual embeddings."""
        from app.services.embedding_service import get_embedding_service
        
        embedding_service = get_embedding_service()
        
        texts = ["Text 1", "Text 2", "Text 3"]
        
        # Individual embeddings
        individual = [embedding_service.embed_text(text) for text in texts]
        
        # Batch embeddings
        batch = embedding_service.embed_texts(texts)
        
        assert len(batch) == len(individual)
        for i, (ind, bat) in enumerate(zip(individual, batch)):
            assert ind == bat, f"Embedding {i} mismatch"
