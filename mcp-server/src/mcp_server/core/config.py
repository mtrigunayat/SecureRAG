"""
MCP Server Configuration

Loads configuration from environment variables and .env file.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    MCP Server configuration.
    
    Loads from environment variables or .env file.
    """
    
    # MCP Server
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 5000
    
    # Backend
    backend_url: str = "http://localhost:8000"
    backend_api_timeout: int = 30
    
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
