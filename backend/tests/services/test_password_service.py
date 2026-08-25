"""
Password service tests

Tests password hashing and verification security.
"""
import pytest

from app.services.password_service import hash_password, verify_password


class TestPasswordHashing:
    """Password hashing security tests"""
    
    def test_password_can_be_hashed(self):
        """Password can be hashed"""
        password = "test123"
        hashed = hash_password(password)
        assert hashed is not None
        assert len(hashed) > 0
        
    def test_correct_password_verifies(self):
        """Correct password verifies against hash"""
        password = "test123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        
    def test_incorrect_password_fails(self):
        """Incorrect password fails verification"""
        password = "test123"
        wrong_password = "wrong"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False
        
    def test_hash_is_different_from_plaintext(self):
        """Hash is different from plaintext password"""
        password = "test123"
        hashed = hash_password(password)
        assert hashed != password
        
    def test_hashing_same_password_produces_different_hashes(self):
        """Hashing same password twice produces different hashes (salt)"""
        password = "test123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # Different hashes due to different salts
        assert hash1 != hash2
        # But both verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)
        
    def test_empty_password(self):
        """Empty password can be hashed"""
        password = ""
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
        
    def test_long_password_truncated(self):
        """Password longer than 72 bytes is truncated"""
        # bcrypt has a 72-byte limit
        long_password = "a" * 100
        hashed = hash_password(long_password)
        # Truncated to 72 bytes
        assert verify_password("a" * 72, hashed) is True
        # Original long password also verifies (gets truncated during verification)
        assert verify_password(long_password, hashed) is True
        
    def test_unicode_password(self):
        """Unicode password can be hashed"""
        password = "密码123🔒"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        
    def test_special_characters(self):
        """Password with special characters"""
        password = "P@ssw0rd!#$%^&*()"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        
    def test_invalid_hash_format_returns_false(self):
        """Invalid hash format returns False instead of raising exception"""
        password = "test123"
        invalid_hash = "not-a-valid-hash"
        # Should return False, not raise exception
        assert verify_password(password, invalid_hash) is False
        
    def test_case_sensitive(self):
        """Password verification is case-sensitive"""
        password = "Test123"
        hashed = hash_password(password)
        assert verify_password("test123", hashed) is False
        assert verify_password("TEST123", hashed) is False
        assert verify_password("Test123", hashed) is True
