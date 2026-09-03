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
from app.services.mcp_token_service import validate_mcp_token, create_mcp_token_for_user
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


class MCPCreateTokenRequest(BaseModel):
    """Request to create a new MCP token."""
    user_id: int = Field(..., description="User ID to create token for")
    description: str = Field(..., description="Token description/purpose")


class MCPCreateTokenResponse(BaseModel):
    """Response after creating MCP token."""
    token: str = Field(..., description="Raw MCP token (only shown once)")
    token_id: int = Field(..., description="Token ID for future reference")
    user_id: int = Field(..., description="User ID")
    description: str = Field(..., description="Token description")
    created_at: str = Field(..., description="ISO timestamp when token was created")


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


@router.post("/create-token", response_model=MCPCreateTokenResponse, status_code=status.HTTP_201_CREATED)
def mcp_create_token(
    request: MCPCreateTokenRequest,
    db: Session = Depends(get_db)
) -> MCPCreateTokenResponse:
    """
    Create a new MCP token for a user.
    
    INTERNAL ENDPOINT - NOT for public use
    
    This endpoint creates a new long-lived MCP token that can be used
    to authenticate subsequent MCP requests via /api/internal/mcp/validate.
    
    The MCP server calls this endpoint during POC authentication to create
    a token that will be used for subsequent requests.
    
    Args:
        request: MCPCreateTokenRequest with user_id and description
        db: Database session
        
    Returns:
        MCPCreateTokenResponse with the raw token (shown only once)
        
    Raises:
        400: If user not found
        401: If unauthorized
        500: If unexpected error
        
    Security:
        - This is an internal endpoint
        - Token is shown only in response (never logged or stored in plaintext)
        - Token hash is stored in database
        - Token is long-lived (1 year default)
        - Can be revoked via separate endpoint
    """
    try:
        from app.models.user import User
        from app.models.mcp_token import MCPToken
        
        # Verify user exists
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            logger.warning(f"MCP token creation failed: user not found (user_id={request.user_id})")
            raise AuthenticationError("User not found")
        
        # Create MCP token for user (returns raw token)
        raw_token = create_mcp_token_for_user(
            user_id=request.user_id,
            description=request.description,
            created_via="mcp_server",
            db=db
        )
        
        # Fetch the just-created token record to get token_id and created_at
        # This uses the raw_token to find the record by looking up the hash
        from app.services.mcp_token_service import hash_mcp_token
        token_hash = hash_mcp_token(raw_token)
        mcp_token_record = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        
        if not mcp_token_record:
            logger.error(f"MCP token record not found after creation (user_id={request.user_id})")
            raise AuthenticationError("Token creation failed")
        
        logger.info(
            f"MCP token created: "
            f"user_id={request.user_id}, "
            f"token_id={mcp_token_record.id}, "
            f"description={request.description}"
        )
        
        return MCPCreateTokenResponse(
            token=raw_token,  # The raw token (only shown once!)
            token_id=mcp_token_record.id,
            user_id=mcp_token_record.user_id,
            description=mcp_token_record.description or "",
            created_at=mcp_token_record.created_at.isoformat()
        )
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"MCP token creation error: {e}")
        raise AuthenticationError("Token creation failed")
