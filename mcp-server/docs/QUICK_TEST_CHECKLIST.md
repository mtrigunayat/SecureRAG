# Quick Reference: Local Testing Checklist

**Print this out or keep in another terminal window while testing**

---

## 🚀 QUICK START (5 MINUTES)

### Terminal 1: Start Backend
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```
✅ Wait for: `Application startup complete`

### Terminal 2: Start MCP Server
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
source venv/bin/activate
python run.py
```
✅ Wait for: `MCP Server Starting` + `Host: 0.0.0.0:5000`

### Terminal 3: Create Test Token
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG
python << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.db.session import SessionLocal
from app.services.mcp_token_service import create_mcp_token
db = SessionLocal()
token_record = create_mcp_token(user_id=1, db=db, expires_days=7)
print(token_record.token)
with open('/tmp/mcp_test_token.txt', 'w') as f:
    f.write(token_record.token)
print("✅ Token saved to /tmp/mcp_test_token.txt")
EOF
```

---

## ✅ VERIFICATION STEPS (In Order)

### 1️⃣ Backend Health
```bash
curl -s http://localhost:8000/health | python -m json.tool
# Expected: {"status": "healthy", ...}
```

### 2️⃣ MCP Health
```bash
curl -s http://localhost:5000/health
# Expected: {"status": "healthy", ...}
```

### 3️⃣ Test Identity Bridge
```bash
MCP_TOKEN=$(cat /tmp/mcp_test_token.txt)
curl -X POST http://localhost:8000/api/internal/mcp/validate \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$MCP_TOKEN\"}" -s | python -m json.tool
# Expected: {user_id, username, department_name, backend_jwt}
```

### 4️⃣ Test Backend /api/chat
```bash
# First get JWT from step 3
BACKEND_JWT=$(curl -X POST http://localhost:8000/api/internal/mcp/validate \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$(cat /tmp/mcp_test_token.txt)\"}" -s | python -c "import sys, json; print(json.load(sys.stdin)['backend_jwt'])")

# Then test chat
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $BACKEND_JWT" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the company deployment process?"}' -s | python -m json.tool
# Expected: {answer: "...", sources: [...]}
```

### 5️⃣ Test MCP Token Validation (Python)
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
source venv/bin/activate
python << 'EOF'
import asyncio, sys
sys.path.insert(0, 'src')
from mcp_server.auth import validate_mcp_token

async def test():
    with open('/tmp/mcp_test_token.txt') as f:
        token = f.read().strip()
    ctx = await validate_mcp_token(token)
    print(f"✅ User: {ctx.username} (ID: {ctx.user_id})")
    print(f"✅ Department: {ctx.department_name}")
    return True

asyncio.run(test())
EOF
```

### 6️⃣ Test Full MCP → Backend Flow (Python)
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
source venv/bin/activate
python << 'EOF'
import asyncio, sys
sys.path.insert(0, 'src')
from mcp_server.auth import validate_mcp_token
from mcp_server.client import BackendAPIClient

async def test():
    print("Testing MCP → Backend Flow...")
    
    # 1. Validate MCP token
    with open('/tmp/mcp_test_token.txt') as f:
        token = f.read().strip()
    ctx = await validate_mcp_token(token)
    print(f"✅ MCP token validated: {ctx.username}")
    
    # 2. Call backend via MCP client
    client = BackendAPIClient()
    response = await client.ask_knowledge_base(
        question="What is the company deployment process?",
        backend_jwt=ctx.backend_jwt
    )
    
    print(f"✅ Backend call successful")
    print(f"   Answer length: {len(response.answer)} chars")
    print(f"   Sources: {len(response.sources)} documents")
    print()
    print("Answer (first 200 chars):")
    print(response.answer[:200] + "...")
    print()
    print("Sources:")
    for i, src in enumerate(response.sources, 1):
        print(f"  {i}. {src.document_name}")
    
    return True

asyncio.run(test())
EOF
```

### 7️⃣ Run Validation Scripts
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
source venv/bin/activate

echo "Running Phase 3 Validation..."
python validate_phase3.py

echo ""
echo "Running Phase 4 Validation..."
python validate_phase4.py
```

