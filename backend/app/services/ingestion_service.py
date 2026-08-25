"""
Document ingestion service

Orchestrates the complete document ingestion pipeline.
"""
from pathlib import Path
from typing import Union
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.pdf_extraction_service import PDFExtractionService
from app.services.text_cleaning_service import TextCleaningService
from app.services.chunking_service import ChunkingService
from app.schemas.ingestion import IngestionResult
from app.models.document import Document, DocumentSensitivity
from app.models.department import Department
from app.repositories.document_repository import DocumentRepository
from app.utils.hashing import hash_file_content
from app.core.errors import (
    UnsupportedFileError,
    DepartmentNotFoundError,
    InvalidSensitivityError,
    IngestionError
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class IngestionService:
    """
    Main service for document ingestion pipeline.
    
    Pipeline:
        1. File validation
        2. Department/sensitivity validation  
        3. Content hashing
        4. Document registration (PostgreSQL)
        5. Text extraction (PDF)
        6. Text cleaning
        7. Chunking
        8. Metadata enrichment
        9. Return validated chunks (ready for Phase 7 embedding)
        
    Re-ingestion behavior:
        - If content hash unchanged: Skip processing, return existing document info
        - If content hash changed: Update document record and reprocess
    """
    
    def __init__(
        self,
        db: Session,
        pdf_extractor: PDFExtractionService = None,
        text_cleaner: TextCleaningService = None,
        chunker: ChunkingService = None,
        document_repo: DocumentRepository = None
    ):
        """
        Initialize ingestion service.
        
        Args:
            db: Database session
            pdf_extractor: PDF extraction service (creates default if None)
            text_cleaner: Text cleaning service (creates default if None)
            chunker: Chunking service (creates default if None)
            document_repo: Document repository (creates default if None)
        """
        self.db = db
        self.pdf_extractor = pdf_extractor or PDFExtractionService()
        self.text_cleaner = text_cleaner or TextCleaningService()
        self.chunker = chunker or ChunkingService()
        self.document_repo = document_repo or DocumentRepository(db)
    
    def ingest_document(
        self,
        file_path: Union[str, Path],
        document_name: str,
        department_name: str,
        sensitivity: str
    ) -> IngestionResult:
        """
        Ingest a document through the complete pipeline.
        
        Args:
            file_path: Path to document file
            document_name: Document name/title
            department_name: Department name (must exist in database)
            sensitivity: Sensitivity level (public/internal/confidential)
            
        Returns:
            IngestionResult with document metadata and chunks
            
        Raises:
            UnsupportedFileError: If file type not supported
            DepartmentNotFoundError: If department doesn't exist
            InvalidSensitivityError: If sensitivity invalid
            Various ingestion errors from pipeline stages
            
        Security:
            - Department must exist in PostgreSQL (prevents typos)
            - Sensitivity must be valid enum value
            - Document text treated as untrusted data
        """
        file_path = Path(file_path)
        
        logger.info(
            f"Starting ingestion: {file_path.name} → '{document_name}' "
            f"(dept={department_name}, sensitivity={sensitivity})"
        )
        
        # 1. Validate file type
        if file_path.suffix.lower() != '.pdf':
            raise UnsupportedFileError(file_path.suffix)
        
        if not file_path.exists():
            raise IngestionError(f"File not found: {file_path}")
        
        # 2. Validate department (must exist in database)
        department = self.db.query(Department).filter(
            Department.name == department_name.lower()
        ).first()
        
        if not department:
            logger.error(f"Department '{department_name}' not found in database")
            raise DepartmentNotFoundError(department_name)
        
        # 3. Validate sensitivity
        try:
            sensitivity_enum = DocumentSensitivity(sensitivity.lower())
        except ValueError:
            raise InvalidSensitivityError(sensitivity)
        
        # 4. Calculate content hash
        content_hash = hash_file_content(file_path)
        logger.info(f"Content hash: {content_hash}")
        
        # 5. Check for existing document with same hash (re-ingestion detection)
        existing_doc = self.db.query(Document).filter(
            Document.content_hash == content_hash,
            Document.name == document_name
        ).first()
        
        if existing_doc:
            logger.info(
                f"Document '{document_name}' with same content hash already exists "
                f"(ID={existing_doc.id}) - skipping ingestion"
            )
            # Return existing document info without reprocessing
            # Note: In production, might want to still return chunks from storage
            # For now, return empty result indicating no new processing needed
            return IngestionResult(
                document_id=existing_doc.id,
                document_name=existing_doc.name,
                department_name=department.name,
                sensitivity=existing_doc.sensitivity,
                content_hash=content_hash,
                page_count=0,
                character_count=0,
                chunk_count=0,
                chunks=[],
                status="UNCHANGED_SKIP_INGESTION"
            )
        
        # 6. Extract text from PDF
        extracted_pages = self.pdf_extractor.extract_text(file_path)
        page_count = len(extracted_pages)
        raw_char_count = sum(len(p.text) for p in extracted_pages)
        
        # 7. Clean extracted text
        cleaned_pages = self.text_cleaner.clean_pages(extracted_pages)
        cleaned_char_count = sum(len(p.text) for p in cleaned_pages)
        
        # 8. Register/update document in PostgreSQL
        document = self._register_document(
            document_name=document_name,
            department_id=department.id,
            sensitivity=sensitivity_enum.value,
            source=str(file_path),
            content_hash=content_hash
        )
        
        # 9. Chunk document
        chunks = self.chunker.chunk_document(
            pages=cleaned_pages,
            document_id=document.id,
            document_name=document.name,
            department_id=department.id,
            department_name=department.name,
            sensitivity=document.sensitivity
        )
        
        logger.info(
            f"Ingestion complete: document_id={document.id}, "
            f"pages={page_count}, chunks={len(chunks)}"
        )
        
        # 10. Return result
        return IngestionResult(
            document_id=document.id,
            document_name=document.name,
            department_name=department.name,
            sensitivity=document.sensitivity,
            content_hash=content_hash,
            page_count=page_count,
            character_count=cleaned_char_count,
            chunk_count=len(chunks),
            chunks=chunks,
            status="READY_FOR_EMBEDDING"
        )
    
    def _register_document(
        self,
        document_name: str,
        department_id: int,
        sensitivity: str,
        source: str,
        content_hash: str
    ) -> Document:
        """
        Register or update document in PostgreSQL.
        
        Args:
            document_name: Document name
            department_id: Department ID
            sensitivity: Sensitivity level
            source: Source file path
            content_hash: Content hash
            
        Returns:
            Document object
            
        Note:
            - indexed_at is NOT set (will be set in Phase 7 after embedding)
            - If document exists with different hash, updates it
        """
        # Check for existing document by name and department
        existing_doc = self.db.query(Document).filter(
            Document.name == document_name,
            Document.department_id == department_id
        ).first()
        
        if existing_doc:
            # Update existing document
            logger.info(f"Updating existing document ID={existing_doc.id}")
            existing_doc.sensitivity = sensitivity
            existing_doc.source = source
            existing_doc.content_hash = content_hash
            existing_doc.indexed_at = None  # Reset indexing status
            existing_doc.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing_doc)
            return existing_doc
        else:
            # Create new document
            document = Document(
                name=document_name,
                department_id=department_id,
                sensitivity=sensitivity,
                source=source,
                content_hash=content_hash,
                indexed_at=None  # Not indexed yet (Phase 7)
            )
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            logger.info(f"Created new document ID={document.id}")
            return document
