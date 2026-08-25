"""
Token service tests

Tests JWT token creation and validation.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.core.errors import ExpiredTokenError, InvalidTokenError
from app.services.token_service import create_access_token, decode_access_token


class TestJWTTokens:
    """JWT token security tests"""
    
    def test_valid_token_can_be_created(self):
        """Valid token can be created"""
        user_id = 123
        token = create_access_token(user_id)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
    def test_valid_token_can_be_decoded(self):
        """Valid token can be decoded"""
        user_id = 123
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        
        assert payload["sub"] == user_id
        assert "iat" in payload
        assert "exp" in payload
        
    def test_expired_token_is_rejected(self):
        """Expired token is rejected"""
        user_id = 123
        # Create token that expires immediately
        payload = {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1)  # Already expired
        }
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        with pytest.raises(ExpiredTokenError) as exc_info:
            decode_access_token(expired_token)
        assert "expired" in str(exc_info.value).lower()
        
    def test_invalid_signature_is_rejected(self):
        """Invalid signature is rejected"""
        user_id = 123
        # Create token with wrong secret
        payload = {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        wrong_secret_token = jwt.encode(payload, "wrong-secret", algorithm=settings.jwt_algorithm)
        
        with pytest.raises(InvalidTokenError) as exc_info:
            decode_access_token(wrong_secret_token)
        assert "signature" in str(exc_info.value).lower()
        
    def test_malformed_token_is_rejected(self):
        """Malformed token is rejected"""
        malformed_tokens = [
            "not.a.jwt",
            "invalid",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        ]
        
        for token in malformed_tokens:
            with pytest.raises(InvalidTokenError):
                decode_access_token(token)
                
    def test_missing_sub_is_rejected(self):
        """Token without 'sub' claim is rejected"""
        # Create token without sub
        payload = {
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        token_without_sub = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        with pytest.raises(InvalidTokenError) as exc_info:
            decode_access_token(token_without_sub)
        assert "sub" in str(exc_info.value).lower()
        
    def test_correct_expiration_is_enforced(self):
        """Token expiration matches configured duration"""
        user_id = 123
        before = datetime.now(timezone.utc)
        token = create_access_token(user_id)
        after = datetime.now(timezone.utc)
        
        payload = decode_access_token(token)
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]
        
        # Calculate token lifetime
        token_lifetime_seconds = exp_timestamp - iat_timestamp
        expected_lifetime_seconds = settings.jwt_expiration_hours * 3600
        
        # Allow 1 second tolerance for test execution time
        assert abs(token_lifetime_seconds - expected_lifetime_seconds) <= 1
        
    def test_token_contains_only_expected_claims(self):
        """Token contains only expected claims (sub, iat, exp)"""
        user_id = 123
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        
        # Should have exactly these claims
        assert set(payload.keys()) == {"sub", "iat", "exp"}
        
    def test_token_uses_correct_algorithm(self):
        """Token header specifies HS256 algorithm"""
        user_id = 123
        token = create_access_token(user_id)
        
        # Decode header without verification
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "HS256"
        
    def test_algorithm_confusion_prevented(self):
        """Algorithm confusion attack is prevented"""
        user_id = 123
        # Try to create token with different algorithm
        payload = {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        # Create token with HS384 (different algorithm)
        token_hs384 = jwt.encode(payload, settings.jwt_secret, algorithm="HS384")
        
        # Should reject due to algorithm mismatch
        with pytest.raises(InvalidTokenError):
            decode_access_token(token_hs384)
            
    def test_user_id_preserved_correctly(self):
        """User ID is preserved correctly through encode/decode"""
        test_user_ids = [1, 123, 999999, 2147483647]  # Various user IDs
        
        for user_id in test_user_ids:
            token = create_access_token(user_id)
            payload = decode_access_token(token)
            assert payload["sub"] == user_id
            
    def test_iat_is_current_time(self):
        """Issued at (iat) claim is current time"""
        before = int(datetime.now(timezone.utc).timestamp())
        token = create_access_token(123)
        after = int(datetime.now(timezone.utc).timestamp())
        
        payload = decode_access_token(token)
        iat = payload["iat"]
        
        # iat should be between before and after
        assert before <= iat <= after
