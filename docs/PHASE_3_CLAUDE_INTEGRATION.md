# Phase 3: Claude MCP Integration Guide

## Overview
Phase 3 completes the SecureRAG system by connecting Claude to your MCP server, enabling Claude to query your knowledge base with department-based access control.

## Architecture
```
Claude (Web Interface)
    ↓ (MCP Protocol over HTTP)
MCP Server (localhost:5001)
    ↓ (Bearer Token Auth)
Backend API (localhost:8000)
    ↓ (JWT + User Context)
Knowledge Base (Qdrant + PostgreSQL)
    ↓ (Department-based ACL)
Filtered Results → Claude
```

## Prerequisites
✅ **Phase 2 Complete**
- MCP Server running on `http://localhost:5001/mcp`
- Backend API running on `http://localhost:8000`
- All 6 infrastructure tests passing

## Step-by-Step Integration

### Step 1: Verify MCP Server is Running
```bash
# Terminal 1: Backend
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/backend
python run.py

# Terminal 2: MCP Server
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
python run.py
```

**Verify with:**
```bash
curl http://localhost:5001/health
# Should return: {"status":"ok","service":"MCP Server"}
```

### Step 2: Get Your MCP Token
Use this pre-generated token:
```
MCP_TOKEN=mcp_TLDwkbdblkYWEnNPXahwk4bhXmJFZfFS97Xtz758sIw
```

Or generate a new one (with backend running):
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/backend
python -m scripts.mcp_token_manager --action create --user-id 1 --description "Claude Integration"
```

### Step 3: Configure Claude (Manual)

1. **Open Claude Settings**
   - Go to https://claude.ai/settings (or similar, depending on your Claude interface)
   - Look for "Custom Remote MCP Servers" or "Extensions"

2. **Add MCP Server Connection**
   - Click "Add MCP Server" or "New Connection"
   - **Name:** `SecureRAG-MCP`
   - **URL:** `http://localhost:5001/mcp`
   - **Type:** `HTTP`
   - **Authentication:** `Bearer Token`
   - **Token:** Paste your MCP token above

3. **Save Configuration**
   - Test connection (should show green/active status)
   - Verify tools are discovered

### Step 4: Test in Claude

**Test 1: Basic Tool Discovery**
```
Ask Claude: "What tools do you have available?"
Expected: Claude lists "ask_knowledge_base" tool
```

**Test 2: Query Knowledge Base**
```
Ask Claude: "What is company policy on remote work?"
Expected: Claude uses ask_knowledge_base tool and returns answer with sources
```

**Test 3: Multi-Turn Conversation**
```
First turn: "Tell me about engineering practices"
Second turn: "What about sales strategies?"
Expected: Tool maintains context and retrieves different documents
```

**Test 4: Source Attribution**
```
Ask Claude: "Can you cite your sources for this answer?"
Expected: Claude shows document names, departments, and content chunks
```

## Testing Multi-User ACL (Advanced)

### Generate Additional Test Tokens
Each department should have its own token for testing:

```bash
# Engineering department (user_id 1)
python -m scripts.mcp_token_manager --action create --user-id 1 --description "Claude: Engineering"

# Sales department (user_id 2)
python -m scripts.mcp_token_manager --action create --user-id 2 --description "Claude: Sales"

# HR department (user_id 3)
python -m scripts.mcp_token_manager --action create --user-id 3 --description "Claude: HR"
```

### Test ACL Enforcement
Use separate Claude browser tabs or sessions with different tokens:

**Session 1 (Engineering Token):**
- Ask: "What are our deployment guidelines?"
- Expected: Returns engineering documents

**Session 2 (Sales Token):**
- Ask: "What are our deployment guidelines?"
- Expected: Returns sales-related docs or "no relevant documents"

**Session 3 (HR Token):**
- Ask: "What are our deployment guidelines?"
- Expected: Returns HR-related docs or "no relevant documents"

## Troubleshooting

### Issue: "Connection Refused"
**Solution:** Verify MCP server is running on port 5001
```bash
lsof -i :5001  # Check what's using port 5001
```

### Issue: "Authentication Failed"
**Solution:** Verify token is correct and hasn't expired
```bash
# Check token in database
cd backend
python -c "
from app.db.session import SessionLocal
from app.models import MCPToken
db = SessionLocal()
tokens = db.query(MCPToken).all()
for t in tokens:
    print(f'User: {t.user_id}, Expires: {t.expires_at}')
"
```

### Issue: "No Tools Available"
**Solution:** Verify MCP initialize handshake succeeded
```bash
curl -X POST http://localhost:5001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
# Should return protocol version and server info
```

### Issue: "No Relevant Documents"
**Solution:** Verify knowledge base has documents for user's department
```bash
# Check ingested documents
cd backend
python -m scripts.ingest_documents --list-departments
```

## Performance Notes

- **Tool Latency:** 1-2 seconds per query (includes vector search + LLM inference)
- **Maximum Context:** ~8,000 tokens per response
- **Concurrent Users:** Supports multiple Claude sessions simultaneously
- **Token Expiry:** 7 days (configurable in backend)

## Next Steps (Phase 4)

After successful Claude integration:
1. Deploy MCP server to Render (production)
2. Deploy backend to Render (production)
3. Update Claude configuration with production URLs
4. Set up monitoring and logging
5. Configure rate limiting and usage quotas

## Support

For issues or questions:
- Check backend logs: `backend/logs/debug.log`
- Check MCP server logs: `mcp-server/logs/debug.log`
- Review error responses in Claude chat

---
**Status:** Phase 3 Ready ✅
**Last Updated:** 2026-09-03
