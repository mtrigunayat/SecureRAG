"""
MCP Token Service Client

Communicates with backend MCP token validation endpoint.
"""
import httpx
from typing import Optional

from mcp_server.core.config import settings
from mcp_server.core.logging import get_logger
from mcp_server.core.errors import (
    AuthenticationError,
    BackendError,
    BackendUnavailableError,
    BackendTimeoutError,
)

logger = get_logger(__name__)


class MCPTokenResponse:
    """Response from backend MCP token validation."""
    
    def __init__(self, data: dict):
        self.user_id: int = data["user_id"]
        self.username: str = data["username"]
        self.department_name: str = data["department_name"]
        self.backend_jwt: str = data["backend_jwt"]
        self.expires_in: int = data["expires_in"]
    
    def __repr__(self) -> str:
        return (
            f"<MCPTokenResponse("
            f"user_id={self.user_id}, "
            f"username={self.username}, "
            f"dept={self.department_name}"
            f")>"
        )


async def validate_token_with_backend(raw_token: str) -> MCPTokenResponse:
    """
    Validate MCP token with backend.
    
    Calls POST /api/internal/mcp/validate on the backend to:
    1. Validate the MCP token
    2. Load authenticated user from database
    3. Create short-lived backend JWT
    4. Return token response
    
    Args:
        raw_token: Raw MCP token string
        
    Returns:
        MCPTokenResponse with user info and JWT
        
    Raises:
        AuthenticationError: If token invalid
        BackendError: If backend error
    """
    if not raw_token:
        raise AuthenticationError("Token required")
    
    try:
        async with httpx.AsyncClient(timeout=settings.backend_api_timeout) as client:
            response = await client.post(
                f"{settings.backend_url}/api/internal/mcp/validate",
                json={"token": raw_token}
            )
        
        if response.status_code == 401:
            logger.warning("MCP token validation rejected by backend")
            raise AuthenticationError("Invalid token")
        
        if response.status_code == 500:
            logger.error(f"Backend validation error: {response.text}")
            raise BackendError("Backend validation failed", "Backend service error")
        
        if response.status_code != 200:
            logger.error(f"Unexpected backend response: {response.status_code}")
            raise BackendError(f"Unexpected status {response.status_code}")
        
        # Parse response
        data = response.json()
        token_response = MCPTokenResponse(data)
        
        logger.info(f"MCP token validated: user_id={token_response.user_id}")
        return token_response
        
    except httpx.TimeoutException:
        logger.error("Backend validation request timed out")
        raise BackendTimeoutError()
    except httpx.ConnectError:
        logger.error(f"Cannot connect to backend: {settings.backend_url}")
        raise BackendUnavailableError()
    except httpx.HTTPError as e:
        logger.error(f"Backend HTTP error: {e}")
        raise BackendUnavailableError()
    except KeyError as e:
        logger.error(f"Invalid backend response: {e}")
        raise BackendError(f"Invalid response structure: {e}")
    except (AuthenticationError, BackendError):
        raise
    except Exception as e:
        logger.error(f"Unexpected validation error: {e}")
        raise AuthenticationError("Authentication failed")
