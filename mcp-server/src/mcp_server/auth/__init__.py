"""
MCP Server Authentication Service

Handles MCP token validation and authenticated request context.
"""
from mcp_server.auth.token_service import validate_token_with_backend, MCPTokenResponse

# Re-export for convenience
__all__ = ["AuthenticatedContext", "validate_mcp_token"]


class AuthenticatedContext:
    """
    Authenticated request context.
    
    Contains information about the authenticated user and is made available
    to MCP tool handlers through the request context.
    
    Security:
        - Contains user_id and department_name from backend
        - Resolved from database (authoritative source)
        - Client cannot override
    """
    
    def __init__(self, token_response: MCPTokenResponse):
        self.user_id = token_response.user_id
        self.username = token_response.username
        self.department_name = token_response.department_name
        self.backend_jwt = token_response.backend_jwt
    
    def __repr__(self) -> str:
        return (
            f"<AuthContext("
            f"user_id={self.user_id}, "
            f"username={self.username}, "
            f"dept={self.department_name}"
            f")>"
        )


async def validate_mcp_token(raw_token: str) -> AuthenticatedContext:
    """
    Validate MCP token and return authenticated context.
    
    This validates the MCP token by calling backend validation service.
    
    Args:
        raw_token: Raw MCP token string
        
    Returns:
        AuthenticatedContext with user identity
        
    Raises:
        AuthenticationError: If token invalid/expired/revoked
        BackendError: If backend error
    """
    # Remove "Bearer " prefix if present
    token = raw_token.replace("Bearer ", "").strip() if raw_token else ""
    
    # Validate with backend
    token_response = await validate_token_with_backend(token)
    
    # Return authenticated context
    return AuthenticatedContext(token_response)

