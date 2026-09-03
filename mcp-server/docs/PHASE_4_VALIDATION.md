# Phase 4 — Claude MCP Integration & End-to-End Validation

**Status**: 🚀 STARTING

**Date**: 2026-09-02

**Objective**: Verify complete MCP flow from Claude through backend, validate security properties, test error scenarios, and prepare for production deployment.

---

## Phase 3 Implementation Inspection Report

### ✅ MCP Server Structure

**Location**: `mcp-server/src/mcp_server/`

```
mcp-server/
├── src/mcp_server/
│   ├── __init__.py                          ✅ Server setup + tool handlers
│   ├── main.py                              ✅ Entry point + Streamable HTTP
│   ├── core/
│   │   ├── config.py                        ✅ Pydantic Settings (mcp_host, mcp_port, backend_url, backend_api_timeout)
│   │   ├── logging.py                       ✅ Structured logging
│   │   └── errors.py                        ✅ MCP-specific exceptions
│   ├── auth/
│   │   ├── __init__.py                      ✅ validate_mcp_token(), AuthenticatedContext
│   │   └── token_service.py                 ✅ Backend token validation (validate_token_with_backend)
│   ├── client/
│   │   ├── __init__.py                      ✅ Re-exports
│   │   └── backend_api_client.py            ✅ HTTP client (BackendAPIClient, ChatResponse, ChatSource)
│   ├── tools/
│   │   ├── __init__.py                      ✅ Re-exports
│   │   └── ask_tool.py                      ✅ ask_knowledge_base_impl
│   ├── health.py                            ✅ Health endpoint
│   └── __pycache__/
├── run.py                                   ✅ Startup script
├── run.sh                                   ✅ Bash wrapper
├── requirements.txt                         ✅ Dependencies
├── Dockerfile                               ✅ Container
├── .dockerignore                            ✅ Docker ignore
└── docs/
    ├── PHASE_3_MCP_SERVER_CORE.md           ✅ Comprehensive documentation
```

### ✅ MCP SDK & Transport

**SDK Version**: `mcp>=0.1.0` (official Anthropic SDK)

**Transport**: Streamable HTTP via `mcp.server.Server` with request handlers

**Python**: 3.10+ (verified)

**Key Dependencies**:
- `mcp>=0.1.0` — Official MCP SDK
- `httpx>=0.25.0` — Async HTTP client
- `pydantic>=2.0` — Configuration & validation
- `pydantic-settings>=2.0` — Settings management
- `python-dotenv>=1.0.0` — Environment variables
- `starlette>=0.35.0` — HTTP framework
- `uvicorn>=0.24.0` — ASGI server

### ✅ MCP Endpoint

**Local Endpoint**: `http://localhost:5000`

**Configuration**:
```python
# From core/config.py
mcp_host: str = "0.0.0.0"  # Can be overridden via environment
mcp_port: int = 5000       # Can be overridden via environment
```

### ✅ Authentication Mechanism

**Flow**:
```
MCP Client Request (Authorization: Bearer <mcp_token>)
    ↓
MCP Server: extract Bearer token
    ↓
Call validate_mcp_token(raw_token)
    ↓
Backend: POST /api/internal/mcp/validate {token}
    ↓
Backend validates MCP token using Phase 2 service
    ↓
Backend returns: {user_id, username, department_name, backend_jwt}
    ↓
Store in AuthenticatedContext (request-scoped via ContextVar)
    ↓
Tool handlers access context
```

**Key Property**: Authentication happens **outside** tool input. Tool receives only `question`.

### ✅ Token Validation Flow

**Location**: `src/mcp_server/auth/token_service.py`

**Function**: `async def validate_token_with_backend(raw_token: str) -> MCPTokenResponse`

