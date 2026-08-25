"""
Logging configuration
"""
import logging
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure application logging.
    
    Logs are written to stdout in a structured format.
    Sensitive information (API keys, secrets, passwords) must never be logged.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Reduce noise from external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def sanitize_log_data(data: Any) -> Any:
    """
    Remove sensitive information from log data.
    
    This is a placeholder for future implementation.
    Should filter out: API keys, passwords, JWT tokens, etc.
    
    Args:
        data: Data to sanitize
        
    Returns:
        Sanitized data safe for logging
    """
    # TODO: Implement in later phases when handling sensitive data
    return data
