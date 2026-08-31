"""
Authentication API tests

Tests login endpoint and current user endpoint using development credentials.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.token_service import create_access_token


# Note: Using client fixture from conftest.py which includes database setup

class TestLoginEndpoint:
    """Login endpoint tests"""
    
    def test_valid_credentials_return_200(self, client):
        """Valid credentials return 200"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "mohit@aithinkers.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
    def test_invalid_password_returns_authentication_failure(self, client):
        """Invalid password returns authentication failure"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "mohit@aithinkers.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        # Generic error message (doesn't reveal if email exists)
        assert "invalid" in data["detail"].lower() or "credentials" in data["detail"].lower()
        
    def test_unknown_email_returns_same_generic_failure(self, client):
        """Unknown email returns same generic authentication failure"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "unknown@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        # Same generic error as invalid password
        assert "invalid" in data["detail"].lower() or "credentials" in data["detail"].lower()
        
    def test_password_hash_is_never_returned(self, client):
        """Password hash is never returned in login response"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "mohit@aithinkers.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only contain token fields
        assert "password_hash" not in data
        assert "password" not in data
        assert set(data.keys()) == {"access_token", "token_type"}
        
    def test_token_response_contains_expected_fields(self, client):
        """Token response contains expected fields"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "karthik@aithinkers.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
        
    def test_returned_token_is_valid_jwt(self, client):
        """Returned token is valid JWT with correct user_id"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "swathi@aithinkers.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # Token should decode successfully
        from app.services.token_service import decode_access_token
        payload = decode_access_token(token)
        assert "sub" in payload
        assert isinstance(payload["sub"], int)
        
    def test_invalid_email_format(self, client):
        """Invalid email format returns validation error"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "not-an-email",
                "password": "password123"
            }
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
        
    def test_missing_email(self, client):
        """Missing email returns validation error"""
        response = client.post(
            "/api/auth/login",
            json={
                "password": "password123"
            }
        )
        
        assert response.status_code == 422
        
    def test_missing_password(self, client):
        """Missing password returns validation error"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "mohit@aithinkers.com"
            }
        )
        
        assert response.status_code == 422
        
    def test_case_sensitive_password(self, client):
        """Password is case-sensitive"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "mohit@aithinkers.com",
                "password": "PASSWORD123"  # Wrong case
            }
        )
        
        assert response.status_code == 401


class TestCurrentUserEndpoint:
    """Current user endpoint (/api/auth/me) tests"""
    
    def test_valid_token_returns_correct_user(self, client):
        """Valid token returns correct user"""
        # Login first to get a valid token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "mohit@aithinkers.com",
                "password": "password123"
            }
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["username"] == "mohit"
        assert data["email"] == "mohit@aithinkers.com"
        
    def test_missing_token_is_rejected(self, client):
        """Missing token is rejected"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
        
    def test_invalid_token_is_rejected(self, client):
        """Invalid token is rejected"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
        
    def test_expired_token_is_rejected(self, client):
        """Expired token is rejected"""
        # Create expired token
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        from app.core.config import settings
        
        payload = {
            "sub": 1,  # Alice's user ID
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1)
        }
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
        
    def test_token_for_nonexistent_user_is_rejected(self, client):
        """Token for nonexistent user is rejected"""
        # Create token for user ID that doesn't exist
        nonexistent_user_id = 999999
        token = create_access_token(nonexistent_user_id)
        
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401
        
    def test_department_comes_from_database_relationship(self, client):
        """Department comes from database relationship"""
        # Login to get valid token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "karthik@aithinkers.com",  # Bob is in Sales
                "password": "password123"
            }
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Department should be loaded from DB relationship
        assert "department" in data
        assert data["department"]["name"] == "sales"
        
    def test_password_hash_is_never_returned(self, client):
        """password_hash is never returned"""
        # Login to get valid token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "swathi@aithinkers.com",
                "password": "password123"
            }
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should never expose password_hash
        assert "password_hash" not in data
        assert "password" not in data
        
    def test_invalid_authorization_header_format(self, client):
        """Invalid Authorization header format is rejected"""
        invalid_headers = [
            {"Authorization": "invalid"},
            {"Authorization": "bearer token"},  # lowercase
            {"Authorization": "Basic token"},  # wrong scheme
            {"Authorization": "token"},  # missing scheme
        ]
        
        for headers in invalid_headers:
            response = client.get("/api/auth/me", headers=headers)
            assert response.status_code == 401
            
    def test_bearer_token_format_required(self, client):
        """Bearer token format is required"""
        # Login to get valid token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "mohit@aithinkers.com",
                "password": "password123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Correct format
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Missing "Bearer " prefix
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": token}
        )
        assert response.status_code == 401
