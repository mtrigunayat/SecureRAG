"""
MCP Server Error Definitions

Custom exceptions for MCP server operations.
"""


class MCPServerException(Exception):
    """Base exception for MCP server errors."""
    
    def __init__(self, message: str, safe_message: str = None):
        """
        Initialize exception.
        
        Args:
            message: Internal error message (logged, not exposed to client)
            safe_message: Safe message to expose to client (generic)
        """
        self.message = message
        self.safe_message = safe_message or "Internal server error"
        super().__init__(self.message)


class AuthenticationError(MCPServerException):
    """MCP token authentication failed."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            safe_message="Authentication failed"
        )


class InvalidTokenError(AuthenticationError):
    """Invalid or malformed MCP token."""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)


class BackendError(MCPServerException):
    """Backend communication error."""
    
    def __init__(self, message: str, safe_message: str = None):
        super().__init__(
            message=message,
            safe_message=safe_message or "Backend service error"
        )


class BackendUnavailableError(BackendError):
    """Backend service is unavailable."""
    
    def __init__(self, message: str = "Backend service unavailable"):
        super().__init__(message, "Backend service unavailable")


class BackendTimeoutError(BackendError):
    """Backend request timed out."""
    
    def __init__(self, message: str = "Backend request timed out"):
        super().__init__(message, "Backend request timed out")


class BackendAuthenticationError(BackendError):
    """Backend rejected authentication."""
    
    def __init__(self, message: str = "Backend authentication failed"):
        super().__init__(message, "Backend authentication failed")


class InvalidBackendResponseError(BackendError):
    """Backend response is invalid or unexpected."""
    
    def __init__(self, message: str = "Invalid backend response"):
        super().__init__(message, "Invalid response from backend")
