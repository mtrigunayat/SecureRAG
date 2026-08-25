"""
Authorization Service

Centralized authorization policy for department-based access control.

CRITICAL SECURITY PRINCIPLE:
    The client MUST NEVER control authorization scope.
    Department information MUST come from PostgreSQL (trusted source).
    The user's department is determined by their authenticated identity.

Authorization Flow:
    1. User authenticates (Phase 4)
    2. User entity loaded from PostgreSQL
    3. User's department loaded via database relationship
    4. Authorization policy checks department match
    5. Access granted or denied

This service establishes the contract for future Qdrant filtering.
"""
from typing import Optional
from app.models.user import User
from app.models.document import Document
from app.core.errors import ForbiddenError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthorizationScope:
    """
    Trusted authorization scope derived from authenticated user.
    
    This object represents the access boundaries for a user.
    It MUST be constructed server-side from PostgreSQL data.
    It MUST NEVER be constructed from client-provided data.
    
    Attributes:
        user_id: Authenticated user ID
        department_id: User's department ID (from PostgreSQL)
        department_name: User's department name (for logging/display)
    
    Future Use:
        The department_id will be used to filter Qdrant vector search results.
        Qdrant filter will be: metadata.department_id == scope.department_id
    """
    
    def __init__(self, user: User):
        """
        Create authorization scope from authenticated user.
        
        Args:
            user: Authenticated User object from PostgreSQL
            
        Security:
            - User must be loaded from PostgreSQL via get_current_user()
            - Department comes from database relationship (not client)
        """
        if not user.department:
            # This should not happen in normal operation
            # User should always have a department in the database
            logger.error(f"User {user.id} has no department relationship")
            raise ForbiddenError("User department not found")
        
        self.user_id = user.id
        self.department_id = user.department.id
        self.department_name = user.department.name
        
        logger.debug(
            f"Created authorization scope: "
            f"user_id={self.user_id}, "
            f"department_id={self.department_id}, "
            f"department_name={self.department_name}"
        )
    
    def __repr__(self) -> str:
        return (
            f"AuthorizationScope("
            f"user_id={self.user_id}, "
            f"department_id={self.department_id}, "
            f"department_name='{self.department_name}'"
            f")"
        )


class AuthorizationService:
    """
    Department-based authorization policy.
    
    POC Authorization Model:
        - Each user belongs to one department
        - Each document belongs to one department
        - Users can only access documents in their own department
    
    Access Rules:
        user.department_id == document.department_id → ALLOW
        user.department_id != document.department_id → DENY
    
    Future Extensions:
        - Public documents (sensitivity = "public")
        - Cross-department sharing
        - Role-based access control (RBAC)
        - Document-level permissions
    
    Security:
        - All checks use stable IDs (not names)
        - Department ID comes from PostgreSQL (trusted)
        - Generic error messages (no information leakage)
    """
    
    def __init__(self):
        """Initialize authorization service."""
        self.logger = get_logger(__name__)
    
    def create_scope(self, user: User) -> AuthorizationScope:
        """
        Create trusted authorization scope from authenticated user.
        
        Args:
            user: Authenticated User object
            
        Returns:
            AuthorizationScope with department_id from PostgreSQL
            
        Security:
            - User MUST be from get_current_user() (authenticated)
            - Department MUST be loaded from database relationship
        """
        return AuthorizationScope(user)
    
    def check_document_access(
        self,
        user: User,
        document: Document
    ) -> bool:
        """
        Check if user can access document.
        
        Args:
            user: Authenticated user
            document: Document to check
            
        Returns:
            True if access allowed, False otherwise
            
        Authorization Logic:
            Same department → allow
            Different department → deny
            
        Security:
            - Compares department_id (stable ID), not names
            - Department comes from PostgreSQL relationship
        """
        if not user.department:
            self.logger.warning(f"User {user.id} has no department")
            return False
        
        if not document.department:
            self.logger.warning(f"Document {document.id} has no department")
            return False
        
        # Authorization check: department ID match
        user_dept_id = user.department.id
        doc_dept_id = document.department.id
        
        has_access = user_dept_id == doc_dept_id
        
        if has_access:
            self.logger.debug(
                f"Access granted: user {user.id} ({user.department.name}) "
                f"accessing document {document.id} ({document.name})"
            )
        else:
            self.logger.warning(
                f"Access denied: user {user.id} ({user.department.name}) "
                f"attempted to access document {document.id} "
                f"from {document.department.name} department"
            )
        
        return has_access
    
    def authorize_document_access(
        self,
        user: User,
        document: Document
    ) -> None:
        """
        Authorize document access or raise exception.
        
        Args:
            user: Authenticated user
            document: Document to access
            
        Raises:
            ForbiddenError: If user does not have permission
            
        Usage:
            try:
                auth_service.authorize_document_access(user, document)
                # Access granted, proceed with operation
            except ForbiddenError:
                # Access denied
        """
        if not self.check_document_access(user, document):
            # Generic error message (don't reveal document details)
            raise ForbiddenError()
    
    def get_department_filter(self, user: User) -> dict:
        """
        Get department filter for future Qdrant queries.
        
        This establishes the contract for Phase 6 (Qdrant integration).
        
        Args:
            user: Authenticated user
            
        Returns:
            Dictionary with department_id for filtering
            
        Future Use:
            This will be used to construct Qdrant metadata filter:
            
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            filter_dict = auth_service.get_department_filter(user)
            
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="department_id",
                        match=MatchValue(value=filter_dict["department_id"])
                    )
                ]
            )
            
        Security:
            - department_id comes from PostgreSQL (trusted)
            - Client cannot influence this value
        """
        if not user.department:
            raise ForbiddenError("User department not found")
        
        return {
            "department_id": user.department.id,
            "department_name": user.department.name  # For logging only
        }


# Global instance (singleton pattern)
authorization_service = AuthorizationService()
