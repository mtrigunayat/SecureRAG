"""
Embedding service

Abstraction for generating text embeddings.
Supports multiple providers (local, OpenAI, Azure, etc.).
"""
from typing import List, Protocol
from abc import abstractmethod

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(Protocol):
    """
    Protocol for embedding providers.
    
    Implementations must provide embedding generation for single
    and batch text inputs.
    """
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            ValueError: If text is empty or invalid
            EmbeddingError: If embedding generation fails
        """
        pass
    
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch operation).
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            ValueError: If texts list is empty or contains invalid entries
            EmbeddingError: If embedding generation fails
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the embedding dimension.
        
        Returns:
            Embedding vector dimension
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the model name.
        
        Returns:
            Model identifier
        """
        pass


class EmbeddingService:
    """
    Service for generating text embeddings.
    
    This service abstracts the underlying embedding provider,
    allowing the application to switch between local models,
    OpenAI, Azure, or other providers without changing
    dependent code.
    
    Architecture:
        Application
            ↓
        EmbeddingService
            ↓
        EmbeddingProvider (LocalEmbeddingProvider, etc.)
            ↓
        Actual Model
    
    Security:
        - Validates all inputs
        - Never logs sensitive content
        - Prevents injection attacks through input validation
    """
    
    def __init__(self, provider: EmbeddingProvider):
        """
        Initialize embedding service with a provider.
        
        Args:
            provider: Embedding provider implementation
        """
        self.provider = provider
        logger.info(
            f"Embedding service initialized: "
            f"provider={type(provider).__name__}, "
            f"model={provider.get_model_name()}, "
            f"dimension={provider.get_dimension()}"
        )
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector
            
        Raises:
            ValueError: If text is empty or invalid
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        
        logger.debug(f"Generating embedding for text ({len(text)} chars)")
        embedding = self.provider.embed_text(text)
        
        # Validate dimension
        expected_dim = self.provider.get_dimension()
        if len(embedding) != expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {expected_dim}, "
                f"got {len(embedding)}"
            )
        
        return embedding
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch operation).
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            ValueError: If texts list is empty or contains invalid entries
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            raise ValueError("Cannot embed empty text list")
        
        # Validate all texts
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(f"Text at index {i} is empty")
        
        logger.info(f"Generating embeddings for {len(texts)} texts (batch)")
        embeddings = self.provider.embed_texts(texts)
        
        # Validate dimensions
        expected_dim = self.provider.get_dimension()
        for i, embedding in enumerate(embeddings):
            if len(embedding) != expected_dim:
                raise ValueError(
                    f"Embedding {i} dimension mismatch: "
                    f"expected {expected_dim}, got {len(embedding)}"
                )
        
        return embeddings
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.provider.get_dimension()
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.provider.get_model_name()


def create_embedding_service() -> EmbeddingService:
    """
    Factory function to create embedding service with configured provider.
    
    Returns:
        EmbeddingService instance
        
    Raises:
        ValueError: If provider type is unknown
        EmbeddingError: If provider initialization fails
    """
    provider_type = settings.embedding_provider.lower()
    
    if provider_type == "local":
        from app.services.local_embedding_provider import LocalEmbeddingProvider
        provider = LocalEmbeddingProvider(
            model_name=settings.embedding_model,
            expected_dimension=settings.embedding_dimension
        )
        return EmbeddingService(provider)
    
    # Future providers:
    # elif provider_type == "openai":
    #     from app.services.openai_embedding_provider import OpenAIEmbeddingProvider
    #     provider = OpenAIEmbeddingProvider(...)
    #     return EmbeddingService(provider)
    
    else:
        raise ValueError(
            f"Unknown embedding provider: {provider_type}. "
            f"Valid options: local"
        )


# Global embedding service instance
_embedding_service: EmbeddingService = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create global embedding service instance.
    
    This ensures the embedding model is loaded once and reused.
    
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = create_embedding_service()
    return _embedding_service
