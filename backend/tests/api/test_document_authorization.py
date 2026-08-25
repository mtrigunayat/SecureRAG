"""
Document API Authorization Tests

Tests for department-based authorization on document endpoints.

CRITICAL SECURITY TESTS:
    - Access matrix: Alice (Engineering), Bob (Sales), Charlie (HR)
    - Client manipulation tests (query params, headers, body)
    - Authorization vs Authentication boundary
    - Information leakage prevention
"""
import pytest
from fastapi.testclient import TestClient


class TestDocumentAccessMatrix:
    """
    Test access matrix for department-based authorization.
    
    Users:
        Alice → Engineering (dept_id=1)
        Bob → Sales (dept_id=2)
        Charlie → HR (dept_id=3)
    
    Documents:
        Engineering: docs 1,2,3
        Sales: docs 4,5,6
        HR: docs 7,8,9
    
    Matrix:
                     Eng(1-3)  Sales(4-6)  HR(7-9)
        Alice (Eng)    ✓          ✗          ✗
        Bob (Sales)    ✗          ✓          ✗
        Charlie (HR)   ✗          ✗          ✓
    """
    
    # ============================================================
    # Alice (Engineering) Access Tests
    # ============================================================
    
    def test_alice_can_access_engineering_documents(self, client: TestClient):
        """Alice can access Engineering documents."""
        # Login as Alice
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Engineering documents: 1, 2, 3
        for doc_id in [1, 2, 3]:
            response = client.get(
                f"/api/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == doc_id
            assert data["department"]["name"] == "engineering"
    
    def test_alice_cannot_access_sales_documents(self, client: TestClient):
        """Alice cannot access Sales documents."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Sales documents: 4, 5, 6
        for doc_id in [4, 5, 6]:
            response = client.get(
                f"/api/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()
    
    def test_alice_cannot_access_hr_documents(self, client: TestClient):
        """Alice cannot access HR documents."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # HR documents: 7, 8, 9
        for doc_id in [7, 8, 9]:
            response = client.get(
                f"/api/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()
    
    # ============================================================
    # Bob (Sales) Access Tests
    # ============================================================
    
    def test_bob_can_access_sales_documents(self, client: TestClient):
        """Bob can access Sales documents."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "bob@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Sales documents: 4, 5, 6
        for doc_id in [4, 5, 6]:
            response = client.get(
                f"/api/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == doc_id
            assert data["department"]["name"] == "sales"
    
    def test_bob_cannot_access_engineering_documents(self, client: TestClient):
        """Bob cannot access Engineering documents."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "bob@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Engineering documents: 1, 2, 3
        for doc_id in [1, 2, 3]:
            response = client.get(
                f"/api/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 403
    
    def test_bob_cannot_access_hr_documents(self, client: TestClient):
        """Bob cannot access HR documents."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "bob@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # HR documents: 7, 8, 9
        for doc_id in [7, 8, 9]:
            response = client.get(
                f"/api/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 403
    
    # ============================================================
    # Charlie (HR) Access Tests
    # ============================================================
    
    def test_charlie_can_access_hr_documents(self, client: TestClient):
        """Charlie can access HR documents."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "charlie@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # HR documents: 7, 8, 9
        for doc_id in [7, 8, 9]:
            response = client.get(
                f"/api/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == doc_id
            assert data["department"]["name"] == "hr"
    
    def test_charlie_cannot_access_engineering_documents(self, client: TestClient):
        """Charlie cannot access Engineering documents."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "charlie@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Engineering documents: 1, 2, 3
        for doc_id in [1, 2, 3]:
            response = client.get(
                f"/api/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 403
    
    def test_charlie_cannot_access_sales_documents(self, client: TestClient):
        """Charlie cannot access Sales documents."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "charlie@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Sales documents: 4, 5, 6
        for doc_id in [4, 5, 6]:
            response = client.get(
                f"/api/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 403


class TestAuthenticationBoundary:
    """Test authentication vs authorization boundary."""
    
    def test_unauthenticated_request_returns_401(self, client: TestClient):
        """Unauthenticated request returns 401 (not 403)."""
        response = client.get("/api/documents/1")
        
        assert response.status_code == 401
        assert "authorization" in response.json()["detail"].lower()
    
    def test_invalid_token_returns_401(self, client: TestClient):
        """Invalid token returns 401 (not 403)."""
        response = client.get(
            "/api/documents/1",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    def test_expired_token_returns_401(self, client: TestClient):
        """Expired token returns 401 (not 403)."""
        # Expired token (expired long ago)
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjE2MDAwMDM2MDB9.fake"
        
        response = client.get(
            "/api/documents/1",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
    
    def test_authenticated_unauthorized_returns_403(self, client: TestClient):
        """Authenticated user without permission returns 403 (not 401)."""
        # Login as Alice (Engineering)
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to access Sales document
        response = client.get(
            "/api/documents/4",  # Sales document
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should be 403 (authorized user, but no permission)
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()


class TestClientManipulation:
    """
    CRITICAL SECURITY TESTS
    
    Verify that client cannot manipulate authorization scope.
    """
    
    def test_query_parameter_cannot_override_department(self, client: TestClient):
        """Query parameter ?department=X cannot override user's department."""
        # Login as Alice (Engineering)
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to access Sales document with ?department=sales
        response = client.get(
            "/api/documents/4?department=sales",  # Sales document + fake param
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should still be denied (department from PostgreSQL, not query param)
        assert response.status_code == 403
    
    def test_header_cannot_override_department(self, client: TestClient):
        """Custom header X-Department cannot override user's department."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to access Sales document with X-Department header
        response = client.get(
            "/api/documents/4",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Department": "sales",  # Fake department header
                "X-Department-ID": "2"     # Fake department ID header
            }
        )
        
        # Should still be denied
        assert response.status_code == 403
    
    def test_department_id_query_param_ignored(self, client: TestClient):
        """?department_id=X cannot override user's department."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try with department_id query parameter
        response = client.get(
            "/api/documents/4?department_id=2",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


class TestDataIntegrity:
    """Test data integrity and edge cases."""
    
    def test_nonexistent_document_returns_404(self, client: TestClient):
        """Nonexistent document returns 404 (not 403)."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Document ID that doesn't exist
        response = client.get(
            "/api/documents/999999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_invalid_document_id_returns_422(self, client: TestClient):
        """Invalid document ID format returns 422."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Invalid ID (zero or negative)
        response = client.get(
            "/api/documents/0",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422


class TestInformationLeakage:
    """Test that unauthorized access doesn't leak information."""
    
    def test_unauthorized_access_generic_error(self, client: TestClient):
        """Unauthorized access returns generic error (no document details)."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to access Sales document
        response = client.get(
            "/api/documents/4",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
        error = response.json()["detail"]
        
        # Error should be generic (not reveal document details)
        assert "permission" in error.lower()
        # Should NOT contain document name, department, etc.
        assert "pricing" not in error.lower()  # Document name
        assert "sales" not in error.lower()    # Department name
    
    def test_password_hash_never_returned(self, client: TestClient):
        """Document response never includes password_hash or sensitive data."""
        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@company.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/documents/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should not include sensitive fields
        assert "password_hash" not in data
        assert "content" not in data  # Document content (future phase)
        assert "embeddings" not in data  # Vector embeddings (future phase)
