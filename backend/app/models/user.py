"""
User model

Represents company employees who can query the knowledge base.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    """
    User entity.
    
    Represents an employee who can:
    - Authenticate to the system (future phase)
    - Query documents
    - Access documents based on department membership
    
    Attributes:
        id: Primary key
        username: Unique username
        email: Unique email address
        full_name: User's full name
        department_id: Foreign key to department
        created_at: Creation timestamp
        updated_at: Last update timestamp
        department: Relationship to Department entity
    
    Note:
        Password/authentication fields will be added in Phase 4.
        Currently modeling identity and department membership only.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # User identity
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    
    # Department membership (defines authorization scope)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    department = relationship("Department", back_populates="users")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', department_id={self.department_id})>"
