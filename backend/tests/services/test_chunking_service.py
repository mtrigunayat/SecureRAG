"""
Tests for chunking service
"""
import pytest

from app.services.chunking_service import ChunkingService
from app.schemas.ingestion import ExtractedPage


class TestChunkingService:
    """Tests for document chunking service."""
    
    def test_chunking_creates_chunks(self):
        """Test that chunking creates chunks."""
        chunker = ChunkingService(chunk_size=100, chunk_overlap=20)
        
        pages = [
            ExtractedPage(
                page_number=1,
                text="This is a sample document with enough text to create multiple chunks. " * 10
            )
        ]
        
        chunks = chunker.chunk_document(
            pages=pages,
            document_id=1,
            document_name="Test Doc",
            department_id=1,
            department_name="engineering",
            sensitivity="internal"
        )
        
        assert len(chunks) > 1
        assert all(chunk.document_id == 1 for chunk in chunks)
    
    def test_chunk_size_configuration_respected(self):
        """Test that chunk size configuration is respected."""
        chunk_size = 100
        chunker = ChunkingService(chunk_size=chunk_size, chunk_overlap=10)
        
        pages = [
            ExtractedPage(page_number=1, text="word " * 200)
        ]
        
        chunks = chunker.chunk_document(
            pages=pages,
            document_id=1,
            document_name="Test",
            department_id=1,
            department_name="test",
            sensitivity="internal"
        )
        
        # Chunks should be approximately chunk_size (may vary slightly due to splitting logic)
        for chunk in chunks:
            # Allow some flexibility
            assert len(chunk.text) <= chunk_size * 1.5
    
    def test_chunks_have_deterministic_ids(self):
        """Test that chunk IDs are deterministic."""
        chunker = ChunkingService(chunk_size=100, chunk_overlap=20)
        
        pages = [ExtractedPage(page_number=1, text="Test text " * 50)]
        
        chunks1 = chunker.chunk_document(
            pages=pages,
            document_id=42,
            document_name="Test",
            department_id=1,
            department_name="test",
            sensitivity="internal"
        )
        
        chunks2 = chunker.chunk_document(
            pages=pages,
            document_id=42,
            document_name="Test",
            department_id=1,
            department_name="test",
            sensitivity="internal"
        )
        
        # Same input should produce same chunk IDs
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id
    
    def test_chunks_preserve_page_information(self):
        """Test that chunks preserve page information."""
        chunker = ChunkingService(chunk_size=50, chunk_overlap=10)
        
        pages = [
            ExtractedPage(page_number=1, text="Page 1 content " * 10),
            ExtractedPage(page_number=2, text="Page 2 content " * 10),
        ]
        
        chunks = chunker.chunk_document(
            pages=pages,
            document_id=1,
            document_name="Test",
            department_id=1,
            department_name="test",
            sensitivity="internal"
        )
        
        # All chunks should have valid page information
        for chunk in chunks:
            assert chunk.page_start >= 1
            assert chunk.page_end >= chunk.page_start
            assert chunk.page_end <= 2
    
    def test_chunk_metadata_complete(self):
        """Test that chunks have complete metadata."""
        chunker = ChunkingService(chunk_size=100, chunk_overlap=20)
        
        pages = [ExtractedPage(page_number=1, text="Test content " * 30)]
        
        chunks = chunker.chunk_document(
            pages=pages,
            document_id=123,
            document_name="Test Document",
            department_id=5,
            department_name="engineering",
            sensitivity="confidential"
        )
        
        for chunk in chunks:
            # Verify all required metadata fields
            assert chunk.chunk_id
            assert chunk.document_id == 123
            assert chunk.document_name == "Test Document"
            assert chunk.department_id == 5
            assert chunk.department_name == "engineering"
            assert chunk.sensitivity == "confidential"
            assert chunk.page_start > 0
            assert chunk.page_end > 0
            assert chunk.chunk_index >= 0
            assert len(chunk.text) > 0
    
    def test_empty_pages_return_no_chunks(self):
        """Test that empty pages don't create chunks."""
        chunker = ChunkingService()
        
        pages = [
            ExtractedPage(page_number=1, text=""),
            ExtractedPage(page_number=2, text="   "),
        ]
        
        chunks = chunker.chunk_document(
            pages=pages,
            document_id=1,
            document_name="Empty",
            department_id=1,
            department_name="test",
            sensitivity="internal"
        )
        
        assert len(chunks) == 0
    
    def test_chunk_ordering_is_sequential(self):
        """Test that chunks are ordered sequentially."""
        chunker = ChunkingService(chunk_size=100, chunk_overlap=20)
        
        pages = [ExtractedPage(page_number=1, text="Sequential text " * 50)]
        
        chunks = chunker.chunk_document(
            pages=pages,
            document_id=1,
            document_name="Test",
            department_id=1,
            department_name="test",
            sensitivity="internal"
        )
        
        # Chunk indices should be sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
