"""
MCP Server Authentication Service

Handles MCP token validation and authenticated request context.
"""
import httpx
from mcp_server.auth.token_service import validate_token_with_backend, MCPTokenResponse
from mcp_server.core.config import settings
from mcp_server.core.errors import AuthenticationError, BackendError
from mcp_server.core.logging import get_logger

logger = get_logger(__name__)

# Re-export for convenience
__all__ = ["AuthenticatedContext", "validate_mcp_token", "get_poc_auth_context"]


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


async def get_poc_auth_context() -> AuthenticatedContext:
    """
    POC: Get authenticated context using stored credentials.
    
    For proof-of-concept testing, this authenticates using credentials
    stored in environment variables (POC_USER_EMAIL, POC_USER_PASSWORD)
    instead of requiring a Bearer token.
    
    Flow:
    1. Get email/password from env vars
    2. Call backend /api/auth/login
    3. Call backend /api/auth/me to get user info
    4. Call backend /api/internal/mcp/create-token to get MCP token
    5. Validate token and return AuthenticatedContext
    
    Returns:
        AuthenticatedContext with user identity
        
    Raises:
        AuthenticationError: If credentials invalid or backend error
    """
    # Check if POC credentials are configured
    if not settings.poc_user_email or not settings.poc_user_password:
        raise AuthenticationError(
            "POC credentials not configured in .env (POC_USER_EMAIL, POC_USER_PASSWORD)"
        )
    
    try:
        async with httpx.AsyncClient(timeout=settings.backend_timeout) as client:
            # Step 1: Authenticate with backend
            login_response = await client.post(
                f"{settings.backend_url}/api/auth/login",
                json={
                    "email": settings.poc_user_email,
                    "password": settings.poc_user_password
                }
            )
            
            if login_response.status_code != 200:
                logger.error(f"POC login failed: {login_response.status_code} {login_response.text}")
                raise AuthenticationError("POC login failed")
            
            # Get JWT token
            login_data = login_response.json()
            access_token = login_data.get("access_token")
            
            if not access_token:
                raise AuthenticationError("No access token returned from login")
            
            # Step 2: Get user info from /api/auth/me
            me_response = await client.get(
                f"{settings.backend_url}/api/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if me_response.status_code != 200:
                logger.error(f"POC /api/auth/me failed: {me_response.status_code}")
                raise AuthenticationError("Failed to retrieve user info")
            
            user_data = me_response.json()
            user_id = user_data.get("id")
            username = user_data.get("username")
            
            # Step 3: Create MCP token via backend
            token_response = await client.post(
                f"{settings.backend_url}/api/internal/mcp/create-token",
                json={
                    "user_id": user_id,
                    "description": f"Claude MCP POC: {username}"
                },
                headers={
                    "X-Internal-Service": settings.internal_service_key or "mcp-server"
                }
            )
            
            if token_response.status_code != 201:
                logger.error(f"POC token creation failed: {token_response.status_code}")
                raise AuthenticationError("Failed to create MCP token")
            
            mcp_token = token_response.json().get("token")
            
            if not mcp_token:
                raise AuthenticationError("No MCP token returned")
            
            # Step 4: Validate the MCP token and get auth context
            logger.info(f"POC authentication successful for user: {username} (id={user_id})")
            
            # Validate the token we just created
            auth_context = await validate_mcp_token(mcp_token)
            return auth_context
            
    except httpx.TimeoutException:
        raise AuthenticationError("Backend timeout during POC authentication")
    except httpx.RequestError as e:
        raise AuthenticationError(f"Backend connection error: {e}")

