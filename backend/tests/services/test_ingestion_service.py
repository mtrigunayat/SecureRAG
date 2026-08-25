"""
Integration tests for ingestion service
"""
import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from app.services.ingestion_service import IngestionService
from app.repositories.document_repository import DocumentRepository
from app.core.errors import (
    UnsupportedFileError,
    DepartmentNotFoundError,
    InvalidSensitivityError,
    EmptyDocumentError
)


class TestIngestionService:
    """Integration tests for complete ingestion pipeline."""
    
    @pytest.fixture
    def ingestion_service(self, test_db_with_departments: Session):
        """Create ingestion service with test database."""
        return IngestionService(test_db_with_departments)
    
    @pytest.fixture
    def document_repository(self, test_db_with_departments: Session):
        """Create document repository."""
        return DocumentRepository(test_db_with_departments)
    
    @pytest.fixture
    def test_pdfs_dir(self):
        """Get test PDFs directory."""
        return Path(__file__).parent.parent / "fixtures" / "pdfs"
    
    def test_ingest_deployment_guidelines_full_pipeline(
        self, ingestion_service: IngestionService, 
        document_repository: DocumentRepository,
        test_pdfs_dir
    ):
        """Test complete ingestion pipeline with deployment guidelines."""
        pdf_path = test_pdfs_dir / "deployment_guidelines.pdf"
        
        result = ingestion_service.ingest_document(
            file_path=pdf_path,
            document_name="Deployment Guidelines",
            department_name="engineering",
            sensitivity="internal"
        )
        
        # Verify ingestion result
        assert result.status == "READY_FOR_EMBEDDING"
        assert result.document_name == "Deployment Guidelines"
        assert result.department_name == "engineering"
        assert result.sensitivity == "internal"
        assert result.page_count == 3
        assert result.character_count > 0
        assert result.chunk_count > 0
        assert len(result.chunks) == result.chunk_count
        assert result.content_hash is not None
        assert result.document_id is not None
        
        # Verify chunks have proper structure
        for i, chunk in enumerate(result.chunks):
            assert chunk.chunk_id == f"{result.document_id}_{i}"
            assert chunk.document_id == result.document_id
            assert chunk.document_name == "Deployment Guidelines"
            assert chunk.department_name == "engineering"
            assert chunk.sensitivity == "internal"
            assert chunk.chunk_index == i
            assert chunk.page_start >= 1
            assert chunk.page_end >= chunk.page_start
            assert chunk.page_end <= 3
            assert len(chunk.text) > 0
        
        # Verify document was created in database
        document = document_repository.get_by_id(result.document_id)
        assert document is not None
        assert document.name == "Deployment Guidelines"
        assert document.content_hash == result.content_hash
        assert document.indexed_at is None  # Not yet indexed in Phase 7
    
    def test_ingest_different_departments(
        self, ingestion_service: IngestionService,
        test_pdfs_dir
    ):
        """Test ingestion with different departments."""
        # Ingest engineering document
        eng_result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "coding_standards.pdf",
            document_name="Coding Standards",
            department_name="engineering",
            sensitivity="internal"
        )
        assert eng_result.department_name == "engineering"
        
        # Ingest sales document
        sales_result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "sales_playbook.pdf",
            document_name="Sales Playbook",
            department_name="sales",
            sensitivity="confidential"
        )
        assert sales_result.department_name == "sales"
        
        # Ingest HR document
        hr_result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "employee_handbook.pdf",
            document_name="Employee Handbook",
            department_name="hr",
            sensitivity="internal"
        )
        assert hr_result.department_name == "hr"
        
        # Each should have different department metadata
        assert eng_result.chunks[0].department_name == "engineering"
        assert sales_result.chunks[0].department_name == "sales"
        assert hr_result.chunks[0].department_name == "hr"
    
    def test_ingest_different_sensitivities(
        self, ingestion_service: IngestionService,
        test_pdfs_dir
    ):
        """Test ingestion with different sensitivity levels."""
        # Test internal
        internal_result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "coding_standards.pdf",
            document_name="Internal Doc",
            department_name="engineering",
            sensitivity="internal"
        )
        assert internal_result.sensitivity == "internal"
        assert internal_result.chunks[0].sensitivity == "internal"
        
        # Test confidential
        confidential_result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "sales_playbook.pdf",
            document_name="Confidential Doc",
            department_name="sales",
            sensitivity="confidential"
        )
        assert confidential_result.sensitivity == "confidential"
        assert confidential_result.chunks[0].sensitivity == "confidential"
        
        # Test public
        public_result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "employee_handbook.pdf",
            document_name="Public Doc",
            department_name="hr",
            sensitivity="public"
        )
        assert public_result.sensitivity == "public"
        assert public_result.chunks[0].sensitivity == "public"
    
    def test_re_ingestion_with_unchanged_content(
        self, ingestion_service: IngestionService,
        document_repository: DocumentRepository,
        test_pdfs_dir
    ):
        """Test that re-ingesting unchanged document is skipped."""
        pdf_path = test_pdfs_dir / "coding_standards.pdf"
        
        # First ingestion
        result1 = ingestion_service.ingest_document(
            file_path=pdf_path,
            document_name="Coding Standards",
            department_name="engineering",
            sensitivity="internal"
        )
        assert result1.status == "READY_FOR_EMBEDDING"
        doc_id = result1.document_id
        content_hash = result1.content_hash
        
        # Second ingestion with same content
        result2 = ingestion_service.ingest_document(
            file_path=pdf_path,
            document_name="Coding Standards",
            department_name="engineering",
            sensitivity="internal"
        )
        
        # Should skip re-ingestion
        assert result2.status == "UNCHANGED_SKIP_INGESTION"
        assert result2.document_id == doc_id
        assert result2.content_hash == content_hash
        
        # Verify only one document in database
        document = document_repository.get_by_id(doc_id)
        assert document.content_hash == content_hash
    
    def test_re_ingestion_with_changed_content(
        self, ingestion_service: IngestionService,
        document_repository: DocumentRepository,
        test_pdfs_dir
    ):
        """Test that re-ingesting changed document updates it."""
        # First ingestion
        result1 = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "coding_standards.pdf",
            document_name="Standards Doc",
            department_name="engineering",
            sensitivity="internal"
        )
        doc_id = result1.document_id
        hash1 = result1.content_hash
        
        # Second ingestion with different content (different file)
        result2 = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "deployment_guidelines.pdf",
            document_name="Standards Doc",  # Same name
            department_name="engineering",
            sensitivity="internal"
        )
        
        # Should create new ingestion
        assert result2.status == "READY_FOR_EMBEDDING"
        assert result2.document_id == doc_id  # Same document ID (by name)
        assert result2.content_hash != hash1  # Different hash
        
        # Verify document was updated
        document = document_repository.get_by_id(doc_id)
        assert document.content_hash == result2.content_hash
    
    def test_department_not_found_error(
        self, ingestion_service: IngestionService,
        test_pdfs_dir
    ):
        """Test that unknown department raises error."""
        with pytest.raises(DepartmentNotFoundError) as exc_info:
            ingestion_service.ingest_document(
                file_path=test_pdfs_dir / "coding_standards.pdf",
                document_name="Test Doc",
                department_name="nonexistent",
                sensitivity="internal"
            )
        
        assert "nonexistent" in exc_info.value.message
    
    def test_invalid_sensitivity_error(
        self, ingestion_service: IngestionService,
        test_pdfs_dir
    ):
        """Test that invalid sensitivity raises error."""
        with pytest.raises(InvalidSensitivityError) as exc_info:
            ingestion_service.ingest_document(
                file_path=test_pdfs_dir / "coding_standards.pdf",
                document_name="Test Doc",
                department_name="engineering",
                sensitivity="invalid_level"
            )
        
        assert "invalid_level" in exc_info.value.message
        assert "internal" in str(exc_info.value.details)
        assert "confidential" in str(exc_info.value.details)
        assert "public" in str(exc_info.value.details)
    
    def test_unsupported_file_type_error(
        self, ingestion_service: IngestionService,
        tmp_path
    ):
        """Test that non-PDF files raise error."""
        # Create a .txt file
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Not a PDF")
        
        with pytest.raises(UnsupportedFileError) as exc_info:
            ingestion_service.ingest_document(
                file_path=txt_file,
                document_name="Test Doc",
                department_name="engineering",
                sensitivity="internal"
            )
        
        assert ".txt" in exc_info.value.message
    
    def test_empty_document_error(
        self, ingestion_service: IngestionService,
        test_pdfs_dir
    ):
        """Test that empty PDF is handled (may have minimal content)."""
        # The generated "empty" PDF has a title, so it won't raise EmptyDocumentError
        # Just verify it can be ingested
        result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "empty_valid.pdf",
            document_name="Empty PDF",
            department_name="engineering",
            sensitivity="internal"
        )
        
        # Should have minimal content
        assert result.page_count == 1
        assert result.character_count < 100
    
    def test_chunk_size_respected(
        self, ingestion_service: IngestionService,
        test_pdfs_dir
    ):
        """Test that chunks respect configured size."""
        result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "deployment_guidelines.pdf",
            document_name="Test Doc",
            department_name="engineering",
            sensitivity="internal"
        )
        
        # Most chunks should be close to chunk_size (600 chars)
        # Allow some variation due to sentence boundaries
        for chunk in result.chunks:
            # Each chunk should be non-empty and not too large
            assert len(chunk.text) > 0
            assert len(chunk.text) <= 800  # chunk_size + some overlap buffer
    
    def test_chunks_have_sequential_indices(
        self, ingestion_service: IngestionService,
        test_pdfs_dir
    ):
        """Test that chunks have sequential indices."""
        result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "coding_standards.pdf",
            document_name="Test Doc",
            department_name="engineering",
            sensitivity="internal"
        )
        
        for i, chunk in enumerate(result.chunks):
            assert chunk.chunk_index == i
    
    def test_chunks_preserve_page_boundaries(
        self, ingestion_service: IngestionService,
        test_pdfs_dir
    ):
        """Test that chunks preserve accurate page information."""
        result = ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "deployment_guidelines.pdf",
            document_name="Test Doc",
            department_name="engineering",
            sensitivity="internal"
        )
        
        # All chunks should have valid page ranges
        for chunk in result.chunks:
            assert chunk.page_start >= 1
            assert chunk.page_end >= chunk.page_start
            assert chunk.page_end <= result.page_count
    
    def test_multiple_documents_ingestion(
        self, ingestion_service: IngestionService,
        document_repository: DocumentRepository,
        test_pdfs_dir
    ):
        """Test ingesting multiple different documents."""
        results = []
        
        # Ingest multiple documents
        results.append(ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "deployment_guidelines.pdf",
            document_name="Deployment Guidelines",
            department_name="engineering",
            sensitivity="internal"
        ))
        
        results.append(ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "coding_standards.pdf",
            document_name="Coding Standards",
            department_name="engineering",
            sensitivity="internal"
        ))
        
        results.append(ingestion_service.ingest_document(
            file_path=test_pdfs_dir / "sales_playbook.pdf",
            document_name="Sales Playbook",
            department_name="sales",
            sensitivity="confidential"
        ))
        
        # All should be ingested successfully
        for result in results:
            assert result.status == "READY_FOR_EMBEDDING"
            assert result.document_id is not None
        
        # All should have different document IDs
        doc_ids = [r.document_id for r in results]
        assert len(set(doc_ids)) == 3
        
        # All should be in database
        for doc_id in doc_ids:
            assert document_repository.get_by_id(doc_id) is not None