**Process**:
1. Check token not empty → `AuthenticationError` if missing
2. POST `/api/internal/mcp/validate {token}` to backend
3. Backend performs Phase 2 token validation
4. Backend loads User + Department from database
5. Backend creates short-lived backend JWT (1 hour)
6. Backend returns `MCPTokenResponse` with:
   - `user_id` (int)
   - `username` (str)
   - `department_name` (str)
   - `backend_jwt` (str, short-lived)
   - `expires_in` (int, 3600 seconds)
7. Raise `AuthenticationError` on 401 (invalid/expired/revoked)
8. Raise `BackendUnavailableError` on connection issues

**Error Handling**: All errors are wrapped as generic messages (no token details leaked).

### ✅ Backend Identity Bridge

**Location**: `backend/app/api/mcp_internal.py`

**Endpoint**: `POST /api/internal/mcp/validate`

**Flow**:
```
MCP Server
    │
    ├─ raw MCP token
    ├─ POST /api/internal/mcp/validate {token}
    │
    └─ Backend:
        1. Validate MCP token (Phase 2 service)
        2. Load User from database
        3. Verify User has department
        4. Call create_access_token(user.id) → backend JWT (1 hour)
        5. Return {user_id, username, department_name, backend_jwt, expires_in}
    │
    └─ MCP Server receives:
        - Authenticated user_id
        - Department (from database)
        - Short-lived backend JWT (1 hour)
```

**Security Properties**:
- Backend verifies MCP token is genuine (Phase 2 service)
- Backend loads User from database (authoritative)
- Department comes from User.department relationship (authoritative)
- Backend JWT is short-lived (1 hour)
- MCP server **must authenticate token BEFORE calling endpoint**
- Cannot bypass by calling endpoint without authentication

### ✅ ask_knowledge_base Implementation

**Location**: `src/mcp_server/tools/ask_tool.py`

**Function**: `async def ask_knowledge_base_impl(question: str, auth_context, backend_client) -> str`

**Input**: 
- `question` (string, 1-1000 chars)
- No `user_id`, `department_id`, `token`, or auth fields

**Process**:
1. Log tool invocation with `user_id`, `department`, `question_len`
2. Call `backend_client.ask_knowledge_base(question, backend_jwt)`
3. Backend returns `ChatResponse` with `answer` and `sources`
4. Format response:
   ```
   Answer: {backend answer}
   
   Sources:
   1. {document_name} ({department_name}) [p.{page_start}-{page_end}, score: {score}]
   ```
5. Return formatted string

**Backend Handling**:
- Backend receives question + JWT (user_id embedded in JWT)
- Backend decodes JWT → user_id
- Backend loads User → department
- Backend applies Qdrant ACL filtering
- Backend generates answer via Azure OpenAI
- Backend returns answer + sources

**Tool Registration** (in `__init__.py`):
```json
{
  "name": "ask_knowledge_base",
  "description": "Query the company's internal knowledge base...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "The question to ask about the knowledge base",
        "minLength": 1,
        "maxLength": 1000
      }
    },
    "required": ["question"]
  }
}
```

### ✅ Backend API Client

**Location**: `src/mcp_server/client/backend_api_client.py`

**Class**: `BackendAPIClient`

**Method**: `async def ask_knowledge_base(question: str, backend_jwt: str) -> ChatResponse`

**Request**:
```
POST http://localhost:8000/api/chat
Authorization: Bearer {backend_jwt}
Content-Type: application/json
{
  "question": "..."
}
```

**Response Types**:
- `ChatSource`: `{document_id, document_name, sensitivity, score?, page_start?, page_end?}`
- `ChatResponse`: `{answer, sources: ChatSource[]}`

**Error Handling**:
- 401: Backend JWT rejected → `BackendError`
- 403: Authorization denied → `BackendError`
- 500: Backend error → `BackendError`
- Timeout → `BackendTimeoutError`
- Connection error → `BackendUnavailableError`
- Invalid JSON → `BackendError`

### ✅ Local Startup Process

**Default**:
```bash
cd mcp-server
python run.py
```

