"""
Department model

Represents organizational departments (e.g., Engineering, Sales, HR).
Departments own documents and contain users.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.db.session import Base


class Department(Base):
    """
    Department entity.
    
    A department is an organizational unit that:
    - Contains users (employees)
    - Owns documents
    - Defines authorization scope for document access
    
    Attributes:
        id: Primary key
        name: Unique department name (e.g., "engineering", "sales", "hr")
        description: Optional description
        created_at: Creation timestamp
        updated_at: Last update timestamp
        users: Relationship to User entities
        documents: Relationship to Document entities
    """
    
    __tablename__ = "departments"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Department name (unique, lowercase for consistency)
    name = Column(String(100), unique=True, nullable=False, index=True)
    
    # Optional description
    description = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="department", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="department", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Department(id={self.id}, name='{self.name}')>"
