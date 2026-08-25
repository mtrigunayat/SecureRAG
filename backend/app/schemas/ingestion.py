"""
Ingestion schemas

Data contracts for document ingestion pipeline (Phase 6).
"""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ExtractedPage(BaseModel):
    """
    Represents a single page of extracted text from a PDF.
    
    Attributes:
        page_number: 1-indexed page number
        text: Extracted text content from the page
    """
    page_number: int = Field(..., ge=1, description="1-indexed page number")
    text: str = Field(..., description="Extracted text content from the page")
    
    model_config = ConfigDict(frozen=True)


class DocumentChunk(BaseModel):
    """
    Represents a processed document chunk ready for embedding (Phase 7).
    
    This is the Phase 6 → Phase 7 contract.
    Phase 7 will consume these chunks to generate embeddings
    and index them into Qdrant.
    
    Attributes:
        chunk_id: Deterministic identifier (document_id + chunk_index)
        document_id: PostgreSQL document ID
        document_name: Document name for display/debugging
        department_id: Department ID for ACL filtering
        department_name: Department name for display
        sensitivity: Document sensitivity level
        page_start: Starting page number (1-indexed)
        page_end: Ending page number (1-indexed, inclusive)
        chunk_index: 0-indexed position in document chunk sequence
        text: Chunk text content (ready for embedding)
        
    Security:
        - department_id and department_name come from PostgreSQL (trusted source)
        - Client cannot influence these values
        - Used for Qdrant ACL filtering in Phase 7+
    """
    chunk_id: str = Field(..., description="Deterministic chunk identifier")
    document_id: int = Field(..., description="PostgreSQL document ID")
    document_name: str = Field(..., description="Document name")
    department_id: int = Field(..., description="Department ID (for ACL)")
    department_name: str = Field(..., description="Department name (for display)")
    sensitivity: str = Field(..., description="Sensitivity level")
    page_start: int = Field(..., ge=1, description="Starting page number")
    page_end: int = Field(..., ge=1, description="Ending page number (inclusive)")
    chunk_index: int = Field(..., ge=0, description="Chunk position in document")
    text: str = Field(..., min_length=1, description="Chunk text content")
    
    model_config = ConfigDict(frozen=True)


class IngestionResult(BaseModel):
    """
    Result of document ingestion process.
    
    Attributes:
        document_id: PostgreSQL document ID
        document_name: Document name
        department_name: Department name
        sensitivity: Document sensitivity level
        content_hash: SHA-256 content hash
        page_count: Number of pages extracted
        character_count: Total characters extracted
        chunk_count: Number of chunks created
        chunks: List of document chunks (ready for Phase 7)
        status: Ingestion status message
    """
    document_id: int = Field(..., description="PostgreSQL document ID")
    document_name: str = Field(..., description="Document name")
    department_name: str = Field(..., description="Department name")
    sensitivity: str = Field(..., description="Sensitivity level")
    content_hash: str = Field(..., description="SHA-256 content hash")
    page_count: int = Field(..., ge=0, description="Number of pages")
    character_count: int = Field(..., ge=0, description="Total characters extracted")
    chunk_count: int = Field(..., ge=0, description="Number of chunks created")
    chunks: List[DocumentChunk] = Field(..., description="Document chunks")
    status: str = Field(default="READY_FOR_EMBEDDING", description="Ingestion status")
    
    model_config = ConfigDict(frozen=True)
