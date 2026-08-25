"""
Application error definitions and handlers
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """
    Base exception for application-specific errors.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(AppException):
    """Database connection or query error."""
    
    def __init__(self, message: str = "Database error occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class VectorDBError(AppException):
    """Vector database connection or query error."""
    
    def __init__(self, message: str = "Vector database error occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


# Future error classes for later phases:
# class AuthenticationError(AppException)
# class AuthorizationError(AppException)
# class ValidationError(AppException)
# class RetrievalError(AppException)
# class LLMError(AppException)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Global handler for application exceptions.
    
    Args:
        request: FastAPI request object
        exc: Application exception
        
    Returns:
        JSON error response
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global handler for HTTP exceptions.
    
    Args:
        request: FastAPI request object
        exc: HTTP exception
        
    Returns:
        JSON error response
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global handler for unexpected exceptions.
    
    Args:
        request: FastAPI request object
        exc: Unexpected exception
        
    Returns:
        JSON error response (generic, doesn't expose internal details)
    """
    # Log the full error internally
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    # Return generic error to user (don't expose internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An unexpected error occurred"
        }
    )
