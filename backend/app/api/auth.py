"""
Authentication endpoints

Handles user login and identity resolution.
"""
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.password_service import verify_password
from app.services.token_service import create_access_token
from app.dependencies.auth import get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, CurrentUserResponse
from app.core.errors import InvalidCredentialsError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)]
) -> TokenResponse:
    """
    Authenticate user and return JWT access token.
    
    Args:
        credentials: Login credentials (email + password)
        db: Database session
        
    Returns:
        JWT access token
        
    Raises:
        InvalidCredentialsError: If credentials are invalid
        
    Security:
        - Passwords never logged
        - Generic error message (doesn't reveal if email exists)
        - Password verified using bcrypt
        - Token contains only user ID (no sensitive data)
        
    Usage:
        POST /api/auth/login
        {
            "email": "alice@company.com",
            "password": "password123"
        }
        
        Response:
        {
            "access_token": "eyJ...",
            "token_type": "bearer"
        }
    """
    # Find user by email
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(credentials.email)
    
    # Verify user exists and password is correct
    # Use constant-time comparison to prevent timing attacks
    if not user or not verify_password(credentials.password, user.password_hash):
        # Generic error - don't reveal whether email exists
        logger.warning(f"Failed login attempt for email: {credentials.email}")
        raise InvalidCredentialsError()
    
    # Generate JWT access token
    access_token = create_access_token(user.id)
    
    logger.info(f"Successful login for user: {user.username} (id={user.id})")
    
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)]
) -> CurrentUserResponse:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Authenticated user from JWT token
        
    Returns:
        User information with department
        
    Security:
        - Requires valid JWT token
        - Department comes from PostgreSQL relationship (trusted source)
        - Never exposes password_hash
        - User identity verified via JWT + PostgreSQL lookup
        
    Usage:
        GET /api/auth/me
        Authorization: Bearer <token>
        
        Response:
        {
            "id": 1,
            "username": "alice",
            "email": "alice@company.com",
            "full_name": "Alice Johnson",
            "department": {
                "id": 1,
                "name": "engineering",
                "description": "Engineering and development team"
            }
        }
    """
    # Department loaded from PostgreSQL relationship (trusted source)
    # This is the foundation for future authorization
    return CurrentUserResponse.model_validate(current_user)
