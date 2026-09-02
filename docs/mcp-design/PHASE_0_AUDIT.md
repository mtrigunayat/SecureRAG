# Phase 0: Existing Backend Audit for MCP Integration

**Date**: 2026-09-02  
**Status**: Audit Complete - No Code Changes Made  
**Scope**: Read-only analysis of existing backend architecture, auth, ACL, and RAG flows

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [A. Current Architecture](#a-current-architecture)
3. [B. Authentication Flow](#b-authentication-flow)
4. [C. Authorization Flow](#c-authorization-flow)
5. [D. RAG Flow](#d-rag-flow)
6. [E. MCP Integration Point](#e-mcp-integration-point)
7. [F. Files That Will Likely Need Changes](#f-files-that-will-likely-need-changes)
8. [G. Risks / Concerns](#g-risks--concerns)
9. [H. Phase 0 Conclusion](#h-phase-0-conclusion)

---

## Executive Summary

The Secure RAG Knowledge Assistant already implements a **security-first RAG pipeline** with:

- ✅ JWT authentication with secure token handling
- ✅ Department-based authorization enforced at retrieval-time (not post-retrieval)
- ✅ ACL filtering inside Qdrant vector database
- ✅ Prompt injection defenses via strict message separation
- ✅ Hallucination prevention via empty-retrieval checks
- ✅ Backend-controlled source attribution

**For MCP integration**, we should **expose existing HTTP endpoints via MCP tools**, not duplicate any RAG, auth, or ACL logic.

---

## A. Current Architecture

### System Architecture Diagram

```
Claude or MCP Client
    ↓
Interface Layer (React Frontend today, MCP Server Phase 1)
    ↓
FastAPI API Layer (main.py)
    ↓
Auth Dependency Chain (get_current_user)
    ↓
RAG Orchestration (RAGService)
    ├─ RetrievalService (Qdrant + ACL)
    ├─ PromptBuilder (secure prompt construction)
    ├─ LLMService (Azure OpenAI)
    └─ Backend Source Builder
    ↓
Response with Sources (ChatResponse)
```

### Backend Project Structure

**Entry Point and App Bootstrap:**
- `backend/app/main.py` - FastAPI app, lifespan, router registration

**API Routes (Controllers):**
- `backend/app/api/auth.py` - Login, current user info
- `backend/app/api/chat.py` - RAG chat generation
- `backend/app/api/retrieval.py` - Retrieval-only endpoint
- `backend/app/api/documents.py` - Document metadata (test endpoint)
- `backend/app/api/health.py` - Service health checks

**Service Layer:**
- `backend/app/services/rag_service.py` - RAG orchestration
- `backend/app/services/retrieval_service.py` - Retrieval with ACL
- `backend/app/services/qdrant_service.py` - Qdrant integration
- `backend/app/services/embedding_service.py` - Embedding abstraction
- `backend/app/services/local_embedding_provider.py` - Local embeddings (free)
- `backend/app/services/llm_service.py` - LLM abstraction
- `backend/app/services/providers/azure_openai_provider.py` - Azure OpenAI implementation
- `backend/app/services/prompt_builder.py` - Secure prompt construction
- `backend/app/services/token_service.py` - JWT creation and validation
- `backend/app/services/password_service.py` - Bcrypt password handling
- `backend/app/services/authorization_service.py` - Department-based authorization

**Data Models:**
- `backend/app/models/user.py` - User entity (with department FK)
- `backend/app/models/department.py` - Department entity
- `backend/app/models/document.py` - Document entity

**Schemas (API Contracts):**
- `backend/app/schemas/auth.py` - Login request/response
- `backend/app/schemas/chat.py` - Chat request/response with sources
- `backend/app/schemas/retrieval.py` - Retrieval request/response
- `backend/app/schemas/document.py` - Document metadata

**Database:**
- `backend/app/db/session.py` - SQLAlchemy session management
- `backend/app/db/seed.py` - Database initialization with demo data
- `backend/app/repositories/user_repository.py` - User data access
- `backend/app/repositories/document_repository.py` - Document data access

**Dependencies:**
- `backend/app/dependencies/auth.py` - FastAPI dependency for authentication

**Core Configuration:**
- `backend/app/core/config.py` - Settings management
- `backend/app/core/errors.py` - Custom exception definitions
- `backend/app/core/logging.py` - Logging configuration

**Runtime & Deployment:**
- `docker-compose.yml` - Container orchestration
- `backend/Dockerfile` - Backend container image
- `.env.example` - Environment variables template
- `backend/alembic/` - Database migrations

---

## B. Authentication Flow

### Complete Authentication Flow

```
Login Request (email + password)
    ↓
POST /api/auth/login
    ↓
backend/app/api/auth.py :: login()
    ↓
UserRepository.get_by_email() [PostgreSQL lookup]
    ↓
verify_password() [bcrypt constant-time check]
    ↓
create_access_token(user_id) [JWT creation]
    ↓
JWT Token Response (access_token, token_type: "bearer")
    ↓
Frontend stores in localStorage
    ↓
Subsequent requests include: Authorization: Bearer <token>
    ↓
FastAPI routes with Depends(get_current_user)
    ↓
get_token_from_header() [extract Bearer token]
    ↓
decode_access_token() [JWT validation + expiration check]
    ↓
extract user_id from "sub" claim
    ↓
UserRepository.get_by_id() [reload from PostgreSQL with department relationship]
    ↓
Authenticated User object with department
    ↓
RAG/authorization logic uses this trusted user identity
```

### Authentication Details

**Login Endpoint:**
- **Route**: POST `/api/auth/login`
- **Function**: `login()` in `backend/app/api/auth.py`
- **Input**: `LoginRequest` with email and password
- **Output**: `TokenResponse` with JWT access_token

**User Lookup:**
- **Function**: `UserRepository.get_by_email()`
- **File**: `backend/app/repositories/user_repository.py`
- **Query**: Uses `joinedload(User.department)` to avoid lazy-loading issues
- **Returns**: User with department relationship or None

**Password Verification:**
- **Function**: `verify_password(plain_password, hashed_password)`
- **File**: `backend/app/services/password_service.py`
- **Implementation**: bcrypt.checkpw (constant-time comparison)
- **Security**: Never logs passwords; generic error messages on failure

**JWT Token Generation:**
- **Function**: `create_access_token(user_id)`
- **File**: `backend/app/services/token_service.py`
- **Algorithm**: HS256 (explicit, not negotiable)
- **Payload**:
  - `sub` (subject): User ID as string
  - `iat` (issued at): Timestamp
  - `exp` (expiration): Current time + JWT_EXPIRATION_HOURS (default: 1 hour)
- **Secret**: From `settings.jwt_secret` (required environment variable)

**Get Current User (Token Validation):**
- **Dependency**: `get_current_user()` in `backend/app/dependencies/auth.py`
- **Used in all protected endpoints** via `Depends(get_current_user)`

**Token Extraction:**
- **Function**: `get_token_from_header()`
- **Header Format**: `Authorization: Bearer <token>`
- **Raises**: `AuthenticationError` (401) if missing or malformed

**JWT Validation:**
- **Function**: `decode_access_token(token)`
- **File**: `backend/app/services/token_service.py`
- **Checks**:
  1. Signature verification (HS256 with configured secret)
  2. Expiration check
  3. Required claim validation ("sub" must exist)
  4. Algorithm restriction (prevents algorithm confusion attacks)
- **Raises**: `ExpiredTokenError` (401) or `InvalidTokenError` (401)

**User Identity Resolution:**
- **User ID Extraction**: Convert "sub" claim from string to int
- **Database Reload**: `UserRepository.get_by_id(user_id)`
- **File**: `backend/app/repositories/user_repository.py`
- **Loaded Relationship**: Department via `joinedload(User.department)`
- **Returns**: Authenticated User object (never from JWT payload directly)
- **Raises**: `AuthenticationError` if user no longer exists

**How Authenticated Info Reaches Backend:**
1. Frontend gets token from `/api/auth/login`
2. Frontend stores token in localStorage (key: `auth_token`)
3. Frontend includes token in every API request (Authorization header)
4. Backend FastAPI dependency extracts token → validates JWT → reloads user from DB
5. Department is loaded from PostgreSQL relationship (trusted source, not from JWT)
6. Authenticated `User` object with `department` passed to endpoint handlers

**Frontend Client Implementation:**
- **Auth Context**: `frontend/src/contexts/AuthContext.tsx`
- **API Client**: `frontend/src/services/apiClient.ts`
- **Token Propagation**: `apiClient` automatically includes Bearer token in all requests

---

## C. Authorization Flow

### Department-Based ACL

```
Authenticated User (from JWT + DB)
    ↓
User.department (from PostgreSQL relationship, TRUSTED)
    ↓
Department.id (server-resolved, client CANNOT influence)
    ↓
AuthorizationService.get_department_filter()
    ↓
Qdrant Filter(must=[FieldCondition(department_id == X)])
    ↓
QdrantService.search(query_filter=filter)
    ↓
Authorized Chunks ONLY (department_id matches)
    ↓
Non-ACL Code (no post-filtering in Python)
    ↓
Chunks → LLM (only authorized content)
```

### Authorization Details

**User-Department Relationship:**
- **User Model**: `backend/app/models/user.py`
  - `department_id` (FK to departments.id, NOT NULL)
  - `department` (SQLAlchemy relationship)
- **Department Model**: `backend/app/models/department.py`
  - `id` (PK)
  - `name` (unique, e.g., "engineering", "sales", "hr")
  - `users` (back_populates relationship)

**Department Resolution (Retrieval):**
- **Function**: `RetrievalService._resolve_department(user)`
- **File**: `backend/app/services/retrieval_service.py`
- **Security**: Reads from PostgreSQL relationship, not from client request
- **Returns**: `(department_id, department_name)` tuple
- **Raises**: `AuthorizationError` if user has no department

**ACL Filter Construction:**
- **Function**: `RetrievalService._build_department_filter(department_id)`
- **File**: `backend/app/services/retrieval_service.py`
- **Implementation**:
  ```python
  Filter(
      must=[
          FieldCondition(
              key="department_id",
              match=MatchValue(value=department_id)
          )
      ]
  )
  ```
- **Security**: Client cannot modify or bypass this filter

**Qdrant ACL Enforcement:**
- **Function**: `QdrantService.search()`
- **File**: `backend/app/services/qdrant_service.py`
- **Implementation**: Passes `department_filter` to `client.query_points(query_filter=...)`
- **Location**: Filtering happens **INSIDE Qdrant** during search (not post-retrieval in Python)
- **Critical**: Unauthorized chunks never retrieved from database

**Result Normalization:**
- **Function**: `RetrievalService._normalize_results(raw_results)`
- **File**: `backend/app/services/retrieval_service.py`
- **Does NOT filter by department** (already done by Qdrant)
- **Simply converts** Qdrant response format to `RetrievalChunk` schema

**Non-RAG Document ACL Check:**
- **Endpoint**: GET `/api/documents/{document_id}`
- **Function**: `get_document_metadata()` in `backend/app/api/documents.py`
- **Authorization Check**:
  ```python
  authorization_service.authorize_document_access(current_user, document)
  ```
- **Logic**: `user.department.id == document.department.id` → allow, else 403
- **File**: `backend/app/services/authorization_service.py`

**Authorization Service:**
- **Function**: `AuthorizationService.check_document_access(user, document)`
- **File**: `backend/app/services/authorization_service.py`
- **Returns**: Boolean (has access or not)
- **Function**: `AuthorizationService.authorize_document_access(user, document)`
- **Raises**: `ForbiddenError` (403) if check fails
- **Function**: `AuthorizationService.get_department_filter(user)`
- **Returns**: Dict with `{"department_id": int, "department_name": str}`
- **Future Use**: Can be used to construct Qdrant filters programmatically

**Seed Data (Demo Departments & Users):**
- **Departments** (from `backend/app/db/seed.py`):
  1. engineering
  2. sales
  3. hr
  4. general
- **Users** (demo credentials, POC only):
  - mohit@aithinkers.com / password123 → engineering
  - deepak@aithinkers.com / password123 → engineering
  - karthik@aithinkers.com / password123 → sales
  - swathi@aithinkers.com / password123 → hr

**Security Guarantees:**
1. ✅ User department from PostgreSQL (never from client)
2. ✅ ACL filter applied in Qdrant (not post-retrieval)
3. ✅ Unauthorized chunks never reach LLM
4. ✅ Authorization scope immutable by client request
5. ✅ Generic error messages (no information leakage)

---

## D. RAG Flow

### Complete Secure RAG Pipeline

```
User Question (client provides ONLY question)
    ↓
POST /api/chat
    ↓
Authenticate: Depends(get_current_user)
    ↓
RAGService.generate(question, authenticated_user)
    ├─ RetrievalService.retrieve()
    │   ├─ _validate_question()
    │   ├─ _resolve_department(user)  [TRUSTED: from DB]
    │   ├─ _embed_question()
    │   │   └─ EmbeddingService.embed_text()
    │   │       └─ LocalEmbeddingProvider.embed_text()
    │   │           └─ sentence-transformers/all-MiniLM-L6-v2
    │   ├─ _build_department_filter(dept_id)
    │   ├─ _search_vectors(query_vector, filter)
    │   │   └─ QdrantService.search(query_filter=filter)
    │   │       └─ Qdrant applies ACL INSIDE database
    │   └─ _normalize_results() → RetrievalChunk[]
    │
    ├─ Check if empty retrieval
    │   └─ If empty: return controlled "no info" response (NO LLM CALL)
    │
    ├─ PromptBuilder.build_messages()
    │   ├─ build_system_message() [TRUSTED: backend-controlled]
    │   ├─ build_context_section() [UNTRUSTED: documents marked as data]
    │   └─ build_user_message() [user question clearly separated]
    │
    ├─ LLMService.generate(messages)
    │   └─ AzureOpenAIProvider.generate()
    │       └─ Azure GPT-4.1-mini API call
    │
    └─ RAGService._build_sources(chunks)
        └─ Backend constructs sources from retrieval metadata
            (NOT from LLM output)
    ↓
ChatResponse with answer + sources
```

### RAG Endpoint Details

**Endpoint:**
- **Route**: POST `/api/chat`
- **Function**: `chat()` in `backend/app/api/chat.py`
- **Input**: `ChatRequest` with `question` field only
- **Output**: `ChatResponse` with `answer`, `sources`, metadata

**RAG Orchestration:**
- **Service**: `RAGService` in `backend/app/services/rag_service.py`
- **Entry Point**: `RAGService.generate(question, authenticated_user)`
- **Dependencies**:
  - `RetrievalService` (for retrieval-time ACL)
  - `PromptBuilder` (for secure prompt construction)
  - `LLMService` (for generation)

### Retrieval Service (Phase 8)

**Function**: `RetrievalService.retrieve(question, authenticated_user)`

**Step 1: Question Validation**
- **Function**: `_validate_question(question)`
- **Checks**: Not empty, not > 1000 chars

**Step 2: Department Resolution**
- **Function**: `_resolve_department(user)`
- **Source**: PostgreSQL user.department relationship (TRUSTED)
- **Returns**: `(department_id, department_name)`

**Step 3: Query Embedding**
- **Function**: `_embed_question(question)`
- **Service**: `EmbeddingService.embed_text(question)`
- **Provider**: `LocalEmbeddingProvider` using sentence-transformers
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimension**: 384
- **Cost**: $0 (local CPU inference)
- **Returns**: 384-dimensional embedding vector

**Step 4: ACL Filter Construction**
- **Function**: `_build_department_filter(department_id)`
- **Returns**: Qdrant `Filter` object restricting to user's department

**Step 5: Vector Search with ACL**
- **Function**: `_search_vectors(query_vector, department_filter)`
- **Qdrant Call**: `qdrant_service.search(collection, query_vector, department_filter, top_k, score_threshold)`
- **Qdrant Function**: `client.query_points(query_filter=department_filter, ...)`
- **Key Parameters**:
  - `top_k`: `settings.retrieval_top_k` (default: 5)
  - `score_threshold`: `settings.retrieval_score_threshold` (default: 0.4)
  - **Security**: Filter applied DURING Qdrant search (not post-retrieval)

**Step 6: Relevance Filtering**
- Qdrant returns only chunks with `score >= score_threshold`
- Applied by Qdrant server, not Python code

**Step 7: Result Normalization**
- **Function**: `_normalize_results(raw_results)`
- **Converts**: Qdrant response to `RetrievalChunk` schema
- **Does NOT filter** (Qdrant already filtered by ACL)
- **Returns**: List of `RetrievalChunk` objects with all metadata

**Retrieval Result Schema:**
- **Response Type**: `RetrievalResult`
- **Fields**:
  - `question` (str) - original user question
  - `chunks` (List[RetrievalChunk]) - authorized and relevant chunks
  - `retrieved_count` (int) - number of chunks returned
  - `user_department_id` (int) - for transparency
  - `user_department_name` (str) - for transparency

**Chunk Structure:**
- **Type**: `RetrievalChunk`
- **Fields**:
  - `chunk_id` (str) - deterministic ID
  - `document_id` (int) - parent document
  - `document_name` (str) - for display
  - `department_id` (int) - ACL metadata
  - `department_name` (str) - for display
  - `sensitivity` (str) - classification level
  - `page_start`, `page_end` (int) - for source citation
  - `chunk_index` (int) - position in document
  - `chunk_text` (str) - actual content
  - `score` (float) - similarity score (0.0-1.0)

### LLM Generation (Phase 9)

**Function**: `RAGService.generate(question, authenticated_user)`

**Step 1: Retrieval**
- Calls `RetrievalService.retrieve()` (described above)
- Gets: `RetrievalResult` with authorized chunks

**Step 2: Empty Retrieval Check**
- If `retrieved_count == 0`:
  - Returns controlled response: "I don't have enough information..."
  - **NO LLM CALL** (prevents hallucination)
  - **CRITICAL**: Saves cost and prevents fabrication

**Step 3: Secure Prompt Construction**
- **Service**: `PromptBuilder` in `backend/app/services/prompt_builder.py`
- **Function**: `build_messages(question, chunks)`
- **Returns**: List of `LLMMessage` objects

**System Message (TRUSTED):**
- Backend-controlled instructions
- Never modifiable by documents or client
- Explicit defenses against prompt injection:
  - Instructs model to treat documents as DATA, not instructions
  - Lists examples of malicious text to ignore
  - Requires grounding in provided context
  - Forbids revealing system prompts or making external calls
- **File**: `backend/app/services/prompt_builder.py`
- **Constant**: `PromptBuilder.SYSTEM_PROMPT`

**Context Section (UNTRUSTED):**
- Built from authorized retrieval chunks
- Each chunk clearly marked with `[SOURCE N]` label
- Metadata included: document name, pages, department, sensitivity
- Chunks separated with clear boundaries
- **Function**: `build_context_section(chunks)`

**User Message (CLEAR SEPARATION):**
- Context section followed by separator line `---`
- Then `Question: <user question>`
- **Function**: `build_user_message(question, context)`

**Message List:**
1. System message (backend-controlled instructions)
2. User message (context + question)
- **No assistant message** (single-turn query)

**Step 4: LLM Generation**
- **Service**: `LLMService` in `backend/app/services/llm_service.py`
- **Function**: `generate(messages, temperature, max_tokens)`
- **Provider**: `AzureOpenAIProvider` in `backend/app/services/providers/azure_openai_provider.py`
- **Model**: GPT-4.1-mini via Azure OpenAI
- **Configuration**:
  - `temperature`: 0.0 (deterministic)
  - `max_tokens`: 1000
  - API version: 2024-12-01-preview
- **Returns**: `LLMResponse` with content, model, usage metadata

**Step 5: Source Construction (Backend-Controlled)**
- **Function**: `RAGService._build_sources(chunks)`
- **Implementation**: Deduplicates chunks by document_id
- **Returns**: List of `ChatSource` objects
- **Security**: Sources from retrieval metadata, NOT from LLM text
- **Prevents**: LLM from inventing or modifying source references

**Source Schema:**
- **Type**: `ChatSource`
- **Fields**:
  - `document_id` (int)
  - `document_name` (str)
  - `department_name` (str)
  - `sensitivity` (str)
  - `page_start`, `page_end` (int)
  - `score` (float) - relevance score

**Step 6: Response Assembly**
- **Type**: `ChatResponse`
- **Fields**:
  - `answer` (str) - LLM-generated text
  - `sources` (List[ChatSource]) - backend-constructed citations
  - `retrieved_count` (int) - number of chunks used
  - `user_department_name` (str) - for transparency
  - `model` (str) - "gpt-4.1-mini"

### Configuration & Thresholds

**File**: `backend/app/core/config.py`

Key settings:
- `retrieval_top_k`: 5 (max chunks to retrieve)
- `retrieval_score_threshold`: 0.4 (minimum similarity score, cosine distance)
- `chunk_size`: 600 (characters per chunk)
- `chunk_overlap`: 100 (character overlap between chunks)
- `llm_temperature`: 0.0 (deterministic)
- `llm_max_tokens`: 1000
- `jwt_expiration_hours`: 1

### Qdrant Payload Structure

**Stored in every vector point** (from `VectorIndexingService._create_points`):
```python
{
    "document_id": int,
    "chunk_id": str,
    "document_name": str,
    "department_id": int,        # CRITICAL: used for ACL filtering
    "department_name": str,
    "sensitivity": str,
    "page_start": int,
    "page_end": int,
    "chunk_index": int,
    "chunk_text": str
}
```

**Why this matters for MCP**: The payload is what makes ACL filtering possible at retrieval time. This structure is baked into indexed vectors and must be preserved.

---

## E. MCP Integration Point

### Recommended Integration Architecture

**Best Approach: Thin HTTP Adapter**

The MCP server should expose the existing HTTP endpoints via MCP tools. Do not duplicate RAG logic.

```
Claude (MCP Client)
    ↓
MCP Server (thin adapter)
    ├─ Tool: authenticate(email, password)
    │   └─ calls POST /api/auth/login
    │
    ├─ Tool: ask(question, token)
    │   └─ calls POST /api/chat
    │
    ├─ Tool: retrieve(question, token)
    │   └─ calls POST /api/retrieval
    │
    └─ Tool: whoami(token)
        └─ calls GET /api/auth/me
    ↓
Existing FastAPI Backend (unmodified)
    ├─ Auth endpoints
    ├─ RAG endpoints
    └─ All existing security/ACL logic
    ↓
PostgreSQL + Qdrant (unchanged)
```

### Specific Integration Points

**Authentication:**
- **Endpoint**: POST `/api/auth/login`
- **File**: `backend/app/api/auth.py` function `login()`
- **MCP Tool**: `authenticate(email: str, password: str) -> {access_token: str}`
- **Flow**:
  1. MCP client calls authenticate
  2. MCP server calls POST /api/auth/login with credentials
  3. Backend returns JWT token
  4. MCP server returns token to client
  5. Client stores token for subsequent requests

**Current User Info:**
- **Endpoint**: GET `/api/auth/me`
- **File**: `backend/app/api/auth.py` function `get_current_user_info()`
- **MCP Tool**: `whoami(token: str) -> {id, username, email, department}`
- **Flow**: MCP client provides token, gets authenticated user details

**RAG Chat:**
- **Endpoint**: POST `/api/chat`
- **File**: `backend/app/api/chat.py` function `chat()`
- **MCP Tool**: `ask(question: str, token: str) -> {answer, sources, retrieved_count}`
- **Flow**:
  1. MCP client calls ask with question and token
  2. MCP server calls POST /api/chat with ChatRequest
  3. Backend returns full RAG response
  4. MCP server returns answer + sources to client

**Retrieval-Only (Optional):**
- **Endpoint**: POST `/api/retrieval`
- **File**: `backend/app/api/retrieval.py` function `retrieve_documents()`
- **MCP Tool**: `retrieve(question: str, token: str) -> {chunks, retrieved_count}`
- **Use Case**: Raw retrieval without LLM generation

### Why This Is The Cleanest Integration

✅ **Reuses existing authentication:**
- JWT validation already hardened
- Token dependency already in place

✅ **Reuses existing authorization:**
- ACL filtering in Qdrant
- Department resolution from DB
- No code duplication

✅ **Reuses existing RAG:**
- Embedding generation
- Retrieval with filters
- Prompt construction
- LLM orchestration

✅ **Maintains security boundaries:**
- Client is untrusted (MCP layer)
- Server is trusted (FastAPI backend)
- Department scope immutable

✅ **Maintains auditability:**
- All security decisions logged server-side
- No logic drift between clients

### What NOT To Do

❌ Do not let MCP reconstruct department scope  
❌ Do not let MCP call Qdrant directly  
❌ Do not let MCP call LLM directly  
❌ Do not duplicate prompt construction  
❌ Do not bypass JWT validation  
❌ Do not store credentials in MCP config files  

---

## F. Files That Will Likely Need Changes

### Files That Should Remain Untouched (Security-Critical)

These implement core RAG, auth, and ACL logic. Do not modify unless fixing bugs.

1. **`backend/app/services/retrieval_service.py`**
   - Retrieval orchestration with ACL
   - Department resolution and filter construction
   - Qdrant search integration
   - Do not modify

2. **`backend/app/services/rag_service.py`**
   - RAG pipeline orchestration
   - Empty-retrieval check (prevents hallucination)
   - Source construction (backend-controlled)
   - Do not modify

3. **`backend/app/services/qdrant_service.py`**
   - Qdrant integration
   - ACL filter application during search
   - Do not modify

4. **`backend/app/services/prompt_builder.py`**
   - Secure prompt construction
   - System/data/user message separation
   - Prompt injection defenses
   - Do not modify

5. **`backend/app/dependencies/auth.py`**
   - JWT extraction and validation
   - User identity resolution
   - Do not modify

6. **`backend/app/services/token_service.py`**
   - JWT creation and validation
   - Algorithm enforcement
   - Do not modify

7. **`backend/app/services/providers/azure_openai_provider.py`**
   - LLM provider integration
   - Error sanitization
   - Do not modify

### Files That May Need Modification Later

1. **`backend/app/main.py`**
   - May need MCP-support routes (if any)
   - Keep modifications minimal
   - Example: error handler for MCP-specific exceptions

2. **`backend/app/core/config.py`**
   - May need MCP-specific settings
   - Example: MCP_ENABLED flag, MCP_PORT
   - Keep change scope narrow

3. **`.env.example`**
   - Add MCP configuration variables
   - Example: MCP_HOST, MCP_PORT, MCP_MAX_TOOLS
   - Clarify environment variable naming

4. **`docker-compose.yml`**
   - May add MCP service container
   - Example: mcp-server service if running as separate process
   - Keep backend service unchanged

5. **`README.md`**
   - Add MCP usage documentation
   - Add MCP setup instructions
   - Keep existing documentation intact

### Likely New Files/Directories for MCP

**Recommended structure (Phase 1):**
```
backend/
├── mcp/
│   ├── __init__.py
│   ├── server.py              # MCP server main entry point
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── auth_tools.py      # authenticate, whoami
│   │   └── rag_tools.py       # ask, retrieve
│   ├── client/
│   │   ├── __init__.py
│   │   └── backend_api_client.py  # HTTP client for backend API
│   └── schemas/
│       ├── __init__.py
│       └── tool_contracts.py  # MCP tool definitions
├── app/
│   └── (existing backend code - unchanged)
└── (existing files - unchanged)
```

**Alternative (separate package):**
```
mcp_server/
├── __init__.py
├── server.py
├── tools/
├── client/
└── schemas/

backend/
└── (existing backend code - unchanged)
```

---

## G. Risks / Concerns

### 1. Retrieval Score Threshold Configuration Drift

**Issue**: Runtime configuration and documentation disagree

- **Config file** (`backend/app/core/config.py`):
  - `retrieval_score_threshold: float = 0.4` (default)
  - Comment says "Minimum similarity score (cosine)"

- **Documentation** (`README.md`, `backend/app/api/chat.py`):
  - Repeatedly states "score >= 0.7" as threshold
  - Chat endpoint docs explicitly say "Relevance threshold: score >= 0.7"

- **Tests** (`backend/tests/integration/test_secure_retrieval.py`):
  - Assert `settings.retrieval_score_threshold == 0.7`
  - This would FAIL with current 0.4 default

**Risk**: 
- Behavior mismatch between expected and actual
- Security expectations (fewer false positives at 0.7) vs. reality (more false positives at 0.4)
- MCP clients based on docs will have wrong expectations

**Recommendation**:
- Decide on correct threshold value (0.4 or 0.7)
- Update all three locations consistently
- Add validation test to ensure consistency

### 2. Environment Variable Naming Inconsistency

**Issue**: .env template vs. config code naming

- **`.env.example`**: defines `RELEVANCE_THRESHOLD`
- **`backend/app/core/config.py`**: reads `retrieval_score_threshold` and default 0.4
- No mapping between these two

**Risk**:
- Users setting RELEVANCE_THRESHOLD=0.7 in .env will not see effect
- Silent config failure (setting ignored)
- Operator confusion during deployment

**Recommendation**:
- Rename env var to `RETRIEVAL_SCORE_THRESHOLD` for consistency
- Update .env.example
- Add validation test

### 3. Document Repository Duplicate Method Bug

**Issue**: `DocumentRepository` has duplicate method definitions

- **File**: `backend/app/repositories/document_repository.py`
- **Methods duplicated**: `get_by_id()`, `get_by_department()`, `get_all()`
- **Problem**: Earlier definitions use `joinedload(Document.department)`, later definitions don't
- **Result**: Later definitions override, may cause unexpected lazy-loading

**Risk**:
- Lazy-loading issues when session closed
- Subtle bugs in document authorization checks
- Performance degradation in some code paths

**Recommendation**:
- Remove duplicate definitions (keep joinedload versions)
- Run full test suite
- Verify document authorization endpoints work correctly

### 4. JWT Secret Startup Hardening Gap

**Issue**: Optional jwt_secret with late validation

- **Config** (`backend/app/core/config.py`):
  - `jwt_secret: Optional[str] = None` (optional)
  - No startup validation

- **Token service** (`backend/app/services/token_service.py`):
  - `decode_access_token()` checks `if not settings.jwt_secret` and logs error
  - But `create_access_token()` does not explicitly validate before use

**Risk**:
- Production deployment without JWT_SECRET env var could start successfully
- Failures only occur when first token decoded or created
- User authentication fails mid-request instead of at startup

**Recommendation**:
- Make `jwt_secret` required in config (no Optional, no default)
- Add startup validation in application lifespan
- Fail fast if JWT_SECRET not configured

### 5. Qdrant Collection Readiness Coupling

**Issue**: Qdrant collection created at first index, not at startup

- **App startup** (`backend/app/main.py`):
  - Calls `init_qdrant()` which creates client only
  - Does NOT verify or create collection

- **Indexing** (`backend/app/services/vector_indexing_service.py`):
  - `__init__` calls `_ensure_collection()` which creates/verifies
  - Collection only guaranteed after first document indexed

**Risk**:
- First retrieval before any indexing fails silently
- Health check passes even if Qdrant not ready for queries
- MCP client may fail on first "ask" if no documents indexed yet

**Recommendation**:
- Move `ensure_collection()` to app startup
- Update health check to verify collection exists
- Or explicitly document "must ingest documents before querying"

### 6. MCP Authentication Session Ergonomics

**Issue**: No refresh token flow, 1-hour JWT expiration

- **Token lifetime** (`backend/app/core/config.py`):
  - `jwt_expiration_hours: int = 1`
  - No refresh token endpoint

- **MCP use case**:
  - Long-running conversation may need token refresh
  - Token expires during multi-turn interaction
  - No automatic re-authentication

**Risk**:
- MCP client session fails after 1 hour
- User must re-authenticate mid-conversation
- Poor UX for long-running chatbots

**Decision Needed in Phase 1**:
- Extend token lifetime for MCP use case?
- Add refresh token endpoint?
- Document re-auth flow for MCP clients?

### 7. Ingestion Script / Schema Alignment

**Issue**: Script interface doesn't perfectly align with service schema

- **Ingestion script** (`backend/scripts/ingest_documents.py`):
  - References `ingestion_result.vector_count`
  - Also shows `indexing_result.vector_count`

- **Actual response schemas** (`backend/app/schemas/indexing.py`):
  - `IndexingResult` has field `indexed_count`, not `vector_count`

- **Risk**: Script output references non-existent field (will fail)

**Recommendation**:
- Verify ingestion script runs without errors
- Fix field name references
- Add integration test for end-to-end ingest flow

### 8. Configuration Consistency for Thresholds and Limits

**Issue**: Multiple places define similar thresholds

- Retrieval score threshold (0.4 vs. 0.7 confusion)
- Top-k limit (5 chunks)
- Chunk size (600 chars)
- Chunk overlap (100 chars)
- LLM temperature (0.0)
- LLM max tokens (1000)

**Risk**:
- If centralizing config for MCP, must sync all values
- Docs might reference different values
- Tests might hard-code assumptions

**Recommendation**:
- Audit all threshold/limit values before MCP Phase 1
- Document where each is read from
- Ensure .env.example has all tunable values
- Add config validation test

---

## H. Phase 0 Conclusion

### 1. What We Understand

✅ **Complete authentication pipeline:**
- JWT-based with secure token generation and validation
- User identity resolved from PostgreSQL (trusted source)
- Department membership loaded from database relationship

✅ **Complete authorization architecture:**
- Department-based ACL enforced at retrieval-time (Qdrant)
- Not post-retrieval filtering in Python
- No client influence over authorization scope

✅ **Complete RAG flow:**
- Retrieval → Prompt Construction → LLM → Sources
- Secure prompt separation (system instructions untouched by documents)
- Backend-controlled source attribution

✅ **Existing embedding and vector search:**
- Local embeddings (free, $0 cost)
- Qdrant integration with ACL support
- Payload structure enables department filtering

✅ **Existing LLM integration:**
- Azure OpenAI provider
- Deterministic (temperature 0.0)
- Proper error handling

✅ **Clean API interfaces:**
- `/api/auth/login` and `/api/auth/me` for authentication
- `/api/chat` for RAG generation
- `/api/retrieval` for retrieval-only use cases

### 2. What Can Be Reused

✅ **Everything in the service layer** - no duplication needed:
- `RetrievalService` - retrieval with ACL
- `RAGService` - RAG orchestration
- `PromptBuilder` - secure prompt construction
- `EmbeddingService` - query embeddings
- `LLMService` - generation
- `AuthorizationService` - policy enforcement

✅ **All authentication and JWT logic** - MCP just needs to call endpoints:
- Token creation and validation
- User identity resolution
- Password handling

✅ **All ACL logic** - no changes needed:
- Department resolution
- Qdrant filter construction
- Retrieval-time enforcement

✅ **All existing endpoints** - can be wrapped by MCP tools:
- `/api/auth/login` → authenticate tool
- `/api/auth/me` → whoami tool
- `/api/chat` → ask tool
- `/api/retrieval` → retrieve tool

### 3. What Should NOT Be Duplicated

❌ **Do not replicate RAG orchestration** - call existing service  
❌ **Do not replicate ACL filtering** - use existing Qdrant filters  
❌ **Do not replicate embedding generation** - call existing service  
❌ **Do not replicate prompt construction** - call existing service  
❌ **Do not replicate LLM integration** - call existing service  
❌ **Do not replicate authentication** - use existing JWT logic  

**Single source of truth principle**: Every security-critical decision should live in exactly one place.

### 4. What Needs to Be Decided in Phase 1

**Architecture decisions:**
1. MCP deployment model: separate process vs. in-process module?
2. How should MCP server authenticate to backend?
   - Shared secret?
   - Local socket without auth?
   - Service-to-service JWT?
3. Should MCP support token caching or per-call authentication?

**Configuration decisions:**
1. Clarify and fix threshold configuration drift (0.4 vs. 0.7)
2. Resolve environment variable naming inconsistencies
3. Fix repository duplicate method bugs
4. Add JWT_SECRET startup validation

**Feature decisions:**
1. Support token refresh for long-running sessions?
2. Expose retrieval-only tool or chat-only?
3. Add rate limiting at MCP layer?
4. Streaming responses for long answers?

**Documentation decisions:**
1. How to document MCP vs. HTTP client usage
2. Whether MCP supports same features as HTTP client
3. MCP setup and deployment guide

---

## Summary

**The Secure RAG Knowledge Assistant is ready for MCP exposure.**

The existing backend implements:
- ✅ Strong authentication (JWT + DB)
- ✅ Strong authorization (Qdrant ACL filters)
- ✅ Strong RAG (secure prompts + grounding)
- ✅ Strong defenses (prompt injection, hallucination)

**For MCP Phase 1**, simply:
1. Create thin MCP server that wraps existing HTTP endpoints
2. No RAG/auth/ACL logic duplication
3. Fix the 8 risks identified above
4. Make the 4 architectural decisions
5. Deploy and test

**No core backend changes required during Phase 0-1 audit and MCP adaptation.**

---

**Report Generated**: 2026-09-02  
**Status**: Ready for Phase 1 Planning  
**Next Step**: Address G. Risks and H. Phase 0 Conclusion decisions
