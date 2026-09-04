# MCP Server — Secure Company Knowledge Base Integration

**Status**: Phase 10 ✅ Complete | Production Ready

**What is this?** A Model Context Protocol (MCP) server that bridges Claude AI to your company's internal knowledge base. Claude can safely query company policies, procedures, and documentation without direct access to your infrastructure.

---

## Quick Start

### Prerequisites
- Python 3.10+
- Backend running on `http://localhost:8000` (or production Render URL)
- Valid MCP token (see Token Management in backend)

### 1. Setup

```bash
cd mcp-server
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 2. Configure

Create `.env` file:
```env
MCP_HOST=0.0.0.0
MCP_PORT=5000
BACKEND_URL=http://localhost:8000
BACKEND_API_TIMEOUT=30
LOG_LEVEL=INFO
```

### 3. Start

```bash
python run.py
```

**Expected Output**:
```
============================================================
MCP Server Starting
============================================================
Host: 0.0.0.0:5000
Backend: http://localhost:8000
Log Level: INFO
============================================================
```

### 4. Verify

```bash
python validate_phase3.py
```

All tests should **PASS**.
```

---

## Architecture

### Overall Flow

```
Claude
  ↓ (has MCP token)
  ├─ "What is the deployment process?"
  ├─ Calls MCP tool: ask_knowledge_base(question="...")
  │
MCP Server (localhost:5000)
  ├─ Validates MCP token with backend
  ├─ Gets authenticated user + department
  ├─ Calls backend /api/chat
  │
Backend (localhost:8000)
  ├─ Authenticates with JWT
  ├─ Loads user + department from database
  ├─ Calls Qdrant with department ACL
  ├─ Calls Azure OpenAI for generation
  ├─ Returns answer + sources
  │
MCP Server
  ├─ Formats response
  ├─ Returns to Claude
  │
Claude
  └─ Presents answer to user
```

### Authentication Flow

```
1. Claude sends MCP request with Bearer token
   Authorization: Bearer mcp_xxxxxxxxxxxx

2. MCP Server extracts token

3. MCP Server calls Backend: POST /api/internal/mcp/validate
   {"token": "mcp_xxxxxxxxxxxx"}

4. Backend validates MCP token (Phase 2)
   - Checks token in database
   - Checks expiration
   - Loads User + Department

5. Backend creates short-lived JWT (1 hour)
   create_access_token(user.id)

6. Backend returns to MCP Server:
   {
     "user_id": 1,
     "username": "alice",
     "department_name": "engineering",
     "backend_jwt": "eyJ...",
     "expires_in": 3600
   }

7. MCP Server stores authenticated context (request-scoped)

8. MCP Server calls Backend: POST /api/chat
   Authorization: Bearer {backend_jwt}
   {"question": "What is the deployment process?"}

9. Backend returns answer + sources

10. MCP Server formats response

11. Claude receives formatted response
```

### Key Properties

| Property | Value | Reason |
|----------|-------|--------|
| **Transport** | HTTP Streamable | Standard MCP protocol |
| **MCP Token** | Long-lived (365 days) | Can be stored in Claude configuration |
| **Backend JWT** | Short-lived (1 hour) | Security best practice |
| **Authentication** | Outside tool input | Tool input is ONLY `question` |
| **Identity Source** | Backend database | Cannot be spoofed |
| **ACL Enforcement** | Backend Qdrant | Server-side filtering |
| **Tool Count** | 1 tool | Minimal, focused scope |

---

## Configuration

### Environment Variables

`.env` file:

```env
# MCP Server binding
MCP_HOST=0.0.0.0              # Listen on all interfaces
MCP_PORT=5000                 # Custom port

# Backend integration
BACKEND_URL=http://localhost:8000
BACKEND_API_TIMEOUT=30        # Request timeout in seconds

# Logging
LOG_LEVEL=INFO                # INFO, DEBUG, WARNING, ERROR
```

See `.env.example` for all options.

### Logging

Logs are structured and secure:

**Safe Examples**:
```
2026-09-02 15:44:05 - mcp_server - INFO - Tool invoked: ask_knowledge_base | user_id=1 | dept=engineering | question_len=32
2026-09-02 15:44:06 - mcp_server - INFO - Backend request: POST /api/chat
2026-09-02 15:44:07 - mcp_server - INFO - Backend response: 200 OK | sources=3
```

