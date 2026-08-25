"""
Authentication dependencies

FastAPI dependencies for JWT validation and user resolution.
"""
from typing import Annotated
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.token_service import decode_access_token
from app.core.errors import AuthenticationError, InvalidTokenError
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_token_from_header(authorization: Annotated[str | None, Header()] = None) -> str:
    """
    Extract Bearer token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        JWT token string
        
    Raises:
        AuthenticationError: If header is missing or malformed
        
    Expected format: "Bearer <token>"
    """
    if not authorization:
        raise AuthenticationError("Missing authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise InvalidTokenError("Invalid authorization header format")
    
    return parts[1]


def get_current_user(
    token: Annotated[str, Depends(get_token_from_header)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """
    Get the current authenticated user.
    
    This dependency:
    1. Extracts Bearer token from Authorization header
    2. Validates JWT (signature, expiration, structure)
    3. Extracts user ID from token subject (sub)
    4. Loads user from PostgreSQL (trusted source)
    5. Returns authenticated User object
    
    Args:
        token: JWT token from Authorization header
        db: Database session
        
    Returns:
        Authenticated User object with department relationship loaded
        
    Raises:
        AuthenticationError: If authentication fails at any step
        
    Security:
        - Token validation enforced
        - User loaded from PostgreSQL (NOT from JWT payload)
        - Department comes from database relationship (trusted)
        - Client cannot choose authenticated user
        - Client cannot override department
    """
    # Decode and validate JWT
    try:
        payload = decode_access_token(token)
    except Exception as e:
        # decode_access_token already logs details
        raise
    
    # Extract user ID from subject
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise InvalidTokenError("Token missing user ID")
    
    # Validate user ID format
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid user ID format in token: {user_id_str}")
        raise InvalidTokenError("Invalid token format")
    
    # Load user from PostgreSQL (trusted source)
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if not user:
        # User was deleted after token was issued
        logger.warning(f"Token references non-existent user: {user_id}")
        raise AuthenticationError("User not found")
    
    # User object includes department relationship
    # This is the TRUSTED source for authorization (future phase)
    return user
