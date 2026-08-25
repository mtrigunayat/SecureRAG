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


class AuthenticationError(AppException):
    """Authentication failed error."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials error (generic message for security)."""
    
    def __init__(self):
        super().__init__(
            message="Invalid credentials",
            details={}
        )


class InvalidTokenError(AuthenticationError):
    """Invalid or malformed JWT token."""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(
            message=message,
            details={}
        )


class ExpiredTokenError(AuthenticationError):
    """Expired JWT token."""
    
    def __init__(self):
        super().__init__(
            message="Token has expired",
            details={}
        )


# ============================================================
# Authorization Errors (Phase 5)
# ============================================================

class AuthorizationError(AppException):
    """
    Base class for authorization errors.
    
    Authorization errors occur when an authenticated user
    attempts to access a resource they do not have permission for.
    
    HTTP Status: 403 Forbidden
    
    Distinction:
        - 401 Unauthorized: User is NOT authenticated
        - 403 Forbidden: User IS authenticated but lacks permission
    """
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details or {}
        )


class ForbiddenError(AuthorizationError):
    """
    Raised when an authenticated user does not have permission
    to access a resource.
    
    This is the primary authorization error.
    Use generic messages to avoid leaking information about
    resources the user should not know about.
    """
    
    def __init__(self, message: str = "You do not have permission to access this resource"):
        super().__init__(message, details={})


# ============================================================
# Resource Errors
# ============================================================

class NotFoundError(AppException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={}
        )


# ============================================================
# Ingestion Errors (Phase 6)
# ============================================================

class IngestionError(AppException):
    """
    Base class for document ingestion errors.
    
    Ingestion errors occur during document processing:
    file validation, text extraction, chunking, etc.
    
    HTTP Status: 400 Bad Request (user-correctable errors)
                 or 422 Unprocessable Entity (validation errors)
    """
    def __init__(self, message: str = "Document ingestion failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {}
        )


class UnsupportedFileError(IngestionError):
    """Unsupported file type error."""
    
    def __init__(self, file_type: Optional[str] = None):
        message = f"Unsupported file type: {file_type}" if file_type else "Unsupported file type"
        super().__init__(
            message=message,
            details={"supported_types": ["pdf"]}
        )


class InvalidPDFError(IngestionError):
    """Invalid or corrupt PDF file."""
    
    def __init__(self, reason: Optional[str] = None):
        message = f"Invalid PDF file: {reason}" if reason else "Invalid PDF file"
        super().__init__(message=message)


class EmptyDocumentError(IngestionError):
    """Document contains no extractable text."""
    
    def __init__(self):
        super().__init__(
            message="Document contains no extractable text. OCR is not currently supported.",
            details={"ocr_supported": False}
        )


class TextExtractionError(IngestionError):
    """Text extraction from document failed."""
    
    def __init__(self, reason: Optional[str] = None):
        message = f"Text extraction failed: {reason}" if reason else "Text extraction failed"
        super().__init__(message=message)


class ChunkingError(IngestionError):
    """Document chunking failed."""
    
    def __init__(self, reason: Optional[str] = None):
        message = f"Chunking failed: {reason}" if reason else "Chunking failed"
        super().__init__(message=message)


class DepartmentNotFoundError(IngestionError):
    """Department does not exist in database."""
    
    def __init__(self, department_name: str):
        super().__init__(
            message=f"Department '{department_name}' does not exist",
            details={"department_name": department_name}
        )


class InvalidSensitivityError(IngestionError):
    """Invalid document sensitivity level."""
    
    def __init__(self, sensitivity: str):
        super().__init__(
            message=f"Invalid sensitivity level: {sensitivity}",
            details={
                "provided": sensitivity,
                "valid_values": ["public", "internal", "confidential"]
            }
        )


# Future error classes for later phases:
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
    # Use FastAPI standard format: {"detail": "message"}
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
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
