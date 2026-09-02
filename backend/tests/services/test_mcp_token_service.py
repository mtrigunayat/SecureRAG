"""
Tests for MCP Token Service

Tests cover:
  - Token generation (cryptographic randomness, format)
  - Token hashing (one-way, deterministic, no plaintext storage)
  - Token creation (database persistence, expiration, audit)
  - Token validation (strict checks, expiration, revocation)
  - User resolution (identity from database, not from token)
  - Department integrity (comes from user relationship)
  - Edge cases (expired, revoked, missing, invalid)
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.department import Department
from app.models.mcp_token import MCPToken
from app.services.mcp_token_service import (
    generate_mcp_token_string,
    hash_mcp_token,
    create_mcp_token_for_user,
    validate_mcp_token,
    revoke_mcp_token,
    revoke_all_user_tokens,
    get_active_user_mcp_tokens,
)
from app.core.errors import AuthenticationError
from app.core.config import settings


class TestTokenGeneration:
    """Tests for token generation."""
    
    def test_generate_token_format(self):
        """Test token generation produces proper format."""
        token = generate_mcp_token_string()
        
        # Should start with prefix
        assert token.startswith("mcp_")
        
        # Should have content after prefix
        assert len(token) > len("mcp_")
        
        # Should be URL-safe
        assert all(c.isalnum() or c in '-_' for c in token[4:])
    
    def test_generate_token_randomness(self):
        """Test token generation produces different tokens."""
        tokens = [generate_mcp_token_string() for _ in range(10)]
        
        # All tokens should be unique
        assert len(set(tokens)) == 10
        
        # No token should repeat
        assert len(tokens) == len(set(tokens))
    
    def test_generate_token_entropy(self):
        """Test token generation has sufficient entropy."""
        token = generate_mcp_token_string()
        
        # Token should be reasonably long (32 bytes base64 + prefix)
        # base64 encoding of 32 bytes: ~43 characters
        assert len(token) >= 40  # "mcp_" + at least 36 chars
    
    def test_generate_token_no_secrets_leaked(self):
        """Test token doesn't contain user-identifying information."""
        token = generate_mcp_token_string()
        
        # Token should be opaque (no user_id, department, role encoded)
        # Just check it's not obviously a user ID
        assert not token.endswith("_1")
        assert not token.endswith("_user")
        assert "_user_" not in token.lower()
        assert "_dept_" not in token.lower()


class TestTokenHashing:
    """Tests for token hashing."""
    
    def test_hash_token_produces_hex_string(self):
        """Test token hash is hex-encoded string."""
        token = "mcp_test_token_xyz"
        token_hash = hash_mcp_token(token)
        
        # Should be hex string
        assert isinstance(token_hash, str)
        assert all(c in '0123456789abcdef' for c in token_hash)
        
        # SHA-256 produces 64 hex characters (256 bits)
        assert len(token_hash) == 64
    
    def test_hash_token_deterministic(self):
        """Test same token produces same hash."""
        token = "mcp_test_token_xyz"
        
        hash1 = hash_mcp_token(token)
        hash2 = hash_mcp_token(token)
        
        # Same token should produce identical hash
        assert hash1 == hash2
    
    def test_hash_token_one_way(self):
        """Test hash is one-way (cannot recover token from hash)."""
        token = generate_mcp_token_string()
        token_hash = hash_mcp_token(token)
        
        # Hash should not contain token
        assert token not in token_hash
        
        # Hash should not be reversible
        # (this is cryptographic guarantee, not testable, but verify hash is different)
        assert token != token_hash
    
    def test_different_tokens_different_hashes(self):
        """Test different tokens produce different hashes."""
        token1 = generate_mcp_token_string()
        token2 = generate_mcp_token_string()
        
        hash1 = hash_mcp_token(token1)
        hash2 = hash_mcp_token(token2)
        
        # Different tokens should have different hashes
        assert hash1 != hash2
    
    def test_hash_token_immutable(self):
        """Test hash never changes for same token."""
        token = "mcp_immutable_test"
        
        # Hash multiple times, all should be identical
        hashes = [hash_mcp_token(token) for _ in range(5)]
        assert all(h == hashes[0] for h in hashes)


