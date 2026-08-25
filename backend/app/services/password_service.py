"""
Password hashing service

Provides secure password hashing and verification using bcrypt.
"""
import bcrypt

from app.core.logging import get_logger

logger = get_logger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password (string)
        
    Security:
        - Never logs the password
        - Uses bcrypt with automatic salt (rounds=12)
        - Each hash is unique even for identical passwords
        - Truncates to 72 bytes (bcrypt limitation)
        
    Note:
        Using bcrypt directly instead of passlib due to Python 3.13 compatibility.
        Passlib 1.7.4 has known issues with newer bcrypt versions.
    """
    # Convert password to bytes (bcrypt requires bytes)
    # Truncate to 72 bytes (bcrypt limitation)
    password_bytes = password.encode('utf-8')[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string for database storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
        
    Security:
        - Never logs passwords
        - Constant-time comparison (bcrypt.checkpw)
        - No manual string comparison
    """
    try:
        # Convert to bytes
        password_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        
        # bcrypt.checkpw handles constant-time comparison
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        # Invalid hash format or verification error
        logger.warning(f"Password verification failed: {type(e).__name__}")
        return False
