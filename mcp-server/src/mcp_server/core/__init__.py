"""
MCP Server Configuration

Loads environment variables for MCP server operation.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    MCP Server settings loaded from environment variables.
    
    The MCP server requires:
    - Backend URL (where existing FastAPI app runs)
    - Logging configuration
    - Network binding
    
    The MCP server does NOT require:
    - Database credentials (backend has the database)
    - Azure OpenAI keys (backend has the LLM)
    - Qdrant credentials (backend has the vector DB)
    - User passwords (we use MCP tokens)
    """
    
    # MCP Server Network
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 5000
    
    # Backend Communication
    backend_url: str = "http://localhost:8000"
    backend_api_timeout: int = 30  # seconds
    
    # Logging
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
