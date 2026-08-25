"""
Tests for health check endpoints
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint():
    """Test the root endpoint returns basic info."""
    client = TestClient(app)
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["version"] == "0.1.0"


def test_health_endpoint_structure():
    """Test the health endpoint returns proper structure."""
    client = TestClient(app)
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check structure
    assert "status" in data
    assert "services" in data
    
    # Check services
    assert "database" in data["services"]
    assert "vector_db" in data["services"]
    
    # Status should be one of: healthy, degraded
    assert data["status"] in ["healthy", "degraded"]


def test_health_endpoint_service_values():
    """Test the health endpoint service values are valid."""
    client = TestClient(app)
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Service statuses should be either "ok" or "unavailable"
    for service, status in data["services"].items():
        assert status in ["ok", "unavailable"], f"Invalid status for {service}: {status}"
