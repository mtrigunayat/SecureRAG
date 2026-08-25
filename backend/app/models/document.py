"""
Document model

Represents company documents in the knowledge base.
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class DocumentSensitivity(str, Enum):
    """
    Document sensitivity classification.
    
    Values:
        PUBLIC: Accessible to all users (future use)
        INTERNAL: Standard internal documents
        CONFIDENTIAL: Sensitive internal documents (future use)
    """
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


class Document(Base):
    """
    Document entity.
    
    Represents a company document in the knowledge base.
    PostgreSQL stores document metadata and ownership.
    Qdrant (future phase) will store the actual chunks and embeddings.
    
    Attributes:
        id: Primary key (will be used as document_id in Qdrant)
        name: Document name/title
        department_id: Foreign key to department (defines access scope)
        sensitivity: Classification level
        source: Original file path or source reference
        content_hash: Hash for duplicate detection
        indexed_at: When document was indexed to Qdrant (null if not indexed)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        department: Relationship to Department entity
    
    PostgreSQL-Qdrant Contract:
        This document.id will be stored in Qdrant payloads as "document_id".
        Chunks will reference this ID to maintain the relationship.
    """
    
    __tablename__ = "documents"
    
    # Primary key (will be used as document_id in Qdrant)
    id = Column(Integer, primary_key=True, index=True)
    
    # Document identity
    name = Column(String(255), nullable=False, index=True)
    
    # Department ownership (defines access scope)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    
    # Sensitivity classification
    sensitivity = Column(String(50), nullable=False, default=DocumentSensitivity.INTERNAL.value)
    
    # Source reference (file path, URL, etc.)
    source = Column(Text, nullable=True)
    
    # Content hash for duplicate detection and re-indexing
    content_hash = Column(String(64), nullable=True, index=True)
    
    # Indexing status
    indexed_at = Column(DateTime, nullable=True)  # Null = not indexed yet
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    department = relationship("Department", back_populates="documents")
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, name='{self.name}', department_id={self.department_id})>"
