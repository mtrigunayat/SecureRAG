"""
Tests for configuration management
"""
import os
import pytest
from app.core.config import Settings


def test_settings_default_values():
    """Test that settings have sensible defaults."""
    # Temporarily clear DATABASE_URL if set in environment
    original_db_url = os.environ.get("DATABASE_URL")
    
    try:
        # Set minimal required config
        os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
        
        settings = Settings()
        
        assert settings.app_env == "development"
        assert settings.app_port == 8000
        assert settings.log_level == "INFO"
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.jwt_algorithm == "HS256"
        assert settings.chunk_size == 600
        assert settings.chunk_overlap == 100
        assert settings.relevance_threshold == 0.7
    finally:
        # Restore original environment
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url


def test_settings_from_environment():
    """Test that settings can be loaded from environment variables."""
    original_env = os.environ.copy()
    
    try:
        os.environ["DATABASE_URL"] = "postgresql://custom:pass@localhost/custom_db"
        os.environ["APP_ENV"] = "production"
        os.environ["APP_PORT"] = "9000"
        os.environ["QDRANT_URL"] = "http://custom:6333"
        
        settings = Settings()
        
        assert settings.database_url == "postgresql://custom:pass@localhost/custom_db"
        assert settings.app_env == "production"
        assert settings.app_port == 9000
        assert settings.qdrant_url == "http://custom:6333"
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)
