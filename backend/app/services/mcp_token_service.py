"""
MCP Token Service

Provides MCP token generation, validation, and user resolution.

Security Design:
  - Tokens are opaque, randomly generated credentials
  - Raw tokens are never stored (only cryptographic hashes)
  - Hashing is one-way (SHA-256)
  - Tokens expire based on expiration timestamp
  - Tokens can be revoked immediately
  - User identity is resolved from database (never from token)
  - Token validation is strict (all checks required)

Usage:
  # Generate token for user (admin operation)
  raw_token = generate_mcp_token(user_id=1)
  # Token returned to user one time
  
  # Validate token (MCP server operation)
  user = validate_mcp_token(raw_token, db)
  # User object with department loaded
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.mcp_token import MCPToken
from app.models.user import User
from app.core.config import settings
from app.core.errors import AuthenticationError, InvalidTokenError
from app.core.logging import get_logger

logger = get_logger(__name__)

# MCP Token format prefix (for readability/identification)
MCP_TOKEN_PREFIX = "mcp_"

# Bytes of randomness (256 bits = 32 bytes)
MCP_TOKEN_RANDOM_BYTES = 32


def generate_mcp_token_string() -> str:
    """
    Generate a cryptographically secure random MCP token string.
    
    Returns:
        Opaque token string (never stored in database)
        
    Format:
        mcp_<base64-url-safe-random-bytes>
        
    Example:
        "mcp_xK9vL2mQ8pR5sTu3VwXyZ1aB2cD4eF5gH6iJ7kL8mN9oP0qR"
        
    Security:
        - Uses secrets.token_urlsafe() (cryptographically secure)
        - 256 bits of entropy (MCP_TOKEN_RANDOM_BYTES)
        - URL-safe alphabet (safe for logging, URLs, environment vars)
        - Cannot be guessed (entropy too high)
        - No structure that reveals user_id or department
    """
    random_bytes = secrets.token_urlsafe(MCP_TOKEN_RANDOM_BYTES)
    return f"{MCP_TOKEN_PREFIX}{random_bytes}"


def hash_mcp_token(raw_token: str) -> str:
    """
    Hash an MCP token using SHA-256.
    
    Args:
        raw_token: Raw MCP token string
        
    Returns:
        Hex-encoded SHA-256 hash (64 characters)
        
    Security:
        - SHA-256 is cryptographically secure one-way function
        - Output is 64 hex characters (256 bits)
        - Token cannot be recovered from hash
        - Suitable for database storage
        - Same token always produces same hash (deterministic)
        - Different tokens extremely unlikely to collide (2^256 space)
    """
    token_bytes = raw_token.encode('utf-8')
    token_hash = hashlib.sha256(token_bytes).hexdigest()
    return token_hash


def create_mcp_token_for_user(
    user_id: int,
    db: Session,
    description: Optional[str] = None,
    created_by_user_id: Optional[int] = None,
    created_via: Optional[str] = None,
    expires_in_days: Optional[int] = None
) -> str:
    """
    Create a new MCP token for a user.
    
    This is an administrative operation (e.g., token creation CLI).
    
    Args:
        user_id: User ID to create token for
        db: Database session
        description: Optional description (e.g., "Claude MCP")
        created_by_user_id: Optional admin user ID who created this
        created_via: Optional creation method (cli/api/manual)
        expires_in_days: Days until expiration (default from config)
        
    Returns:
        Raw MCP token string (returned to user, not stored)
        
    Raises:
        AuthenticationError: If user doesn't exist
        
    Process:
        1. Verify user exists
        2. Generate random token string
        3. Hash token
        4. Store hash in database
        5. Return raw token (one-time display)
        
    Security:
        - Raw token is never persisted
        - Only hash is stored
        - Token returned only once (not recoverable)
        - User must store securely (Anthropic platform, .env, etc.)
        
    Audit:
        - created_at: Timestamp
        - created_by_user_id: Admin who issued token
        - description: Purpose/context
        - created_via: Method of creation
    """
    from app.repositories.user_repository import UserRepository
    
    # Verify user exists
    user = UserRepository(db).get_by_id(user_id)
    if not user:
        logger.error(f"Cannot create MCP token: user_id={user_id} not found")
        raise AuthenticationError("User not found")
    
    # Determine expiration
    if expires_in_days is None:
        expires_in_days = settings.mcp_token_expiration_days
    
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    # Generate raw token (NOT stored)
    raw_token = generate_mcp_token_string()
    
    # Hash token for storage
    token_hash = hash_mcp_token(raw_token)
    
    # Create database record
    mcp_token_record = MCPToken(
        user_id=user_id,
        token_hash=token_hash,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        description=description,
        created_by_user_id=created_by_user_id,
        created_via=created_via or "manual"
    )
    
    db.add(mcp_token_record)
    db.commit()
    db.refresh(mcp_token_record)
    
    logger.info(
        f"MCP token created: user_id={user_id}, "
        f"token_id={mcp_token_record.id}, "
        f"expires={expires_at.isoformat()}, "
        f"created_via={created_via}"
    )
    
    # Return raw token (one-time display)
    # This is the only time the raw token is ever exposed
    return raw_token


def validate_mcp_token(raw_token: str, db: Session) -> User:
    """
    Validate an MCP token and return the authenticated user.
    
    This is the main entry point for MCP server authentication.
    
    Args:
        raw_token: Raw MCP token from client
        db: Database session
        
    Returns:
        Authenticated User object (with department loaded)
        
    Raises:
        AuthenticationError: If token is invalid, expired, revoked, or user not found
        
    Validation Steps:
        1. Check token is not empty
        2. Hash token
        3. Look up token_hash in database
        4. Check token exists
        5. Check token not revoked (revoked_at IS NULL)
        6. Check token not expired (expires_at > NOW)
        7. Load user from database
        8. Check user exists
        9. Load user's department
        10. Update last_used_at
        
    Security:
        - Token must be EXACTLY correct (hash comparison)
        - User identity comes from database (not from token)
        - Department comes from database relationship (not from token)
        - Client cannot override any of these
        - All checks are required (fail if any missing)
        
    Audit:
        - Logs successful validations (user_id, token_id)
        - Logs failures (reasons, but not token itself)
        - Updates last_used_at for anomaly detection
    """
    now = datetime.utcnow()
    
    # Validate input
    if not raw_token:
        logger.warning("MCP token validation failed: token is empty")
        raise AuthenticationError("Token is required")
    
    # Hash the provided token
    token_hash = hash_mcp_token(raw_token)
    
    # Look up token in database
    mcp_token_record = db.query(MCPToken).filter(
        MCPToken.token_hash == token_hash
    ).first()
    
    if not mcp_token_record:
        logger.warning(f"MCP token validation failed: token not found (hash={token_hash[:16]}...)")
        raise AuthenticationError("Invalid token")
    
    # Check if token is revoked
    if mcp_token_record.revoked_at is not None:
        logger.warning(
            f"MCP token validation failed: token revoked "
            f"(token_id={mcp_token_record.id}, user_id={mcp_token_record.user_id})"
        )
        raise AuthenticationError("Invalid token")
    
    # Check if token has expired
    if mcp_token_record.expires_at <= now:
        logger.info(
            f"MCP token validation failed: token expired "
            f"(token_id={mcp_token_record.id}, user_id={mcp_token_record.user_id}, "
            f"expired_at={mcp_token_record.expires_at.isoformat()})"
        )
        raise AuthenticationError("Invalid token")
    
    # Load user from database (authoritative source of identity)
    user = db.query(User).filter(User.id == mcp_token_record.user_id).first()
    if not user:
        logger.error(
            f"MCP token validation failed: user not found "
            f"(token_id={mcp_token_record.id}, user_id={mcp_token_record.user_id})"
        )
        raise AuthenticationError("Invalid token")
    
    # Ensure department is loaded (required for authorization)
    if user.department is None:
        logger.error(
            f"MCP token validation failed: user has no department "
            f"(user_id={user.id})"
        )
        raise AuthenticationError("Invalid token")
    
    # Update last_used_at for audit trail
    try:
        mcp_token_record.last_used_at = now
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to update last_used_at for token: {e}")
        # Don't fail authentication if audit update fails
        db.rollback()
    
    logger.info(
        f"MCP token validated successfully: "
        f"token_id={mcp_token_record.id}, "
        f"user_id={user.id}, "
        f"department={user.department.name}"
    )
    
    return user


def revoke_mcp_token(token_id: int, db: Session) -> bool:
    """
    Revoke a specific MCP token immediately.
    
    Args:
        token_id: ID of token to revoke
        db: Database session
        
    Returns:
        True if revocation succeeded, False if token not found
        
    Security:
        - Revocation is immediate
        - Cannot be undone
        - Token becomes invalid on next validation attempt
        - Audit trail: revoked_at timestamp is set
        
    Audit:
        - revoked_at is set to current time
        - Logged for compliance
    """
    mcp_token_record = db.query(MCPToken).filter(MCPToken.id == token_id).first()
    
    if not mcp_token_record:
        logger.warning(f"Revocation failed: MCP token not found (token_id={token_id})")
        return False
    
    if mcp_token_record.revoked_at is not None:
        logger.info(f"MCP token already revoked (token_id={token_id})")
        return True
    
    mcp_token_record.revoked_at = datetime.utcnow()
    db.commit()
    
    logger.info(
        f"MCP token revoked: "
        f"token_id={token_id}, "
        f"user_id={mcp_token_record.user_id}"
    )
    
    return True


def revoke_all_user_tokens(user_id: int, db: Session) -> int:
    """
    Revoke all MCP tokens for a user (e.g., when compromised or user leaves).
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        Number of tokens revoked
        
    Security:
        - Immediate revocation
        - All tokens become invalid
        - Cannot be recovered
        - Audit trail: revoked_at timestamps set
    """
    now = datetime.utcnow()
    
    # Update all non-revoked tokens for user
    revoked_count = db.query(MCPToken).filter(
        MCPToken.user_id == user_id,
        MCPToken.revoked_at.is_(None)
    ).update({MCPToken.revoked_at: now})
    
    db.commit()
    
    if revoked_count > 0:
        logger.warning(
            f"Revoked all MCP tokens for user: "
            f"user_id={user_id}, "
            f"tokens_revoked={revoked_count}"
        )
    
    return revoked_count


def get_user_mcp_tokens(user_id: int, db: Session) -> list:
    """
    Get all MCP tokens for a user (including expired and revoked).
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        List of MCPToken records
        
    Usage:
        For admin viewing token history/status
    """
    return db.query(MCPToken).filter(MCPToken.user_id == user_id).all()


def get_active_user_mcp_tokens(user_id: int, db: Session) -> list:
    """
    Get only active (non-expired, non-revoked) MCP tokens for a user.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        List of valid MCPToken records
        
    Usage:
        For token management/rotation
    """
    now = datetime.utcnow()
    return db.query(MCPToken).filter(
        MCPToken.user_id == user_id,
        MCPToken.revoked_at.is_(None),
        MCPToken.expires_at > now
    ).all()
