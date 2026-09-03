"""
MCP Server Configuration

Loads configuration from environment variables and .env file.
Supports local development and cloud deployment (Render, Qdrant Cloud, etc.)
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    MCP Server configuration.
    
    Loads from environment variables or .env file.
    
    Local development:
        MCP_HOST=0.0.0.0
        MCP_PORT=5000
        BACKEND_URL=http://localhost:8000
    
    Cloud deployment (Render):
        MCP_HOST=0.0.0.0
        MCP_PORT={set by Render via PORT environment variable}
        BACKEND_URL=https://my-backend.onrender.com
    """
    
    # MCP Server
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 5000  # Overridden by PORT environment variable if set
    mcp_public_url: str = "http://localhost:5000"  # Public URL for OAuth discovery
    
    # Backend
    backend_url: str = "http://localhost:8000"  # Must be set to deployed backend URL in production
    backend_api_timeout: int = 30
    
    # Logging
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Override port from PORT environment variable if set (Render compatibility)
        import os
        if "PORT" in os.environ:
            self.mcp_port = int(os.environ["PORT"])


# Global settings instance
settings = Settings()
