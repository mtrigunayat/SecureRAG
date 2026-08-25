"""
Chat schemas

Data contracts for Phase 9 RAG generation API.
"""
from typing import List
from pydantic import BaseModel, Field, ConfigDict


class ChatRequest(BaseModel):
    """
    Request for RAG-based chat completion.
    
    Security:
        - Only the question is provided by the client
        - department_id is resolved server-side from authenticated user
        - system_prompt is backend-controlled
        - context is retrieved server-side with ACL filtering
        - Client CANNOT inject arbitrary context
        - Client CANNOT modify system instructions
    """
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User's question to ask the knowledge base"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What is our leave policy?"
            }
        }
    )


class ChatSource(BaseModel):
    """
    Source document citation for answer.
    
    Sources are backend-controlled, NOT LLM-generated.
    This prevents the LLM from inventing source metadata.
    """
    document_id: int = Field(..., description="Source document ID")
    document_name: str = Field(..., description="Document name")
    department_name: str = Field(..., description="Department that owns this document")
    sensitivity: str = Field(..., description="Document sensitivity level")
    page_start: int = Field(..., ge=1, description="Starting page number")
    page_end: int = Field(..., ge=1, description="Ending page number")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    
    model_config = ConfigDict(frozen=True)


class ChatResponse(BaseModel):
    """
    RAG-based chat completion response.
    
    Contains:
        - Generated answer (from LLM)
        - Source citations (from backend, not LLM)
        - Metadata about the response
    
    Security:
        - Answer generated from authorized context only
        - Sources are backend-controlled
        - No system prompt exposed
        - No full context exposed
        - No API keys exposed
    """
    answer: str = Field(..., description="Generated answer from LLM")
    sources: List[ChatSource] = Field(
        default_factory=list,
        description="Source documents used (backend-controlled)"
    )
    retrieved_count: int = Field(..., description="Number of chunks retrieved")
    user_department_name: str = Field(..., description="User's department (for transparency)")
    
    # Optional metadata
    model: str = Field(default="gpt-4.1-mini", description="LLM model used")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "Full-time employees receive 20 days of paid time off (PTO) annually. PTO accrues at a rate of 1.67 days per month. Unused PTO can be carried over up to 5 days into the next year.",
                "sources": [
                    {
                        "document_id": 5,
                        "document_name": "HR Policies 2024",
                        "department_name": "hr",
                        "sensitivity": "internal",
                        "page_start": 12,
                        "page_end": 13,
                        "score": 0.87
                    }
                ],
                "retrieved_count": 1,
                "user_department_name": "hr",
                "model": "gpt-4.1-mini"
            }
        }
    )
