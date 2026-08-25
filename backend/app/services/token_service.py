"""
JWT token service

Provides JWT token creation and validation.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jose import JWTError, jwt

from app.core.config import settings
from app.core.errors import InvalidTokenError, ExpiredTokenError
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_access_token(user_id: int) -> str:
    """
    Create a JWT access token for a user.
    
    Args:
        user_id: User's database ID
        
    Returns:
        Encoded JWT token string
        
    Token payload contains:
        - sub: User ID (subject)
        - iat: Issued at timestamp
        - exp: Expiration timestamp
        
    Security:
        - Uses HS256 algorithm (explicitly restricted)
        - Secret from environment variable
        - Configurable expiration
        - Minimal payload (no sensitive data)
    """
    now = datetime.utcnow()
    expire = now + timedelta(hours=settings.jwt_expiration_hours)
    
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: Encoded JWT token string
        
    Returns:
        Decoded token payload with 'sub' converted to integer
        
    Raises:
        InvalidTokenError: Token is malformed or has invalid signature
        ExpiredTokenError: Token has expired
        
    Security:
        - Validates signature
        - Validates expiration
        - Explicitly restricts algorithm to HS256
        - No algorithm confusion attack vulnerability
        - Validates required claims (sub)
    """
    if not settings.jwt_secret:
        logger.error("JWT_SECRET not configured")
        raise InvalidTokenError("Authentication not properly configured")
    
    try:
        # Decode with explicit algorithm restriction (prevent algorithm confusion)
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Validate required claim
        if "sub" not in payload:
            raise InvalidTokenError("Token missing 'sub' claim")
        
        # Convert sub to integer (JWT stores it as string)
        try:
            payload["sub"] = int(payload["sub"])
        except (ValueError, TypeError):
            raise InvalidTokenError("Token 'sub' claim is not a valid integer")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise ExpiredTokenError()
    except InvalidTokenError:
        # Re-raise our own InvalidTokenError
        raise
    except JWTError as e:
        # Check for signature verification failure
        error_msg = str(e).lower()
        if "signature" in error_msg:
            logger.warning("JWT signature verification failed")
            raise InvalidTokenError("Invalid token signature")
        else:
            logger.warning(f"JWT validation failed: {type(e).__name__}")
            raise InvalidTokenError("Invalid token")
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {type(e).__name__}")
        raise InvalidTokenError("Invalid token")
