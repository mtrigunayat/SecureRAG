# Phase 1: MCP Architecture & Tool Design

**Date**: 2026-09-02  
**Status**: Design Phase Only — NO Code Changes / Implementation  
**Purpose**: Define architecture, authentication, token model, and MCP tooling for remote MCP server integration

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Step 1: Backend Review Summary](#step-1-backend-review-summary)
3. [Step 2: Target Architecture](#step-2-target-architecture)
4. [Step 3: MCP Authentication → Backend Identity Problem](#step-3-mcp-authentication--backend-identity-problem)
5. [Step 4: MCP Token Model](#step-4-mcp-token-model)
6. [Step 5: MCP Tools Design](#step-5-mcp-tools-design)
7. [Step 6: Tool Behavior for Claude](#step-6-tool-behavior-for-claude)
8. [Step 7: Request/Response Contract](#step-7-requestresponse-contract)
9. [Step 8: Error Handling](#step-8-error-handling)
10. [Step 9: Repository Structure](#step-9-repository-structure)
11. [Step 10: Deployment Architecture](#step-10-deployment-architecture)
12. [Step 11: Security Threat Model](#step-11-security-threat-model)
13. [Step 12: What Changes vs What Stays](#step-12-what-changes-vs-what-stays)
14. [Step 13: Final Recommendation](#step-13-final-recommendation)

---

## Executive Summary

**Objective**: Add MCP (Model Context Protocol) remote server support to Secure RAG Knowledge Assistant, allowing Claude to access the internal knowledge base directly.

**Key Principles**:
- ✅ MCP is an **adapter layer only** — not a replacement
- ✅ Existing FastAPI backend remains authoritative for auth, authz, RAG
- ✅ MCP is a **separate service** deployable independently
- ✅ Per-user MCP tokens (not shared credentials)
- ✅ Department ACL enforced by backend (not MCP)
- ✅ No direct Qdrant/LLM access from MCP

**Architecture at a Glance**:
```
Claude (Remote MCP Client)
    ↓ HTTPS + MCP Protocol
MCP Server (mcp-server/)
    ↓ Internal HTTP (Backend API calls)
FastAPI Backend (existing)
    ↓ Existing authorization + RAG
Qdrant + PostgreSQL + Azure OpenAI
```

**Authentication Flow**:
- Claude presents per-user MCP token to MCP server
- MCP server validates token and identifies user (separate from backend JWT)
- MCP server obtains backend JWT for that user
- MCP server calls backend endpoints with that JWT
- Backend validates JWT, loads user from PostgreSQL, applies department ACL
- Response returns to MCP, which returns to Claude

**This document is design-only. Implementation follows after approval.**

---

## Step 1: Backend Review Summary

### Backend Current State ✅ Verified

I've reviewed the actual backend code against Phase 0 audit. Key verifications:

#### Authentication (`backend/app/api/auth.py`)
- ✅ `POST /api/auth/login` accepts email/password
- ✅ Returns `TokenResponse` with `access_token` and `token_type: "bearer"`
- ✅ Token is JWT, created by `token_service.create_access_token(user_id)`
- ✅ JWT payload: `{"sub": str(user_id), "iat": now, "exp": expire}`
- ✅ Expiration: configurable, default 1 hour (`jwt_expiration_hours`)
- ✅ Algorithm: HS256 (hardcoded), secret from `JWT_SECRET` env var

#### User Resolution (`backend/app/dependencies/auth.py`)
- ✅ `get_current_user(token, db)` dependency
- ✅ Decodes JWT, extracts `sub` (user_id)
- ✅ **Loads user from PostgreSQL** (trusted source) — does NOT use JWT payload for identity
- ✅ Joins `User.department` relationship
- ✅ Raises `AuthenticationError` if user not found or token invalid
- ✅ User object passed to all endpoints

#### Department & Authorization (`backend/app/models/user.py`, `authorization_service.py`)
- ✅ User model has `department_id` FK
- ✅ Department relationship loaded via `joinedload`
- ✅ `AuthorizationService` creates `AuthorizationScope` from authenticated user
- ✅ Scope contains `user_id`, `department_id`, `department_name` (all from database)
- ✅ Policy: `user.department.id == document.department.id` for access

#### Retrieval with ACL (`backend/app/services/retrieval_service.py`)
- ✅ `retrieve(question, authenticated_user)` method
- ✅ Resolves user department from authenticated_user (from PostgreSQL)
- ✅ Builds Qdrant filter: `Filter(must=[FieldCondition(key="department_id", match=MatchValue(value=user.department.id))])`
- ✅ Executes: `qdrant_service.search(query_filter=department_filter, top_k=5, score_threshold=0.4)`
- ✅ Returns `RetrievalResult` with chunks + metadata

#### RAG Pipeline (`backend/app/services/rag_service.py`, `prompt_builder.py`)
- ✅ `RAGService.generate(question, authenticated_user)` orchestrates full RAG
- ✅ Calls `retrieval_service.retrieve()` first (returns authorized chunks)
- ✅ Builds secure prompt via `PromptBuilder`
- ✅ System message backend-controlled (in `SYSTEM_PROMPT` constant)
- ✅ Calls `LLMService.generate()` with prompt
- ✅ Sources constructed server-side from chunk metadata (not from LLM text)
- ✅ Returns `ChatResponse` with answer + `sources: list[ChatSource]`

#### Configuration (`backend/app/core/config.py`)
- ✅ All settings loaded from environment via `pydantic-settings`
- ✅ Key settings:
  - `jwt_secret` (required, from `JWT_SECRET` env)
  - `jwt_expiration_hours` (default: 1)
  - `retrieval_score_threshold` (default: 0.4)
  - `retrieval_top_k` (default: 5)
- ⚠️ **NOTED**: Threshold inconsistency (config says 0.4, tests expect 0.7)

#### Public API Endpoints (Relevant to MCP)
```
POST /api/auth/login
  Request:  {email, password}
  Response: {access_token, token_type}

GET /api/auth/me
  Header:   Authorization: Bearer <jwt>
  Response: {id, username, email, full_name, department}

POST /api/chat
  Header:   Authorization: Bearer <jwt>
  Request:  {question}
  Response: {answer, sources[], retrieved_count, user_department_name}

POST /api/retrieval
  Header:   Authorization: Bearer <jwt>
  Request:  {question}
  Response: {chunks[], retrieved_count, user_department_id, user_department_name}
```

**Critical Security Invariants Verified**:
1. ✅ User identity comes from JWT decoding → PostgreSQL lookup (not from JWT payload)
2. ✅ Department comes from database relationship (not from client)
3. ✅ ACL filter applied inside Qdrant (not post-retrieval)
4. ✅ Source metadata backend-controlled (not LLM-generated)
5. ✅ System prompt backend-controlled

**Verification Conclusion**: Phase 0 audit is accurate. Backend is secure and well-designed for MCP adapter integration.

---

## Step 2: Target Architecture

### System Diagram

```
┌────────────────────────────────────────────────────────────┐
│                     Internet / Anthropic                   │
│                                                            │
│                  Claude / MCP Client                       │
└────────────┬───────────────────────────────────────────────┘
             │
             │ HTTPS + MCP Protocol
             │ (remote MCP transport)
             ▼
┌────────────────────────────────────────────────────────────┐
│                  MCP Server                                │
│              (mcp-server/ directory)                       │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ MCP Endpoint                                         │ │
│  │ - Tool handlers: ask_knowledge_base()               │ │
│  │ - Receives MCP token from Claude                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                        │                                   │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │ MCP Token Service                                   │ │
│  │ - Validate MCP token                                │ │
│  │ - Look up user identity                             │ │
│  │ - Obtain backend JWT for user                       │ │
│  └──────────────────────────────────────────────────────┘ │
│                        │                                   │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │ Backend API Client                                  │ │
│  │ - Call /api/chat, /api/retrieval                    │ │
│  │ - Inject backend JWT in Authorization header       │ │
│  └──────────────────────────────────────────────────────┘ │
│                        │                                   │
└────────────────────────┼───────────────────────────────────┘
                         │
                         │ HTTP (internal network)
                         │ Backend JWT in Authorization header
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│               FastAPI Backend (existing)                   │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ /api/chat                                            │ │
│  │ /api/retrieval                                       │ │
│  │ /api/auth/me (optional, for user verification)     │ │
│  └──────────────────────────────────────────────────────┘ │
│                        │                                   │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │ get_current_user() Dependency                       │ │
│  │ - Validates backend JWT                             │ │
│  │ - Loads User from PostgreSQL                        │ │
│  │ - Loads Department relationship                     │ │
│  └──────────────────────────────────────────────────────┘ │
│                        │                                   │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │ Authorization Service                               │ │
│  │ RetrievalService with ACL Filtering                │ │
│  │ RAGService Orchestration                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                        │                                   │
│  ┌────────┬────────────▼────────────┬────────────┐       │
│  ▼        ▼                         ▼            ▼       │
│ PostgreSQL Qdrant         Azure OpenAI       RAG Engine  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Authentication / Authorization / ACL Enforcement Flow

```
Claude asks: "What's our password policy?"
    │
    │ MCP token: "mcp_token_XYZ..."
    ▼
MCP Server receives request
    │ Validate token: "mcp_token_XYZ" → User: Mohit (Engineering)
    │
    ├─ MCP Token Service looks up token in storage
    ├─ Maps to user_id=1 (Mohit) + department_id=2 (Engineering)
    │
    │ Obtain backend JWT for Mohit
    │
    ├─ Call internal endpoint to get JWT for user_id=1
    │ (or pre-generate when MCP token is created)
    │ (or short-lived token stored)
    │
    │ JWT: "eyJ0eXAiOiJKV1QiLC...", sub="1"
    │
    │ Call backend: POST /api/chat
    │   Header: Authorization: Bearer eyJ0eXA...
    │   Body: {question: "What's our password policy?"}
    │
    ▼
FastAPI Backend /api/chat endpoint
    │
    ├─ get_current_user() dependency
    │   ├─ Validates JWT signature
    │   ├─ Checks expiration
    │   ├─ Extracts sub="1" (user_id)
    │   └─ Loads User from PostgreSQL
    │       └─ user.id=1, user.email="mohit@...", user.department_id=2
    │       └─ Loads User.department relationship
    │       └─ department.id=2, department.name="Engineering"
    │
    ├─ Confirms: User is Mohit, Department is Engineering
    │
    ├─ RetrievalService.retrieve(question="...", user=Mohit)
    │   ├─ Builds Qdrant filter:
    │   │   Filter(must=[FieldCondition(key="department_id", match=MatchValue(value=2))])
    │   │
    │   ├─ Executes Qdrant search with filter
    │   │   → Only chunks with department_id=2 returned
    │   │   → HR documents (dept=3) filtered out server-side
    │   │
    │   ├─ Applies relevance threshold
    │   └─ Returns RetrievalResult with authorized chunks
    │
    ├─ PromptBuilder constructs secure prompt
    │
    ├─ LLMService generates answer from authorized context
    │
    ├─ Builds sources from chunk metadata (backend-controlled)
    │
    └─ Returns ChatResponse
        {
          "answer": "Our password policy is...",
          "sources": [
            {document_name, page, department},
            ...
          ],
          "retrieved_count": 3,
          "user_department_name": "Engineering"
        }
    │
    ▼
MCP Server receives response
    │
    ├─ Extracts answer, sources, metadata
    ├─ Formats for Claude
    │
    └─ Returns to Claude via MCP
        {
          "answer": "Our password policy is...",
          "sources": [
            {document_name, page, department},
            ...
          ]
        }
    │
    ▼
Claude receives answer
    │
    └─ Responds to user with answer + sources
```

### Key Architecture Points

| Component | Responsibility | Security Boundary |
|-----------|-----------------|-------------------|
| **Claude** | Sends question via MCP protocol | Untrusted (malicious client) |
| **MCP Server** | Token validation, backend API adapter | Validates tokens, injects JWTs |
| **MCP Token** | Per-user authentication to MCP server | Different from backend JWT |
| **Backend JWT** | Per-user authentication to backend | Generated by backend /api/auth/login |
| **Backend** | Validates JWT, loads user, applies ACL | Authoritative for auth, authz, RAG |
| **PostgreSQL** | User identity and department source | Trusted source of truth |
| **Qdrant** | Vector search with server-side filtering | ACL filter applied at query time |

---

## Step 3: MCP Authentication → Backend Identity Problem

### The Challenge

Current frontend flow:
```
User Email + Password
    ↓
POST /api/auth/login
    ↓
JWT Token
    ↓
Store in localStorage
    ↓
Include in Authorization header for all requests
    ↓
Backend validates JWT, loads User + Department
    ↓
Secure RAG execution
```

New MCP flow challenge:
```
Claude presents "MCP token"
    ↓
MCP Server receives it
    ↓
???? How does MCP server communicate identity to backend?
```

### Attack Scenario to Prevent

```
Malicious MCP Client connects to MCP server
  ↓
Claims: "I am user_id=3 (Karthik, Sales)"
  ↓
Claims: "department_id=4 (HR)"
  ↓
Requests: ask_knowledge_base("What's the HR budget?")
  ↓
Without proper security:
  → MCP server might pass user_id/department directly
  → Backend receives untrusted parameter
  → Authorization check bypassed
  → HR documents leaked to Sales user
```

### Candidate Approaches

#### Option A: MCP Token → User → Backend JWT

**Architecture**:
```
MCP Token (opaque, per-user)
    ↓
MCP Token Service validates and maps token → user_id
    ↓
MCP server obtains backend JWT for that user
    ↓
Backend JWT injected in HTTP requests to backend
    ↓
Backend validates JWT (existing flow)
    ↓
Backend loads User + Department from PostgreSQL
    ↓
Secure RAG
```

**How it works**:
1. At setup time: Admin creates MCP token for user (e.g., "mcp_token_abc123_Mohit")
2. MCP token stored securely (hashed in database or secure cache)
3. MCP token → User mapping stored (encrypted at rest, secure access)
4. When Claude connects:
   - Claude provides MCP token (e.g., via MCP authentication mechanism)
   - MCP server validates token against database
   - Token maps to user_id=1 (Mohit)
   - MCP server calls backend: `POST /api/auth/token-to-jwt` or similar
   - Backend returns short-lived JWT for user_id=1
   - MCP server caches JWT (while valid) or regenerates per request
   - MCP server calls `POST /api/chat` with JWT
   - Backend validates JWT, loads user+department (existing)

**Security Analysis**:
- ✅ User identity cryptographically bound to MCP token
- ✅ MCP token cannot be forged (hashed/encrypted at rest)
- ✅ Backend JWT prevents MCP tampering (signature validated)
- ✅ Department always loaded from PostgreSQL (not from MCP token)
- ✅ Attack scenario blocked: Even if malicious client claims "department_id=4", backend loads actual user's department from database
- ✅ Backward compatible: No changes to existing backend endpoints
- ✅ Auditability: Can log MCP token usage

**Implementation Complexity**: Moderate
- Add MCP token table to database
- Add MCP token → user mapping
- Add backend endpoint to convert MCP token to JWT (or pre-generate)
- Add token validation service in MCP server
- Add caching for JWTs (optional, for performance)

**Coupling**: Loose
- MCP server depends on backend token endpoint only
- No changes to chat, retrieval, auth logic
- Backend unchanged except for optional token endpoint

**Scalability**: Good
- Stateless MCP servers (token lookup in database)
- Multiple MCP instances can coexist
- No shared state issues

**Auditability**: Excellent
- Log every MCP token usage
- Log which backend JWT was issued for which MCP token
- Trace MCP requests through to backend via JWT

**Impact on Existing Backend**: Minimal
- Optionally add `/api/auth/mcp-token-to-jwt` endpoint
- Or: MCP server calls existing `/api/auth/login` internally (if MCP tokens map to backend credentials)
- Or: Pre-generate backend JWTs when MCP tokens created (separate backend process)

**Fit for POC**: ✅ Excellent
- Simple to implement
- Leverages existing JWT validation
- Clear security model

**Fit for Production**: ✅ Yes
- Standardized approach (OAuth-like)
- Can support token rotation
- Audit trail clear

---

#### Option B: Service-to-Service Internal Authentication

**Architecture**:
```
MCP Token (opaque, per-user)
    ↓
MCP Token Service validates and maps token → user_id
    ↓
MCP server includes user_id in authenticated request header
    ↓
Backend validates request via shared secret or certificate
    ↓
Backend trusts MCP server to have validated identity
    ↓
Backend loads user + department
```

**How it works**:
1. MCP server and backend share a secret (e.g., `MCP_SERVER_SECRET`)
2. MCP server validates MCP token locally, extracts user_id
3. MCP server creates signed request header:
   - `X-MCP-User-ID: 1`
   - `X-MCP-Signature: HMAC(user_id, server_secret, timestamp)`
4. MCP server calls backend with signed header
5. Backend validates signature (must be from trusted MCP server)
6. Backend loads User for user_id=1 from PostgreSQL
7. Backend trusts that MCP server validated the MCP token

**Security Analysis**:
- ✅ User identity cryptographically signed by MCP server
- ✅ Backend trusts MCP server (shared secret)
- ✅ Department loaded from PostgreSQL (not from header)
- ✅ Attack scenario blocked (same as Option A)
- ⚠️ **Risk**: If MCP server is compromised, malicious actor can forge requests as any user
- ⚠️ **Risk**: Shared secret between services (operational complexity)

**Implementation Complexity**: Moderate to High
- Add shared secret infrastructure
- Add signature generation/validation in both services
- Add backend logic to trust MCP-signed requests
- Harder to debug (signature validation failures unclear)

**Coupling**: Tighter
- MCP server tightly coupled to backend via shared secret
- Changes to backend validation logic require coordination

**Scalability**: Reasonable
- Shared secret must be distributed to all MCP instances
- Rotation requires coordinated update

**Auditability**: Good
- Can log which MCP server made request
- Can trace back to MCP token

**Impact on Existing Backend**: Moderate
- Add new endpoint or modify existing to accept MCP-signed requests
- Add validation logic in dependency

**Fit for POC**: ⚠️ Acceptable but more complex than Option A
- Requires shared secret management
- Adds signature validation overhead

**Fit for Production**: ⚠️ Workable but requires careful secret rotation
- Good if MCP server is internal/trusted
- Risk if MCP server is compromised

---

#### Option C: MCP as In-Process Module (Not Separate Service)

**Architecture**:
```
Claude
    ↓
MCP Server (runs inside backend)
    ↓
Shared memory / direct function calls
    ↓
RAGService, RetrievalService, etc.
```

**How it works**:
1. MCP server runs as Python module within FastAPI app
2. No HTTP calls, direct function invocation
3. MCP token validated, maps to user_id
4. Call RAGService directly: `rag_service.generate(question, user_id)`
5. User loaded from database, RAG executed
6. Response returned

**Security Analysis**:
- ✅ No network exposure between MCP and backend
- ✅ Same security model as frontend (get_current_user dependency)
- ✅ Simplest implementation
- ❌ **Blocker**: Violates requirement that "MCP must be independently deployable from backend"
- ❌ **Blocker**: Cannot host MCP separately from backend

**Implementation Complexity**: Lowest
- Add MCP handlers as FastAPI routes
- Reuse existing RAG services
- No token mapping layer needed

**Coupling**: Tightest
- MCP is part of backend codebase
- Cannot scale MCP independently

**Scalability**: Limited
- MCP and backend scale together
- Cannot overscale MCP without overscaling backend

**Auditability**: Good (same as backend)

**Impact on Existing Backend**: Significant
- Changes to app architecture
- Additional dependencies in FastAPI app

**Fit for POC**: ✅ Could work for POC, but violates constraints

**Fit for Production**: ❌ Does not meet "independently deployable" requirement

---

#### Option D: MCP Server with Backend Credential Storage

**Architecture**:
```
MCP Token (maps to backend email/password or API key)
    ↓
MCP Token Service looks up credentials
    ↓
MCP server calls POST /api/auth/login with credentials
    ↓
Backend returns JWT
    ↓
MCP server uses JWT for subsequent calls
```

**How it works**:
1. Admin creates MCP token and associates it with backend email/password OR API key
2. When Claude connects, MCP server receives token
3. MCP server looks up stored credentials in database
4. MCP server calls `/api/auth/login` (or token endpoint) with those credentials
5. Backend validates and returns JWT
6. MCP server uses JWT for API calls

**Security Analysis**:
- ✅ Reuses existing backend auth flow
- ❌ **Risk**: Storing user passwords in MCP database (even if hashed)
- ❌ **Risk**: Compromised MCP database exposes passwords
- ⚠️ Credentials at rest in MCP (not ideal)

**Implementation Complexity**: Low to Moderate
- Simple lookup and credential injection
- Reuses existing login flow

**Coupling**: Loose to existing flow, but tight to credentials

**Scalability**: Good

**Auditability**: Good (can trace back to MCP token → credentials)

**Fit for POC**: ✅ Acceptable
- Simple to implement
- Reuses existing mechanisms

**Fit for Production**: ⚠️ Conditional
- If credentials are single-use tokens/API keys (not passwords), acceptable
- If passwords stored, not recommended

---

### Recommendation: **Option A** (MCP Token → User → Backend JWT)

**Chosen Architecture**:
```
MCP Token (opaque, per-user, hashed at rest)
    ↓ MCP Token Service validates
User Identity (user_id, mapped in secure database)
    ↓ Obtain backend JWT (via new endpoint or pre-generated)
Backend JWT (short-lived, signature-validated)
    ↓ Backend validates JWT
User + Department (loaded from PostgreSQL)
    ↓ Backend applies ACL
Secure RAG
```

**Rationale**:
1. **Security**: User identity cryptographically bound to MCP token (hash), cannot be forged
2. **Prevention of Attack**: Even malicious MCP client claiming "department_id=4" is blocked because:
   - MCP token validates to specific user_id
   - Backend JWT includes that user_id
   - Backend loads actual user from database
   - Backend gets actual department from database
   - No client input can override department
3. **Backward Compatible**: No changes to existing backend endpoints (except optional token endpoint)
4. **Auditability**: Clear chain: MCP token → user → JWT → backend request → logs
5. **Scalability**: Stateless design (token lookup in database)
6. **Implementation Complexity**: Moderate (acceptable for POC)
7. **Production Ready**: Yes, same pattern as OAuth

**Implementation Overview** (not detailed code, architecture only):

1. **New Database Table**: `mcp_tokens`
   ```
   id, token_hash, user_id, created_at, expires_at, last_used_at, revoked_at
   ```

2. **MCP Server Components**:
   - MCP Token Validator Service
   - Backend JWT Obtainer (cache or on-demand)
   - Backend API HTTP Client (with JWT injection)

3. **Backend Changes** (optional new endpoint):
   - `POST /internal/auth/mcp-token-to-jwt` (internal only, requires shared secret OR direct service-to-service)
   - Input: `{mcp_token: "..."}` signed with MCP server secret
   - Output: `{access_token, expires_in}`
   - OR: Pre-generate JWTs when MCP tokens created (separate backend process)

4. **No Changes to**:
   - Existing auth flow
   - Existing chat/retrieval endpoints
   - Existing JWT structure
   - Existing authorization logic

---

## Step 4: MCP Token Model

### Objectives

1. Bind user identity to MCP token securely
2. Support expiration and revocation
3. Allow audit trail
4. Be production-ready (vs just POC)
5. Keep implementation reasonable for POC

### Token Format

**Design**: Opaque token (not self-describing like JWT)

**Why opaque**:
- ✅ Requires database lookup to validate (forces security check)
- ✅ Cannot be forged without database access
- ✅ Token rotations easier (database change only)
- ✅ Audit trail built-in (who used what token when)
- ✅ Revocation immediate (database record)

**Token Structure**:
```
mcp_user_<random_base64>_<timestamp>

Example: mcp_user_xK9vL2mQ8pR5sTu_1725226800

Where:
  - "mcp_user_" = prefix (identifies token type, version)
  - "xK9vL2mQ8pR5sTu" = 64 random bits (128 bits / 2) in base64
  - "1725226800" = creation timestamp (Unix, for human readability)
```

**Length**: ~50-60 characters (reasonable for Claude context)

**Randomness**: 
- Use `secrets.token_urlsafe(12)` (96 bits from Python's `secrets` module)
- Cryptographically secure (suitable for authentication tokens)
- URL-safe (can be pasted into CLI, logs, etc.)

### Secure Randomness

```python
import secrets
token_bytes = secrets.token_bytes(16)  # 128 bits
token_b64 = base64.urlsafe_b64encode(token_bytes).decode().rstrip('=')
# Result: ~22 character base64 string

# Format: "mcp_user_" + token_b64 + "_" + timestamp
mcp_token = f"mcp_user_{token_b64}_{int(time.time())}"
```

### Token Storage (Database)

**Table**: `mcp_tokens`

```sql
CREATE TABLE mcp_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,  -- SHA256(token)
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,  -- Expiration time
    last_used_at TIMESTAMP,
    revoked_at TIMESTAMP,  -- NULL = active, set = revoked
    description VARCHAR(255),  -- "Claude MCP", "Mobile App", etc.
    
    -- For audit
    created_by_user_id INTEGER REFERENCES users(id),
    created_via TEXT,  -- "admin_portal", "api", etc.
    
    INDEX (user_id),
    INDEX (token_hash),
    INDEX (expires_at),
    INDEX (revoked_at)
);
```

**Why hash at rest**:
- ✅ If database is compromised, raw tokens are not exposed
- ✅ Hash is one-way (cannot reverse to get token)
- ✅ New token must be presented by MCP server to validate

**Hashing Algorithm**: SHA256
- Suitable for tokens
- Fast, standard

### Token Generation

**Process** (Admin/User-initiated, out of band from MCP):

1. Admin or user initiates MCP token creation (via admin portal, API, or CLI)
2. Backend generates:
   ```python
   token = f"mcp_user_{secrets.token_urlsafe(12)}_{int(time.time())}"
   token_hash = hashlib.sha256(token.encode()).hexdigest()
   ```
3. Backend stores in database:
   ```python
   mcp_token_record = MCP_Token(
       user_id=user_id,
       token_hash=token_hash,
       expires_at=now + timedelta(days=365),  # 1 year by default
       created_by_user_id=admin_id,
       description="Claude MCP Access"
   )
   db.add(mcp_token_record)
   db.commit()
   ```
4. Backend returns raw token to user (ONE TIME):
   ```json
   {
     "mcp_token": "mcp_user_xK9vL2mQ8pR5sTu_1725226800",
     "expires_at": "2027-09-02T12:00:00Z",
     "note": "Save this token securely. You won't see it again."
   }
   ```
5. User securely stores token (e.g., Anthropic platform, password manager)

**One-Time Display**:
- ✅ Token returned only during creation
- ✅ Subsequent views show only token_hash or masked preview
- ✅ Prevents accidental exposure via logs

### Token → User Mapping

**MCP Server Validation Flow**:

1. Claude connects to MCP server with MCP token
2. MCP server receives token: `mcp_user_xK9vL2mQ8pR5sTu_1725226800`
3. MCP server hashes it: `SHA256(token) = "abc123..."`
4. MCP server queries database:
   ```sql
   SELECT user_id FROM mcp_tokens 
   WHERE token_hash = 'abc123...'
   AND revoked_at IS NULL
   AND expires_at > NOW()
   LIMIT 1
   ```
5. If found:
   - Valid token for user_id=X
   - MCP server proceeds (obtain backend JWT for user_id=X)
6. If not found:
   - Token invalid, revoked, or expired
   - Return MCP error: "Invalid or expired token"

### Expiration

**Default**: 1 year (or configurable)

**Rationale**:
- Longer than backend JWT (1 hour)
- Allows long-lived MCP setup for Claude
- Still allows regular rotation (security best practice)

**Behavior**:
```
Expiration Time Reached
    ↓
MCP server validation query fails (expires_at > NOW() fails)
    ↓
Token rejected
    ↓
MCP error to Claude: "Token expired, please refresh"
    ↓
User generates new MCP token
    ↓
Anthropic platform updated with new token
```

### Revocation

**Process**:

1. User wants to revoke token (lost device, compromise, rotation)
2. User initiates revocation via admin portal / API
3. Backend updates database:
   ```sql
   UPDATE mcp_tokens 
   SET revoked_at = NOW() 
   WHERE token_hash = 'abc123...'
   ```
4. Immediately effective:
   - Next MCP server validation query includes `AND revoked_at IS NULL`
   - Query fails
   - MCP connection rejected

**Audit Trail**:
```
mcp_tokens table:
  revoked_at = timestamp of revocation
  (can log who revoked and why if needed)
```

### Rotation

**Process** (planned rotation):

1. User generates new MCP token (same user)
2. User updates Anthropic platform with new token
3. User revokes old token
4. Old token stops working, new one works

**Advantage**:
- Zero downtime (new token active before old one revoked)
- Clear audit trail (old and new tokens both tracked)
- Can list all tokens per user (for audit)

### Auditing

**What to log**:

In MCP server logs:
```
2026-09-02 14:23:45 INFO MCP token validation: user_id=1, token_created=2026-09-02, last_used=2026-09-02T14:00:00
2026-09-02 14:23:46 INFO Backend API call: user_id=1, endpoint=/api/chat, question="..."
2026-09-02 14:23:50 INFO Backend response: answer_length=150 chars, sources=3
```

In backend logs (existing):
```
2026-09-02 14:23:46 INFO /api/chat called by user_id=1 (department_id=2)
2026-09-02 14:23:48 INFO Retrieval: user_id=1, chunks=5, department_filter=2
2026-09-02 14:23:49 INFO LLM call: model=gpt-4.1-mini, tokens_used=150
```

**Tracing**:
- Can correlate MCP logs + backend logs via user_id
- Can see which MCP tokens used which resources
- Can audit compliance (who accessed what documents when)

### Invalid Token Handling

**Scenarios**:

1. **Token not found in database**:
   ```
   MCP Error: "Authentication failed: Invalid token"
   HTTP Status: 401 (Unauthorized)
   Log: "MCP token validation failed: not found"
   ```

2. **Token expired**:
   ```
   MCP Error: "Authentication failed: Token expired"
   HTTP Status: 401
   Log: "MCP token validation failed: expired at 2027-09-02"
   ```

3. **Token revoked**:
   ```
   MCP Error: "Authentication failed: Token revoked"
   HTTP Status: 401
   Log: "MCP token validation failed: revoked"
   ```

4. **User deleted**:
   ```
   MCP Error: "Authentication failed: User not found"
   HTTP Status: 401
   Log: "MCP token validation failed: user not found"
   ```

5. **Malformed token**:
   ```
   MCP Error: "Authentication failed: Invalid token format"
   HTTP Status: 400 (Bad Request)
   Log: "MCP token validation failed: malformed token"
   ```

### Expired Token Handling

**Process**:

1. MCP server attempts validation
2. Database query: `expires_at > NOW()` fails
3. MCP server returns error
4. Claude receives error
5. Conversation stops
6. User must generate new token

**Better UX** (optional):
- MCP server could return specific error: "Your MCP token expired on 2027-09-02. Please generate a new one."
- Provides actionable feedback

### Revoked Token Handling

Similar to expired:
1. Query includes `AND revoked_at IS NULL`
2. If revoked, query fails
3. MCP error returned
4. Claude informed
5. User action needed

### Comparison: Backend JWT vs MCP Token

| Aspect | Backend JWT | MCP Token |
|--------|------------|-----------|
| **Format** | Self-signed, contains claims | Opaque, no claims |
| **Validation** | Verify signature | Database lookup |
| **Lifespan** | 1 hour (short-lived) | 1 year (long-lived) |
| **Generation** | Via login endpoint | Via admin/user portal |
| **Storage** | Client (localStorage) | Secure (env var, Anthropic platform) |
| **Revocation** | Not supported (wait for expiration) | Immediate via database |
| **Use Case** | Frontend <→ Backend | Claude <→ MCP Server |
| **Compromise Impact** | 1 hour window | Requires database OR token compromise |

### MCP Token Lifecycle

```
1. Token Creation
   Admin/User initiates creation
   ↓
   Backend generates token (random)
   ↓
   Backend stores hash in database
   ↓
   Backend returns raw token (one-time)
   
2. Token Active
   User stores token securely (Anthropic platform)
   ↓
   Claude uses token to connect to MCP
   ↓
   MCP server validates token per request
   ↓
   Token usable until expiration or revocation

3. Token Expiration
   Time reaches expires_at
   ↓
   MCP server query fails (expires_at > NOW() = false)
   ↓
   Token rejected

4. Token Revocation
   User revokes (via portal/API)
   ↓
   revoked_at set in database
   ↓
   MCP server query fails (revoked_at IS NULL = false)
   ↓
   Token immediately inactive

5. Token Rotation
   User creates new token
   ↓
   User updates Claude config
   ↓
   User revokes old token
   ↓
   Seamless transition
```

---

## Step 5: MCP Tools Design

### Business Requirement (Recap)

> If a user asks Claude something related to the company's internal knowledge base, Claude should be able to call the MCP server and obtain the answer from our existing Secure RAG backend instead of relying on Claude's own knowledge.

### Tool Selection Philosophy

**Principle**: Expose high-level business functions, not implementation details.

**Why NOT expose all endpoints**:
- ❌ `list_accessible_documents` - Leaks internal API structure
- ❌ `search_documents_by_department` - Lets Claude influence department filtering
- ❌ `get_raw_chunk` - Exposes low-level retrieval
- ✅ `ask_knowledge_base` - High-level, Claude doesn't need to know implementation

### Recommended Tool Set

#### Primary Tool: `ask_knowledge_base`

**Purpose**: Answer questions using the company's internal knowledge base.

**When Claude should use it**:
- User asks about internal company knowledge (policies, procedures, documentation)
- User asks about engineering practices, architecture, infrastructure
- User asks about HR benefits, policies, compensation guidelines
- User asks about sales materials, pricing, product information
- User asks about security guidelines, incident response procedures
- Anything referencing "our", "company", "internal", "proprietary"

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "question": {
      "type": "string",
      "description": "Natural language question about company knowledge",
      "maxLength": 1000
    }
  },
  "required": ["question"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "answer": {
      "type": "string",
      "description": "Answer based on retrieved company documents"
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "document_name": {"type": "string"},
          "section": {"type": "string"},
          "department": {"type": "string"},
          "excerpt": {"type": "string", "description": "Relevant text snippet"}
        }
      },
      "description": "Documents/sections used to generate answer"
    },
    "confidence": {
      "type": "string",
      "enum": ["high", "medium", "low"],
      "description": "Confidence in answer based on retrieval quality"
    },
    "no_results": {
      "type": "boolean",
      "description": "True if no relevant documents found"
    }
  },
  "required": ["answer", "sources"]
}
```

**Authentication Requirement**: 
- ✅ Requires valid MCP token (presented to MCP server)
- ✅ MCP server validates token, obtains backend JWT
- ✅ Backend JWT injected in /api/chat call
- ✅ Backend validates JWT, loads user+department

**Authorization Requirement**:
- ✅ Backend department ACL enforced (see Step 2 architecture)
- ✅ Only documents in user's department returned
- ✅ Qdrant filter applied server-side
- ✅ No client influence on filtering

**Backend Endpoint Mapping**:
- `POST /api/chat` (existing)
- Request: `{question: "..."}`
- Response: `{answer, sources, retrieved_count, user_department_name}`

**Security Considerations**:
- ✅ No department selection parameter (frontend doesn't decide)
- ✅ No user_id override (MCP token → user_id mapping automatic)
- ✅ No document_id filtering (client can't cherry-pick)
- ✅ Source metadata trusted (backend-generated)
- ✅ Answer grounded in documents (LLM generation from authorized chunks only)

**Required for POC**: ✅ Yes

**Why This Tool Alone is Sufficient**:
1. Covers primary business requirement (answer questions about knowledge base)
2. Delegation: Delegate searching/filtering to backend (not Claude responsibility)
3. Security: Claude can't influence authorization
4. Simplicity: One tool = clear mental model for Claude
5. Extensibility: Future tools can be added later (retrieve, search) if needed

---

### Optional Tool: `retrieve_knowledge_base` (Discussed, Not Recommended for POC)

**Purpose**: Retrieve raw documents/chunks without LLM generation.

**When Claude might use it**: 
- User asks for exact quotes or full documents
- User wants to see all relevant documents before asking follow-up question

**Why NOT include in POC**:
- ❌ Adds complexity (two tools to manage)
- ❌ Claude rarely needs raw chunks (LLM can summarize)
- ❌ Tool description unclear to Claude (when to use vs ask_knowledge_base?)
- ❌ Doubles backend load (two calls for same query)

**Future consideration**: Add in Phase 2 if users ask for document listing/browsing.

---

### Optional Tool: `search_documents` (Not Recommended)

**Why NOT include**:
- ❌ Violates principle of not exposing implementation details
- ❌ Claude doesn't understand vector search semantics
- ❌ Tool description creates ambiguity (search for what?)
- ❌ Backend already does search (ask_knowledge_base calls retrieval)
- ❌ Risk of Claude misusing (asking for "all documents" → performance)

---

### Optional Tool: `list_accessible_documents` (Not Recommended)

**Why NOT include**:
- ❌ Leaks internal document structure to Claude
- ❌ Not part of primary business requirement
- ❌ Creates chatty interaction (list → ask → ask → ...)
- ❌ Backend already filters documents (no need for Claude to see list first)

---

### Tool Descriptions for Claude

**Critical**: Tool descriptions must guide Claude to make smart decisions.

**ask_knowledge_base Description**:

```
Use this tool when the user asks about:
- Company policies, procedures, or internal processes
- Engineering documentation, architecture, or best practices
- HR benefits, compensation, employment guidelines
- Sales materials, pricing, product information
- Security policies, incident response, compliance
- Any proprietary or internal company knowledge

The tool will search the company's internal knowledge base and provide an answer with sources.
Use this tool for ANY question that refers to "our", "company", "internal", or "proprietary" knowledge.

The tool will only return information from documents your user's department is authorized to access.
You cannot access cross-department information.

Example:
- User: "What's our password policy?" → Use this tool
- User: "How do we handle data breaches?" → Use this tool
- User: "What's the company vacation policy?" → Use this tool
- User: "What's Python?" → Don't use this tool (general knowledge)
- User: "Who won the World Cup?" → Don't use this tool (general knowledge)
```

**Why this phrasing**:
- ✅ Clear examples (when to use, when not)
- ✅ Emphasizes "internal" and "company" keywords (prompt engineering)
- ✅ Mentions department authorization (sets expectations)
- ✅ Action-oriented ("Use this tool when...")

---

## Step 6: Tool Behavior for Claude

### Challenge

Tool descriptions cannot force an LLM to use a tool, only guide it.

Claude might:
- ✅ Correctly use the tool for internal knowledge questions
- ⚠️ Try to answer from its own knowledge instead of using the tool
- ⚠️ Use the tool for questions it shouldn't (general knowledge)
- ⚠️ Chain tool calls incorrectly

### Design Principles for Reliability

**1. Make Tool Invocation Natural**

```
Tool Description:
"Use this tool when the user asks about company policies, 
 engineering documentation, HR benefits, security guidelines, 
 or any internal company knowledge."
```

**Why**: Claude is trained on "use this when..." phrasing. Makes it natural to invoke.

**2. Make Tool Useful for ALL Relevant Questions**

By covering:
- Policies (HR, Security, Engineering)
- Documentation (Architecture, Guides)
- Information (Pricing, Sales, Compensation)
- Procedures (Incident Response, Onboarding)

Claude sees tool as broadly applicable to business context.

**3. Make Tool Descriptions Self-Evident**

Example context window usage:
```
User: "What's our password policy?"
Claude thinks: "This asks about 'our' policy → company knowledge → use ask_knowledge_base tool"
Tool invoked → Success
```

vs

```
User: "What's the capital of France?"
Claude thinks: "This is general knowledge → don't use tool"
Tool not invoked → Correct
```

**4. Include Negative Examples in Description**

```
Tool description:
"Use this tool for: passwords policies, engineering guides, product pricing, HR benefits
Don't use this tool for: general knowledge, current events, math problems, general Python questions"
```

**Why**: Negative examples help Claude learn boundaries.

**5. Provide Clear Feedback for Misuse**

When Claude uses tool incorrectly (e.g., "What's Python?"):
- Tool still executes and returns results (or no results)
- Response includes: "This doesn't seem to be an internal company question..."
- Claude learns from feedback (next time, avoid)

### Factors Affecting Reliability

| Factor | Effect | Design Mitigation |
|--------|--------|-------------------|
| Tool description clarity | 🔴 High | Clear examples, "use when", boundaries |
| Tool name | 🔴 Medium | "ask_knowledge_base" (verb + object) |
| Tool purpose statement | 🔴 High | Business-focused ("answer company Qs") |
| Response quality | 🟢 Medium | Empty results show "no docs found" |
| Tool count | 🟢 Low | Single tool is clearest |
| Backend quality | 🟢 High | If retrieval is good, Claude trusts tool |

### Expected Behavior Patterns

**Pattern 1: Direct Invocation** ✅ (Good)
```
User: "What's our PTO policy?"
Claude: "I'll check our knowledge base..."
[Calls ask_knowledge_base]
Response: "Our PTO policy..."
Claude: "Here's what I found..."
```

**Pattern 2: No Invocation** ✅ (Correct)
```
User: "What's Python?"
Claude: "Python is a programming language..."
[No tool call]
(Claude answers from its own knowledge)
```

**Pattern 3: Fallback to Tool** ✅ (Good)
```
User: "I need to know about our data retention policy"
Claude: "I'm not certain about our internal policy..."
[Calls ask_knowledge_base]
Response: "Our data retention policy..."
```

**Pattern 4: Tool Misuse** ⚠️ (Sub-optimal)
```
User: "What's the weather?"
Claude: "I'll check our knowledge base..."
[Calls ask_knowledge_base]
Response: (No results)
Claude: "This doesn't seem relevant to our company knowledge base. 
         I don't have access to weather information."
```

### Reliability Expectations

**POC Target**: 85-90% correct tool invocation rate
- Tool invoked for ~85% of internal knowledge questions
- Tool not invoked for ~90% of general knowledge questions

**Not 100%**: Some errors expected (LLM limitation)

**How to Improve** (if needed later):
1. System prompt: Emphasize when to use tool
2. Few-shot examples: Show good/bad invocations
3. Tool refinement: Rename, rewrite description
4. Feedback: User can say "use the tool" or "don't use the tool"

---

## Step 7: Request/Response Contract

### High-Level Request Path

```
Claude → MCP Protocol
    ↓
MCP Server receives: {tool: "ask_knowledge_base", input: {question: "..."}}
    ↓
MCP Server:
  1. Validates MCP token
  2. Maps token to user_id
  3. Obtains backend JWT for user_id
  4. Calls backend: POST /api/chat
  5. Receives response
  6. Transforms to MCP response
    ↓
Claude receives: {answer, sources, confidence}
```

### MCP Tool Call Contract

**MCP Tool Name**: `ask_knowledge_base`

**MCP Input** (received by MCP server):
```json
{
  "question": "What's our password policy?"
}
```

**MCP Server Processing**:

```python
# Pseudo-code
def handle_ask_knowledge_base(mcp_token, question):
    # 1. Validate MCP token
    user_id = validate_mcp_token(mcp_token)
    if not user_id:
        raise MCP_Error("Invalid token", error_code=401)
    
    # 2. Get backend JWT
    backend_jwt = get_backend_jwt_for_user(user_id)
    if not backend_jwt:
        raise MCP_Error("Backend error", error_code=500)
    
    # 3. Call backend
    backend_response = call_backend(
        endpoint="/api/chat",
        method="POST",
        headers={"Authorization": f"Bearer {backend_jwt}"},
        json={"question": question}
    )
    
    # 4. Transform response
    return {
        "answer": backend_response["answer"],
        "sources": format_sources(backend_response["sources"]),
        "confidence": assess_confidence(backend_response),
        "no_results": len(backend_response["sources"]) == 0
    }
```

### Backend Request/Response Details

**MCP Server → Backend Call**:

```http
POST /api/chat HTTP/1.1
Host: backend.internal
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
  "question": "What's our password policy?"
}
```

**Backend Response** (from `ChatResponse` schema):

```json
{
  "answer": "Our password policy requires...",
  "sources": [
    {
      "document_name": "Security Policy v2.1",
      "section": "Authentication Requirements",
      "department": "Engineering",
      "page": 3
    },
    {
      "document_name": "HR Handbook",
      "section": "Information Security",
      "department": "HR",
      "page": 15
    }
  ],
  "retrieved_count": 5,
  "user_department_name": "Engineering",
  "model": "gpt-4.1-mini"
}
```

**MCP Server → Claude (MCP Response)**:

```json
{
  "answer": "Our password policy requires...",
  "sources": [
    {
      "document_name": "Security Policy v2.1",
      "section": "Authentication Requirements",
      "department": "Engineering",
      "excerpt": "Passwords must be at least 16 characters..."
    },
    {
      "document_name": "HR Handbook",
      "section": "Information Security",
      "department": "HR",
      "excerpt": "All employees must follow engineering security standards..."
    }
  ],
  "confidence": "high"
}
```

### Special Cases: No Results

**Scenario**: Qdrant search returns no relevant documents.

**Backend Response**:
```json
{
  "answer": "I don't have information about that topic in our knowledge base.",
  "sources": [],
  "retrieved_count": 0,
  "user_department_name": "Engineering"
}
```

**MCP Response to Claude**:
```json
{
  "answer": "I don't have information about that in our knowledge base.",
  "sources": [],
  "confidence": "low",
  "no_results": true
}
```

**Claude Behavior**:
- Will likely explain to user that knowledge isn't in database
- May offer to help from general knowledge
- User can refine question and try again

### Special Cases: Unauthorized Document Access Attempt

**Scenario**: User in Sales department asks about HR payroll.

**Backend Authorization Check**:
```
User department: Sales (id=4)
Document department: HR (id=3)
Check: 4 == 3? NO → Unauthorized
```

**Backend ACL Filter Applied**:
```python
# Qdrant search includes filter
filter = Filter(must=[
    FieldCondition(key="department_id", match=MatchValue(value=4))
])
# Only documents with department_id=4 (Sales) returned
# HR documents (department_id=3) filtered at Qdrant server
```

**Result**: Backend returns only authorized documents (Sales documents)

**MCP Response**: Normal (user doesn't know other documents exist)

**Security**: ✅ Bypass prevented (ACL at Qdrant layer, not post-retrieval)

### Field Mapping: MCP Response vs Backend Response

| MCP Response Field | Backend ChatResponse Field | Source | Purpose |
|-------------------|--------------------------|--------|---------|
| `answer` | `answer` | LLM output | Main answer |
| `sources[].document_name` | `sources[].document_name` | Document metadata | Document name |
| `sources[].section` | N/A (in chunk) | Chunk metadata | Document section |
| `sources[].department` | `user_department_name` | User context | For transparency |
| `sources[].excerpt` | N/A (from chunk text) | Chunk content | Relevant quote |
| `confidence` | N/A (derived) | Score + retrieved_count | LLM-derived confidence |
| `no_results` | Derived from `sources.len` | Computed | Empty result flag |

### Error Responses

**Invalid Request** (malformed question):

```json
{
  "error": "Invalid request",
  "message": "Question too long (max 1000 characters)",
  "error_code": 400
}
```

**Unauthorized** (invalid/expired MCP token):

```json
{
  "error": "Unauthorized",
  "message": "Invalid or expired token",
  "error_code": 401
}
```

**Backend Unavailable**:

```json
{
  "error": "Service unavailable",
  "message": "Backend service is not responding",
  "error_code": 503
}
```

**LLM Failure**:

```json
{
  "error": "LLM error",
  "message": "Failed to generate response",
  "error_code": 500
}
```

---

## Step 8: Error Handling

### Error Categories

#### 1. Authentication Errors

**Invalid MCP Token**:
- **Cause**: Token not found in database, malformed, never issued
- **Detection**: MCP server token validation lookup fails
- **Response to Claude**: `HTTP 401 Unauthorized`
- **MCP Response**: 
  ```json
  {
    "error": "authentication_failed",
    "message": "Invalid authentication token"
  }
  ```
- **User Action**: Regenerate MCP token

**Expired MCP Token**:
- **Cause**: Current time > token.expires_at
- **Detection**: MCP server validation query: `expires_at > NOW()` fails
- **Response to Claude**: `HTTP 401 Unauthorized`
- **MCP Response**:
  ```json
  {
    "error": "token_expired",
    "message": "Your token expired on 2027-09-02"
  }
  ```
- **User Action**: Create new MCP token

**Revoked MCP Token**:
- **Cause**: User or admin revoked the token
- **Detection**: MCP server validation query: `revoked_at IS NULL` fails
- **Response to Claude**: `HTTP 401 Unauthorized`
- **MCP Response**:
  ```json
  {
    "error": "token_revoked",
    "message": "This token has been revoked"
  }
  ```
- **User Action**: Create new MCP token

**Unknown User**:
- **Cause**: MCP token maps to user_id that doesn't exist
- **Detection**: User lookup from database fails
- **Response to Claude**: `HTTP 401 Unauthorized`
- **MCP Response**:
  ```json
  {
    "error": "user_not_found",
    "message": "User account not found"
  }
  ```
- **Mitigation**: Check database consistency (should not happen)

---

#### 2. Authorization Errors

**Unauthorized Document Access** (already prevented by Qdrant filter):
- **Cause**: User in department X tries to access documents in department Y
- **Detection**: Qdrant filter applied at query time
- **Result**: Department Y documents not returned, no error (user sees no results)
- **Security**: ✅ Attack prevented before it reaches backend

**Example**:
- Sales user asks: "What's the HR headcount plan?"
- Qdrant filter: `department_id=4` (Sales only)
- HR documents (department_id=3) excluded
- Backend returns: "No documents found matching that query"
- Sales user sees: "No information available" (not "access denied")

---

#### 3. Retrieval Errors

**No Relevant Documents**:
- **Cause**: Vector search returns zero chunks above threshold
- **Detection**: `retrieved_count = 0`
- **Backend Response**: `answer = "I don't have information..."`, `sources = []`
- **MCP Response**: `{"answer": "...", "sources": [], "no_results": true}`
- **Claude Behavior**: Explains to user that knowledge isn't in database

**Qdrant Unavailable**:
- **Cause**: Qdrant service down or unreachable
- **Detection**: RetrievalService.retrieve() receives connection error
- **Backend Response**: `HTTP 500 Service Unavailable`
- **MCP Response**:
  ```json
  {
    "error": "service_unavailable",
    "message": "Knowledge base service is temporarily unavailable"
  }
  ```
- **Claude Behavior**: Apologizes and suggests trying later

**Embedding Generation Failed**:
- **Cause**: Local embedding model fails (OOM, corrupted model)
- **Detection**: EmbeddingService.embed_text() raises exception
- **Backend Response**: `HTTP 500 Internal Server Error`
- **MCP Response**:
  ```json
  {
    "error": "processing_error",
    "message": "Failed to process your question"
  }
  ```
- **Mitigation**: Auto-restart embedding service, alert ops

---

#### 4. Application Errors

**LLM Failure**:
- **Cause**: Azure OpenAI unavailable, quota exceeded, API error
- **Detection**: LLMService.generate() receives API error
- **Backend Response**: `HTTP 500 Internal Server Error`
- **MCP Response**:
  ```json
  {
    "error": "generation_failed",
    "message": "Failed to generate response"
  }
  ```
- **Claude Behavior**: Acknowledges and asks user to retry

**Backend Unavailable**:
- **Cause**: FastAPI backend process down, network unreachable
- **Detection**: MCP server HTTP request to backend times out or gets connection refused
- **Response to Claude**: `HTTP 503 Service Unavailable`
- **MCP Response**:
  ```json
  {
    "error": "backend_unavailable",
    "message": "Backend service is not responding"
  }
  ```
- **Claude Behavior**: Apologizes and suggests trying later

**Backend JWT Obtention Failed**:
- **Cause**: MCP server cannot obtain JWT for user (backend token endpoint down)
- **Detection**: MCP TokenService.get_backend_jwt() fails
- **Response to Claude**: `HTTP 503 Service Unavailable`
- **MCP Response**:
  ```json
  {
    "error": "backend_unavailable",
    "message": "Cannot authenticate with backend service"
  }
  ```

---

#### 5. Request Validation Errors

**Malformed Question**:
- **Cause**: Question empty, not a string, etc.
- **Detection**: FastAPI/MCP validation
- **Response**: `HTTP 400 Bad Request`
- **MCP Response**:
  ```json
  {
    "error": "invalid_request",
    "message": "Question must be a non-empty string"
  }
  ```

**Question Too Long**:
- **Cause**: Question exceeds 1000 characters
- **Detection**: Backend validation or MCP server
- **Response**: `HTTP 400 Bad Request`
- **MCP Response**:
  ```json
  {
    "error": "invalid_request",
    "message": "Question too long (maximum 1000 characters)"
  }
  ```

---

### Error Separation Matrix

| Layer | Error Type | Separation | Handling |
|-------|-----------|-----------|----------|
| **Authentication** | Invalid/expired/revoked token | 401 Unauthorized | Regenerate token |
| **Authorization** | User lacks access (ACL) | Filtered silently (no error) | N/A (prevented) |
| **Retrieval** | No documents found | 200 OK + empty sources | Explain to user |
| **Retrieval** | Backend unavailable | 503 Service Unavailable | Retry later |
| **Application** | LLM/Qdrant failure | 500 Internal Server Error | Alert ops |
| **Validation** | Malformed request | 400 Bad Request | Clarify request |

### Logging Strategy

**MCP Server Logs** (what to capture):

```
Level   Message                                    Action
-----   -------                                    ------
ERROR   MCP token validation failed: not found     Alert if repeated
WARN    MCP token expired: token_id=123           Normal operation
INFO    MCP request: user_id=1, question_len=50   Audit trail
ERROR   Backend unavailable: connection refused    Alert ops
ERROR   Embedding service failed: OOM              Alert ops
```

**Backend Logs** (existing):

```
INFO    /api/chat called by user_id=1 (dept=2)
ERROR   Qdrant search failed: timeout
INFO    Retrieval: 5 chunks, score>=0.4
INFO    LLM: 150 tokens used
```

**Correlation**:
- MCP logs include `user_id` and backend call details
- Backend logs include same user_id
- Can correlate MCP error → backend error via logs

---

## Step 9: Repository Structure

### Proposed `mcp-server/` Directory Layout

```
mcp-server/
├── README.md                           # MCP server documentation
├── pyproject.toml                      # Python project config (Poetry/uv)
├── requirements.txt                    # Python dependencies
├── Dockerfile                          # Container image
├── .dockerignore                       # Docker build ignoring
├── .env.example                        # Example environment variables
├── docker-compose.dev.yml              # Dev-only docker compose (optional)
│
├── src/
│   └── mcp_server/
│       ├── __init__.py
│       ├── main.py                     # MCP server entry point
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py               # Settings (env vars, validation)
│       │   ├── logging.py              # Logging configuration
│       │   └── errors.py               # MCP-specific exceptions
│       │
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── token_service.py        # MCP token validation
│       │   └── jwt_manager.py          # Backend JWT obtaining/caching
│       │
│       ├── client/
│       │   ├── __init__.py
│       │   ├── backend_api_client.py   # HTTP client for backend calls
│       │   └── exceptions.py           # Backend client exceptions
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base_tool.py            # Base tool class (abstract)
│       │   ├── ask_tool.py             # ask_knowledge_base tool handler
│       │   └── tool_registry.py        # Tool registration/discovery
│       │
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── mcp_tools.py            # MCP tool input/output schemas
│       │   └── backend_types.py        # Backend response type hints
│       │
│       └── utils/
│           ├── __init__.py
│           └── helpers.py              # Utility functions
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     # Pytest fixtures
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_token_service.py       # Token validation tests
│   │   ├── test_jwt_manager.py         # JWT obtaining tests
│   │   └── test_backend_client.py      # Backend API client tests
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_ask_tool.py            # End-to-end tool tests
│   │   ├── test_mcp_server.py          # MCP server tests
│   │   └── fixtures/
│   │       ├── mock_backend.py         # Mock backend responses
│   │       └── test_tokens.py          # Test tokens
│   │
│   └── security/
│       ├── __init__.py
│       └── test_token_validation.py    # Security-focused tests
│
└── docs/
    ├── SETUP.md                        # Installation/setup guide
    ├── CONFIGURATION.md                # Environment variables
    ├── API.md                          # MCP tool API documentation
    ├── ARCHITECTURE.md                 # MCP server architecture
    └── DEPLOYMENT.md                   # Deployment guide
```

### Key Directories Explained

**`src/mcp_server/`**: Source code
- Entry point: `main.py` runs MCP server
- Modular organization (core, auth, client, tools, schemas)
- Clean separation of concerns

**`src/mcp_server/core/`**: Infrastructure
- `config.py`: Environment variables and validation
- `logging.py`: Structured logging
- `errors.py`: Custom exceptions

**`src/mcp_server/auth/`**: Authentication
- `token_service.py`: Validate MCP token → user_id
- `jwt_manager.py`: Obtain/cache backend JWT for user_id

**`src/mcp_server/client/`**: Backend Integration
- `backend_api_client.py`: HTTP client for `/api/chat`, `/api/retrieval`, etc.
- Handles JWT injection in Authorization header
- Error handling (retry, timeout)

**`src/mcp_server/tools/`**: MCP Tool Handlers
- `base_tool.py`: Abstract base class for all tools
- `ask_tool.py`: Implementation of `ask_knowledge_base` tool
- `tool_registry.py`: Register tools with MCP server

**`src/mcp_server/schemas/`**: Data Contracts
- `mcp_tools.py`: Input/output schemas for MCP tools (Pydantic)
- `backend_types.py`: Type hints for backend responses

**`tests/`**: Test Suite
- Unit tests: Token validation, JWT, client
- Integration tests: End-to-end tool execution
- Security tests: Token bypass attempts, etc.

**`docs/`**: Documentation
- Setup guide for developers
- Configuration reference
- API documentation for MCP tools
- Deployment instructions

### Configuration File Example

**`.env.example`**:
```bash
# MCP Server
MCP_HOST=0.0.0.0
MCP_PORT=5000

# Backend
BACKEND_URL=http://localhost:8000
BACKEND_API_TIMEOUT=30

# Database (for MCP tokens)
DATABASE_URL=postgresql://mcp_user:mcp_password@postgres:5432/mcp_tokens

# Logging
LOG_LEVEL=INFO

# Security
DEBUG=false
```

### Dockerfile Sketch (Not Implementation, Outline Only)

```dockerfile
# Dockerfile (mcp-server/)
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ /app/src/

# Expose port
EXPOSE 5000

# Run MCP server
CMD ["python", "-m", "mcp_server.main"]
```

### Dependency Philosophy

**Keep dependencies minimal**:
- ✅ `httpx` or `requests`: HTTP client
- ✅ `pydantic`: Data validation
- ✅ `pydantic-settings`: Configuration management
- ✅ `python-jose` or `PyJWT`: JWT handling (if needed, or reuse backend token format)
- ✅ `python-dotenv`: Load .env files
- ✅ `mcp`: Official MCP SDK (when available)
- ✅ `psycopg2-binary` or `asyncpg`: Database driver (for MCP token lookup)

**Avoid**:
- ❌ Duplicating dependencies from backend (FastAPI, SQLAlchemy, etc.)
- ❌ Heavy dependencies (NumPy, Pandas)
- ❌ Embedding libraries (not MCP server responsibility)

---

## Step 10: Deployment Architecture

### Deployment Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     Internet / Anthropic                         │
│                                                                 │
│                   Claude / MCP Client                            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ HTTPS (encrypted, public URL)
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              MCP Server (Public)                                │
│              (mcp.example.com:8000)                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ MCP Endpoint                                             │ │
│  │ - Listen on 0.0.0.0:8000                                │ │
│  │ - Accept HTTPS connections                              │ │
│  │ - Validate MCP tokens                                   │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ Private network (not internet-facing)
                 │ HTTP or internal HTTPS
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Backend Network (Private)                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ FastAPI Backend                                          │ │
│  │ (backend.internal:8000)                                  │ │
│  │ - Not internet-facing                                    │ │
│  │ - Only accepts requests from MCP server                 │ │
│  │ - Validates backend JWT                                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ PostgreSQL + Qdrant                                      │ │
│  │ (private)                                                │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Service Responsibilities

| Service | Internet Facing | Purpose | Deployment |
|---------|-----------------|---------|-----------|
| **MCP Server** | ✅ Yes (public HTTPS) | Accept Claude connections, forward to backend | Scalable, independent |
| **FastAPI Backend** | ❌ No (internal only) | RAG, auth, authorization | Existing deployment |
| **PostgreSQL** | ❌ No (internal only) | Data storage | Existing deployment |
| **Qdrant** | ❌ No (internal only) | Vector search | Existing deployment |

### Network Topology

**Current (POC/Dev)**:
```
docker-compose.yml
├── postgres (internal)
├── qdrant (internal)
└── backend (internal + port 8000 exposed for testing)
```

**After MCP Addition**:
```
docker-compose.yml (existing)
├── postgres (internal)
├── qdrant (internal)
└── backend (internal, only MCP server calls it)

mcp-server/docker-compose.yml (new, optional for local dev)
└── mcp (exposed on port 5000 for local testing)

Production Deployment:
├── Kubernetes / Docker Swarm / VM cluster
│   ├── MCP Server instances (load balanced, auto-scaled)
│   │   ├── replica-1
│   │   ├── replica-2
│   │   └── replica-3
│   └── Ingress / Load Balancer → mcp.example.com:443 (HTTPS)
│
└── Backend cluster (existing, separate namespace/deployment)
    ├── Backend instances
    ├── PostgreSQL cluster
    └── Qdrant cluster
    
MCP instances communicate with backend via internal DNS/IP
(e.g., backend.internal:8000 or K8s service)
```

### Secrets & Credentials

**MCP Server needs**:
1. `BACKEND_URL`: URL of FastAPI backend (e.g., `http://backend.internal:8000`)
2. `DATABASE_URL`: PostgreSQL connection for MCP token storage
3. `JWT_SECRET`: (optional) If MCP server needs to sign anything
4. `LOG_LEVEL`: Logging verbosity

**Backend already has**:
1. `DATABASE_URL`: PostgreSQL
2. `QDRANT_URL`: Qdrant
3. `JWT_SECRET`: For token validation
4. `AZURE_OPENAI_*`: LLM credentials

**Never expose publicly**:
- ❌ `DATABASE_URL` (backend or MCP)
- ❌ `JWT_SECRET`
- ❌ `AZURE_OPENAI_API_KEY`
- ❌ Individual MCP tokens (one-time display only)

**Storage**:
- Environment variables (via Kubernetes Secrets, AWS Secrets Manager, etc.)
- `.env` file (dev only, excluded from Git)
- Configuration management (Terraform, Helm, etc.)

### TLS/HTTPS

**MCP Server Endpoint**:
- ✅ HTTPS only (no HTTP)
- ✅ Valid certificate (not self-signed for production)
- ✅ Certificate renewal automated (Let's Encrypt + certbot, or cloud provider)

**Backend Endpoint** (internal):
- ⚠️ Can use HTTP internally (private network)
- ✅ Or HTTP + TLS if internal TLS enabled
- ✅ mTLS optional (service-to-service authentication)

### Scalability

**MCP Server** (stateless):
- ✅ Scale horizontally (multiple instances)
- ✅ Load balancer routes requests across instances
- ✅ Each instance independently validates tokens + calls backend
- ✅ No state shared between instances

**Example scaling**:
```
Client request 1 → MCP Replica 1 → Backend
Client request 2 → MCP Replica 2 → Backend
Client request 3 → MCP Replica 3 → Backend

All replicas:
- Read MCP tokens from same database
- Call same backend
- No contention or coordination needed
```

**Backend** (existing):
- Unchanged scaling model
- Can add instances as needed
- MCP server pool scales independently

### Monitoring & Observability

**MCP Server Metrics**:
- Request rate (requests/sec)
- Latency (p50, p95, p99)
- Error rate (4xx, 5xx)
- Token validation success rate
- Backend call success rate

**Logs**:
- Structured logging (JSON format)
- Log level configurable
- User action traceability (user_id, MCP token usage)
- Error details (stack traces for 5xx)

**Health Check**:
- `/health` endpoint: Returns 200 if MCP server healthy
- Checks: Database connectivity, backend connectivity
- Used by load balancer for routing decisions

---

## Step 11: Security Threat Model

### Threat Categories

#### 1. Token Threats

**Threat 1a: Token Theft**
- **Attack**: Attacker obtains MCP token (phishing, leaked env var, compromised device)
- **Impact**: Attacker can impersonate user to MCP server
- **Duration**: Until token expiration or revocation
- **Mitigation**:
  - ✅ Tokens are opaque (hashing required, not self-contained)
  - ✅ Tokens expire (default 1 year, user can set shorter)
  - ✅ Tokens can be revoked immediately
  - ✅ Encourage users to store securely (Anthropic platform, password manager)
  - ✅ Logging of token usage (can detect anomalies)
  - ✅ User can revoke if suspected compromise

**Threat 1b: Token Forgery**
- **Attack**: Attacker generates fake MCP token
- **Impact**: Could gain access if backend accepts it
- **Mitigation**:
  - ✅ Token hashing (attacker cannot know hash without database access)
  - ✅ Database lookup required (cannot forge without database compromise)
  - ✅ If successful: requires database compromise (separate threat)

**Threat 1c: Token Replay**
- **Attack**: Attacker captures MCP token from network, replays it
- **Impact**: Same as token theft
- **Mitigation**:
  - ✅ HTTPS required (eavesdropping prevented)
  - ✅ Token doesn't contain state that needs replay protection

**Threat 1d: Token Exposure in Logs**
- **Attack**: Raw MCP token logged, exposed in error messages or debug output
- **Impact**: Anyone with log access can use token
- **Mitigation**:
  - ✅ Never log raw tokens (only token_id or masked preview)
  - ✅ Log validation failures with token hash (not raw)
  - ✅ Code review to prevent accidental logging

---

#### 2. Impersonation Threats

**Threat 2a: User Impersonation via Malicious Input**
- **Attack**: Attacker tries to pass `user_id=2` in request to become different user
- **Impact**: Access different user's documents/department
- **Mitigation**:
  - ✅ User identity bound to MCP token (not in request)
  - ✅ MCP token → user_id lookup done server-side
  - ✅ Client cannot override user_id
  - ✅ Backend JWT includes correct user_id (validated by backend)

**Threat 2b: Department Spoofing**
- **Attack**: Attacker tries to pass `department_id=3` to access HR docs
- **Impact**: Access cross-department documents
- **Mitigation**:
  - ✅ Department loaded from PostgreSQL (trusted source)
  - ✅ Not passed in request, derived from user
  - ✅ Qdrant filter enforced at database layer
  - ✅ Attacker cannot override department

---

#### 3. Authorization Bypass Threats

**Threat 3a: ACL Bypass via Qdrant Direct Access**
- **Attack**: Attacker connects to Qdrant directly (if exposed)
- **Impact**: Retrieve all documents without ACL filter
- **Mitigation**:
  - ✅ Qdrant must be internal-only (not exposed to internet)
  - ✅ No direct Qdrant access from MCP server (all queries via backend)
  - ✅ Firewall rules restrict access to Qdrant

**Threat 3b: ACL Bypass via Backend Direct Access**
- **Attack**: Attacker connects to backend directly (if exposed)
- **Impact**: Call backend endpoints, bypass MCP token validation
- **Mitigation**:
  - ✅ Backend must be internal-only
  - ✅ MCP server is only public endpoint
  - ✅ Backend JWT still required (protects against unauthenticated calls)

**Threat 3c: Post-Retrieval Filtering Bypass**
- **Attack**: Attacker modifies MCP server to bypass department filter
- **Impact**: Retrieve unauthorized documents
- **Mitigation**:
  - ✅ Filter applied at Qdrant layer (not in MCP server)
  - ✅ Even compromised MCP server cannot bypass
  - ✅ Backend also validates (defense in depth)

---

#### 4. Man-in-the-Middle (MITM) Threats

**Threat 4a: MCP Token Interception**
- **Attack**: Attacker intercepts MCP token in transit
- **Impact**: Token theft (same as threat 1a)
- **Mitigation**:
  - ✅ HTTPS required (TLS encryption)
  - ✅ Certificate validation (prevents MITM in most scenarios)

**Threat 4b: Backend Communication Interception**
- **Attack**: Attacker intercepts MCP → Backend communication
- **Impact**: Intercept JWT, get answer to questions
- **Mitigation**:
  - ✅ Internal network (private, not internet-facing)
  - ✅ Can add TLS between MCP and backend (optional)
  - ✅ Network segmentation (MCP and backend in same private network)

---

#### 5. MCP Server Compromise Threats

**Threat 5a: MCP Server Compromised (Malware/Exploit)**
- **Attack**: Attacker gains code execution in MCP server
- **Impact**: 
  - Attacker can impersonate any user (has access to MCP tokens in memory)
  - Attacker can modify queries, capture responses
  - Attacker can access backend with any user's JWT
- **Mitigation**:
  - ✅ Defense in depth: Backend JWT still required
  - ✅ Backend validates JWT (even if MCP malicious, must present valid JWT)
  - ✅ Logging on backend (anomalies detected via audit trail)
  - ✅ Container security: minimal base image, regular scanning
  - ✅ Network isolation: MCP can only reach backend + database
  - ✅ Regular security updates
  - ✅ RBAC: MCP server runs as non-root, limited privileges

**Note**: If MCP server is fully compromised, attacker has access to what that MCP instance users do. Cannot access other users' data beyond what they can see (backend ACL still enforced).

---

#### 6. Backend Compromise Threats

**Threat 6a: Backend Compromised**
- **Attack**: Attacker gains access to backend
- **Impact**: 
  - All documents accessible (ACL bypassed)
  - User credentials and passwords at risk
  - System fully compromised
- **Mitigation**: (Existing backend responsibility)
  - ✅ Backend security practices (RBAC, secrets management, etc.)
  - ✅ Not introduced by MCP

---

#### 7. Injection Threats

**Threat 7a: Prompt Injection in Question**
- **Attack**: User embeds malicious instructions in question
- **Impact**: LLM might follow injected instructions instead of system prompt
- **Mitigation**:
  - ✅ System prompt backend-controlled (not influenced by MCP)
  - ✅ Strict prompt construction (clear boundaries between context and question)
  - ✅ This is existing backend protection (not MCP-specific)

**Threat 7b: SQL Injection in MCP Token**
- **Attack**: Attacker crafts token with SQL injection payload
- **Impact**: Database compromise
- **Mitigation**:
  - ✅ Token used as parameter (not string interpolation)
  - ✅ Parameterized queries (PostgreSQL prepared statements)
  - ✅ Token validation doesn't concatenate strings

---

#### 8. Information Disclosure Threats

**Threat 8a: Leaked Internal Backend URL**
- **Attack**: Attacker discovers backend URL (from error messages, logs, etc.)
- **Impact**: Attacker can try to connect to backend directly
- **Mitigation**:
  - ✅ Generic error messages (don't expose URLs)
  - ✅ Backend JWT still required (protects even if URL known)
  - ✅ Firewall rules (backend only accepts from MCP server)

**Threat 8b: Leaked Source Metadata**
- **Attack**: User sees sensitive metadata (department name, document classification)
- **Impact**: Information disclosure (minor)
- **Mitigation**:
  - ✅ Source metadata intentionally provided (user needs to know source)
  - ✅ Department filter prevents cross-department access (metadata from user's own dept)
  - ✅ Design decision: transparency vs secrecy (transparency chosen)

**Threat 8c: Tokens in Error Messages**
- **Attack**: Malformed token causes error that echoes back the token
- **Impact**: Token exposure
- **Mitigation**:
  - ✅ Validate and mask token before using
  - ✅ Error messages don't include request details
  - ✅ Code review for accidental exposure

---

#### 9. Denial of Service (DoS) Threats

**Threat 9a: Token Database Exhaustion**
- **Attack**: Attacker creates millions of MCP tokens
- **Impact**: Database bloated, legitimate tokens slow to validate
- **Mitigation**:
  - ✅ Rate limiting (limit tokens created per user per day)
  - ✅ Database cleanup (old revoked/expired tokens archived)
  - ✅ Admin portal shows token counts (detects abuse)
  - ✅ Revoke suspicious token patterns (anomaly detection)

**Threat 9b: Backend Flooded with MCP Requests**
- **Attack**: Attacker generates many requests from MCP server
- **Impact**: Backend overload, service unavailable
- **Mitigation**:
  - ✅ Rate limiting (per MCP server, per user, global)
  - ✅ Backend autoscaling
  - ✅ Request queuing (handle spikes gracefully)
  - ✅ Monitoring (detect unusual patterns)

**Threat 9c: Slow Query DoS**
- **Attack**: Attacker sends queries that take long time to process
- **Impact**: Backend resources consumed, other users delayed
- **Mitigation**:
  - ✅ Query timeout (60 seconds, configurable)
  - ✅ Rate limiting by user (users can't send many slow queries)
  - ✅ Backend monitoring (slow queries detected)

---

#### 10. Confused Deputy Problem

**Threat 10a: Confused Deputy**
- **Attack**: MCP server (deputy) tricked into making request on behalf of attacker
- **Impact**: Attacker gains privileges of MCP server
- **Mitigation**:
  - ✅ MCP server only acts on behalf of authenticated user (via MCP token)
  - ✅ Attacker cannot control which user MCP server acts as (token binding)
  - ✅ Backend validates JWT (sees correct user_id)

---

### Security Incident Response

**If MCP Token Leaked**:
1. User/Admin revokes token immediately (database update)
2. MCP server rejects token on next use
3. Claude connection drops
4. User creates new token
5. No data accessed post-revocation

**If Attacker Accesses Backend Directly**:
1. Backend JWT still required (authentication enforced)
2. If attacker has token, they already compromised MCP
3. Escalate to backend security incident

**If Database Breached**:
1. MCP tokens are hashed (raw tokens not exposed)
2. If hashes are stolen: attacker cannot forge tokens
3. If attacker cracks hashes (slow): can compromise tokens created with weak randomness
4. Mitigation: Rotate tokens (users create new ones), invalidate old ones

---

## Step 12: What Changes vs What Stays

### Components That Must Remain UNTOUCHED ✅

#### Backend Authentication Flow
- ✅ `backend/app/dependencies/auth.py` → `get_current_user()`
- ✅ `backend/app/services/token_service.py` (JWT creation/validation)
- ✅ `backend/app/api/auth.py` (login endpoint)
- ✅ `backend/app/services/password_service.py` (bcrypt hashing)
- ✅ **Reason**: Existing, secure, already validated. MCP uses same flow (indirectly via backend JWT).

#### Authorization & ACL
- ✅ `backend/app/services/authorization_service.py`
- ✅ `backend/app/services/retrieval_service.py` (Qdrant filtering)
- ✅ Department-based ACL model
- ✅ **Reason**: Core security boundary. Cannot be replicated in MCP. Backend must remain authoritative.

#### RAG Pipeline
- ✅ `backend/app/services/rag_service.py`
- ✅ `backend/app/services/prompt_builder.py`
- ✅ `backend/app/services/llm_service.py`
- ✅ `backend/app/services/embedding_service.py`
- ✅ **Reason**: MCP is adapter only. RAG stays in backend.

#### Vector Database Integration
- ✅ `backend/app/services/qdrant_service.py`
- ✅ Qdrant collection schema
- ✅ ACL filter construction
- ✅ **Reason**: No changes needed for MCP support.

#### Database Models
- ✅ `backend/app/models/user.py`
- ✅ `backend/app/models/department.py`
- ✅ `backend/app/models/document.py`
- ✅ **Reason**: MCP doesn't interact with models directly (goes through API).

#### Configuration
- ✅ `backend/app/core/config.py` (existing settings)
- ✅ **Note**: New MCP-specific settings go in `mcp-server/`, not backend.
- ✅ **Reason**: Separation of concerns. MCP has its own config.

#### API Endpoints (Existing)
- ✅ `POST /api/auth/login` - No changes
- ✅ `GET /api/auth/me` - No changes
- ✅ `POST /api/chat` - No changes (already supports JWT auth)
- ✅ `POST /api/retrieval` - No changes
- ✅ **Reason**: MCP uses existing endpoints. No endpoint modifications needed.

#### Frontend
- ✅ `frontend/` - Completely unchanged
- ✅ **Reason**: MCP is separate from frontend. No interaction needed.

#### Docker Setup
- ✅ `docker-compose.yml` (existing services)
- ✅ `backend/Dockerfile`
- ✅ **Reason**: Backend deployment unchanged. MCP has separate docker setup.

---

### Components That Will Be ADDED

#### New Database Table
- 📝 `mcp_tokens` table (PostgreSQL)
  ```sql
  CREATE TABLE mcp_tokens (
      id SERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id),
      token_hash VARCHAR(255) NOT NULL UNIQUE,
      created_at TIMESTAMP NOT NULL DEFAULT NOW(),
      expires_at TIMESTAMP NOT NULL,
      last_used_at TIMESTAMP,
      revoked_at TIMESTAMP,
      description VARCHAR(255),
      created_by_user_id INTEGER REFERENCES users(id),
      created_via TEXT,
      INDEX (user_id),
      INDEX (token_hash),
      INDEX (expires_at)
  );
  ```
- **Scope**: Backend database (new table)
- **Migration**: Alembic migration file `backend/alembic/versions/XXX_add_mcp_tokens_table.py`

#### Optional Backend Endpoint (for MCP token → JWT conversion)
- 📝 `POST /api/internal/mcp-token-to-jwt` (internal only)
- **Purpose**: Convert MCP token to backend JWT
- **Security**: Requires shared secret or certificate auth between MCP and backend
- **Alternative**: Pre-generate JWTs when MCP token created (no new endpoint needed)
- **Decision**: To be made in Phase 2 implementation

#### MCP Server Application
- 📝 `mcp-server/` directory (new, complete separate service)
- Contents: Source code, tests, configuration, documentation (outlined in Step 9)

#### MCP Token Admin Interface (Optional, for POC can be manual/CLI)
- 📝 Admin portal / CLI tool to create/revoke MCP tokens
- **Scope**: Backend admin feature or separate tool
- **Requirement**: Must allow admin to generate tokens for users
- **Delivery**: Could be simple CLI script, admin endpoint, or external portal

---

### Components With Minor Changes

#### Backend Configuration
- 📝 `.env.example` - Add optional MCP-related settings (optional)
  ```bash
  # MCP Support (optional)
  MCP_ENABLED=true
  MCP_TOKEN_EXPIRATION_DAYS=365
  ```
- **Reason**: Optional, for feature flags or tuning
- **Effort**: Minimal (documentation only)

#### Backend Logging
- 📝 Optionally enhance logging to track MCP-originated requests
  ```python
  logger.info(f"/api/chat called by user_id={user.id} (via MCP)")
  ```
- **Reason**: Audit trail improvement
- **Effort**: Minimal (existing logs sufficient, enhancement optional)

#### Backend Documentation
- 📝 `backend/README.md` - Add note about MCP
- 📝 `docs/` - Add MCP architecture documentation
- **Reason**: Documentation keeps codebase understandable
- **Effort**: Low

---

### Summary: Change Matrix

| Component | Type | Change | Effort | Risk |
|-----------|------|--------|--------|------|
| FastAPI Backend | Existing | No code changes | 0% | None |
| Auth Flow | Existing | No changes | 0% | None |
| Authorization/ACL | Existing | No changes | 0% | None |
| RAG Pipeline | Existing | No changes | 0% | None |
| Database Schema | Existing | Add mcp_tokens table | Low | Low |
| Endpoints | Existing | No changes (reuse) | 0% | None |
| Frontend | Existing | No changes | 0% | None |
| Docker | Existing | No changes (backend) | 0% | None |
| MCP Server | **NEW** | Create new service | High | Medium |
| MCP Token Admin | **NEW** | Create admin feature | Medium | Low |
| Documentation | Existing | Enhance | Low | None |

**Overall Risk Assessment**: ✅ Low to Medium
- Backend is not modified (lowest risk)
- New MCP service is isolated (separate deployment)
- Token table addition is backward-compatible
- Can be deployed independently

---

## Step 13: Final Recommendation

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Claude / Anthropic Platform                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTPS + MCP Remote Transport
                         │ (MCP Protocol)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server                                   │
│            (mcp-server/ directory)                             │
│         Independently Deployable Service                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ MCP Tool: ask_knowledge_base                            │  │
│  │ Input: {question: string}                               │  │
│  │ Output: {answer, sources[], confidence}                │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        ↓                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ MCP Token Service                                       │  │
│  │ - Validate MCP token → user_id                         │  │
│  │ - Look up in PostgreSQL (mcp_tokens table)             │  │
│  │ - Immediate revocation support                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        ↓                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ JWT Manager                                             │  │
│  │ - Obtain backend JWT for authenticated user            │  │
│  │ - Cache or regenerate (TBD in Phase 2)                │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        ↓                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Backend API Client                                      │  │
│  │ - HTTP client for /api/chat, /api/retrieval            │  │
│  │ - Injects backend JWT in Authorization header          │  │
│  │ - Error handling, retries, timeouts                    │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Internal Network (HTTP/HTTPS)
                         │ Backend JWT in Authorization header
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Existing)                          │
│         Not Modified for MCP Support                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Endpoint: POST /api/chat                                │  │
│  │ - Accepts: {question}                                  │  │
│  │ - Requires: Bearer JWT (from MCP server)              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        ↓                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ get_current_user() Dependency                           │  │
│  │ - Validates JWT signature                              │  │
│  │ - Loads User from PostgreSQL (trusted)                │  │
│  │ - Loads Department relationship                        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        ↓                                        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ RetrievalService + AuthorizationService                 │ │
│  │ - Department resolved from User (not from client)      │ │
│  │ - Qdrant filter: department_id = user.department_id   │ │
│  │ - ACL filter applied server-side at Qdrant layer      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                        ↓                                        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ RAGService Orchestration                                │ │
│  │ - Secure prompt construction (system prompt backend-    │ │
│  │   controlled)                                           │ │
│  │ - LLM generation (Azure OpenAI)                        │ │
│  │ - Source attribution (backend-controlled)              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                        ↓                                        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ChatResponse                                             │ │
│  │ - {answer, sources[], user_department_name}            │ │
│  └──────────────────────────────────────────────────────────┘ │
│                        ↓                                        │
│  ┌────────────┬──────────────────┬────────────────────┐       │
│  ▼            ▼                  ▼                    ▼        │
│ PostgreSQL  Qdrant           Local Embeddings    Azure OpenAI │
│ (Auth/Auth) (Vector Search)  (Query Embedding)   (LLM)       │
│             (ACL Filtering)                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Authentication Flow

```
1. TOKEN CREATION (One-time, out-of-band)
   Admin / User Portal
   ↓
   Admin creates MCP token for user "Mohit"
   ↓
   Backend generates: mcp_token_<random>_<timestamp>
   ↓
   Stores: SHA256(token) in mcp_tokens table
   ↓
   Returns raw token (one-time display)
   ↓
   User stores securely (Anthropic platform / .env / password manager)

2. CLAUDE CONNECTS (Every conversation)
   Claude Client
   ↓
   Connects to MCP server with MCP token
   ↓
   MCP: "authenticate with token=mcp_token_..."
   ↓
   MCP Server validates:
     - Hash token: SHA256(mcp_token)
     - Query: SELECT user_id FROM mcp_tokens 
               WHERE token_hash='<hash>' 
               AND revoked_at IS NULL 
               AND expires_at > NOW()
     - Result: user_id=1 (Mohit, Engineering)

3. MCP SERVER GETS BACKEND JWT
   MCP Server
   ↓
   Option A: Call POST /api/auth/login with pre-stored credentials
   Option B: Pre-generate JWT when MCP token created
   Option C: Call new endpoint /api/internal/mcp-token-to-jwt with MCP token
   (Decision in Phase 2)
   ↓
   Backend returns: Bearer JWT (expires in 1 hour)
   ↓
   MCP caches JWT (reuse for 30 min, regenerate after)

4. MCP CALLS BACKEND
   MCP Server
   ↓
   POST /api/chat
   Authorization: Bearer eyJ0eXAiOiJKV1QiLC...
   Content-Type: application/json
   
   {
     "question": "What's our password policy?"
   }
   ↓
   Backend receives:
   - Validates JWT signature
   - Extracts user_id=1
   - Loads User+Department from PostgreSQL
   - Resolves department_id=2 (Engineering)

5. BACKEND ENFORCES ACL
   Backend
   ↓
   RetrievalService.retrieve():
   - Department: Engineering (2)
   - Build Qdrant filter: {department_id: 2}
   - Qdrant query with filter
   - Only documents where department_id=2 returned
   - HR documents (dept=3) filtered out server-side
   ↓
   RAGService.generate():
   - Prompt builder with authorized chunks only
   - LLM generates answer
   - Sources from chunk metadata (backend-controlled)

6. RESPONSE TO CLAUDE
   Backend → MCP Server
   ↓
   ChatResponse:
   {
     "answer": "Our password policy requires...",
     "sources": [{document_name, section, dept}, ...],
     "retrieved_count": 5
   }
   ↓
   MCP transforms to MCP format
   ↓
   MCP → Claude
   ↓
   Claude presents to user
```

### Recommended Token Model

**Token Lifecycle**:
```
Create                          Active                      End
  ↓                               ↓                          ↓
Admin creates token            Claude uses token       Time to retire
  ↓                               ↓                          ↓
Generate: mcp_user_XYZ...      Validate per request    Expiration or
  ↓                               ↓                      revocation
Hash: SHA256(token)            Query PostgreSQL         ↓
  ↓                               ↓                  Database update
Store in database               Return 401 if fail       (revoked_at)
  ↓                               ↓                          ↓
Return raw token               Proceed                    Rejected
(one-time)
```

**Storage**:
```
mcp_tokens table:
  id, user_id, token_hash (unique),
  created_at, expires_at (default: now + 1 year),
  last_used_at, revoked_at,
  description, created_by_user_id
```

**Validation Query**:
```sql
SELECT user_id FROM mcp_tokens
WHERE token_hash = SHA256(provided_token)
  AND revoked_at IS NULL
  AND expires_at > NOW()
```

### Recommended MCP Tools

**Primary Tool: `ask_knowledge_base`**
- Input: `{question: string}`
- Output: `{answer, sources[], confidence, no_results}`
- Purpose: Answer questions using company knowledge base
- Description: Clear guidance on when/when-not to use
- Backend Endpoint: `POST /api/chat` (existing)
- Security: Requires MCP token + backend JWT

**No Secondary Tools** (for POC):
- ❌ `retrieve_documents` (not needed, ask_knowledge_base sufficient)
- ❌ `search_documents` (implementation detail exposure)
- ❌ `list_documents` (leaks structure, not required)

**Future Tools** (Phase 2+):
- `retrieve_raw_chunks` (if users request raw documents)
- `search_documents` (with clear scope)
- `get_document_metadata` (for document browsing)

### Recommended Repository Structure

```
mcp-server/
├── README.md
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── .env.example
│
├── src/mcp_server/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── errors.py
│   ├── auth/
│   │   ├── token_service.py
│   │   └── jwt_manager.py
│   ├── client/
│   │   └── backend_api_client.py
│   ├── tools/
│   │   ├── base_tool.py
│   │   ├── ask_tool.py
│   │   └── tool_registry.py
│   ├── schemas/
│   │   ├── mcp_tools.py
│   │   └── backend_types.py
│   └── utils/
│       └── helpers.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── security/
│
└── docs/
    ├── SETUP.md
    ├── CONFIGURATION.md
    ├── API.md
    └── DEPLOYMENT.md
```

### Recommended Deployment Model

**Topology**:
```
Internet
  ↓
Claude (Remote MCP Client)
  ↓ HTTPS: mcp.example.com:443
  ↓
MCP Server (Public)
  ├─ Stateless, scalable
  ├─ Load balanced (multiple replicas)
  ├─ Auto-scaling on load
  ↓
Private Network
  ↓
MCP Server ← → PostgreSQL (mcp_tokens)
  ↓
MCP Server → Backend (internal HTTP)
  ↓
Backend (Private, not internet-facing)
  ├─ Existing deployment
  ├─ Accepts calls only from MCP
  ├─ Validates backend JWT
  ↓
PostgreSQL (auth) + Qdrant (vectors) + Azure OpenAI (LLM)
```

**Network Isolation**:
- ✅ MCP: Public HTTPS (mcp.example.com)
- ✅ Backend: Private/internal only
- ✅ MCP → Backend: Private network (no internet routing)
- ✅ PostgreSQL/Qdrant: Private/internal only

**Secrets**:
- Environment variables (Kubernetes Secrets, AWS Secrets Manager, etc.)
- Never in code, never in logs
- Rotation automated (certificates, tokens, credentials)

### Recommended Security Principles

1. **Defense in Depth**
   - MCP validates token → Maps to user_id
   - Backend validates JWT → Loads user from database
   - Backend ACL enforced at Qdrant layer
   - Even if one layer compromised, others remain

2. **Least Privilege**
   - MCP server can only reach backend + database
   - MCP server doesn't execute arbitrary queries
   - Backend runs with minimal required permissions
   - Qdrant access restricted to backend

3. **Trustworthiness**
   - User identity bound to MCP token (cryptographically)
   - Department loaded from database (not from request)
   - ACL enforced server-side (not client-side)
   - Source metadata backend-generated (not LLM-generated)

4. **Auditability**
   - Log all MCP token usage (user_id, timestamp)
   - Log all backend requests (which user, what query)
   - Correlate MCP logs + backend logs via user_id
   - Retention: Audit logs kept for compliance (90 days minimum)

5. **Observability**
   - Metrics: Request rate, latency, errors
   - Logs: Structured (JSON), searchable
   - Traces: Correlation across MCP → backend
   - Alerts: Anomalies (unusual token usage, rate spikes)

### Recommended Implementation Phases

**Phase 1 (Current): Architecture & Design** ✅
- Completed: All 13 steps
- Outcome: Detailed design document (this file)
- Next: Stakeholder review + approval

**Phase 2: Backend Infrastructure**
- Add `mcp_tokens` table to PostgreSQL
- Create Alembic migration
- Implement MCP token admin feature (CLI or endpoint)
- Optional: New backend endpoint `/api/internal/mcp-token-to-jwt`

**Phase 3: MCP Server Core**
- Create `mcp-server/` directory structure
- Implement token validation service
- Implement JWT manager (get/cache backend JWT)
- Implement backend API client
- Write unit tests for auth services

**Phase 4: MCP Tools**
- Implement `ask_knowledge_base` tool handler
- Implement tool registry
- Integrate with MCP SDK
- Write integration tests (mock backend)

**Phase 5: Deployment & Testing**
- Dockerfile + docker-compose for MCP
- Health checks + monitoring
- End-to-end testing (Claude client simulation)
- Security testing (token bypass attempts, etc.)

**Phase 6: Production Deployment**
- Deploy MCP server to production
- Configure HTTPS / certificate management
- Set up load balancing / auto-scaling
- Enable audit logging + monitoring
- Gradual rollout (shadow mode, then GA)

**Phase 7+: Expansion**
- Additional MCP tools (retrieve, search, etc.)
- Enhanced analytics / dashboard
- Feedback loop with Claude team (if Claude improvements needed)
- Regular security audits

### Exit Criteria for Phase 1 Design

**This document is complete when**:
- ✅ All 13 steps addressed with detailed explanations
- ✅ Security model validated (threat model covers major attacks)
- ✅ Architecture aligns with constraints (independent deployment, per-user tokens, no backend changes)
- ✅ No unresolved decisions (or decisions deferred with clear rationale)
- ✅ Stakeholders can review and approve

**This document requires NO implementation**:
- No code changes
- No files created
- No databases modified
- No deployments

**Next step**: Present design to stakeholders for review → Approval → Phase 2 implementation.

---

## Summary: Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Auth Flow** | Option A (MCP Token → User → Backend JWT) | Secure, backward-compatible, auditability |
| **Token Model** | Opaque, hashed at rest, 1-year expiration | Security best practice, supports revocation |
| **Tool Set** | Single: `ask_knowledge_base` | Simplicity, sufficient for MVP, extensible |
| **Deployment** | Separate service, independent scaling | Meets constraint, enables independent hosting |
| **Backend Changes** | Add `mcp_tokens` table only | Minimize changes, maximum security assurance |
| **Security** | Defense in depth (token + JWT + ACL) | Prevents major attack scenarios |

---

**END OF PHASE 1 DESIGN DOCUMENT**

This document provides a complete architecture blueprint for Phase 2+ implementation. No code has been written or modified. Design is ready for stakeholder review.
