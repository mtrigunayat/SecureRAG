"""
Local embedding provider

Uses sentence-transformers for local, free embedding generation.
No external API calls, no API keys required.
"""
from typing import List
import numpy as np

from app.core.errors import EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalEmbeddingProvider:
    """
    Local embedding provider using sentence-transformers.
    
    This provider runs embeddings locally on CPU (or GPU if available).
    No external API calls, no API keys, $0 cost.
    
    Architecture:
        LocalEmbeddingProvider
            ↓
        SentenceTransformer
            ↓
        all-MiniLM-L6-v2
            ↓
        384-dimensional vectors
    
    Model:
        sentence-transformers/all-MiniLM-L6-v2
        - Dimension: 384
        - Size: ~80MB
        - Speed: Fast on CPU
        - Quality: Good for semantic similarity
        - License: Apache 2.0
    
    Important:
        The SAME model MUST be used for:
        - Document chunk embeddings (Phase 7)
        - Query embeddings (Phase 8)
        
        Both must exist in the same vector space.
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        expected_dimension: int = 384
    ):
        """
        Initialize local embedding provider.
        
        Args:
            model_name: Sentence-transformers model name
            expected_dimension: Expected embedding dimension
            
        Raises:
            EmbeddingError: If model loading fails
        """
        self.model_name = model_name
        self.expected_dimension = expected_dimension
        
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading local embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            
            # Verify dimension
            test_embedding = self.model.encode("test", convert_to_numpy=True)
            actual_dimension = len(test_embedding)
            
            if actual_dimension != expected_dimension:
                raise EmbeddingError(
                    f"Model {model_name} produces {actual_dimension}-dimensional "
                    f"embeddings, expected {expected_dimension}"
                )
            
            logger.info(
                f"Local embedding model loaded successfully: "
                f"{model_name} (dimension={actual_dimension})"
            )
            
        except ImportError as e:
            raise EmbeddingError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            ) from e
        except Exception as e:
            raise EmbeddingError(
                f"Failed to load embedding model {model_name}: {e}"
            ) from e
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            ValueError: If text is empty
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Convert numpy array to list
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch operation).
        
        This is more efficient than calling embed_text() multiple times
        as the model can process batches internally.
        
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
        
        try:
            logger.debug(f"Batch embedding {len(texts)} texts")
            
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                batch_size=32  # Process in batches
            )
            
            # Convert numpy arrays to lists
            return [emb.tolist() for emb in embeddings]
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise EmbeddingError(
                f"Failed to generate batch embeddings: {e}"
            ) from e
    
    def get_dimension(self) -> int:
        """
        Get the embedding dimension.
        
        Returns:
            Embedding vector dimension (384 for all-MiniLM-L6-v2)
        """
        return self.expected_dimension
    
    def get_model_name(self) -> str:
        """
        Get the model name.
        
        Returns:
            Model identifier
        """
        return self.model_name