**Startup Log**:
```
2026-09-02 XX:XX:XX - mcp_server - INFO - MCP Server Starting
2026-09-02 XX:XX:XX - mcp_server - INFO - Host: 0.0.0.0:5000
2026-09-02 XX:XX:XX - mcp_server - INFO - Backend: http://localhost:8000
2026-09-02 XX:XX:XX - mcp_server - INFO - Log Level: INFO
```

**Endpoint Ready**: `http://localhost:5000`

---

## Phase 4 Validation Steps

### STEP 1 — Verify MCP Tool Contract

**Objective**: Confirm tool input schema contains ONLY `question`, no auth fields.

**File**: `mcp-server/src/mcp_server/__init__.py` (lines ~58-75)

**Expected Tool Definition**:
```json
{
  "name": "ask_knowledge_base",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": {"type": "string", "minLength": 1, "maxLength": 1000}
    },
    "required": ["question"]
  }
}
```

**Forbidden Fields**: 
- ❌ `user_id`
- ❌ `token`
- ❌ `department_id`
- ❌ `department_name`
- ❌ `mcp_token`
- ❌ `password`

**Verification Method**:
1. Start MCP server: `python run.py`
2. Inspect server logs for tool registration
3. Verify tool definition in `__init__.py`

**Status**: ✅ VERIFIED

---

### STEP 2 — Verify MCP Tool Description

**Objective**: Confirm tool description clearly guides Claude when to use the tool.

**File**: `mcp-server/src/mcp_server/__init__.py` (lines ~65-69)

**Expected Description**:
```
"Query the company's internal knowledge base to answer questions about policies, 
procedures, documentation, and organizational knowledge. Use this tool when the user 
asks about company-specific information, internal guidelines, security procedures, 
HR policies, or technical documentation. This tool will only return information that 
you are authorized to access based on your department."
```

**Properties**:
- ✅ Clear use cases (policies, procedures, documentation)
- ✅ Guidance on when to invoke
- ✅ Disclaimer about authorization
- ✅ NOT claiming 100% tool invocation
- ✅ NOT making false guarantees

**Status**: ✅ VERIFIED

---

### STEP 3 — Verify MCP Response

**Objective**: Confirm MCP response preserves backend ChatResponse fields without inventing data.

**File**: `mcp-server/src/mcp_server/tools/ask_tool.py` (lines ~56-81)

**Expected Response Structure**:
```python
response = backend_client.ask_knowledge_base(question, backend_jwt)
# response is ChatResponse:
#   - answer: str
#   - sources: List[ChatSource]
#   - (optionally) retrieved_count, user_department_name

# Formatted as:
# "Answer: {answer}\n\nSources:\n1. {doc_name} ({dept}) [p.X-Y, score: Z]"
```

**Forbidden Additions**:
- ❌ `confidence_score` (unless backend provides)
- ❌ `relevance_percentage` (unless backend provides)
- ❌ `retrieval_latency` (unless backend provides)
- ❌ Raw chunks (unless backend provides)
- ❌ Internal metadata (unless backend provides)

**Status**: ✅ VERIFIED

---

### STEP 4 — Local End-to-End Flow

**Objective**: Test complete MCP flow WITHOUT Claude (local verification).

**Flow**:
```
1. Start MCP server
2. Simulate MCP client request
3. Validate MCP token
4. Get authenticated context
5. Call backend /api/chat
6. Receive answer + sources
7. Verify response format
```

**Verification Script**: `mcp-server/validate_phase3.py`

**Run**:
```bash
cd mcp-server
source venv/bin/activate
python validate_phase3.py
```

**Expected Output**:
```
✅ Configuration Loading: PASS
✅ MCP Server Creation: PASS
✅ Tool Registration: PASS
✅ Authentication Context: PASS
✅ Backend Client: PASS
✅ Module Imports: PASS
... (all tests PASS)
```

**Status**: 🔄 NEEDS TESTING (local environment setup required)

---

