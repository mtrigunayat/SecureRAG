"""
User repository

Provides data access methods for User entities.
"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.core.errors import DatabaseError


class UserRepository:
    """
    Repository for User entity database operations.
    
    Encapsulates database access logic for users.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID with department relationship loaded.
        
        Args:
            user_id: User ID
            
        Returns:
            User if found, None otherwise
            
        Note:
            Uses joinedload to eagerly load department relationship
            to avoid lazy loading issues when session is closed.
        """
        return (
            self.db.query(User)
            .options(joinedload(User.department))
            .filter(User.id == user_id)
            .first()
        )
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User if found, None otherwise
        """
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email with department relationship loaded.
        
        Args:
            email: Email address
            
        Returns:
            User if found, None otherwise
            
        Note:
            Uses joinedload to eagerly load department relationship
            to avoid lazy loading issues when session is closed.
        """
        return (
            self.db.query(User)
            .options(joinedload(User.department))
            .filter(User.email == email)
            .first()
        )
    
    def get_by_department(self, department_id: int) -> List[User]:
        """
        Get all users in a department.
        
        Args:
            department_id: Department ID
            
        Returns:
            List of users in the department
        """
        return self.db.query(User).filter(User.department_id == department_id).all()
    
    def get_all(self) -> List[User]:
        """
        Get all users.
        
        Returns:
            List of all users
        """
        return self.db.query(User).all()
    
    def create(
        self,
        username: str,
        email: str,
        full_name: str,
        department_id: int,
        password_hash: str = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            username: Unique username
            email: Unique email address
            full_name: User's full name
            department_id: Department ID
            password_hash: Optional password hash (for testing)
            
        Returns:
            Created user
            
        Raises:
            DatabaseError: If username or email already exists, or department not found
        """
        # Use a default password hash if none provided (for testing)
        if password_hash is None:
            import bcrypt
            password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        try:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                password_hash=password_hash,
                department_id=department_id
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
            if "username" in str(e):
                raise DatabaseError(f"Username '{username}' already exists") from e
            elif "email" in str(e):
                raise DatabaseError(f"Email '{email}' already exists") from e
            else:
                raise DatabaseError(f"Failed to create user: {e}") from e
    
    def update(
        self,
        user_id: int,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        department_id: Optional[int] = None
    ) -> Optional[User]:
        """
        Update user.
        
        Args:
            user_id: User ID
            email: New email (optional)
            full_name: New full name (optional)
            department_id: New department ID (optional)
            
        Returns:
            Updated user if found, None otherwise
        """
        user = self.get_by_id(user_id)
        if user:
            if email is not None:
                user.email = email
            if full_name is not None:
                user.full_name = full_name
            if department_id is not None:
                user.department_id = department_id
            try:
                self.db.commit()
                self.db.refresh(user)
            except IntegrityError as e:
                self.db.rollback()
                raise DatabaseError(f"Failed to update user: {e}") from e
        return user
    
    def delete(self, user_id: int) -> bool:
        """
        Delete user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False
