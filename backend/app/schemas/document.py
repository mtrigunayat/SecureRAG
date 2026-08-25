"""
Document schemas

Request/response models for document endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.auth import DepartmentResponse


class DocumentMetadataResponse(BaseModel):
    """
    Document metadata response (safe for authorized users).
    
    This schema returns only safe metadata.
    Document content, embeddings, and vectors are NOT included.
    
    Attributes:
        id: Document ID
        name: Document name
        department: Department (from PostgreSQL relationship)
        sensitivity: Classification level
        source: Original source reference
        indexed_at: When indexed to Qdrant (if applicable)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        
    Security:
        - Only returned to authorized users
        - Does not include actual document content
        - Does not include embeddings or vector data
        - Department verified via authorization service
    """
    id: int
    name: str
    department: DepartmentResponse  # From PostgreSQL relationship
    sensitivity: str
    source: Optional[str] = None
    indexed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "Deployment Guidelines",
                    "department": {
                        "id": 1,
                        "name": "engineering",
                        "description": "Engineering and development team"
                    },
                    "sensitivity": "internal",
                    "source": "/docs/engineering/deployment.md",
                    "indexed_at": "2026-08-25T10:00:00Z",
                    "created_at": "2026-08-20T09:00:00Z",
                    "updated_at": "2026-08-25T10:00:00Z"
                }
            ]
        }
    }
