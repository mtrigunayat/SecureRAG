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
    
    # OpenAI (for future phases)
    openai_api_key: Optional[str] = None
    
    # Authentication (for future phases)
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 1
    
    # RAG Configuration (for future phases)
    chunk_size: int = 600
    chunk_overlap: int = 100
    relevance_threshold: float = 0.7
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