### STEP 5 — Test Multiple Users Manually

**Objective**: Verify different users get different authenticated contexts.

**Setup** (using Phase 2 tokens):
```bash
# Generate two MCP tokens in backend
python backend/scripts/mcp_token_manager.py create

# User A: admin (department: engineering)
# User B: user (department: sales)
```

**Test**:
```
User A Token → MCP Server
  ↓ validate_token_with_backend()
  ↓ user_id=1, dept=engineering
  ↓ context stored

User B Token → MCP Server
  ↓ validate_token_with_backend()
  ↓ user_id=2, dept=sales
  ↓ context stored (different from User A)
```

**Verification**:
- User A context != User B context
- No context leakage between requests
- Each user sees their own department

**Status**: 🔄 NEEDS TESTING

---

### STEP 6 — Verify ACL Isolation

**Objective**: Confirm MCP respects backend department-based ACL.

**Test Case**: Ask about department-specific document

**Example**:
```
Engineering User:
  Question: "What is the deployment process?"
  Expected: Returns engineering deployment docs (from Qdrant)

Sales User (same question):
  Expected: Backend Qdrant ACL filters → no unauthorized docs
  Result: Different answer or "not available" (backend behavior)
```

**Verification**:
- Engineering user gets engineering documents only
- Sales user gets sales documents only
- MCP does NOT filter (backend is responsible)

**Key Property**: Qdrant ACL is applied server-side by backend, not by MCP.

**Status**: 🔄 NEEDS TESTING

---

### STEP 7 — Verify No Identity Spoofing

**Objective**: Attempt to override user identity through tool arguments.

**Attack 1**: User tries to pass `user_id` in tool input
```json
{
  "question": "What is the HR policy?",
  "user_id": 2
}
```
**Expected**: Schema validation rejects (extra field) or MCP ignores.

**Attack 2**: User tries to pass `department` in tool input
```json
{
  "question": "What is the HR policy?",
  "department": "HR"
}
```
**Expected**: Schema validation rejects or MCP ignores.

**Result**: Tool uses ONLY authenticated context from MCP token, never from input.

**Status**: ✅ DESIGN VERIFIED

---

### STEP 8 — Connect to Claude

**Objective**: Configure Claude to use MCP server.

**Prerequisites**:
- MCP server running: `python run.py`
- MCP endpoint: `http://localhost:5000`
- Valid MCP token for testing user

**Claude Configuration** (varies by Claude client):

**Option A: Desktop Claude (if supports custom MCP)**:
1. Settings → MCP Servers
2. Add Custom MCP
3. Type: HTTP
4. URL: `http://localhost:5000`
5. Auth: Bearer token (MCP token)

**Option B: Claude API with MCP**:
```python
# Pseudocode (verify actual Claude API docs)
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=[
        # MCP tools auto-loaded from MCP server
    ],
    messages=[
        {"role": "user", "content": "What is our deployment process?"}
    ]
)
```

**Expected**: Claude lists `ask_knowledge_base` as available tool.

**Status**: 🔄 NEEDS TESTING (depends on Claude client capability)

---

### STEP 9 — Do Not Deploy Yet

**Decision**: Keep MCP server local for now.

**Reason**: Public deployment requires HTTPS, proper networking, and security hardening.

**Next Phase**: Phase 5 handles public HTTPS deployment.

**Status**: ✅ DEFERRED TO PHASE 5

---

### STEP 10 — Claude Invocation Test

**Objective**: Have Claude automatically invoke `ask_knowledge_base` for internal company question.

**Setup**: Claude connected to MCP server (from STEP 8).

**Test Question**:
```
User asks Claude: "What is the deployment process?"
```

**Expected**:
1. Claude recognizes question is about internal company knowledge
2. Claude invokes `ask_knowledge_base` tool with question
3. MCP server authenticates with MCP token
4. MCP calls backend → Qdrant → Azure OpenAI
5. Backend returns answer + sources
6. MCP formats response
7. Claude presents to user

