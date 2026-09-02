# MCP Server - Secure RAG Knowledge Assistant

Model Context Protocol (MCP) server for the Secure RAG Knowledge Assistant.

This is an **adapter service** that allows remote MCP clients (like Claude via MCP) to query the existing SecureRAG backend.

## Architecture

```
MCP Client (Claude)
    ↓ MCP Protocol
MCP Server (this app)
    ↓ HTTP + JWT
Existing Backend (FastAPI)
    ↓ (unchanged)
Existing RAG Pipeline
```

The MCP server:
- ✅ Authenticates MCP clients using MCP tokens
- ✅ Validates requests with the existing backend
- ✅ Maintains department-based authorization
- ✅ Delegates RAG to the existing backend
- ✅ Returns results to the client

Does NOT:
- ❌ Access Qdrant directly
- ❌ Call Azure OpenAI directly
- ❌ Replicate RAG logic
- ❌ Store user passwords
- ❌ Manage embeddings

## Quick Start

### Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your backend URL

# Run server
python -m mcp_server.main
```

Server listens on `http://localhost:5000`

Health check: `curl http://localhost:5000/health`

### Docker

```bash
# Build image
docker build -t secure-rag-mcp-server .

# Run container
docker run -p 5000:5000 \
  -e BACKEND_URL=http://localhost:8000 \
  secure-rag-mcp-server
```

## Configuration

Create `.env` file with:

```
MCP_HOST=0.0.0.0
MCP_PORT=5000
BACKEND_URL=http://localhost:8000
BACKEND_API_TIMEOUT=30
LOG_LEVEL=INFO
```

See `.env.example` for all options.

## MCP Authentication

MCP clients authenticate using **MCP tokens** (created via backend admin CLI).

Token flow:
1. Admin creates token for user: `python backend/scripts/mcp_token_manager.py --action create --user-id 1`
2. User provides token to MCP client
3. MCP client includes token in requests: `Authorization: Bearer mcp_xxx...`
4. MCP server validates token with backend
5. Backend returns authenticated user identity
6. MCP server uses identity for subsequent backend calls

## Tools

### `ask_knowledge_base`

Query the company knowledge base.

**Input:**
```json
{
  "question": "What is our password policy?"
}
```

**Output:**
```
Generated answer with sources...

**Sources:**
1. **Security Policy** (Engineering) [p.5-6, score: 0.92]
2. **HR Handbook** (HR) [p.12, score: 0.87]

_Retrieved 2 document(s) from Engineering_
```

The backend:
- Retrieves relevant documents for the user's department
- Generates answer from authorized content only
- Prevents access to documents outside user's department
- Returns sources for transparency

## Backend Integration

The MCP server requires a backend endpoint to validate MCP tokens and exchange them for session JWTs.

**Required Backend Endpoint:**

```
POST /api/internal/mcp/validate
Authorization: (none - this validates the MCP token)
Content-Type: application/json

Request:
{
  "token": "mcp_xxx..."
}

Response (200):
{
  "user_id": 123,
  "username": "john.doe",
  "department_name": "Engineering",
  "backend_jwt": "<short-lived-jwt>"
}

Errors:
401 - Invalid/expired/revoked token
500 - Internal error
```

The backend_jwt is a short-lived JWT used for subsequent /api/chat requests.

## Security

- ✅ MCP tokens are opaque and cryptographically random
- ✅ Raw tokens never logged or exposed
- ✅ Token validation happens server-side in backend
- ✅ User identity from database (cannot be spoofed)
- ✅ Department enforced by backend (cannot be overridden)
- ✅ Backend JWTs are short-lived
- ✅ All errors return generic messages
- ✅ Backend remains authoritative

## Development

### Project Structure

```
mcp-server/
├── src/mcp_server/
│   ├── __init__.py           # Main server setup
│   ├── main.py               # Entry point
│   ├── core/
│   │   ├── config.py         # Configuration
│   │   ├── logging.py        # Logging setup
│   │   └── errors.py         # Exception types
│   ├── auth/
│   │   └── __init__.py       # Token validation
│   ├── client/
│   │   └── __init__.py       # Backend API client
│   └── tools/
│       └── __init__.py       # MCP tool implementations
├── .env.example
├── requirements.txt
├── pyproject.toml
├── Dockerfile
└── README.md
```

### Manual Testing

```bash
# Health check
curl http://localhost:5000/health

# MCP request (requires valid MCP token)
curl -X POST http://localhost:5000/mcp \
  -H "Authorization: Bearer mcp_xxx..." \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "ask_knowledge_base", "arguments": {"question": "..."}}}'
```

### Logging

Server logs to stdout. Useful information:
- MCP request authentication
- Tool invocations
- Backend communication
- Errors

Error details logged server-side only. Client receives generic messages.

## Limitations (By Design)

- Only one tool: `ask_knowledge_base` (more tools added in future phases)
- No caching (requests hit backend each time)
- No Claude integration yet (that's Phase 4)
- No public deployment yet
- No database (relies on backend's database)

## Next Steps

- **Phase 4**: Connect to Claude via MCP protocol
- **Phase 5**: Add more tools (search, retrieve, etc.)
- **Phase 6**: Caching and performance optimization
- **Phase 7**: Production deployment

## Support

For issues:
1. Check logs: `LOG_LEVEL=DEBUG` for verbose output
2. Verify backend is running: `curl http://localhost:8000/health`
3. Test authentication: Use CLI to create test token
4. Review this README

## License

Same as Secure RAG project
