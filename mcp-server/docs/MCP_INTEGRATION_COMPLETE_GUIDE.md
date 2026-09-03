# MCP Integration - Complete Guide for SecureRAG

**Document Purpose:** Comprehensive explanation of Model Context Protocol (MCP) integration in SecureRAG, covering architecture, implementation, and deployment.

**Target Audience:** Technical leads, architects, and development teams.

---

## Table of Contents
1. [What is MCP?](#what-is-mcp)
2. [Why Do We Need MCP?](#why-do-we-need-mcp)
3. [How Does MCP Work?](#how-does-mcp-work)
4. [SecureRAG MCP Architecture](#securerag-mcp-architecture)
5. [Authentication Flow](#authentication-flow)
6. [Backend Integration](#backend-integration)
7. [MCP Server Implementation](#mcp-server-implementation)
8. [Deployment & Testing](#deployment--testing)
9. [Key Components & Files](#key-components--files)
10. [Use Cases & Benefits](#use-cases--benefits)

---

## What is MCP?

### Definition
**Model Context Protocol (MCP)** is an open-source standard that enables AI models (like Claude) to securely interact with external tools and data sources through standardized message formats and protocols.

### Core Concept
MCP acts as a **bridge between AI applications and backend services**, allowing:
- AI models to invoke custom tools and functions
- Secure authentication and authorization
- Structured data exchange
- Real-time integration with knowledge bases and APIs

### MCP vs Traditional API Integration

| Aspect | Traditional API | MCP |
|--------|-----------------|-----|
| **Protocol** | HTTP/REST/GraphQL | Standardized JSON-RPC over HTTP |
| **Tools** | Generic endpoints | Defined, discoverable tools |
| **Context** | Stateless requests | Maintains conversation context |
| **Security** | API keys/OAuth | Tokens, service-level auth |
| **Discovery** | Documentation required | Self-discovering tool definitions |

---

## Why Do We Need MCP?

### 1. **Direct Knowledge Base Access for AI**
Without MCP:
- AI models can't access your proprietary knowledge base
- Users must manually copy-paste information
- No real-time data integration

With MCP:
- Claude directly queries your RAG knowledge base
- Automatic document retrieval and summarization
- Real-time, contextual answers

### 2. **Enterprise Security**
- **Data stays in your infrastructure** - Claude doesn't need to see raw documents
- **User-level access control** - MCP enforces department-based ACLs
- **Audit trail** - All queries logged with user identity
- **Token-based authentication** - Not relying on passwords

### 3. **Scalability**
- One MCP server can handle thousands of concurrent Claude conversations
- Backend RAG system remains unchanged
- Stateless, easily deployable architecture

### 4. **Better User Experience**
- Claude answers questions with actual document sources
- No need to switch between tools
- Conversational interface to knowledge base
- Reduced hallucination through real data grounding

### 5. **Extensibility**
- Easy to add new tools (custom queries, document management, etc.)
- Can integrate multiple backends
- Framework-agnostic design

---

## How Does MCP Work?

### MCP Protocol Flow (High Level)

```
Claude (Client)
    ↓
    ├─→ Request: "Initialize" (discover available tools)
    ├─→ Response: [Tool definitions including "ask_knowledge_base"]
    │
    ├─→ Request: "Call tool 'ask_knowledge_base' with question"
    ├─→ MCP Server processes request
    │   ├─ Authenticate user
    │   ├─ Get backend JWT
    │   ├─ Query RAG knowledge base
    │   ├─ Filter results by user's department ACL
    │   └─ Format response with sources
    └─→ Response: "Answer with [SOURCE 1], [SOURCE 2]..."
```

### Message Format (JSON-RPC 2.0)

**Tool Discovery Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

**Tool Discovery Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "ask_knowledge_base",
        "description": "Query the knowledge base for information",
        "inputSchema": {
          "type": "object",
          "properties": {
            "question": {
              "type": "string",
              "description": "The question to ask"
            }
          },
          "required": ["question"]
        }
      }
    ]
  }
}
```

**Tool Call Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "ask_knowledge_base",
    "arguments": {
      "question": "What are the coding standards?"
    }
  }
}
```

**Tool Call Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "The coding standards emphasize... [SOURCES listed]"
      }
    ]
  }
}
```

### Authentication Flow in MCP

```
MCP Request arrives
    ↓
1. Check for Bearer token in Authorization header
    ├─ If valid → Use Bearer token JWT
    └─ If missing/invalid → Try POC authentication
2. POC Authentication (4-step process):
    ├─ Step 1: Login with hardcoded credentials
    │   └─ POST /api/auth/login
    │      Response: JWT access token
    ├─ Step 2: Get user info
    │   └─ GET /api/auth/me
    │      Response: user_id, username, department_name
    ├─ Step 3: Create MCP token
    │   └─ POST /api/internal/mcp/create-token
    │      Request: {user_id, description}
    │      Response: raw MCP token (shown once only)
    └─ Step 4: Validate token and get backend JWT
        └─ POST /api/internal/mcp/validate
           Request: {token}
           Response: user_id, username, department_name, backend_jwt
3. Use backend JWT for subsequent /api/chat requests
    ↓
MCP Tool executes with authenticated context
```

---

## SecureRAG MCP Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Claude (AI Model)                    │
│                    (Anthropic's Claude AI)                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ JSON-RPC over HTTP
                 │ (MCP Protocol)
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                   MCP Server (Python/Starlette)              │
│              https://secure-rag-mcp.onrender.com             │
├─────────────────────────────────────────────────────────────┤
│ Features:                                                     │
│ - Tool: ask_knowledge_base                                   │
│ - Authentication: Hardcoded POC + Bearer token support       │
│ - Async HTTP transport (Streamable)                          │
│ - Error handling & logging                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP REST Calls
                 │ (with JWT Authentication)
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Python/FastAPI)                │
│          https://securerag-backendd.onrender.com             │
├─────────────────────────────────────────────────────────────┤
│ Key Endpoints for MCP:                                       │
│ - POST /api/auth/login                                       │
│ - GET  /api/auth/me                                          │
│ - POST /api/internal/mcp/create-token    ← ADDED             │
│ - POST /api/internal/mcp/validate                            │
│ - POST /api/chat (RAG Query)                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─────────────────┬──────────────────┐
                 ↓                 ↓                  ↓
        ┌──────────────┐  ┌─────────────────┐  ┌──────────┐
        │  PostgreSQL  │  │  Qdrant Cloud   │  │ Document │
        │  (Metadata)  │  │  (Embeddings)   │  │  Store   │
        └──────────────┘  └─────────────────┘  └──────────┘
            Users            Vector DB         Knowledge
           Tokens            Documents          Base
           Access            Retrieval
           Control
```

### Data Flow: Complete End-to-End Query

```
1. Claude User Query
   └─→ "What are the coding standards?"

2. MCP Server receives request
   └─→ Extracts question from JSON-RPC message

3. Authentication (4-step POC flow)
   └─→ Step 1: Login → JWT
   └─→ Step 2: Get user info → user_id, dept
   └─→ Step 3: Create MCP token → raw token
   └─→ Step 4: Validate token → backend JWT

4. Backend Processing
   ├─→ Receive /api/chat request with JWT
   ├─→ Verify JWT signature & expiration
   ├─→ Load user from database
   ├─→ Get user's department ACL
   └─→ Query Qdrant with semantic search

5. RAG Pipeline
   ├─→ Convert question to embedding (same model as docs)
   ├─→ Search Qdrant for top-K similar documents
   ├─→ Filter results by user's department_id
   ├─→ Pass retrieved docs + question to LLM
   ├─→ LLM generates answer grounded in retrieved docs
   └─→ Format response with sources and document attribution

6. Response Back to Claude
   ├─→ Structured answer with document sources
   ├─→ Source metadata (document name, type)
   └─→ User can follow up with more context

7. Claude presents to user
   └─→ "The coding standards emphasize... [SOURCE 1] [SOURCE 2]"
```

---

## Authentication Flow

### POC Authentication (Hardcoded Credentials)

**Why Hardcoded?**
- Simplifies proof-of-concept testing
- Removes OAuth complexity
- Allows immediate deployment
- Later replaceable with proper OAuth

**Credentials:**
```
Email: mohit@aithinkers.com
Password: password123
```

### 4-Step Authentication Process

#### Step 1: Login to Backend
```
POST /api/auth/login
Content-Type: application/json

{
  "email": "mohit@aithinkers.com",
  "password": "password123"
}

Response (200 OK):
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**What happens:**
- Backend validates email/password against database
- Generates short-lived JWT (1 hour expiration)
- Returns access token for subsequent requests

#### Step 2: Get User Information
```
GET /api/auth/me
Authorization: Bearer {access_token}

Response (200 OK):
{
  "id": 1,
  "username": "mohit",
  "email": "mohit@aithinkers.com",
  "full_name": "Mohit Trigunayat",
  "department": {
    "id": 1,
    "name": "engineering",
    "description": "Engineering and development team"
  }
}
```

**What happens:**
- Backend uses JWT to identify user
- Loads full user record from database
- Returns user info including department (crucial for ACL)

#### Step 3: Create MCP Token
```
POST /api/internal/mcp/create-token
Content-Type: application/json
X-Internal-Service: mcp-server

{
  "user_id": 1,
  "description": "Claude MCP POC: mohit"
}

Response (201 Created):
{
  "token": "mcp_rlpEZxmWoOZ6QfYlw_0CXjFCHOENsOZth7KQ_MRVJ-I",
  "token_id": 1,
  "user_id": 1,
  "description": "Claude MCP POC: mohit",
  "created_at": "2026-09-03T17:43:05.123519"
}
```

**What happens:**
- Backend creates long-lived MCP token (1 year expiration)
- Stores token_hash (never stores raw token)
- Returns raw token (shown only once - critical!)
- MCP server saves this token for future validation

**Token Security:**
- Raw token shown only in response
- Token_hash stored in database
- Same user can have multiple tokens
- Tokens can be revoked (soft delete)

#### Step 4: Validate Token
```
POST /api/internal/mcp/validate
Content-Type: application/json

{
  "token": "mcp_rlpEZxmWoOZ6QfYlw_0CXjFCHOENsOZth7KQ_MRVJ-I"
}

Response (200 OK):
{
  "user_id": 1,
  "username": "mohit",
  "department_name": "engineering",
  "backend_jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

**What happens:**
- Backend hashes incoming token and searches database
- Validates token not expired/revoked
- Loads authenticated user from database
- Creates new short-lived backend JWT (1 hour)
- Returns user context + JWT for subsequent requests

### Token Lifecycle

```
MCP Token (Long-lived, 1 year):
├─ Created: POST /api/internal/mcp/create-token
├─ Stored: token_hash in mcp_tokens table
├─ Used: Validation step
├─ Validation: POST /api/internal/mcp/validate
└─ Revocation: Soft delete (revoked_at timestamp)

Backend JWT (Short-lived, 1 hour):
├─ Created: During MCP token validation
├─ Used: For /api/chat requests
├─ Expiration: 3600 seconds from creation
└─ Renewal: Get new JWT from /api/internal/mcp/validate
```

---

## Backend Integration

### What Was Added to Backend

#### 1. New Endpoint: POST /api/internal/mcp/create-token

**Location:** `backend/app/api/mcp_internal.py`

**Purpose:** Create long-lived MCP tokens for service-to-service communication

**Request Schema:**
```python
class MCPCreateTokenRequest(BaseModel):
    user_id: int
    description: str
```

**Response Schema:**
```python
class MCPCreateTokenResponse(BaseModel):
    token: str  # Raw token (shown only once!)
    token_id: int
    user_id: int
    description: str
    created_at: str  # ISO timestamp
```

**Implementation Details:**
```python
@router.post("/create-token", response_model=MCPCreateTokenResponse, status_code=201)
def mcp_create_token(
    request: MCPCreateTokenRequest,
    db: Session = Depends(get_db)
) -> MCPCreateTokenResponse:
    # 1. Verify user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise AuthenticationError("User not found")
    
    # 2. Create MCP token (returns raw token)
    raw_token = create_mcp_token_for_user(
        user_id=request.user_id,
        description=request.description,
        created_via="mcp_server",
        db=db
    )
    
    # 3. Fetch token record for metadata
    token_hash = hash_mcp_token(raw_token)
    mcp_token_record = db.query(MCPToken).filter(
        MCPToken.token_hash == token_hash
    ).first()
    
    # 4. Return token (raw shown only once)
    return MCPCreateTokenResponse(
        token=raw_token,
        token_id=mcp_token_record.id,
        user_id=mcp_token_record.user_id,
        description=mcp_token_record.description or "",
        created_at=mcp_token_record.created_at.isoformat()
    )
```

**Security Features:**
- User existence validation
- Token uniqueness (hash-based)
- Long expiration (configurable, default 1 year)
- Can be revoked via separate endpoint
- Audit trail (created_via, created_by_user_id)

#### 2. Database Table: mcp_tokens

**Location:** `backend/app/models/mcp_token.py`

**Schema:**
```sql
CREATE TABLE mcp_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    revoked_at TIMESTAMP,
    description VARCHAR(255),
    created_by_user_id INTEGER REFERENCES users(id),
    created_via VARCHAR(50)
);

-- Indexes for performance
CREATE UNIQUE INDEX ix_mcp_tokens_token_hash ON mcp_tokens(token_hash);
CREATE INDEX ix_mcp_tokens_revoked_at ON mcp_tokens(revoked_at);
CREATE INDEX ix_mcp_tokens_expires_at ON mcp_tokens(expires_at);
CREATE INDEX ix_mcp_tokens_user_id ON mcp_tokens(user_id);
```

**Fields Explained:**
- `token_hash`: Hashed token (never store raw)
- `expires_at`: When token becomes invalid
- `last_used_at`: Track token usage patterns
- `revoked_at`: Soft-delete for token revocation
- `created_via`: Audit trail (e.g., "mcp_server")

#### 3. Token Service Functions

**Location:** `backend/app/services/mcp_token_service.py`

**Key Functions:**
```python
# Generate token string
def generate_mcp_token_string() -> str:
    """Generate cryptographically random token"""
    random_bytes = secrets.token_urlsafe(32)  # 256-bit entropy
    return f"mcp_{random_bytes}"
    # Example: mcp_rlpEZxmWoOZ6QfYlw_0CXjFCHOENsOZth7KQ_MRVJ-I

# Hash token for database storage
def hash_mcp_token(raw_token: str) -> str:
    """Hash token using SHA-256"""
    return hashlib.sha256(raw_token.encode()).hexdigest()

# Create token for user
def create_mcp_token_for_user(
    user_id: int,
    description: str,
    created_via: str,
    db: Session
) -> str:
    """Create and return raw token (shown only once)"""
    # Token validity: configurable days (default 365)
    expires_at = datetime.utcnow() + timedelta(days=365)
    raw_token = generate_mcp_token_string()
    token_hash = hash_mcp_token(raw_token)
    
    mcp_token_record = MCPToken(
        user_id=user_id,
        token_hash=token_hash,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        description=description,
        created_via=created_via
    )
    
    db.add(mcp_token_record)
    db.commit()
    return raw_token  # ← Only place raw token is exposed

# Validate token
def validate_mcp_token(raw_token: str, db: Session) -> User:
    """Validate token and return authenticated user"""
    # Compute hash
    token_hash = hash_mcp_token(raw_token)
    
    # Find token record
    mcp_token_record = db.query(MCPToken).filter(
        MCPToken.token_hash == token_hash
    ).first()
    
    # Checks:
    # 1. Token exists
    if not mcp_token_record:
        raise AuthenticationError("Invalid token")
    
    # 2. Token not revoked
    if mcp_token_record.revoked_at is not None:
        raise AuthenticationError("Token revoked")
    
    # 3. Token not expired
    if mcp_token_record.expires_at <= datetime.utcnow():
        raise AuthenticationError("Token expired")
    
    # Load user from database
    user = db.query(User).filter(
        User.id == mcp_token_record.user_id
    ).first()
    
    # Update last_used_at
    mcp_token_record.last_used_at = datetime.utcnow()
    db.commit()
    
    return user
```

#### 4. API Router Registration

**Location:** `backend/app/main.py`

**Code:**
```python
from app.api.mcp_internal import router as mcp_internal_router

# Register MCP internal routes
app.include_router(mcp_internal_router)

# This exposes:
# - POST /api/internal/mcp/create-token
# - POST /api/internal/mcp/validate
```

### Existing Endpoints Used by MCP

#### /api/auth/login
- **Purpose:** Initial authentication with email/password
- **Used in:** POC Step 1
- **Returns:** JWT access token

#### /api/auth/me
- **Purpose:** Get authenticated user info
- **Used in:** POC Step 2
- **Returns:** User details including department

#### /api/chat
- **Purpose:** RAG query endpoint
- **Used in:** Tool execution
- **Input:** JWT + question
- **Returns:** Answer + sources with ACL filtering

#### /api/retrieval
- **Purpose:** Raw document retrieval
- **Used in:** Knowledge base access (with ACL)
- **Returns:** Filtered documents per user department

---

## MCP Server Implementation

### Architecture

**Location:** `mcp-server/` (separate Python repository)

**Structure:**
```
mcp-server/
├── src/mcp_server/
│   ├── main.py                 # Starlette app entry point
│   ├── transport.py            # MCP HTTP transport layer
│   ├── auth/
│   │   ├── __init__.py        # Auth service (POC flow)
│   │   └── token_service.py   # Token validation
│   ├── tools/
│   │   └── ask_tool.py        # ask_knowledge_base tool
│   ├── client/
│   │   └── backend_api_client.py  # Backend HTTP calls
│   └── core/
│       ├── config.py           # Environment configuration
│       ├── errors.py           # Exception classes
│       └── logging.py          # Logging setup
├── .env                         # Configuration (production)
├── Dockerfile                   # Docker image
└── requirements.txt             # Dependencies
```

### Key Files

#### 1. main.py - Starlette Application

**Purpose:** Setup HTTP server and MCP endpoints

**Endpoints:**
```python
# Health check (used by Render)
GET /health
Response: {"status": "healthy", "service": "MCP Server", "version": "0.2.0"}

# MCP JSON-RPC endpoint (all requests here)
POST /mcp
Content-Type: application/json
Body: JSON-RPC 2.0 messages

# Examples:
# - Request: {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
# - Request: {"jsonrpc": "2.0", "id": 2, "method": "tools/call", ...}
```

**Code Snippet:**
```python
from starlette.applications import Starlette
from starlette.routing import Route

# Health endpoint
async def health_endpoint(request):
    return JSONResponse({
        "status": "healthy",
        "service": "MCP Server",
        "version": "0.2.0"
    })

# MCP endpoint (handles all JSON-RPC)
async def mcp_endpoint_handler(request):
    # Uses official MCP transport layer
    return await handle_mcp_request(request)

routes = [
    Route('/health', health_endpoint, methods=['GET']),
    Route('/mcp', mcp_endpoint_handler, methods=['POST']),
]

app = Starlette(routes=routes)
```

#### 2. auth/__init__.py - Authentication Service

**Purpose:** Implements 4-step POC authentication and token validation

**Main Function: get_poc_auth_context()**

```python
async def get_poc_auth_context() -> AuthenticatedContext:
    """
    POC: Get authenticated context using hardcoded credentials
    
    Flow:
    1. Login with hardcoded email/password → JWT
    2. Get user info from /api/auth/me → user_id, dept
    3. Create MCP token via /api/internal/mcp/create-token → raw token
    4. Validate token via /api/internal/mcp/validate → backend JWT
    
    Returns:
        AuthenticatedContext with user_id, username, department_name, backend_jwt
    """
    
    # Hardcoded POC credentials
    poc_email = "mohit@aithinkers.com"
    poc_password = "password123"
    
    async with httpx.AsyncClient(timeout=settings.backend_timeout) as client:
        
        # STEP 1: Login
        login_response = await client.post(
            f"{settings.backend_url}/api/auth/login",
            json={"email": poc_email, "password": poc_password}
        )
        access_token = login_response.json()["access_token"]
        
        # STEP 2: Get user info
        me_response = await client.get(
            f"{settings.backend_url}/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = me_response.json()
        user_id = user_data["id"]
        username = user_data["username"]
        
        # STEP 3: Create MCP token
        token_response = await client.post(
            f"{settings.backend_url}/api/internal/mcp/create-token",
            json={
                "user_id": user_id,
                "description": f"Claude MCP POC: {username}"
            },
            headers={"X-Internal-Service": "mcp-server"}
        )
        mcp_token = token_response.json()["token"]
        
        # STEP 4: Validate token and get backend JWT
        auth_context = await validate_mcp_token(mcp_token)
        return auth_context
```

**AuthenticatedContext Class:**
```python
class AuthenticatedContext:
    """Holds authenticated user information"""
    
    def __init__(self, token_response: MCPTokenResponse):
        self.user_id = token_response.user_id
        self.username = token_response.username
        self.department_name = token_response.department_name
        self.backend_jwt = token_response.backend_jwt
```

#### 3. transport.py - MCP Transport Layer

**Purpose:** Handle JSON-RPC routing and authentication

**Authentication Chain:**
```python
async def mcp_endpoint(request):
    """
    Handles all MCP JSON-RPC requests
    
    Authentication chain:
    1. Try Bearer token from Authorization header
    2. Fall back to POC authentication
    3. Fall back to demo context (error)
    """
    
    try:
        # Try Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer "
            auth_context = await validate_mcp_token(token)
            # ✓ Use Bearer token
        else:
            # Fall back to POC authentication
            auth_context = await get_poc_auth_context()
            # ✓ Use POC hardcoded credentials
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        auth_context = demo_context  # ✗ Demo context (fails in prod)
    
    # Process MCP request with authenticated context
    return await official_mcp_transport.handle(request, auth_context)
```

#### 4. tools/ask_tool.py - Knowledge Base Tool

**Purpose:** Implement `ask_knowledge_base` MCP tool

**Tool Definition:**
```python
ask_knowledge_base_tool = {
    "name": "ask_knowledge_base",
    "description": "Query the SecureRAG knowledge base for information",
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask the knowledge base"
            }
        },
        "required": ["question"]
    }
}
```

**Implementation:**
```python
async def ask_knowledge_base_impl(
    question: str,
    auth_context: AuthenticatedContext
) -> str:
    """
    Execute knowledge base query with user authentication
    
    Flow:
    1. Use auth_context.backend_jwt to authenticate
    2. POST /api/chat with question
    3. Backend returns answer + sources
    4. Filter by user's department_name ACL
    5. Format response with attribution
    """
    
    async with httpx.AsyncClient() as client:
        # Call backend with authenticated JWT
        response = await client.post(
            f"{settings.backend_url}/api/chat",
            json={"question": question},
            headers={"Authorization": f"Bearer {auth_context.backend_jwt}"}
        )
        
        if response.status_code == 401:
            raise AuthenticationError("Backend authentication failed")
        
        if response.status_code != 200:
            raise BackendError(f"Backend error: {response.text}")
        
        # Parse response
        chat_response = ChatResponse(**response.json())
        
        # Format answer with sources
        formatted_answer = format_response(chat_response)
        
        return formatted_answer
```

**Response Format:**
```
The coding standards emphasize writing code for readability and 
maintainability first, with performance as a secondary concern...

**Sources:**
1. **Coding Standards** [internal]

_Retrieved 1 document(s)_
```

#### 5. client/backend_api_client.py - Backend HTTP Client

**Purpose:** Handle HTTP communication with FastAPI backend

**Key Class:**
```python
class BackendAPIClient:
    """Async HTTP client for backend communication"""
    
    async def ask_knowledge_base(
        self,
        question: str,
        jwt_token: str
    ) -> ChatResponse:
        """Query knowledge base with authenticated JWT"""
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.backend_url}/api/chat",
                json={"question": question},
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            # Error handling
            if response.status_code == 401:
                logger.error("JWT validation failed")
                raise AuthenticationError("Invalid JWT")
            
            if response.status_code == 403:
                logger.error("User not authorized for this department")
                raise AuthorizationError("Access denied")
            
            if response.status_code >= 500:
                raise BackendError("Server error")
            
            # Parse response
            return ChatResponse(**response.json())
```

#### 6. core/config.py - Configuration Management

**Purpose:** Load environment variables

**Environment Variables:**
```python
class Settings(BaseSettings):
    # Backend configuration
    backend_url: str = "https://securerag-backendd.onrender.com"
    backend_timeout: int = 30  # seconds
    
    # MCP Server configuration
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 5001
    
    # Security
    internal_service_key: str = "mcp-server"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

**.env File (Production):**
```env
BACKEND_URL=https://securerag-backendd.onrender.com
MCP_HOST=0.0.0.0
MCP_PORT=5001
BACKEND_API_TIMEOUT=30
LOG_LEVEL=INFO
```

### Key Dependencies

```
# MCP Protocol
anthropic==0.28.0  # Official MCP SDK

# HTTP Requests
httpx==0.27.0  # Async HTTP client

# Web Server
starlette==0.37.2  # Lightweight async framework
uvicorn==0.28.0    # ASGI server

# Data Validation
pydantic==2.6.0    # Request/response validation

# Configuration
python-dotenv==1.0.0  # .env file loading

# Logging
python-json-logger==2.0.7  # JSON log format
```

---

## Deployment & Testing

### Deployment Architecture

```
GitHub Repository
    ↓
    ├─→ backend/ code changes
    │   └─→ Render webhook
    │       └─→ Pull latest code
    │       └─→ Build Docker image
    │       └─→ Deploy to https://securerag-backendd.onrender.com
    │
    └─→ mcp-server/ code changes
        └─→ Render webhook
            └─→ Pull latest code
            └─→ Build Docker image
            └─→ Deploy to https://secure-rag-mcp.onrender.com
```

### Deployment Steps

#### 1. Backend Deployment (New Endpoints)

```bash
# 1. Commit changes
git add backend/app/api/mcp_internal.py
git commit -m "Add /api/internal/mcp/create-token endpoint"

# 2. Push to GitHub
git push origin main

# 3. Render automatically:
#    - Detects changes
#    - Builds Docker image
#    - Runs migrations
#    - Restarts service
#    - Endpoints available immediately
```

#### 2. MCP Server Deployment

```bash
# 1. Update MCP server code (if needed)
git add mcp-server/
git commit -m "Update MCP server configuration"

# 2. Push to GitHub
git push origin main

# 3. Render automatically redeploys MCP server
```

### Testing & Verification

#### Test 1: Backend Token Creation Endpoint

```bash
# Create MCP token
curl -X POST https://securerag-backendd.onrender.com/api/internal/mcp/create-token \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service: mcp-server" \
  -d '{
    "user_id": 1,
    "description": "Claude MCP POC: mohit"
  }'

# Response:
{
  "token": "mcp_rlpEZxmWoOZ6QfYlw_0CXjFCHOENsOZth7KQ_MRVJ-I",
  "token_id": 1,
  "user_id": 1,
  "description": "Claude MCP POC: mohit",
  "created_at": "2026-09-03T17:43:05.123519"
}
```

#### Test 2: Token Validation

```bash
curl -X POST https://securerag-backendd.onrender.com/api/internal/mcp/validate \
  -H "Content-Type: application/json" \
  -d '{
    "token": "mcp_rlpEZxmWoOZ6QfYlw_0CXjFCHOENsOZth7KQ_MRVJ-I"
  }'

# Response:
{
  "user_id": 1,
  "username": "mohit",
  "department_name": "engineering",
  "backend_jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

#### Test 3: MCP Server Health

```bash
curl https://secure-rag-mcp.onrender.com/health

# Response:
{
  "status": "healthy",
  "service": "MCP Server",
  "version": "0.2.0"
}
```

#### Test 4: MCP Tool Execution

```bash
curl -X POST https://secure-rag-mcp.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "ask_knowledge_base",
      "arguments": {
        "question": "What are the coding standards?"
      }
    }
  }'

# Response:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "The coding standards emphasize... [SOURCES]"
      }
    ]
  }
}
```

#### Test 5: Claude Integration

```
In Claude or Claude App:
1. Access MCP servers
2. Add MCP server: https://secure-rag-mcp.onrender.com
3. Ask question: "What are the coding standards?"
4. Claude calls ask_knowledge_base tool
5. MCP server authenticates and queries backend
6. Claude receives answer with sources
7. Claude presents formatted response to user
```

---

## Key Components & Files

### Backend Files Added/Modified

| File | Purpose | Change |
|------|---------|--------|
| `backend/app/api/mcp_internal.py` | MCP token endpoints | **ADDED** |
| `backend/app/models/mcp_token.py` | Token data model | Existing, unchanged |
| `backend/app/services/mcp_token_service.py` | Token operations | Existing, unchanged |
| `backend/app/main.py` | Router registration | Register mcp_internal router |

### MCP Server Files

| File | Purpose |
|------|---------|
| `mcp-server/src/mcp_server/main.py` | HTTP server setup |
| `mcp-server/src/mcp_server/transport.py` | MCP message handling |
| `mcp-server/src/mcp_server/auth/__init__.py` | 4-step authentication |
| `mcp-server/src/mcp_server/tools/ask_tool.py` | Knowledge base tool |
| `mcp-server/src/mcp_server/client/backend_api_client.py` | Backend HTTP client |
| `mcp-server/src/mcp_server/core/config.py` | Configuration |
| `mcp-server/.env` | Production config |

### Database Tables

| Table | Purpose | Status |
|-------|---------|--------|
| `mcp_tokens` | Stores MCP token hashes | Existing |
| `users` | User authentication | Existing |
| `documents` | Knowledge base | Existing |

---

## Use Cases & Benefits

### Primary Use Case: Claude Integration

**Before MCP:**
```
User: "What are the coding standards?"
↓
User copies/pastes from docs to Claude
↓
Claude answers based on provided text
↓
No citation or source tracking
```

**After MCP:**
```
User: "What are the coding standards?"
↓
Claude calls ask_knowledge_base tool via MCP
↓
MCP server queries SecureRAG backend
↓
Backend performs semantic search in Qdrant
↓
Backend applies user's department ACL
↓
Answer returned with document sources
↓
Claude presents formatted response with citations
```

### Secondary Use Cases

1. **Multi-User Knowledge Base Access**
   - Each user has MCP token bound to their user_id
   - Department-level ACL enforced
   - Audit trail of all queries

2. **Integration with Other AI Systems**
   - Any system can create an MCP token
   - Call /api/internal/mcp/validate to get backend JWT
   - Use JWT to query /api/chat

3. **Real-Time Knowledge Updates**
   - Document changes immediately reflected in MCP
   - No caching layer between Claude and knowledge base
   - Always up-to-date answers

### Business Benefits

| Benefit | Impact |
|---------|--------|
| **Reduced Hallucination** | Claude answers grounded in real documents |
| **Better UX** | Conversational interface to knowledge base |
| **Security** | User-level ACL enforcement, audit trail |
| **Scalability** | Stateless MCP server, horizontal scaling |
| **Extensibility** | Easy to add new tools and integrations |
| **Compliance** | Data stays in infrastructure, not sent to Claude |

---

## Architecture Decisions & Rationale

### 1. Why Hardcoded Credentials for POC?

**Decision:** Use hardcoded email/password instead of OAuth

**Rationale:**
- Simplifies proof-of-concept testing
- Eliminates OAuth setup complexity
- Enables immediate deployment
- Can be replaced with proper OAuth later
- Sufficient for internal testing

**Trade-offs:**
- ✗ Not production-ready
- ✓ Quick to implement
- ✓ Easy to iterate

### 2. Why Long-Lived MCP Tokens?

**Decision:** MCP tokens valid for 1 year

**Rationale:**
- MCP is meant for service-to-service communication
- Tokens can be revoked if compromised
- Reduces re-authentication overhead
- Server-to-server trust model

**Alternative:** Short-lived (1 hour)
- Would require constant re-authentication
- More complex token refresh logic
- Better security but worse performance

### 3. Why Separate Token Types?

**MCP Token (1 year):**
- For MCP server to prove identity
- Created once, stored securely by MCP server

**Backend JWT (1 hour):**
- For individual API requests
- Created fresh during validation
- Short expiration limits damage if leaked

**Rationale:** Defense in depth - even if MCP token leaked, backend JWT can't be used for long.

### 4. Why HTTP Transport vs Native Protocol?

**Decision:** Use Streamable HTTP transport over native socket

**Rationale:**
- Works through corporate firewalls
- Can be deployed on serverless (Render)
- No special port requirements
- Same security as HTTPS

**Trade-off:** Slightly higher latency, but acceptable for user-facing queries

---

## Security Considerations

### Token Security

```
Raw Token (shown once):
└─→ User copies to secure location
    └─→ Only stored in MCP server config
    └─→ Never logged or displayed again

Token Hash (stored in DB):
└─→ SHA-256 hash
└─→ Cannot reverse to get raw token
└─→ Each request hashes incoming token and compares
```

### JWT Security

```
JWT Contents:
├─ sub (subject): user_id = 1
├─ iat (issued at): timestamp
└─ exp (expiration): timestamp + 1 hour

Verification:
├─ Backend checks signature (HMAC-SHA256)
├─ Backend checks expiration
├─ Backend validates against user in database
└─ Rejects if any check fails
```

### ACL Enforcement

```
For each query:
1. Extract user_id from JWT
2. Load user from database
3. Get user's department_id
4. Query Qdrant only for documents accessible to department
5. Filter results before returning to MCP
```

---

## Future Enhancements

### Short-Term (Next Sprint)

1. **Replace Hardcoded Credentials**
   - Implement proper OAuth flow
   - Use Anthropic API for Claude authentication
   - Store credentials securely (not in code)

2. **Add Token Management UI**
   - Create/revoke tokens from dashboard
   - View token usage statistics
   - Expire tokens manually

3. **Enhanced Logging**
   - Log all MCP queries with user/department
   - Build analytics dashboard
   - Track token usage patterns

### Medium-Term (Next Quarter)

1. **Additional Tools**
   - `search_documents` - Find specific documents
   - `get_document` - Retrieve full document
   - `upload_document` - Add new documents
   - `create_note` - Users can create notes

2. **Multi-Backend Support**
   - Support multiple knowledge bases
   - Route queries to appropriate backend
   - Federated search across backends

3. **Performance Optimization**
   - Cache frequently asked questions
   - Optimize embedding search
   - Add query result caching

### Long-Term (6+ Months)

1. **Full OAuth Integration**
   - Connect to existing identity provider
   - Support multiple SSO providers
   - Implement token expiration workflows

2. **Advanced ACL**
   - Document-level access control
   - Time-based access (expires after date)
   - Role-based permissions

3. **AI-Powered Features**
   - Auto-generate document summaries
   - Suggest relevant documents
   - Detect and highlight outdated information

---

## Troubleshooting Guide

### Issue: "Backend error - Backend authentication failed"

**Cause:** MCP token creation failed

**Solutions:**
1. Check backend URL in .env: `BACKEND_URL=https://securerag-backendd.onrender.com`
2. Verify backend is running: `curl https://securerag-backendd.onrender.com/api/health`
3. Check hardcoded credentials still work: `curl -X POST https://securerag-backendd.onrender.com/api/auth/login ...`

### Issue: "404 Not Found" on /api/internal/mcp/create-token

**Cause:** Backend hasn't been redeployed after adding endpoint

**Solution:** 
1. Push changes to GitHub
2. Wait for Render redeployment (2-5 minutes)
3. Verify endpoint: `curl -X POST https://securerag-backendd.onrender.com/api/internal/mcp/create-token ...`

### Issue: "Token validation failed: Token expired"

**Cause:** MCP token older than 1 year

**Solution:**
1. Create new token: Call `/api/internal/mcp/create-token` again
2. Update MCP server configuration with new token
3. Restart MCP server

### Issue: "User has no department"

**Cause:** User record missing department relationship

**Solution:**
1. Check user exists in database
2. Verify user.department_id is set
3. Ensure department exists in departments table

---

## Conclusion

MCP (Model Context Protocol) transforms how AI models interact with knowledge bases by providing:

1. **Standardized Interface** - Consistent tool definitions and protocols
2. **Secure Authentication** - Token-based, user-scoped access control
3. **Real-Time Integration** - No caching, always current information
4. **Scalable Architecture** - Stateless servers, horizontal scaling
5. **Better User Experience** - Conversational AI with actual data

The SecureRAG implementation demonstrates a production-ready MCP integration that:
- Authenticates users securely
- Enforces department-level ACL
- Performs semantic search on knowledge base
- Returns answers with document attribution
- Maintains audit trail for compliance

This enables Claude (and other AI models) to become knowledgeable about your organization's internal documentation, policies, and procedures - dramatically improving accuracy and usefulness while maintaining security and compliance.

---

## References

- **MCP Specification:** https://modelcontextprotocol.io
- **Anthropic Claude:** https://claude.ai
- **FastAPI Documentation:** https://fastapi.tiangolo.com
- **Qdrant Vector Database:** https://qdrant.tech
- **Starlette Framework:** https://www.starlette.io

---

**Document Version:** 1.0  
**Last Updated:** September 3, 2026  
**Author:** SecureRAG Development Team  
**Status:** Production Ready