**Key Behavior**:
- Claude **decides** to invoke the tool (model behavior)
- Do NOT modify MCP/backend just because Claude sometimes doesn't invoke for obvious questions
- Focus on making tool description clear

**Verification Logs**:
```
2026-09-02 XX:XX:XX - mcp_server - INFO - Tool invoked: ask_knowledge_base
2026-09-02 XX:XX:XX - mcp_server - INFO - Backend request: POST /api/chat
2026-09-02 XX:XX:XX - mcp_server - INFO - Backend response: 200 OK
```

**Status**: 🔄 NEEDS TESTING

---

### STEP 11 — Verify Rephrased Questions

**Objective**: Confirm MCP works with semantically equivalent questions.

**Test Cases**:
```
Question 1: "What is the deployment process?"
Question 2: "How do we deploy to production?"
Question 3: "Deployment steps?"
```

**Expected**:
- All three questions go through MCP → backend → RAG retrieval
- Backend Qdrant retrieval threshold: 0.4 (verified in existing RAG)
- Same sources retrieved for semantically equivalent questions
- Small variations in phrasing handled by backend RAG

**Verification**:
- Questions 1, 2, 3 return similar answers
- Sources are consistent
- MCP does NOT perform its own retrieval logic

**Status**: 🔄 NEEDS TESTING

---

### STEP 12 — Verify Source Attribution

**Objective**: Confirm sources are correctly passed from backend through MCP to Claude.

**Test**:
```
Backend returns:
{
  "answer": "...",
  "sources": [
    {
      "document_name": "Engineering Deployment Guide",
      "department_name": "engineering",
      "page_start": 1,
      "page_end": 5,
      "score": 0.87
    }
  ]
}

MCP formats as:
"Answer: ...

Sources:
1. Engineering Deployment Guide (engineering) [p.1-5, score: 0.87]"

Claude presents:
"... based on the Engineering Deployment Guide ..."
```

**Verification**:
- Document name preserved
- Department preserved
- Page numbers preserved
- Score preserved
- No sources invented

**Status**: ✅ DESIGN VERIFIED

---

### STEP 13 — Error Scenarios

**Objective**: Verify proper error handling for common failure cases.

#### 13A: Invalid MCP Token
**Input**: Malformed/invalid token
**Expected**: `AuthenticationError` → generic "authentication failed" message
**Verification**: No token details in error

#### 13B: Revoked MCP Token
**Input**: Valid token format but revoked in database
**Expected**: Backend `/api/internal/mcp/validate` returns 401
**Verification**: MCP converts to `AuthenticationError`

#### 13C: Expired MCP Token
**Input**: Token with past expiration date
**Expected**: Backend validation rejects → `AuthenticationError`
**Verification**: MCP handles gracefully

#### 13D: Backend Unavailable
**Input**: Backend service down
**Expected**: `BackendUnavailableError` → "service unavailable" message
**Verification**: No backend URL in error

#### 13E: Backend Timeout
**Input**: Backend /api/chat takes >30 seconds
**Expected**: `BackendTimeoutError` after timeout
**Verification**: MCP cancels request cleanly

#### 13F: Empty Retrieval
**Input**: Question with no relevant documents
**Expected**: Backend returns empty sources list
**Verification**: MCP forwards result (backend decides behavior)

#### 13G: Invalid Question
**Input**: Question with special characters, >1000 chars
**Expected**: Schema validation rejects or backend handles
**Verification**: No stack trace exposed

**Status**: 🔄 NEEDS TESTING

---

### STEP 14 — Concurrent User Safety

**Objective**: Verify no request cross-contamination under concurrent load.

**Test**:
```
Simulate 5 concurrent MCP requests:
  Request A (User 1, Token A, Question A)
  Request B (User 2, Token B, Question B)
  Request C (User 1, Token A, Question C)
  Request D (User 3, Token C, Question D)
  Request E (User 2, Token B, Question E)
```