---

## 📊 RESULTS SUMMARY

### SUCCESS ✅ (All Checks Pass)
```
✅ Backend health: 200 OK
✅ MCP health: 200 OK
✅ Identity bridge: Returns JWT
✅ Backend /api/chat: Returns answer + sources
✅ MCP token validation: Returns user context
✅ Full MCP flow: Works end-to-end
✅ Validation scripts: All PASS

→ READY FOR PHASE 5 ✅
```

### FAILURE ❌ (Check These)
```
Backend connection refused?
  → Backend not running in Terminal 1
  → Port 8000 already in use: kill -9 $(lsof -t -i:8000)

MCP connection refused?
  → MCP server not running in Terminal 2
  → Port 5000 already in use: kill -9 $(lsof -t -i:5000)

Token validation error?
  → Token file missing: /tmp/mcp_test_token.txt
  → Regenerate from "Create Test Token" step

Backend /api/chat returns 401?
  → Backend JWT expired
  → Regenerate JWT from identity bridge test

Module not found error?
  → venv not activated: source venv/bin/activate
  → Dependencies missing: pip install -r requirements.txt
```

---

## 🎯 WHAT'S BEING TESTED

```
Claude (future)
    ↓ MCP Token
    ↓
MCP Server (5000)
    ├─ Validates token with Backend
    ├─ Gets user identity + JWT
    ├─ Calls Backend /api/chat
    └─ Returns formatted answer
    
Backend (8000)
    ├─ Validates MCP token → returns JWT ✅
    ├─ Accepts JWT for /api/chat ✅
    ├─ Applies department ACL ✅
    ├─ Calls Qdrant ✅
    ├─ Calls Azure OpenAI ✅
    └─ Returns answer + sources ✅
    
Qdrant & Azure OpenAI
    └─ Not tested directly (backend handles)
```

---

## ⏱️ EXPECTED TIMING

| Step | Time | What's Happening |
|------|------|-----------------|
| 1-2 | 2 min | Services startup |
| 3 | 1 min | Token creation |
| 4-6 | 3 min | HTTP/curl tests |
| 7 | 5 min | Python integration tests |
| 8 | 2 min | Full end-to-end test |
| 9 | 2 min | Run validation scripts |
| **TOTAL** | **~18 min** | Complete verification |

---

## 🔍 WHAT TO LOOK FOR IN LOGS

### In Terminal 1 (Backend)
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete

[When token validated]
INFO: MCP token validated: user_id=1

[When /api/chat called]
INFO: Chat endpoint called: question_len=44
INFO: Qdrant query: dept=engineering, threshold=0.4
INFO: Azure OpenAI generation...
INFO: Returning: answer + 2 sources
```

### In Terminal 2 (MCP Server)
```
MCP Server Starting
Host: 0.0.0.0:5000
Backend: http://localhost:8000

[When request comes in]
INFO: Tool invoked: ask_knowledge_base
INFO: User validated: user_id=1, dept=engineering
INFO: Backend request: POST /api/chat
INFO: Backend response: 200 OK | sources=2
INFO: Tool response sent to client
```

---

## 🛡️ SECURITY CHECKS

**Before moving to Phase 5, verify:**

```
❌ No raw MCP tokens in logs
❌ No JWTs (eyJ...) in logs
❌ No passwords in logs
❌ No API keys in logs
❌ Tool input only has {question}
❌ user_id/dept not overridable via input
❌ Department filtering working (ACL)
```

---

## 📝 NOTES

- Keep both Terminal 1 & 2 running throughout testing
- Use Terminal 3 for curl/python commands
- Save MCP token to `/tmp/mcp_test_token.txt` for easy access
- If something fails, check Terminal 1 & 2 logs first
- Most issues are: ports in use, venv not activated, dependencies missing

---

## 🚀 NEXT PHASE (After All ✅)

Once everything passes:
1. Document results in Phase 4 Completion Report
2. Commit code and tests to git
3. Begin Phase 5: Claude Integration
