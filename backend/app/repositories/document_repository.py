"""
Document repository

Provides data access methods for Document entities.
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.document import Document, DocumentSensitivity
from app.core.errors import DatabaseError


class DocumentRepository:
    """
    Repository for Document entity database operations.
    
    Encapsulates database access logic for documents.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_by_id(self, document_id: int) -> Optional[Document]:
        """
        Get document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        return self.db.query(Document).filter(Document.id == document_id).first()
    
    def get_by_department(self, department_id: int) -> List[Document]:
        """
        Get all documents in a department.
        
        Args:
            department_id: Department ID
            
        Returns:
            List of documents in the department
        """
        return self.db.query(Document).filter(Document.department_id == department_id).all()
    
    def get_by_content_hash(self, content_hash: str) -> Optional[Document]:
        """
        Get document by content hash.
        
        Args:
            content_hash: Content hash
            
        Returns:
            Document if found, None otherwise
        """
        return self.db.query(Document).filter(Document.content_hash == content_hash).first()
    
    def get_all(self) -> List[Document]:
        """
        Get all documents.
        
        Returns:
            List of all documents
        """
        return self.db.query(Document).all()
    
    def get_indexed(self) -> List[Document]:
        """
        Get all indexed documents.
        
        Returns:
            List of documents that have been indexed to Qdrant
        """
        return self.db.query(Document).filter(Document.indexed_at.isnot(None)).all()
    
    def get_not_indexed(self) -> List[Document]:
        """
        Get all documents not yet indexed.
        
        Returns:
            List of documents that haven't been indexed to Qdrant yet
        """
        return self.db.query(Document).filter(Document.indexed_at.is_(None)).all()
    
    def create(
        self,
        name: str,
        department_id: int,
        sensitivity: str = DocumentSensitivity.INTERNAL.value,
        source: Optional[str] = None,
        content_hash: Optional[str] = None
    ) -> Document:
        """
        Create a new document.
        
        Args:
            name: Document name
            department_id: Department ID
            sensitivity: Sensitivity classification
            source: Optional source reference
            content_hash: Optional content hash
            
        Returns:
            Created document
            
        Raises:
            DatabaseError: If creation fails
        """
        try:
            document = Document(
                name=name,
                department_id=department_id,
                sensitivity=sensitivity,
                source=source,
                content_hash=content_hash
            )
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            return document
        except IntegrityError as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to create document: {e}") from e
    
    def update(
        self,
        document_id: int,
        name: Optional[str] = None,
        sensitivity: Optional[str] = None,
        source: Optional[str] = None,
        content_hash: Optional[str] = None
    ) -> Optional[Document]:
        """
        Update document metadata.
        
        Args:
            document_id: Document ID
            name: New name (optional)
            sensitivity: New sensitivity (optional)
            source: New source (optional)
            content_hash: New content hash (optional)
            
        Returns:
            Updated document if found, None otherwise
        """
        document = self.get_by_id(document_id)
        if document:
            if name is not None:
                document.name = name
            if sensitivity is not None:
                document.sensitivity = sensitivity
            if source is not None:
                document.source = source
            if content_hash is not None:
                document.content_hash = content_hash
            try:
                self.db.commit()
                self.db.refresh(document)
            except IntegrityError as e:
                self.db.rollback()
                raise DatabaseError(f"Failed to update document: {e}") from e
        return document
    
    def mark_as_indexed(self, document_id: int) -> Optional[Document]:
        """
        Mark document as indexed to Qdrant.
        
        Args:
            document_id: Document ID
            
        Returns:
            Updated document if found, None otherwise
        """
        document = self.get_by_id(document_id)
        if document:
            document.indexed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(document)
        return document
    
    def delete(self, document_id: int) -> bool:
        """
        Delete document.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if deleted, False if not found
        """
        document = self.get_by_id(document_id)
        if document:
            self.db.delete(document)
            self.db.commit()
            return True
        return False
