# 🚀 MCP Integration: Complete End-to-End Flow Guide

**This is your ONE reference file for understanding how MCP works in SecureRAG**

---

## 📖 Table of Contents
1. [Quick Glossary - Simplified Terms](#quick-glossary)
2. [The Big Picture - What Happens](#the-big-picture)
3. [End-to-End Flow with Real Examples](#end-to-end-flow)
4. [Step-by-Step Breakdown](#step-by-step-breakdown)
5. [Code Location Reference](#code-locations)
6. [Request/Response Bodies Explained](#requestresponse-explained)
7. [Why Each Step Exists](#why-each-step)
8. [Error Scenarios](#error-scenarios)

---

## 📚 Quick Glossary - Simplified Terms

### What is a "Request"?
A **request** is a message asking for something. Think of it like sending an email asking a question.

**Example:** "What is the deployment process?"

### What is a "Response"?
A **response** is the answer back to your request. Like receiving a reply email.

**Example:** Response with the deployment steps + document sources.

### What is a "Token"?
A **token** is a special password-like code that proves who you are. It never expires (lives for 365 days).

**Example:** `mcp_xxxxxxxxxxxxx` (this token says "I am user Alice from Engineering dept")

### What is "JWT" (Backend Token)?
A **short-lived token** that the backend gives you after verifying your MCP token. It only lasts 1 hour.

- MCP Token = Long-lived identity proof (365 days)
- JWT = Short-lived access pass for backend (1 hour)

### What is "Authorization Header"?
A special instruction in the message that says "use this token to verify who I am."

**Example:** `Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...`

### What is "ACL" (Access Control List)?
Rules that decide what data you can see based on your department.

**Example:** Alice from Engineering can see Engineering docs, NOT HR docs.

### What is "Qdrant"?
Database that stores document embeddings (smart summaries). It returns relevant documents based on semantic search.

**Example:** Search for "deployment" → Returns Engineering deployment guide + Security checklist.

---

## 🎯 The Big Picture - What Happens

```
USER IN CLAUDE:
"How does deployment work?"
        ↓
CLAUDE CALLS MCP TOOL:
"ask_knowledge_base(question)"
        ↓
MCP SERVER RECEIVES REQUEST:
Validates that you are a real user
        ↓
MCP SERVER GETS AUTHORIZATION FROM BACKEND:
Asks backend "Is this user real? What department?"
        ↓
BACKEND RESPONDS WITH JWT:
"Yes, this is Alice from Engineering dept. Here's JWT."
        ↓
MCP SERVER DELEGATES TO BACKEND:
Sends question + JWT to backend /api/chat endpoint
(MCP doesn't query Qdrant directly!)
        ↓
BACKEND QUERIES QDRANT:
"Search for 'deployment' documents"
        ↓
BACKEND FILTERS BY ACL:
"Remove HR docs - Alice can only see Engineering docs"
        ↓
BACKEND RETURNS ANSWER + SOURCES:
"Deployment involves 3 stages... Sources: [docs]"
        ↓
MCP SERVER FORMATS FOR CLAUDE:
Converts backend response to Claude-friendly format
        ↓
CLAUDE RECEIVES RESPONSE:
Shows answer to user with sources cited
```

**⚠️ IMPORTANT: MCP Server is a PROXY, not a processor!**
- ❌ MCP server does NOT query Qdrant
- ❌ MCP server does NOT filter by ACL
- ❌ MCP server does NOT have database access
- ✅ MCP server ONLY validates tokens and delegates to backend

---

## � KEY INSIGHT: MCP Server is a Proxy, Not a Processor

### What MCP Server Actually Does:
```
Claude → [MCP Server validates token] → [Delegates to Backend] → Backend → Qdrant
```

### What MCP Server Does NOT Do:
| Task | Who Really Does It | Why |
|------|------------------|-----|
| Query Qdrant | Backend only | MCP has no database/Qdrant access |
| Filter by ACL | Backend only | Backend owns the security rules |
| Generate answer | Backend only | MCP is not an LLM |
| Access documents | Backend only | Documents stored in backend |
| Validate JWT | Backend only | MCP just passes it through |

### Why is MCP Designed This Way?

**Security:**
- If Qdrant credentials leaked on MCP, only Qdrant is compromised
- Backend stays secure and controls all ACLs
- Separation of concerns = smaller attack surface

**Simplicity:**
- MCP only needs to know: tokens + HTTP
- MCP doesn't need: database knowledge, Qdrant API, ACL rules
- Easy to scale: multiple MCP servers → same backend

**Flexibility:**
- Can change Qdrant without touching MCP
- Can change ACL rules without deploying MCP
- Can swap backends without MCP knowing

### Real File Architecture

```
┌─────────────────────────────────────────┐
│ MCP SERVER (mcp-server/)                │
│ ├─ Token validation only                │
│ │  └─ File: auth/token_service.py      │
│ ├─ HTTP client to backend               │
│ │  └─ File: client/backend_api_client.py │
│ ├─ Response formatting                  │
│ │  └─ File: tools/ask_tool.py           │
│ └─ NO database code                     │
│    NO Qdrant code                       │
│    NO ACL filtering code                │
└─────────────────────────────────────────┘
                  ↓ (HTTP calls to)
┌─────────────────────────────────────────┐
│ BACKEND (backend/app/)                  │
│ ├─ Token endpoint                       │
│ │  └─ File: api/mcp_internal.py         │
│ ├─ Chat endpoint (searches + filters)   │
│ │  └─ File: api/chat.py                 │
│ ├─ Qdrant queries                       │
│ │  └─ File: services/qdrant_service.py  │
│ ├─ ACL filtering                        │
│ │  └─ File: services/retrieval_service.py │
│ └─ All security logic here              │
└─────────────────────────────────────────┘
```

---

### SCENARIO: User Alice (Engineering) asks "What is the deployment process?"

---

### 🔵 PHASE 1: User Asks Claude

**User Types in Claude:**
```
"What is the deployment process?"
```

**Claude's Brain:**
> "The user is asking about deployment. I have a tool called `ask_knowledge_base` 
> that can search the company's internal documents. I should use that tool."

**Where it happens:** This is in Claude's system - nothing on our end yet.

---

### 🔵 PHASE 2: Claude Calls the MCP Tool

**Claude's Request to MCP Server:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "ask_knowledge_base",
    "arguments": {
      "question": "What is the deployment process?"
    }
  }
}
```

**What this means:**
- `jsonrpc: 2.0` → Standard protocol version (like saying "I speak English")
- `id: 1` → Unique ID so we know which response goes with which request
- `name: "ask_knowledge_base"` → Claude is calling OUR tool
- `arguments.question` → The actual question to search for

**Where it happens:**
- File: **[mcp-server/src/mcp_server/tools/ask_tool.py](../src/mcp_server/tools/ask_tool.py)**
- Function: `handle_tool_call()`

**Why this step:**
✅ Claude needs to know which tools are available
✅ Claude needs to pass the user's question to our backend
✅ Standard format ensures Claude and our server understand each other

---

### 🔵 PHASE 3: MCP Server Receives the Request

**What happens in MCP Server:**

The MCP server receives Claude's request. But wait - how does MCP know WHO the user is? 

Claude doesn't send a username or password. That's the genius of MCP!

**The MCP Token comes into play here:**

In Claude's settings, the MCP server URL is configured with the token:
```
https://secure-rag-mcp-server.com?token=mcp_alice_engineering_xyz123
```

**Or in the Authorization Header:**
```
Authorization: Bearer mcp_alice_engineering_xyz123
```

**Where it happens:**
- File: **[mcp-server/src/mcp_server/main.py](../src/mcp_server/main.py)** → `_call_tool()` function
- File: **[mcp-server/src/mcp_server/auth/token_service.py](../src/mcp_server/auth/token_service.py)** → Validation logic

**Flow:**
```
MCP Server Receives Request
    ↓
Extract MCP Token from headers/URL
    ↓
File: token_service.py
Function: validate_mcp_token(token)
    ↓
Parse token: "mcp_alice_engineering_xyz123"
    ↓
Create AuthenticatedContext:
{
  "user_id": 1,
  "username": "alice",
  "department_name": "engineering"
}
```

**Why this step:**
✅ Proves the user is authorized
✅ We know their department for ACL filtering
✅ We log all queries with their identity (audit trail)

---

### 🔵 PHASE 4: MCP Server Gets Authorization from Backend

**MCP Server's Internal Decision:**
> "I have Alice's MCP token. But I need a SHORT-LIVED access token to query the backend.
> Why? For extra security - if the token leaks, it only works for 1 hour."

**MCP Server Calls Backend:**

```json
POST http://localhost:8000/api/internal/mcp/validate

Request Body:
{
  "token": "mcp_alice_engineering_xyz123"
}

Response Body:
{
  "user_id": 1,
  "username": "alice",
  "department_name": "engineering",
  "backend_jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_in": 3600
}
```

**What this means:**
- Request sends: MCP token
- Response gives: 
  - User info (who are you?)
  - JWT (short-lived access token)
  - Expiration time (expires in 3600 seconds = 1 hour)

**Where it happens:**
- File: **[mcp-server/src/mcp_server/client/backend_api_client.py](../src/mcp_server/client/backend_api_client.py)**
- Function: `validate_mcp_token(token)`

- File: **[backend/app/api/mcp_internal.py](../../backend/app/api/mcp_internal.py)** ← Backend receives it
- Function: `validate_mcp_token()` endpoint

**Why this step:**
✅ Backend verifies MCP token is real (in database)
✅ Backend checks token hasn't expired
✅ Backend creates short-lived JWT for this query
✅ If MCP token is fake/expired → Response is 403 Forbidden (access denied)

---

### 🔵 PHASE 5: MCP Server Queries the Knowledge Base

**WAIT - MCP Server Does NOT Query Qdrant Directly!**

MCP sends the question + JWT to the backend. The backend does ALL the real work:

**MCP Server's Job:**
```
1. Have JWT from Phase 4
2. Send question to backend endpoint
3. Wait for response
4. Pass response to Claude
```

**Backend's Job (the real work):**
```
1. Receive question + JWT
2. Validate JWT
3. Extract user_id, department from JWT
4. Search Qdrant for matching documents
5. Apply ACL filters (remove docs user can't see)
6. Format and return results
```

```json
POST http://localhost:8000/api/chat

Headers:
{
  "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

Request Body:
{
  "question": "What is the deployment process?"
}

Response Body:
{
  "answer": "The deployment process involves three stages...",
  "sources": [
    {
      "document_id": "doc_1",
      "filename": "Engineering_Deployment_Guide.pdf",
      "department": "engineering",
      "page_range": "1-5",
      "score": 0.87,
      "snippet": "Stage 1: Pre-deployment validation...",
      "content": "Full document text..."
    },
    {
      "document_id": "doc_2", 
      "filename": "Security_Deployment_Checklist.pdf",
      "department": "security",
      "page_range": "12-14",
      "score": 0.75,
      "snippet": "Security validation steps...",
      "content": "Full document text..."
    }
  ]
}
```

**What's happening step-by-step:**

1. MCP sends JWT in Authorization header (proves Alice can access backend)
2. Backend receives request
3. Backend extracts JWT → validates it → gets user_id = 1 (Alice)
4. Backend retrieves Alice's department = "engineering"
5. Backend searches Qdrant for documents matching "deployment"
6. Qdrant returns: 5 matching documents
7. Backend filters by ACL:
   - Alice is from engineering → Keep engineering docs
   - Alice is from engineering → Remove HR docs, Sales docs
   - Keep security docs (security-sensitive info everyone needs)
8. Backend returns filtered results

**Where it happens:**

MCP Side:
- File: **[mcp-server/src/mcp_server/client/backend_api_client.py](../src/mcp_server/client/backend_api_client.py)**
- Function: `ask_knowledge_base(question, jwt)`

Backend Side:
- File: **[backend/app/api/chat.py](../../backend/app/api/chat.py)**
- Function: `chat()` endpoint
- Calls: **[backend/app/services/retrieval_service.py](../../backend/app/services/retrieval_service.py)**
  - Function: `retrieve_relevant_documents()`
  - This queries Qdrant
  - Applies ACL filtering based on user's department

Qdrant Side:
- File: **[backend/app/services/qdrant_service.py](../../backend/app/services/qdrant_service.py)**
- Function: `search()`
- Direct connection to Qdrant Cloud (vector database)

**Why this step:**
✅ Frontend doesn't have direct database access
✅ Backend controls what data is returned (security)
✅ Backend applies department-based filtering
✅ JWT proves user is authorized
✅ If JWT expired → Backend returns 403 Forbidden

---

### 🔵 PHASE 6: MCP Server Formats Response

**MCP receives documents from backend. Now it needs to format them for Claude.**

```json
{
  "answer": "The deployment process in our organization involves three main stages:\n\n1. Pre-deployment Validation...",
  "sources": [
    {
      "title": "Engineering Deployment Guide",
      "pages": "1-5",
      "relevance": "0.87"
    },
    {
      "title": "Security Deployment Checklist", 
      "pages": "12-14",
      "relevance": "0.75"
    }
  ]
}
```

**Where it happens:**
- File: **[mcp-server/src/mcp_server/tools/ask_tool.py](../src/mcp_server/tools/ask_tool.py)**
- Function: `_format_response()`

**Why this step:**
✅ Claude needs information in a specific format it understands
✅ Pretty-print the answer so it reads well
✅ Include source citations so user can verify information
✅ Include relevance scores so Claude knows which sources are most reliable

---

### 🔵 PHASE 7: Claude Receives Response & Shows to User

**Claude's Response to User:**

```
The deployment process in our organization involves three stages:

Stage 1: Pre-deployment validation
- Code review
- Security scan
- Performance testing

Stage 2: Staging deployment
- Deploy to staging environment
- Run integration tests
- Load testing

Stage 3: Production deployment
- Blue-green deployment strategy
- Gradual rollout
- Monitoring and alerts

Sources:
📄 Engineering Deployment Guide (p.1-5) - Relevance: 87%
📄 Security Deployment Checklist (p.12-14) - Relevance: 75%
```

**Where it happens:** Claude's frontend → shows to user

**Why this step:**
✅ User gets cited, trustworthy answer
✅ User can verify by looking at source documents
✅ Transparent - clear where information came from

---

## 🛠️ Step-by-Step Breakdown

### Step 1: User Question
```
Input: "What is the deployment process?"
Time: Instant
Type: Synchronous (immediate response)
Handled By: Claude's reasoning engine
```

### Step 2: Claude Recognizes Need for Tool
```
Input: User question in context
Output: Decision to call ask_knowledge_base tool
Time: <100ms
Handled By: Claude's tool selection logic
```

### Step 3: Claude Calls MCP Tool
```
Input: {"question": "What is the deployment process?"}
Output: JSON-RPC request to MCP server
Time: ~10ms
Protocol: JSON-RPC 2.0 over HTTP
Handled By: Claude SDK → [mcp-server/src/mcp_server/main.py]
```

### Step 4: MCP Validates User
```
Input: MCP token from Authorization header
Process: Validate token structure and format
Output: AuthenticatedContext(user_id=1, dept="engineering")
Time: ~5ms
Handled By: [mcp-server/src/mcp_server/auth/token_service.py]
```

### Step 5: MCP Gets Backend Authorization
```
Input: MCP token
Process: POST to backend /api/internal/mcp/validate
Output: JWT token + user info
Time: ~50ms (network round trip)
Handled By: [backend/app/api/mcp_internal.py]

⚠️ This is where MCP gets the JWT to use in next step
```

### Step 6: MCP Delegates to Backend (MCP does NOT query Qdrant!)
```
Input: Question + JWT
Process: POST to backend /api/chat
         Backend searches Qdrant
         Backend filters by ACL
         Backend returns answer + sources
Output: Answer + source documents
Time: ~200-500ms (mainly waiting for Qdrant)
Handled By: 
  - MCP: [mcp-server/src/mcp_server/client/backend_api_client.py]
  - Backend: [backend/app/services/retrieval_service.py]
  - Qdrant: [backend/app/services/qdrant_service.py]

✅ MCP ONLY sends the HTTP request
✅ Backend does ALL the real work
```

### Step 7: MCP Formats Response
```
Input: Documents from backend
Process: Convert to readable format
Output: Answer + sources list
Time: ~10ms
Handled By: [mcp-server/src/mcp_server/tools/ask_tool.py]
```

### Step 8: Claude Shows Response to User
```
Input: Formatted response from MCP
Output: Beautiful response with citations
Time: Instant (displayed to user)
Handled By: Claude frontend
```

**Total Time: ~300-600ms** (less than 1 second!)

---

## 📁 Code Locations Reference

### MCP Server Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `mcp-server/src/mcp_server/main.py` | Entry point, handles tool calls | `_call_tool()`, `initialize()` |
| `mcp-server/src/mcp_server/auth/token_service.py` | Validates MCP tokens | `validate_mcp_token()` |
| `mcp-server/src/mcp_server/client/backend_api_client.py` | HTTP client to backend | `ask_knowledge_base()`, `validate_mcp_token()` |
| `mcp-server/src/mcp_server/tools/ask_tool.py` | The actual tool implementation | `handle_tool_call()`, `_format_response()` |

### Backend Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `backend/app/api/mcp_internal.py` | MCP-specific endpoints | `validate_mcp_token()` |
| `backend/app/api/chat.py` | Chat/retrieval endpoint | `chat()` |
| `backend/app/services/retrieval_service.py` | Document retrieval logic | `retrieve_relevant_documents()` |
| `backend/app/services/qdrant_service.py` | Vector database interactions | `search()`, `ensure_collection()` |
| `backend/app/dependencies/auth.py` | JWT validation | `get_current_user_from_jwt()` |
| `backend/app/db/session.py` | Database connection | `SessionLocal()` |

### Configuration Files

| File | Purpose |
|------|---------|
| `mcp-server/.env` | Environment variables (backend URL, timeouts) |
| `backend/.env` | Database, Qdrant URL, secrets |
| `mcp-server/run.py` | MCP server startup script |
| `backend/app/main.py` | Backend FastAPI app setup |

---

## 📤 Request/Response Explained

### Request Body: Why Do We Send This?

#### Example 1: Claude Calls Tool
```json
{
  "jsonrpc": "2.0",      // ← Protocol version (mandatory for MCP)
  "id": 1,               // ← Request ID (so response matches request)
  "method": "tools/call", // ← We're calling a tool
  "params": {
    "name": "ask_knowledge_base",  // ← Which tool to call
    "arguments": {
      "question": "What is the deployment process?"  // ← The question
    }
  }
}
```

**Why each field:**
- `jsonrpc`: Tells server we're using JSON-RPC protocol (standard)
- `id`: If we send 10 requests in parallel, response ID tells us which is which
- `method`: Specifies the operation (tool calling in this case)
- `name`: Which tool (could have multiple tools like "ask_knowledge_base", "search_docs", etc)
- `arguments`: The actual data (the question)

#### Example 2: MCP Validates User
```json
{
  "token": "mcp_alice_engineering_xyz123"
}
```

**Why:**
- Backend needs to verify this token is real
- Token contains encoded user info
- Backend looks up token in database

#### Example 3: Backend Query for Documents
```json
{
  "question": "What is the deployment process?"
}
```

**Why:**
- Backend needs to search Qdrant
- Question is converted to embeddings
- Embeddings match against document embeddings in Qdrant

---

### Response Body: Why We Return This?

#### Example 1: Tool Call Response
```json
{
  "jsonrpc": "2.0",      // ← Matches protocol
  "id": 1,               // ← Matches request ID
  "result": {            // ← The answer!
    "answer": "The deployment process involves three stages...",
    "sources": [
      {
        "filename": "Engineering_Deployment_Guide.pdf",
        "pages": "1-5",
        "relevance": 0.87
      }
    ]
  }
}
```

**Why each field:**
- `jsonrpc/id`: Matches the request (so Claude knows which response goes with which request)
- `result`: Contains the actual answer
- `answer`: Formatted, readable text for Claude to show user
- `sources`: Proof of where the answer came from

#### Example 2: Token Validation Response
```json
{
  "user_id": 1,
  "username": "alice",
  "department_name": "engineering",
  "backend_jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_in": 3600
}
```

**Why each field:**
- `user_id`: Backend knows who this is
- `username`: For logging/audit trails
- `department_name`: For ACL filtering (only show engineering docs)
- `backend_jwt`: Short-lived token for next 1 hour
- `expires_in`: Token expires in 3600 seconds

#### Example 3: Document Search Response
```json
{
  "answer": "The deployment process...",
  "sources": [
    {
      "document_id": "doc_1",
      "filename": "Engineering_Deployment_Guide.pdf",
      "department": "engineering",
      "score": 0.87,
      "content": "Stage 1: Pre-deployment validation..."
    }
  ]
}
```

**Why each field:**
- `answer`: LLM-generated summary
- `sources`: Original documents for verification
- `document_id`: Unique reference
- `department`: Proves it passed ACL check
- `score`: 0-1, how relevant this document is (0.87 = very relevant)
- `content`: The actual text to cite

---

## 🤔 Why Each Step Exists

### Step 1: User Asks Claude
**Why?** User is the source of questions. Claude is the interface.

### Step 2: Claude Recognizes Tool Need
**Why?** Claude is smart enough to know when to use tools vs. answer from its own training.

### Step 3: Claude Calls MCP Tool
**Why?** MCP is the bridge between Claude and our backend. Without it, Claude can't access our documents.

### Step 4: MCP Validates User Token
**Why?** Security! We need to prove this user is real before giving them access to documents.

**Real Example:**
- Fake request tries to use a random token: `fake_token_xyz`
- MCP validates → Token not in database → Response: "401 Unauthorized"
- Real request uses: `mcp_alice_engineering_xyz123`
- MCP validates → Token found and valid → Continues

### Step 5: MCP Gets Backend JWT
**Why?** Two levels of security:
- MCP token proves "I'm a user in the system"
- JWT proves "I'm authorized RIGHT NOW to make backend requests"

**Real Example:**
- Alice gets MCP token (valid for 365 days)
- Alice is using Claude today
- MCP gets JWT (valid for 1 hour)
- Alice uses Claude 2 hours later
- MCP gets NEW JWT (previous one expired)
- This allows revoking access without changing the long-lived token

### Step 6: Backend Searches Knowledge Base
**Why?** 
- Backend has database access
- Backend knows which documents belong to which department
- Backend applies security filters

**Real Example:**
```
Question: "What is the HR policy for leave?"

Search Result (5 documents found):
1. ✅ HR_Leave_Policy.pdf (dept: hr) → SHOW (public)
2. ✅ Company_Leave_Guidelines.pdf (dept: general) → SHOW (everyone can see)
3. ❌ HR_Employee_Salary_Bands.pdf (dept: hr, sensitive) → HIDE (only HR staff)

Alice from Engineering sees: Documents 1 & 2 only
Bob from HR sees: All 3 documents
```

### Step 7: MCP Formats Response
**Why?** Claude needs a specific format it understands. We make the response pretty and include citations.

### Step 8: Claude Shows to User
**Why?** User gets a conversational, readable answer with sources they can verify.

---

## ❌ Error Scenarios

### Scenario 1: Invalid MCP Token

```
User in Claude: "What is the deployment process?"
    ↓
Claude calls MCP
    ↓
MCP extracts token: "invalid_fake_token"
    ↓
MCP calls backend: POST /api/internal/mcp/validate
    ↓
Backend checks database: Token not found
    ↓
Backend Response: 
{
  "error": "Invalid MCP token",
  "status": 401
}
    ↓
Claude shows to user:
"Error: Could not authenticate with knowledge base. 
Please verify your MCP token configuration."
```

**File handling this:** `backend/app/api/mcp_internal.py` → `validate_mcp_token()`

**HTTP Status:** 401 Unauthorized

---

### Scenario 2: Expired JWT Token

```
MCP gets JWT (expires in 1 hour)
User queries at 59 minutes ✅
User queries at 61 minutes ❌

Second query:
    ↓
MCP sends old JWT: "eyJ0eXAi...OjE1ODA5NDU0NDB9"
    ↓
Backend validates JWT → Token expired
    ↓
Backend Response:
{
  "error": "Token expired",
  "status": 403
}
    ↓
MCP retries:
- Gets new JWT from backend
- Retries request with new JWT
    ↓
Query succeeds ✅
```

**File handling this:** `backend/app/dependencies/auth.py` → JWT validation

**HTTP Status:** 403 Forbidden (but MCP handles retry automatically)

---

### Scenario 3: User from Wrong Department

```
Question: "What is the HR salary band policy?"

Qdrant finds: HR_Salary_Policy.pdf (dept: "hr", sensitive)

Backend check:
- User: alice (dept: "engineering")
- Document: (dept: "hr", security_level: "sensitive")
- Result: NO ACL match
    ↓
Backend Response:
{
  "answer": "I don't have information about salary policies.",
  "sources": []
}
    ↓
Claude shows:
"I couldn't find information about HR salary policies in the available documents.
You may not have access to that information."
```

**File handling this:** `backend/app/services/retrieval_service.py` → ACL filtering

**HTTP Status:** 200 OK (but results are filtered)

---

### Scenario 4: Qdrant Connection Timeout

```
Backend tries to search Qdrant
    ↓
Qdrant takes > 30 seconds to respond (slow cloud)
    ↓
MCP client timeout triggers (30s configured)
    ↓
Backend returns error:
{
  "error": "Knowledge base search timed out",
  "status": 500
}
    ↓
Claude shows:
"I tried to search the knowledge base but it's temporarily unavailable.
Please try again in a moment."
```

**File handling this:** `backend/app/services/qdrant_service.py` → `client_timeout: 30`

**HTTP Status:** 503 Service Unavailable

**Solution:** Retry after 5 seconds

---

## 🔐 Security Layers Explained

### Layer 1: MCP Token Validation
```
Is this token real? Is it in our database?
```
- File: `backend/app/api/mcp_internal.py`
- If fails: 401 Unauthorized

### Layer 2: JWT Authentication
```
Does this user have permission RIGHT NOW?
Has the token expired?
```
- File: `backend/app/dependencies/auth.py`
- If fails: 403 Forbidden

### Layer 3: ACL Filtering
```
Can this user see this document?
Does their department have access?
```
- File: `backend/app/services/retrieval_service.py`
- If fails: Document is silently removed from results

### Layer 4: Qdrant ACL
```
Final check in vector database itself.
Documents are tagged with department.
```
- File: `backend/app/services/qdrant_service.py`
- Defense in depth - catches misconfigurations

---

## 📊 Performance Metrics

| Step | Time | Bottleneck | Optimization |
|------|------|-----------|---------------|
| Token validation | ~5ms | Token lookup | Cached in memory |
| JWT request | ~50ms | Network latency | Connection pooling |
| Qdrant search | ~200-500ms | Vector similarity | Qdrant Cloud indexing |
| Response formatting | ~10ms | String processing | None needed (fast) |
| **Total** | **~300-600ms** | Qdrant | Using Qdrant Cloud with 30s timeout |

---

## 🚀 Complete Flow Diagram

**Key: MCP is a PROXY (thin layer), Backend does the real work**

```
┌─────────────────────────────────────────────────────────────────┐
│ CLAUDE (in Claude app)                                           │
│ User: "What is the deployment process?"                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Claude detects tool need
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ MCP CLIENT (in Claude SDK)                                       │
│ ├─ Prepares tool call request                                    │
│ ├─ Includes authorization header with MCP token                 │
│ └─ Sends JSON-RPC request to MCP server                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP POST to mcp.secure-rag.com
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ MCP SERVER (THIN PROXY LAYER)                                    │
│ File: main.py, tools/ask_tool.py                                │
│ ├─ Receives JSON-RPC request                                     │
│ ├─ Extracts MCP token from Authorization header                 │
│ ├─ Validates token → Gets user_id, department                   │
│ └─ Creates AuthenticatedContext                                 │
│                                                                  │
│ ⚠️ MCP DOES NOT HAVE:                                             │
│    - Qdrant access                                               │
│    - ACL filtering logic                                         │
│    - Document database                                           │
│    - Answer generation                                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Call backend validate endpoint
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ BACKEND (WORKER LAYER)                                           │
│ File: app/api/mcp_internal.py                                    │
│ ├─ POST /api/internal/mcp/validate                              │
│ ├─ Lookup MCP token in database                                 │
│ ├─ Generate short-lived JWT                                     │
│ └─ Return {user_id, dept, JWT}                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ MCP now has JWT token
                           │ Send question with JWT
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ BACKEND - CHAT ENDPOINT (WHERE REAL WORK HAPPENS)                │
│ File: app/api/chat.py                                            │
│ ├─ Receive question + JWT                                        │
│ ├─ Validate JWT → Extract user_id, department                   │
│ ├─ Call retrieval_service.retrieve_relevant_documents()         │
│ └─ Apply ACL filtering (removes docs user can't see)            │
│                                                                  │
│ 🔍 THIS IS WHERE THE SEARCH & FILTERING HAPPENS                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Search for documents
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ QDRANT CLOUD (Vector Database - Outside our control)             │
│ File: app/services/qdrant_service.py (handles communication)    │
│ ├─ Convert question to embedding                                 │
│ ├─ Search for similar document embeddings                        │
│ ├─ Return top 5 matches with scores                              │
│ └─ Apply final ACL check                                         │
│                                                                  │
│ ⚠️ MCP SERVER NEVER TALKS TO QDRANT DIRECTLY!                     │
│    Only backend communicates with Qdrant                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Documents + metadata
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ BACKEND - RESPONSE                                               │
│ ├─ Format documents                                              │
│ ├─ Generate LLM summary (if using GPT)                           │
│ └─ Return {answer, sources[]}                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ JSON response with answer
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ MCP SERVER - RESPONSE FORMATTING (FINAL STEP)                    │
│ File: tools/ask_tool.py → _format_response()                     │
│ ├─ Convert to MCP response format                                │
│ ├─ Include citations                                             │
│ └─ Return to Claude                                              │
│                                                                  │
│ ✅ MCP ONLY FORMATS - it doesn't generate the answer              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ JSON-RPC response
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ CLAUDE (in Claude app)                                           │
│ ├─ Receives formatted response                                   │
│ ├─ Integrates into conversation                                  │
│ └─ Shows to user with sources                                    │
│                                                                  │
│ Output: "The deployment process involves three stages:          │
│          Stage 1: Pre-deployment validation...                   │
│          [Cited from Engineering Deployment Guide p.1-5]"       │
└──────────────────────────────────────────────────────────────────┘
```

**Summary:**
- **MCP Server**: Validates token, delegates to backend, formats response
- **Backend**: Does ALL real work (search, filter, generate answer)
- **Qdrant**: Stores & searches embeddings (only backend talks to it)


---

## ✅ Checklist: What You Should Understand

After reading this guide, you should be able to answer:

- [ ] What is the MCP token and why is it 365 days?
- [ ] What is JWT and why is it 1 hour only?
- [ ] Why does MCP need to call backend's validate endpoint?
- [ ] How does ACL filtering work?
- [ ] What files handle token validation?
- [ ] What files handle document retrieval?
- [ ] What files handle Qdrant search?
- [ ] Why does Claude need to call a tool?
- [ ] What happens if token is invalid?
- [ ] What happens if user doesn't have permission?
- [ ] What's the total time from question to answer?
- [ ] Where are error responses generated?

---

## 🎓 Real-World Example: Complete Flow

**Scenario:** Alice from Engineering asks "What's our GDPR compliance process?"

### The Complete Journey:

**1. Alice types in Claude:**
```
"What's our GDPR compliance process?"
```

**2. Claude's brain:**
```
"This is asking about internal compliance. I should use ask_knowledge_base tool."
```

**3. Claude sends to MCP:**
```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "tools/call",
  "params": {
    "name": "ask_knowledge_base",
    "arguments": {
      "question": "What's our GDPR compliance process?"
    }
  }
}
```

**4. MCP extracts token:**
```
Authorization: Bearer mcp_alice_engineering_365days_hash
```

**5. MCP calls backend validate:**
```
POST /api/internal/mcp/validate
{
  "token": "mcp_alice_engineering_365days_hash"
}
```

**6. Backend responds:**
```json
{
  "user_id": 1,
  "username": "alice",
  "department_name": "engineering",
  "backend_jwt": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 3600
}
```

**7. MCP calls backend chat:**
```
POST /api/chat
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
{
  "question": "What's our GDPR compliance process?"
}
```

**8. Backend queries Qdrant:**
```
Search: "GDPR compliance process"
Results:
- Legal_GDPR_Framework.pdf (dept: legal, score: 0.92)
- Security_GDPR_Requirements.pdf (dept: security, score: 0.88)
- Engineering_GDPR_Implementation.pdf (dept: engineering, score: 0.85)
- HR_GDPR_Training.pdf (dept: hr, score: 0.78)
- Sales_GDPR_Restrictions.pdf (dept: sales, score: 0.72)
```

**9. Backend applies ACL (Alice is engineering):**
```
✅ Legal_GDPR_Framework.pdf (legal = general audience)
✅ Security_GDPR_Requirements.pdf (security = everyone needs this)
✅ Engineering_GDPR_Implementation.pdf (engineering = Alice's dept)
❌ HR_GDPR_Training.pdf (hr = only HR staff)
❌ Sales_GDPR_Restrictions.pdf (sales = only sales staff)

Show: 3 documents
Hide: 2 documents (user not in those departments)
```

**10. Backend generates response:**
```json
{
  "answer": "Our GDPR compliance process involves several layers:\n\n1. Data Classification...",
  "sources": [
    {
      "filename": "Legal_GDPR_Framework.pdf",
      "pages": "1-12",
      "relevance": 0.92,
      "snippet": "Data classification by sensitivity level..."
    },
    {
      "filename": "Security_GDPR_Requirements.pdf",
      "pages": "5-8",
      "relevance": 0.88,
      "snippet": "Security controls for personally identifiable information..."
    },
    {
      "filename": "Engineering_GDPR_Implementation.pdf",
      "pages": "2-15",
      "relevance": 0.85,
      "snippet": "Technical implementation in our systems..."
    }
  ]
}
```

**11. MCP formats response:**
```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "content": [{
      "type": "text",
      "text": "Our GDPR compliance process involves several layers:\n\n1. Data Classification: All company data is classified...\n\nSources:\n- Legal GDPR Framework (p.1-12, 92% relevant)\n- Security GDPR Requirements (p.5-8, 88% relevant)\n- Engineering GDPR Implementation (p.2-15, 85% relevant)"
    }]
  }
}
```

**12. Claude shows to Alice:**
```
"Our GDPR compliance process involves several layers:

1. Data Classification
   All company data is classified by sensitivity level...

2. Security Controls  
   Personally identifiable information is protected by...

3. Technical Implementation
   Our systems implement GDPR through...

Sources I used:
📄 Legal GDPR Framework (pages 1-12)
📄 Security GDPR Requirements (pages 5-8)  
📄 Engineering GDPR Implementation (pages 2-15)

Note: I'm hiding HR and Sales documents since they're restricted to those departments."
```

**Total time: ~350ms**

---

## 🎯 Summary

| Concept | Simple Explanation | Why It Matters |
|---------|-------------------|----------------|
| MCP | Bridge between Claude and our documents | Claude can access internal docs |
| MCP Token | Long-lived proof of identity (365 days) | Claude can be configured once |
| JWT | Short-lived access pass (1 hour) | Extra security - token theft is limited |
| Authorization Header | Message saying "trust me, here's my token" | Proves user identity in requests |
| ACL | Rules for who sees what based on department | Sensitive docs stay secure |
| Qdrant | Database of document summaries | Fast semantic search |
| JSON-RPC | Standard message format | Claude and our server understand each other |
| Tool Call | Claude invoking a function we created | Claude uses our knowledge base |

---

**This file is your complete reference. Bookmark it! 📌**
