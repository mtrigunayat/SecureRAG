"""
MCP Token model

Represents opaque authentication tokens for MCP (Model Context Protocol) clients.

MCP tokens allow remote applications (e.g., Claude via MCP) to authenticate
as a specific user without requiring email/password or long-lived JWTs.

Security model:
  - Raw token: Never stored in database
  - Token hash: SHA-256 stored in database
  - User binding: Token maps to exactly one user_id
  - Expiration: Configurable TTL
  - Revocation: Immediate via database update
  - Last used: Tracked for audit/monitoring
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class MCPToken(Base):
    """
    MCP (Model Context Protocol) authentication token.
    
    Represents a long-lived, opaque credential that binds a remote MCP
    client (e.g., Claude via MCP integration) to a specific user.
    
    The token itself is never stored. Only the cryptographic hash is persisted.
    
    Attributes:
        id: Primary key, auto-incrementing integer
        user_id: Foreign key to users table
        token_hash: SHA-256 hash of the raw MCP token (unique, immutable)
        created_at: Timestamp when token was created
        expires_at: Timestamp when token expires (validation enforces)
        last_used_at: Last successful validation timestamp (for audit)
        revoked_at: If set, token is revoked (immutable once set)
        description: Optional human-readable label (e.g., "Claude personal")
        created_by_user_id: Optional FK to admin user who created token
        created_via: Optional string indicating creation method (cli/api/manual)
        user: Relationship to User entity
    
    Validation Rules:
        1. revoked_at must be NULL
        2. expires_at must be in the future
        3. token_hash must exist in exactly one row per valid token
        4. user_id must reference existing user
    
    Security:
        - Raw token never persisted (only hash)
        - Hash is one-way (SHA-256)
        - Hashing is performed server-side before storage
        - Token cannot be recovered from database
        - Raw token returned only at creation time
        - Revocation is immediate (database-driven, not token-driven)
    
    Audit Trail:
        - created_at: When token was issued
        - created_by_user_id: Who issued it (admin)
        - last_used_at: When it was last used (detects anomalies)
        - revoked_at: When/if it was revoked
        - description: Purpose/context
    
    Identity Binding:
        MCP token → user_id → User entity → Department
        
        The MCP client cannot specify or override:
        - user_id
        - department_id
        - department_name
        - role
        - permissions
        
        All are derived server-side from the persistent database.
    """
    
    __tablename__ = "mcp_tokens"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # User binding (required)
    # Each token belongs to exactly one user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Token hash (unique, required)
    # SHA-256 hash of the raw MCP token
    # Raw token is never stored
    # Hash is one-way (cannot reverse to get original token)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # Lifecycle timestamps (required)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Audit timestamps (optional)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    
    # Metadata (optional)
    description = Column(String(255), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_via = Column(String(50), nullable=True)  # 'cli', 'api', 'manual', etc.
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="mcp_tokens")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    
    def is_valid(self) -> bool:
        """
        Check if token is currently valid.
        
        Valid = not revoked AND not expired
        
        Returns:
            True if token can be used, False if revoked or expired
            
        Note:
            This is a convenience method. Server-side validation
            (in token validation service) is the authoritative check.
        """
        now = datetime.utcnow()
        return self.revoked_at is None and self.expires_at > now
    
    def revoke(self) -> None:
        """
        Revoke this token immediately.
        
        Sets revoked_at to current time.
        Token becomes invalid immediately.
        Cannot be undone (immutable once set).
        """
        if self.revoked_at is None:
            self.revoked_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_revoked(self) -> bool:
        """Check if token has been revoked."""
        return self.revoked_at is not None
    
    def __repr__(self) -> str:
        status = "revoked" if self.is_revoked() else ("expired" if self.is_expired() else "valid")
        return (
            f"<MCPToken("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"status={status}, "
            f"expires={self.expires_at.isoformat()}"
            f")>"
        )