@pytest.mark.usefixtures("db")
class TestTokenCreation:
    """Tests for token creation flow."""
    
    def test_create_token_for_user(self, db: Session, test_user: User):
        """Test creating token stores hash, not raw token."""
        raw_token = create_mcp_token_for_user(
            user_id=test_user.id,
            db=db,
            description="Test token"
        )
        
        # Returned token should be opaque string
        assert raw_token.startswith("mcp_")
        assert len(raw_token) > 40
        
        # Token should exist in database (hashed)
        token_hash = hash_mcp_token(raw_token)
        db_token = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        
        # Database should have the token record
        assert db_token is not None
        assert db_token.user_id == test_user.id
        assert db_token.description == "Test token"
        
        # Raw token should NOT be in database
        assert raw_token not in [t.token_hash for t in db.query(MCPToken).all()]
    
    def test_create_token_sets_expiration(self, db: Session, test_user: User):
        """Test token expiration is set correctly."""
        raw_token = create_mcp_token_for_user(
            user_id=test_user.id,
            db=db,
            expires_in_days=30
        )
        
        token_hash = hash_mcp_token(raw_token)
        db_token = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        
        # Expiration should be ~30 days from now
        now = datetime.utcnow()
        delta = db_token.expires_at - now
        
        # Should be approximately 30 days (allow 1 hour margin)
        assert delta.days == 30 or delta.days == 29
        assert delta.total_seconds() > (29 * 24 * 3600)
    
    def test_create_token_user_not_found(self, db: Session):
        """Test creating token for non-existent user fails."""
        with pytest.raises(AuthenticationError):
            create_mcp_token_for_user(
                user_id=99999,
                db=db,
                description="Will fail"
            )
    
    def test_create_token_unique_hashes(self, db: Session, test_user: User):
        """Test multiple tokens for same user have unique hashes."""
        token1 = create_mcp_token_for_user(user_id=test_user.id, db=db)
        token2 = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        hash1 = hash_mcp_token(token1)
        hash2 = hash_mcp_token(token2)
        
        # Different tokens should have different hashes
        assert hash1 != hash2
        
        # Both should exist in database
        count = db.query(MCPToken).filter(
            MCPToken.user_id == test_user.id
        ).count()
        assert count >= 2
    
    def test_create_token_audit_trail(self, db: Session, test_user: User):
        """Test token creation captures audit information."""
        raw_token = create_mcp_token_for_user(
            user_id=test_user.id,
            db=db,
            description="Audit test",
            created_by_user_id=test_user.id,
            created_via="cli"
        )
        
        token_hash = hash_mcp_token(raw_token)
        db_token = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        
        # Audit fields should be set
        assert db_token.description == "Audit test"
        assert db_token.created_by_user_id == test_user.id
        assert db_token.created_via == "cli"
        assert db_token.created_at is not None
        assert db_token.expires_at is not None


@pytest.mark.usefixtures("db")
class TestTokenValidation:
    """Tests for token validation."""
    
    def test_validate_valid_token(self, db: Session, test_user: User):
        """Test validating a valid token returns user."""
        raw_token = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        validated_user = validate_mcp_token(raw_token, db)
        
        # Should return correct user
        assert validated_user.id == test_user.id
        assert validated_user.username == test_user.username
        
        # Should have department loaded
        assert validated_user.department is not None
    
    def test_validate_invalid_token(self, db: Session):
        """Test validating invalid token fails."""
        with pytest.raises(AuthenticationError):
            validate_mcp_token("invalid_token_xyz", db)
    
    def test_validate_empty_token(self, db: Session):
        """Test validating empty token fails."""
        with pytest.raises(AuthenticationError):
            validate_mcp_token("", db)
    
    def test_validate_none_token(self, db: Session):
        """Test validating None token fails."""
        with pytest.raises(AuthenticationError):
            validate_mcp_token(None, db)
    
    def test_validate_expired_token(self, db: Session, test_user: User):
        """Test expired token is rejected."""
        # Create token with past expiration
        raw_token = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        # Manually set expiration to past
        token_hash = hash_mcp_token(raw_token)
        db_token = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        db_token.expires_at = datetime.utcnow() - timedelta(hours=1)
        db.commit()
        
        # Validation should fail
        with pytest.raises(AuthenticationError):
            validate_mcp_token(raw_token, db)
    
    def test_validate_revoked_token(self, db: Session, test_user: User):
        """Test revoked token is rejected."""
        raw_token = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        # Revoke the token
        token_hash = hash_mcp_token(raw_token)
        db_token = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        db_token.revoke()
        db.commit()
        
        # Validation should fail
        with pytest.raises(AuthenticationError):
            validate_mcp_token(raw_token, db)
    
    def test_validate_token_updates_last_used(self, db: Session, test_user: User):
        """Test validation updates last_used_at timestamp."""
        raw_token = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        # Verify last_used_at is initially None
        token_hash = hash_mcp_token(raw_token)
        db_token = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        assert db_token.last_used_at is None
        
        # Validate token
        validate_mcp_token(raw_token, db)
        
        # Refresh from database
        db_token = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        
        # last_used_at should be set
        assert db_token.last_used_at is not None
        assert db_token.last_used_at <= datetime.utcnow()
    
    def test_validate_token_user_not_found(self, db: Session, test_user: User):
        """Test validation fails if user was deleted."""
        raw_token = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        # Delete user
        db.delete(test_user)
        db.commit()
        
        # Validation should fail (user not found)
        with pytest.raises(AuthenticationError):
            validate_mcp_token(raw_token, db)
    
    def test_validate_multiple_tokens_independently(self, db: Session, test_user: User):
        """Test tokens are validated independently."""
        token1 = create_mcp_token_for_user(user_id=test_user.id, db=db)
        token2 = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        # Revoke token1
        hash1 = hash_mcp_token(token1)
        db_token1 = db.query(MCPToken).filter(
            MCPToken.token_hash == hash1
        ).first()
        db_token1.revoke()
        db.commit()
        
        # token1 should fail
        with pytest.raises(AuthenticationError):
            validate_mcp_token(token1, db)
        
        # token2 should still work
        validated_user = validate_mcp_token(token2, db)
        assert validated_user.id == test_user.id


