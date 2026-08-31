"""
Application configuration management
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    
    # Database
    database_url: str
    
    # Vector Database
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "knowledge_chunks"
    
    # Embeddings (Phase 7 - Local)
    embedding_provider: str = "local"  # local, openai (future), azure (future)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # all-MiniLM-L6-v2 produces 384-dim vectors
    embedding_batch_size: int = 32  # Batch size for local embedding generation
    
    # OpenAI (for future LLM phases)
    openai_api_key: Optional[str] = None
    
    # Azure OpenAI (Phase 9 - LLM Generation)
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: str = "gpt-4.1-mini"
    azure_openai_api_version: str = "2024-12-01-preview"
    llm_temperature: float = 0.0  # Deterministic for enterprise RAG
    llm_max_tokens: int = 1000  # Maximum response length
    
    # Authentication
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 1
    
    # RAG Configuration (Phase 6)
    chunk_size: int = 600
    chunk_overlap: int = 100
    
    # Retrieval Configuration (Phase 8)
    retrieval_top_k: int = 5  # Maximum number of chunks to retrieve
    retrieval_score_threshold: float = 0.4  # Minimum similarity score (cosine)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