**Verification** (via logs):
- Each request maintains separate auth context
- No auth context bleed between requests
- Each user sees correct identity
- Responses properly mapped to users

**Implementation Detail**: `auth_context: ContextVar` (Python contextvars)

**Status**: ✅ DESIGN VERIFIED

---

### STEP 15 — Logging Review

**Objective**: Verify logs contain no sensitive information.

**Safe Logs** (example):
```
2026-09-02 15:44:05 - mcp_server - INFO - Tool invoked: ask_knowledge_base | user_id=1 | dept=engineering | question_len=32
2026-09-02 15:44:06 - mcp_server - INFO - Backend request: POST /api/chat
2026-09-02 15:44:07 - mcp_server - INFO - Backend response: 200 OK | sources=3
```

**Forbidden in Logs** (❌):
- Raw MCP token: `token=mcp_abc123...`
- Authorization header: `Authorization: Bearer eyJ...`
- Backend JWT: `backend_jwt=eyJ...`
- Passwords: `password=...`
- Azure API key: `api_key=...`
- Database password: `db_password=...`
- Full question (if sensitive): Log length only

**Status**: 🔄 NEEDS TESTING (inspect actual logs)

---

### STEP 16 — Existing Application Regression Check

**Objective**: Confirm MCP integration did NOT break existing React/backend.

**Test Existing Flow**:
```
React Frontend
  ↓
POST /api/auth/login {username, password}
  ↓
Backend returns JWT
  ↓
React stores JWT
  ↓
POST /api/chat {question} + Authorization header
  ↓
Backend returns answer + sources
  ↓
React displays answer
```

**Verification**:
- React login still works
- Existing /api/chat still works
- JWT authentication unchanged
- Department ACL still works
- No database schema changes

**Independence**:
- MCP flow: Claude → MCP token → MCP server → Backend
- React flow: React → Backend JWT → Backend
- Both flows work independently and simultaneously

**Status**: 🔄 NEEDS TESTING

---

### STEP 17 — MCP Tool Minimalism

**Objective**: Confirm only `ask_knowledge_base` is implemented.

**Expected Tools**:
- ✅ `ask_knowledge_base` (only tool)

**Forbidden Tools** (not implemented):
- ❌ `list_documents`
- ❌ `search_documents`
- ❌ `get_document`
- ❌ `retrieve_chunks`
- ❌ `get_user_info`
- ❌ `get_department_info`

**Reason**: Keep integration minimal. Expand tools in later phases if needed.

**Status**: ✅ VERIFIED

---

### STEP 18 — Documentation

**Objective**: Comprehensive README for MCP server.

**File**: `mcp-server/README.md`

**Required Sections**:
1. ✅ What the MCP server does
2. ✅ Architecture diagram
3. ✅ Local setup instructions
4. ✅ Environment variables (.env.example)
5. ✅ How MCP authentication works
6. ✅ How MCP token maps to user
7. ✅ How MCP calls backend
8. ✅ Available tools (ask_knowledge_base)
9. ✅ Example tool input
10. ✅ Example tool output
11. ✅ Security model
12. ✅ Local verification steps
13. ✅ Claude connection prerequisites

**Status**: 🔄 NEEDS CREATION

---

### STEP 19 — Final Security Checklist

**Objective**: Explicit verification of all security properties.

**Checklist**:

