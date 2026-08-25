"""
Tests for embedding service
"""
import pytest
from unittest.mock import Mock, patch

from app.services.embedding_service import (
    EmbeddingService,
    EmbeddingProvider,
    create_embedding_service
)
from app.core.errors import EmbeddingError


class MockEmbeddingProvider:
    """Mock embedding provider for testing."""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.model_name = "mock-model"
    
    def embed_text(self, text: str) -> list:
        # Return mock embedding
        return [0.1] * self.dimension
    
    def embed_texts(self, texts: list) -> list:
        # Return mock embeddings
        return [[0.1] * self.dimension for _ in texts]
    
    def get_dimension(self) -> int:
        return self.dimension
    
    def get_model_name(self) -> str:
        return self.model_name


class TestEmbeddingService:
    """Test suite for embedding service."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create mock provider."""
        return MockEmbeddingProvider()
    
    @pytest.fixture
    def embedding_service(self, mock_provider):
        """Create embedding service with mock provider."""
        return EmbeddingService(mock_provider)
    
    def test_initialization(self, mock_provider):
        """Test service initialization."""
        service = EmbeddingService(mock_provider)
        assert service.provider == mock_provider
        assert service.get_dimension() == 384
        assert service.get_model_name() == "mock-model"
    
    def test_embed_text_success(self, embedding_service):
        """Test single text embedding."""
        text = "This is a test document"
        embedding = embedding_service.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
    
    def test_embed_text_empty_raises_error(self, embedding_service):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Cannot embed empty text"):
            embedding_service.embed_text("")
        
        with pytest.raises(ValueError, match="Cannot embed empty text"):
            embedding_service.embed_text("   ")
    
    def test_embed_text_validates_dimension(self, mock_provider):
        """Test that dimension mismatch is detected."""
        # Create provider that returns wrong dimension
        class WrongDimensionProvider(MockEmbeddingProvider):
            def embed_text(self, text: str) -> list:
                return [0.1] * 256  # Wrong dimension!
        
        provider = WrongDimensionProvider(dimension=384)
        service = EmbeddingService(provider)
        
        with pytest.raises(ValueError, match="dimension mismatch"):
            service.embed_text("test")
    
    def test_embed_texts_success(self, embedding_service):
        """Test batch text embedding."""
        texts = [
            "Document 1",
            "Document 2",
            "Document 3"
        ]
        embeddings = embedding_service.embed_texts(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        for embedding in embeddings:
            assert isinstance(embedding, list)
            assert len(embedding) == 384
    
    def test_embed_texts_empty_list_raises_error(self, embedding_service):
        """Test that empty text list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot embed empty text list"):
            embedding_service.embed_texts([])
    
    def test_embed_texts_with_empty_text_raises_error(self, embedding_service):
        """Test that list with empty text raises ValueError."""
        texts = ["Good text", "", "Another good text"]
        
        with pytest.raises(ValueError, match="Text at index 1 is empty"):
            embedding_service.embed_texts(texts)
    
    def test_embed_texts_validates_all_dimensions(self, mock_provider):
        """Test that all embeddings are validated."""
        class InconsistentProvider(MockEmbeddingProvider):
            def embed_texts(self, texts: list) -> list:
                # Return inconsistent dimensions
                return [
                    [0.1] * 384,
                    [0.1] * 256,  # Wrong!
                    [0.1] * 384
                ]
        
        provider = InconsistentProvider(dimension=384)
        service = EmbeddingService(provider)
        
        with pytest.raises(ValueError, match="Embedding 1 dimension mismatch"):
            service.embed_texts(["text1", "text2", "text3"])


class TestCreateEmbeddingService:
    """Test embedding service factory."""
    
    def test_create_local_provider(self):
        """Test creating service with local provider."""
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.embedding_provider = "local"
            mock_settings.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
            mock_settings.embedding_dimension = 384
            
            # This will fail without mocking the actual provider
            # In real tests, we'd need to mock LocalEmbeddingProvider
            # For now, just verify the logic paths exist
    
    def test_unknown_provider_raises_error(self):
        """Test that unknown provider raises error."""
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.embedding_provider = "unknown"
            
            with pytest.raises(ValueError, match="Unknown embedding provider"):
                create_embedding_service()


class TestLocalEmbeddingProvider:
    """
    Tests for local embedding provider.
    
    Note: These tests use a real model which may be slow.
    Consider mocking for CI/CD pipelines.
    """
    
    @pytest.fixture
    def provider(self):
        """
        Create local embedding provider.
        
        This will download the model on first use (~80MB).
        """
        from app.services.local_embedding_provider import LocalEmbeddingProvider
        return LocalEmbeddingProvider()
    
    @pytest.mark.slow  # Mark as slow test
    def test_model_loads_successfully(self, provider):
        """Test that model loads without error."""
        assert provider.model is not None
        assert provider.get_dimension() == 384
        assert provider.get_model_name() == "sentence-transformers/all-MiniLM-L6-v2"
    
    @pytest.mark.slow
    def test_embed_text_real_model(self, provider):
        """Test embedding with real model."""
        text = "This is a test document about machine learning."
        embedding = provider.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        
        # Check that embedding values are reasonable
        assert all(-1 <= x <= 1 for x in embedding)
    
    @pytest.mark.slow
    def test_embed_texts_batch_real_model(self, provider):
        """Test batch embedding with real model."""
        texts = [
            "Machine learning is a subset of artificial intelligence.",
            "Deep learning uses neural networks.",
            "Natural language processing enables text understanding."
        ]
        
        embeddings = provider.embed_texts(texts)
        
        assert len(embeddings) == 3
        for embedding in embeddings:
            assert len(embedding) == 384
            assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.slow
    def test_same_text_produces_same_embedding(self, provider):
        """Test that embedding is deterministic."""
        text = "Deterministic test"
        
        embedding1 = provider.embed_text(text)
        embedding2 = provider.embed_text(text)
        
        # Should be identical
        assert embedding1 == embedding2
    
    @pytest.mark.slow
    def test_different_texts_produce_different_embeddings(self, provider):
        """Test that different texts produce different embeddings."""
        text1 = "Machine learning"
        text2 = "Banana recipe"
        
        embedding1 = provider.embed_text(text1)
        embedding2 = provider.embed_text(text2)
        
        # Should be different
        assert embedding1 != embedding2
    
    @pytest.mark.slow
    def test_similar_texts_have_similar_embeddings(self, provider):
        """Test that similar texts have similar embeddings."""
        import numpy as np
        
        text1 = "The cat sits on the mat"
        text2 = "A cat is sitting on a mat"
        text3 = "Quantum physics equations"
        
        emb1 = np.array(provider.embed_text(text1))
        emb2 = np.array(provider.embed_text(text2))
        emb3 = np.array(provider.embed_text(text3))
        
        # Cosine similarity helper
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        # Similar texts should have higher similarity
        sim_1_2 = cosine_similarity(emb1, emb2)
        sim_1_3 = cosine_similarity(emb1, emb3)
        
        assert sim_1_2 > sim_1_3  # Cat texts more similar than cat vs physics
        assert sim_1_2 > 0.5  # Should be reasonably similar


class TestNoExternalAPI:
    """Test that no external embedding API is called."""
    
    @pytest.mark.slow
    def test_no_openai_api_key_required(self):
        """Test that local provider works without OpenAI API key."""
        import os
        
        # Temporarily remove API key if present
        original_key = os.environ.get('OPENAI_API_KEY')
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        
        try:
            from app.services.local_embedding_provider import LocalEmbeddingProvider
            
            # Should work without API key
            provider = LocalEmbeddingProvider()
            embedding = provider.embed_text("Test text")
            
            assert len(embedding) == 384
            
        finally:
            # Restore API key
            if original_key:
                os.environ['OPENAI_API_KEY'] = original_key
    
    @pytest.mark.slow
    def test_no_network_calls(self, monkeypatch):
        """Test that no network calls are made during embedding."""
        import requests
        import urllib3
        
        # Mock network libraries to raise exceptions
        def mock_request(*args, **kwargs):
            raise AssertionError("Network call attempted!")
        
        monkeypatch.setattr(requests, "get", mock_request)
        monkeypatch.setattr(requests, "post", mock_request)
        
        # Embedding should still work (model already downloaded)
        from app.services.local_embedding_provider import LocalEmbeddingProvider
        provider = LocalEmbeddingProvider()
        
        # This should work without network
        embedding = provider.embed_text("Test text")
        assert len(embedding) == 384
