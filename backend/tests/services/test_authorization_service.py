"""
Authorization Service Tests

Tests for department-based authorization policy.

CRITICAL SECURITY TESTS:
    - Department comes from PostgreSQL (trusted)
    - Client cannot influence authorization scope
    - Same department → allow
    - Different department → deny
"""
import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.document import Document
from app.models.department import Department
from app.services.authorization_service import (
    authorization_service,
    AuthorizationScope,
)
from app.core.errors import ForbiddenError


class TestAuthorizationScope:
    """Test AuthorizationScope creation from authenticated user."""
    
    def test_scope_created_from_user(self, db_session: Session):
        """Scope is created from authenticated user's PostgreSQL department."""
        # Create department
        dept = Department(id=1, name="engineering", description="Engineering team")
        db_session.add(dept)
        
        # Create user
        user = User(
            id=1,
            username="mohit",
            email="mohit@aithinkers.com",
            full_name="Mohit Trigunayat",
            password_hash="hash",
            department_id=dept.id
        )
        user.department = dept  # Simulate relationship
        db_session.add(user)
        db_session.commit()
        
        # Create scope
        scope = AuthorizationScope(user)
        
        assert scope.user_id == 1
        assert scope.department_id == 1
        assert scope.department_name == "engineering"
    
    def test_scope_fails_without_department(self, db_session: Session):
        """Scope creation fails if user has no department."""
        user = User(
            id=1,
            username="mohit",
            email="mohit@aithinkers.com",
            full_name="Mohit Trigunayat",
            password_hash="hash",
            department_id=1
        )
        user.department = None  # No department relationship
        
        with pytest.raises(ForbiddenError, match="User department not found"):
            AuthorizationScope(user)


class TestAuthorizationService:
    """Test department-based authorization policy."""
    
    def test_same_department_allowed(self, db_session: Session):
        """User can access document in same department."""
        # Create department
        dept = Department(id=1, name="engineering")
        db_session.add(dept)
        
        # Create user
        user = User(
            id=1,
            username="mohit",
            email="mohit@aithinkers.com",
            full_name="Mohit Trigunayat",
            password_hash="hash",
            department_id=dept.id
        )
        user.department = dept
        db_session.add(user)
        
        # Create document in same department
        document = Document(
            id=1,
            name="Deployment Guidelines",
            department_id=dept.id
        )
        document.department = dept
        db_session.add(document)
        db_session.commit()
        
        # Check access
        assert authorization_service.check_document_access(user, document) is True
        
        # Should not raise exception
        authorization_service.authorize_document_access(user, document)
    
    def test_different_department_denied(self, db_session: Session):
        """User cannot access document in different department."""
        # Create departments
        engineering = Department(id=1, name="engineering")
        sales = Department(id=2, name="sales")
        db_session.add_all([engineering, sales])
        
        # Create user in engineering
        user = User(
            id=1,
            username="mohit",
            email="mohit@aithinkers.com",
            full_name="Mohit Trigunayat",
            password_hash="hash",
            department_id=engineering.id
        )
        user.department = engineering
        db_session.add(user)
        
        # Create document in sales
        document = Document(
            id=1,
            name="Pricing Policy",
            department_id=sales.id
        )
        document.department = sales
        db_session.add(document)
        db_session.commit()
        
        # Check access
        assert authorization_service.check_document_access(user, document) is False
        
        # Should raise exception
        with pytest.raises(ForbiddenError):
            authorization_service.authorize_document_access(user, document)
    
    def test_get_department_filter(self, db_session: Session):
        """Department filter contains trusted PostgreSQL department_id."""
        dept = Department(id=1, name="engineering")
        db_session.add(dept)
        
        user = User(
            id=1,
            username="mohit",
            email="mohit@aithinkers.com",
            full_name="Mohit Trigunayat",
            password_hash="hash",
            department_id=dept.id
        )
        user.department = dept
        db_session.add(user)
        db_session.commit()
        
        # Get filter
        filter_dict = authorization_service.get_department_filter(user)
        
        # Verify filter contains PostgreSQL department_id
        assert filter_dict["department_id"] == 1
        assert filter_dict["department_name"] == "engineering"
    
    def test_get_department_filter_fails_without_department(self, db_session: Session):
        """Filter creation fails if user has no department."""
        user = User(
            id=1,
            username="mohit",
            email="mohit@aithinkers.com",
            full_name="Mohit Trigunayat",
            password_hash="hash",
            department_id=1
        )
        user.department = None
        
        with pytest.raises(ForbiddenError, match="User department not found"):
            authorization_service.get_department_filter(user)