**Never Logged**:
- ❌ Raw MCP tokens
- ❌ Authorization headers  
- ❌ Backend JWTs
- ❌ Passwords
- ❌ API keys
- ❌ Backend URLs (only standard ports logged)

---

## Available Tools

### `ask_knowledge_base`

Query the company's internal knowledge base.

**When to use**: User asks about company policies, procedures, documentation, internal guidelines, security procedures, HR policies, or technical documentation.

**Input**:
```json
{
  "question": "What is the deployment process?"
}
```

**Input Schema**:
```json
{
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
```

**Output** (formatted as text):
```
Answer: The deployment process involves three stages...

Sources:
1. Engineering Deployment Guide (engineering) [p.1-5, score: 0.87]
2. Security Deployment Checklist (security) [p.12-14, score: 0.75]
```

**Important Properties**:
- ✅ Tool input contains ONLY `question` string
- ✅ No `user_id`, `department`, `token` fields
- ✅ Authentication via Authorization header (outside tool input)
- ✅ User identity resolved from authenticated MCP token
- ✅ Cannot be spoofed

---

## Security Model

### What is Protected

1. **User Identity**: Comes from MCP token, cannot be overridden
2. **Department Access**: From authenticated user's database record
3. **Qdrant ACL**: Applied server-side by backend
4. **Backend Services**: MCP does NOT access Qdrant or Azure OpenAI directly
5. **Credentials**: No passwords, API keys, or secrets stored in MCP

### What Cannot Be Spoofed

```python
# ❌ CANNOT OVERRIDE USER IDENTITY (input validation rejects)
{
  "question": "What is the HR policy?",
  "user_id": 2  # Ignored or rejected by schema validation
}

# ❌ CANNOT OVERRIDE DEPARTMENT (not in input schema)
{
  "question": "What is the HR policy?",
  "department": "hr"  # Ignored or rejected by schema validation
}

# ❌ CANNOT SEND TOKEN IN INPUT
{
  "question": "What is the HR policy?",
  "token": "mcp_..."  # Ignored or rejected by schema validation
}

# ✅ ONLY VALID INPUT
{
  "question": "What is the HR policy?"
}
# User identity comes from Authorization header (MCP token)
# Department comes from authenticated user's database record
```

---

## Local Verification Steps

### Step 1: Start Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health` → HTTP 200

### Step 2: Start MCP Server

```bash
cd mcp-server
source venv/bin/activate
python run.py
```

Verify: See "MCP Server Starting" in logs

### Step 3: Run Validation

```bash
cd mcp-server
python validate_phase3.py
```

Expected: All tests PASS

### Step 4: Create MCP Token

```bash
cd backend
# Generate token for testing user (user_id=1)
python -c "
from app.db.session import SessionLocal
from app.services.mcp_token_service import create_mcp_token

db = SessionLocal()
token_record = create_mcp_token(user_id=1, db=db, expires_days=1)
print(f'Token: {token_record.token}')
print(f'Expires: {token_record.expires_at}')
"
```

### Step 5: Test Tool Locally (Python)

```python
import asyncio
from mcp_server.auth import validate_mcp_token
from mcp_server.client import BackendAPIClient

async def test_tool():
    # Use token from Step 4
    mcp_token = "mcp_xxxxxxxxxxxx"
    
    # Validate token
    auth_context = await validate_mcp_token(mcp_token)
    print(f"Authenticated: user_id={auth_context.user_id}, dept={auth_context.department_name}")
    
    # Call backend
    backend_client = BackendAPIClient()
    response = await backend_client.ask_knowledge_base(
        question="What is the deployment process?",
        backend_jwt=auth_context.backend_jwt
    )
    
    print(f"Answer: {response.answer}")
    print(f"Sources: {len(response.sources)} documents")

asyncio.run(test_tool())
```

---

## Docker

```bash
# Build image
docker build -t secure-rag-mcp-server .

# Run container
docker run -p 5000:5000 \
  -e BACKEND_URL=http://localhost:8000 \
  secure-rag-mcp-server
```

---

## Troubleshooting

### MCP Server Won't Start

