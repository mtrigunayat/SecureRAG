"""
Retrieval schemas

Data contracts for Phase 8 secure vector retrieval.
"""
from typing import List
from pydantic import BaseModel, Field, ConfigDict


class RetrievalRequest(BaseModel):
    """
    Request for document retrieval.
    
    Security:
        - Only the question is provided by the client
        - department_id is resolved server-side from authenticated user
        - Client CANNOT influence authorization scope
    """
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User's question to search the knowledge base"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What is our leave policy?"
            }
        }
    )


class RetrievalChunk(BaseModel):
    """
    Single retrieved chunk with metadata.
    
    This is the contract between Phase 8 (retrieval) and Phase 9 (LLM generation).
    Contains all information needed for source attribution and context.
    """
    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: int = Field(..., description="Parent document ID")
    document_name: str = Field(..., description="Document name for citation")
    department_id: int = Field(..., description="Department ID (for verification)")
    department_name: str = Field(..., description="Department name")
    sensitivity: str = Field(..., description="Document sensitivity level")
    page_start: int = Field(..., ge=1, description="Starting page number")
    page_end: int = Field(..., ge=1, description="Ending page number")
    chunk_index: int = Field(..., ge=0, description="Chunk position in document")
    chunk_text: str = Field(..., description="Chunk content")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    
    model_config = ConfigDict(frozen=True)


class RetrievalResult(BaseModel):
    """
    Complete retrieval result.
    
    Contains:
        - Retrieved chunks matching the query (ACL-filtered)
        - Retrieval metadata
        - User's authorized department (for transparency)
    """
    question: str = Field(..., description="Original user question")
    chunks: List[RetrievalChunk] = Field(
        default_factory=list,
        description="Retrieved chunks (authorized and relevant)"
    )
    retrieved_count: int = Field(..., description="Number of chunks retrieved")
    user_department_id: int = Field(..., description="User's department (server-resolved)")
    user_department_name: str = Field(..., description="User's department name")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What is our leave policy?",
                "chunks": [
                    {
                        "chunk_id": "doc5_chunk2",
                        "document_id": 5,
                        "document_name": "HR Policies 2024",
                        "department_id": 30,
                        "department_name": "hr",
                        "sensitivity": "internal",
                        "page_start": 3,
                        "page_end": 4,
                        "chunk_index": 2,
                        "chunk_text": "Leave Policy: Full-time employees receive 20 days of PTO annually...",
                        "score": 0.87
                    }
                ],
                "retrieved_count": 1,
                "user_department_id": 30,
                "user_department_name": "hr"
            }
        }
    )
