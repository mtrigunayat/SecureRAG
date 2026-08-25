"""
Integration tests for document ingestion service
"""
import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from app.services.ingestion_service import IngestionService
from app.models.department import Department
from app.core.errors import (
    UnsupportedFileError,
    DepartmentNotFoundError,
    InvalidSensitivityError,
    EmptyDocumentError
)


class TestIngestionService:
    """Integration tests for document ingestion."""
    
    @pytest.fixture
    def ingestion_service(self, test_db_with_departments: Session):
        """Create ingestion service with test database."""
        return IngestionService(test_db_with_departments)
    
    @pytest.fixture
    def test_pdf_path(self, tmp_path):
        """Create a simple test PDF file."""
        # For now, skip PDF tests - we'll add them once we have proper test fixtures
        pytest.skip("Test PDF fixtures not yet created")
    
    def test_department_validation(self, ingestion_service: IngestionService, tmp_path):
        """Test that unknown department is rejected."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4\n")  # Minimal PDF header
        
        with pytest.raises(DepartmentNotFoundError) as exc_info:
            ingestion_service.ingest_document(
                file_path=test_file,
                document_name="Test Doc",
                department_name="nonexistent_department",
                sensitivity="internal"
            )
        
        assert "nonexistent_department" in str(exc_info.value.message)
    
    def test_sensitivity_validation(self, ingestion_service: IngestionService, tmp_path):
        """Test that invalid sensitivity is rejected."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4\n")
        
        with pytest.raises(InvalidSensitivityError) as exc_info:
            ingestion_service.ingest_document(
                file_path=test_file,
                document_name="Test Doc",
                department_name="engineering",
                sensitivity="invalid_level"
            )
        
        assert "invalid_level" in str(exc_info.value.message)
    
    def test_unsupported_file_type(self, ingestion_service: IngestionService, tmp_path):
        """Test that non-PDF files are rejected."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Not a PDF")
        
        with pytest.raises(UnsupportedFileError):
            ingestion_service.ingest_document(
                file_path=test_file,
                document_name="Test Doc",
                department_name="engineering",
                sensitivity="internal"
            )
