"""
Authentication schemas

Request/response models for authentication endpoints.
"""
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """
    Login request schema.
    
    Attributes:
        email: User's email address
        password: User's password
    """
    email: EmailStr
    password: str = Field(..., min_length=1, description="User password")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "alice@company.com",
                    "password": "password123"
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """
    Token response schema.
    
    Attributes:
        access_token: JWT access token
        token_type: Token type (always "bearer")
    """
    access_token: str
    token_type: str = "bearer"
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer"
                }
            ]
        }
    }


class DepartmentResponse(BaseModel):
    """Department information in user response"""
    id: int
    name: str
    description: str | None = None
    
    model_config = {
        "from_attributes": True  # Pydantic v2 (was orm_mode in v1)
    }


class CurrentUserResponse(BaseModel):
    """
    Current authenticated user response schema.
    
    Attributes:
        id: User ID
        username: Username
        email: Email address
        full_name: Full name
        department: Department (loaded from PostgreSQL relationship)
        
    Security:
        - password_hash is NEVER included
        - department comes from PostgreSQL (trusted source)
    """
    id: int
    username: str
    email: str
    full_name: str
    department: DepartmentResponse  # Loaded from PostgreSQL relationship
    
    model_config = {
        "from_attributes": True,  # Pydantic v2 (was orm_mode in v1)
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "username": "alice",
                    "email": "alice@company.com",
                    "full_name": "Alice Johnson",
                    "department": {
                        "id": 1,
                        "name": "engineering",
                        "description": "Engineering and development team"
                    }
                }
            ]
        }
    }
