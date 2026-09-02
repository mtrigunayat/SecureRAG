"""
Internal MCP Authentication Endpoints

These endpoints are NOT exposed to the public API.
They are for internal service-to-service communication between
the MCP server and the FastAPI backend.

Security:
  - These endpoints are internal only (should not be exposed publicly)
  - They validate MCP tokens and return short-lived backend JWTs
  - The MCP server is trusted as an internal service
  - User identity comes from database (via MCP token validation)
"""
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.mcp_token_service import validate_mcp_token
from app.services.token_service import create_access_token
from app.core.errors import AuthenticationError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/internal/mcp", tags=["internal", "mcp"])


class MCPTokenRequest(BaseModel):
    """Request to validate MCP token."""
    token: str = Field(..., description="MCP token string")


class MCPValidationResponse(BaseModel):
    """Response after MCP token validation."""
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    department_name: str = Field(..., description="Department name")
    backend_jwt: str = Field(..., description="Short-lived backend JWT for subsequent requests")
    expires_in: int = Field(..., description="JWT expiration in seconds")


@router.post("/validate", response_model=MCPValidationResponse, status_code=status.HTTP_200_OK)
def mcp_validate(
    request: MCPTokenRequest,
    db: Session = Depends(get_db)
) -> MCPValidationResponse:
    """
    Validate MCP token and return backend JWT.
    
    INTERNAL ENDPOINT - NOT for public use
    
    This endpoint:
    1. Takes an MCP token from the MCP server
    2. Validates it using Phase 2 token validation
    3. Loads authenticated user from database
    4. Creates a short-lived backend JWT
    5. Returns user identity + JWT
    
    The MCP server will use the returned JWT for subsequent
    calls to /api/chat and other authenticated endpoints.
    
    Args:
        request: MCPTokenRequest with token
        db: Database session
        
    Returns:
        MCPValidationResponse with user info and JWT
        
    Raises:
        401: If token invalid/expired/revoked
        500: If unexpected error
        
    Security:
        - Token validation is strict (all checks required)
        - User identity from database (authoritative)
        - Department from database relationship (authoritative)
        - Backend JWT is short-lived (1 hour)
        - No passwords involved
        - No user_id in token (resolved from database)
        
    Audit:
        - MCP token last_used_at updated
        - Backend JWT issued to identified user
        - Request logged with user_id
    """
    try:
        # Validate MCP token and get authenticated user
        user = validate_mcp_token(request.token, db)
        
        # User identity is now verified and from database
        if not user.department:
            logger.error(f"User has no department: user_id={user.id}")
            raise AuthenticationError("User configuration error")
        
        # Create short-lived backend JWT for this user
        backend_jwt = create_access_token(user.id)
        
        logger.info(
            f"MCP validation successful: "
            f"user_id={user.id}, "
            f"username={user.username}, "
            f"department={user.department.name}"
        )
        
        return MCPValidationResponse(
            user_id=user.id,
            username=user.username,
            department_name=user.department.name,
            backend_jwt=backend_jwt,
            expires_in=3600  # 1 hour, matches JWT_EXPIRATION_HOURS
        )
        
    except AuthenticationError as e:
        logger.warning(f"MCP validation failed: {e.message}")
        # Return 401 without exposing token details
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error(f"MCP validation error: {e}")
        # Return 500 for unexpected errors
        raise AuthenticationError("Authentication service error")