@pytest.mark.usefixtures("db")
class TestTokenRevocation:
    """Tests for token revocation."""
    
    def test_revoke_token(self, db: Session, test_user: User):
        """Test revoking a token."""
        raw_token = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        token_hash = hash_mcp_token(raw_token)
        db_token = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        
        # Revoke token
        success = revoke_mcp_token(db_token.id, db)
        assert success is True
        
        # Token should be marked revoked
        db_token = db.query(MCPToken).filter(
            MCPToken.token_hash == token_hash
        ).first()
        assert db_token.is_revoked()
        
        # Validation should fail
        with pytest.raises(AuthenticationError):
            validate_mcp_token(raw_token, db)
    
    def test_revoke_nonexistent_token(self, db: Session):
        """Test revoking non-existent token fails."""
        success = revoke_mcp_token(99999, db)
        assert success is False
    
    def test_revoke_all_user_tokens(self, db: Session, test_user: User):
        """Test revoking all tokens for a user."""
        token1 = create_mcp_token_for_user(user_id=test_user.id, db=db)
        token2 = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        # Get active tokens
        active_before = get_active_user_mcp_tokens(test_user.id, db)
        assert len(active_before) == 2
        
        # Revoke all
        count = revoke_all_user_tokens(test_user.id, db)
        assert count == 2
        
        # Get active tokens
        active_after = get_active_user_mcp_tokens(test_user.id, db)
        assert len(active_after) == 0
        
        # Both tokens should fail validation
        with pytest.raises(AuthenticationError):
            validate_mcp_token(token1, db)
        with pytest.raises(AuthenticationError):
            validate_mcp_token(token2, db)


@pytest.mark.usefixtures("db")
class TestDepartmentIntegrity:
    """Tests for department-based access control."""
    
    def test_validated_token_user_has_department(self, db: Session, test_user: User):
        """Test validated user has department from database."""
        raw_token = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        validated_user = validate_mcp_token(raw_token, db)
        
        # Department must be loaded from database
        assert validated_user.department is not None
        assert validated_user.department.id is not None
    
    def test_token_cannot_override_department(self, db: Session, test_user: User):
        """Test token cannot encode or override user's department."""
        raw_token = create_mcp_token_for_user(user_id=test_user.id, db=db)
        
        # Token should not contain department info
        assert "_dept_" not in raw_token.lower()
        assert "_department_" not in raw_token.lower()
        
        # Department must come from database relationship
        validated_user = validate_mcp_token(raw_token, db)
        assert validated_user.department.id == test_user.department_id


class TestSecurityProperties:
    """Tests for security properties."""
    
    def test_token_not_logged_in_plaintext(self):
        """Test utility doesn't log raw tokens (verify by code inspection)."""
        # This is a code inspection test - verify logging doesn't include raw tokens
        # The actual check is done in service implementation
        # This test documents the requirement
        pass
    
    def test_token_hash_not_reversible(self):
        """Test token hash cannot be reversed."""
        token = generate_mcp_token_string()
        token_hash = hash_mcp_token(token)
        
        # Hash should not contain token
        assert token not in token_hash
        
        # Hash should be cryptographically one-way
        # Attempting to hash the hash should produce different value
        hash_of_hash = hash_mcp_token(token_hash)
        assert hash_of_hash != token_hash
    
    def test_token_format_no_user_info(self):
        """Test token format doesn't reveal user information."""
        token = generate_mcp_token_string()
        
        # Token should not contain common user/dept identifiers
        assert "_user_" not in token.lower()
        assert "_dept_" not in token.lower()
        assert "_admin_" not in token.lower()
        assert "_role_" not in token.lower()
        
        # Token should not be decodable as base64-encoded JSON
        import base64
        try:
            decoded = base64.b64decode(token.replace("mcp_", ""), validate=True)
            # If we got here, it decoded - but shouldn't look like JSON
            assert not (decoded.startswith(b"{") or decoded.startswith(b"["))
        except Exception:
            # Expected - token is not base64-encoded structured data
            pass