```
Authentication:
  ☐ MCP token is never exposed to Claude as tool argument
  ☐ MCP token is never logged
  ☐ User identity comes from authenticated MCP credential
  ☐ user_id cannot be spoofed through tool input
  ☐ department cannot be spoofed through tool input

Backend Isolation:
  ☐ MCP does not access Qdrant directly
  ☐ MCP does not access Azure OpenAI directly
  ☐ MCP does not bypass backend ACL
  ☐ MCP does not store passwords
  ☐ MCP does not use long-lived backend JWTs

Authorization:
  ☐ Backend identity bridge is protected (internal only)
  ☐ Backend remains source of truth for ACL
  ☐ Department filtering via Qdrant (server-side)
  ☐ User isolation via request scoping

Application Integrity:
  ☐ Existing React authentication still works
  ☐ Multiple MCP users remain isolated
  ☐ No global current-user state
  ☐ Request context is properly scoped

Error Handling:
  ☐ Error messages do not leak secrets
  ☐ Error messages do not expose backend URLs
  ☐ Error messages do not expose infrastructure details
  ☐ Stack traces logged server-side only

Compliance:
  ☐ MCP design follows Phase 1 specification
  ☐ Backend integration follows Phase 2 specification
  ☐ MCP server implements Phase 3 specification
```

**Status**: 🔄 VERIFICATION REQUIRED

---

## Phase 4 Manual Testing Plan

### Prerequisites
- Backend running: `python -m uvicorn app.main:app --reload` (port 8000)
- MCP server running: `cd mcp-server && python run.py` (port 5000)
- Valid MCP token(s) from Phase 2
- Test users in database with different departments

### Test Sequence

**1. Start Services**
```bash
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: MCP Server
cd mcp-server
python run.py
```

**2. Verify Configuration**
```bash
# MCP server logs should show:
MCP Server Starting
Host: 0.0.0.0:5000
Backend: http://localhost:8000
```

**3. Test Tool Registration** (STEP 1-3)
- MCP server exposes `ask_knowledge_base` tool
- Input schema has only `question` field
- Tool description is clear

**4. Test Local Flow** (STEP 4)
- Run `python mcp-server/validate_phase3.py`
- All tests should pass

**5. Test Multiple Users** (STEP 5-6)
- Create 2 MCP tokens for different users
- Simulate requests with each token
- Verify different authenticated contexts
- Verify ACL isolation

**6. Test Error Scenarios** (STEP 13)
- Send invalid token
- Send expired token
- Simulate backend down
- Simulate timeout
- Inspect error messages

**7. Test Concurrent Requests** (STEP 14)
- Send 5 concurrent requests
- Verify no cross-contamination

**8. Inspect Logs** (STEP 15)
- Capture logs during tests
- Verify no secrets leaked
- Verify proper user identification

**9. Test Existing Backend** (STEP 16)
- React login still works
- Existing /api/chat still works

**10. Connect Claude** (STEP 8-12)
- Configure Claude to use MCP
- Ask Claude internal question
- Verify tool invocation
- Test rephrased questions

---

## Phase 4 Exit Criteria

✅ **ALL** of the following must be **explicitly verified**:

1. ✅ MCP tool contract correct (STEP 1)
2. ✅ Tool description clear (STEP 2)
3. ✅ Response format correct (STEP 3)
4. ✅ Local end-to-end flow works (STEP 4)
5. ✅ Multiple users isolated (STEP 5-6)
6. ✅ ACL properly enforced (STEP 6)
7. ✅ No identity spoofing possible (STEP 7)
8. ✅ Claude connects successfully (STEP 8)
9. ✅ Claude invokes tool for internal questions (STEP 10)
10. ✅ Rephrased questions work (STEP 11)
11. ✅ Source attribution preserved (STEP 12)
12. ✅ Error scenarios handled (STEP 13)
13. ✅ Concurrent requests safe (STEP 14)
14. ✅ Logging is secure (STEP 15)
15. ✅ Existing app not broken (STEP 16)
16. ✅ Tool minimalism maintained (STEP 17)
17. ✅ Documentation complete (STEP 18)
18. ✅ Security checklist passed (STEP 19)
19. ✅ No production deployment yet (STEP 9)

---

## Next Steps

1. **Verify Phase 3 Implementation** (this report)
2. **Run Manual Tests** (STEP 4-19)
3. **Document Results** (Phase 4 Final Report)
4. **Move to Phase 5** (Public HTTPS Deployment) only after all criteria met
