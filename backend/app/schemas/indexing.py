"""
Vector indexing schemas

Data contracts for vector indexing operations (Phase 7).
"""
from typing import Optional
from pydantic import BaseModel, Field


class IndexingResult(BaseModel):
    """
    Result of vector indexing operation.
    
    Attributes:
        document_id: PostgreSQL document ID
        document_name: Document name
        department_name: Department name
        chunk_count: Number of chunks from Phase 6
        embedded_count: Number of embeddings generated
        indexed_count: Number of vectors indexed to Qdrant
        embedding_model: Model used for embeddings
        vector_dimension: Dimension of generated vectors
        collection: Qdrant collection name
        status: Indexing status
    """
    document_id: int = Field(..., description="PostgreSQL document ID")
    document_name: str = Field(..., description="Document name")
    department_name: str = Field(..., description="Department name")
    chunk_count: int = Field(..., ge=0, description="Number of chunks")
    embedded_count: int = Field(..., ge=0, description="Number of embeddings generated")
    indexed_count: int = Field(..., ge=0, description="Number of vectors indexed")
    embedding_model: str = Field(..., description="Embedding model name")
    vector_dimension: int = Field(..., description="Vector dimension")
    collection: str = Field(..., description="Qdrant collection name")
    status: str = Field(..., description="Indexing status")