**Error**: `Address already in use`
```
Solution: Port 5000 already in use
  1. netstat -an | grep 5000
  2. Kill process or use different port: MCP_PORT=5001 python run.py
```

**Error**: `Connection refused` to backend
```
Solution: Backend not running
  1. Start backend: python -m uvicorn app.main:app --reload
  2. Verify: curl http://localhost:8000/health
```

### Tool Invocation Not Working

**Issue**: Claude never invokes `ask_knowledge_base`
```
1. Verify tool is registered: Check MCP logs for "Tool registered"
2. Verify tool description: Should indicate when to use
3. Check MCP endpoint: curl -X GET http://localhost:5000/
4. Test manually: See "Local Verification Steps"
```

### Authentication Errors

**Error**: `Invalid token` / `403 Forbidden`
```
Solution:
  1. Check MCP token is valid: Verify in database
  2. Check token not expired: Token expires_at > now()
  3. Check backend is running: curl http://localhost:8000/health
  4. Check /api/internal/mcp/validate exists: Backend logs
```

---

## File Structure

```
mcp-server/
├── src/mcp_server/
│   ├── __init__.py                    # Server initialization
│   ├── main.py                        # Entry point
│   ├── core/
│   │   ├── config.py                  # Configuration via environment
│   │   ├── logging.py                 # Structured logging
│   │   └── errors.py                  # MCP-specific exceptions
│   ├── auth/
│   │   ├── __init__.py                # AuthenticatedContext validation
│   │   └── token_service.py           # Backend token validation
│   ├── client/
│   │   ├── __init__.py                # Re-exports
│   │   └── backend_api_client.py      # HTTP client for backend
│   └── tools/
│       ├── __init__.py                # Re-exports
│       └── ask_tool.py                # Tool implementation
├── run.py                             # Startup script
├── run.sh                             # Bash wrapper
├── requirements.txt                   # Python dependencies
├── Dockerfile                         # Container image
├── .dockerignore                      # Docker ignore patterns
├── validate_phase3.py                 # Phase 3 validation
├── validate_phase4.py                 # Phase 4 validation framework
└── docs/
    ├── PHASE_3_MCP_SERVER_CORE.md     # Phase 3 docs
    └── PHASE_4_VALIDATION.md          # Phase 4 validation plan
```

---

## Dependencies

- `mcp>=0.1.0` — Official Anthropic Model Context Protocol SDK
- `httpx>=0.25.0` — Async HTTP client for backend calls
- `pydantic>=2.0` — Data validation and settings management
- `pydantic-settings>=2.0` — Environment variable management
- `python-dotenv>=1.0.0` — Load .env files
- `starlette>=0.35.0` — HTTP framework foundation
- `uvicorn>=0.24.0` — ASGI server for HTTP transport

---

## Status & Completion

### Project Phases Completed

✅ **Phase 1**: Core Backend & RAG Infrastructure  
✅ **Phase 2**: MCP Token Management & Authentication  
✅ **Phase 3**: MCP Server Implementation  
✅ **Phase 4**: Claude Integration & Validation  
✅ **Phase 5-10**: Production Deployment, Scaling, & Security Hardening  

### Production Deployment

- **Backend**: Deployed on Render with Qdrant Cloud integration
- **Frontend**: Deployed on Render with responsive UI
- **MCP Server**: Production-ready with full authentication and authorization
- **Database**: PostgreSQL (Neon Cloud) with secure schema
- **Vector DB**: Qdrant Cloud with 30s timeout for reliability

### Maintenance & Monitoring

For ongoing operations:
- Monitor health endpoints regularly
- Review MCP token expiration and rotation
- Check Qdrant Cloud connection status
- Monitor backend logs for authentication errors

---

## Support & Questions

**Implementation Details**: See `docs/PHASE_3_MCP_SERVER_CORE.md`

**Validation & Testing**: See `docs/PHASE_4_VALIDATION.md`

**Backend Integration**: Check `backend/app/api/mcp_internal.py`

**Token Management**: Check `backend/app/services/mcp_token_service.py`

**Deployment Issues**: Refer to backend logs on Render or check local uvicorn output

---

## License & Copyright

© 2026 — Part of Secure RAG Knowledge Assistant project
