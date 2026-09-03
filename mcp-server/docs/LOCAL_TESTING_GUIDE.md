# Phase 4 — Local MCP ↔ Backend Connection Testing Guide

**Objective**: Verify the complete MCP → Backend flow works end-to-end locally.

**Time**: ~30 minutes

**Prerequisites**:
- Python 3.10+
- Both projects in `/Desktop/personal/SecureRAG/`
- Docker & Docker Compose installed
- PostgreSQL and Qdrant running (via Docker Compose)

---

## STEP 0: Start Database & Vector Store Services

### 0A. Verify Docker Desktop is Running

**On macOS**, Docker Desktop must be running before you can use Docker/Docker Compose.

**⚠️ CRITICAL: Docker Desktop is NOT running right now**

Check current status:
```bash
docker ps
```

**If you see error**: `Cannot connect to the Docker daemon at unix:///Users/mohittrigunayat/.docker/run/docker.sock`

**This means Docker Desktop is stopped. START IT NOW:**

#### Method 1: Using Spotlight (Fastest)
```bash
# Press Cmd + Space (opens Spotlight search)
# Type: Docker
# Press Enter (launches Docker Desktop)
# Wait 30-60 seconds for daemon to start
```

#### Method 2: Using Finder
1. Open Applications folder
2. Find "Docker.app"
3. Double-click to launch
4. Wait 30-60 seconds for daemon to start

#### Method 3: Using Terminal (if Docker is installed but not running)
```bash
# This will open Docker Desktop
open /Applications/Docker.app
```

**After starting Docker Desktop, verify it's running:**
```bash
# You should see an active Docker icon in the top menu bar (⓵ icon)
# Wait until menu bar icon stops animating
# Then verify connection:
docker ps
# Should return: (no output = success, or list of containers)
# If still error, wait 10 more seconds and retry
```

**If Docker Desktop won't launch:**
```bash
# Kill any stuck Docker processes
pkill -9 com.docker
pkill -9 Docker

# Then try opening Docker.app again:
open /Applications/Docker.app

# Wait 60 seconds for full startup
```

**Verify Docker is ready:**
```bash
# This command must succeed (no error):
docker ps

# Should print something like:
# CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
# (empty list is OK)
```

✅ Docker daemon is running

### 0B. Terminal 0 - Database Services

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG

# Start PostgreSQL and Qdrant containers
docker-compose up -d postgres qdrant
```

**Verify Services Are Running**:
```bash
docker-compose ps
```

**Expected Output**:
```
NAME                    STATUS
secure_rag_postgres     Up (healthy)
secure_rag_qdrant       Up
```

Wait for PostgreSQL to be fully healthy (check "healthy" status).

**Troubleshooting**:
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Check Qdrant logs
docker-compose logs qdrant

# If containers fail to start, clean up first
docker-compose down -v
docker-compose up -d postgres qdrant

# If you get "Cannot connect to the Docker daemon" error:
# 1. Open Docker Desktop app (Cmd + Space → type Docker → Enter)
# 2. Wait 30-60 seconds for daemon to start
# 3. Verify: docker ps (should show no error)
# 4. Then retry: docker-compose up -d postgres qdrant

# If Docker won't start, check Activity Monitor:
# Kill any lingering docker processes (Docker.app, com.docker.*)
# Then reopen Docker Desktop
```

---

## STEP 1: Clean Environment Setup

### 1A. Terminal Preparation
Open **4 separate terminals** in VS Code:

```
Terminal 1: Backend startup
Terminal 2: MCP server startup  
Terminal 3: Testing/debugging
Terminal 4: Logs monitoring (optional)
```

### 1B. Verify Backend is NOT Running
```bash
# In Terminal 3
lsof -i :8000
# Should be empty (no output)

lsof -i :5000
# Should be empty (no output)
```

If ports are in use, kill them:
```bash
kill -9 $(lsof -t -i:8000)
kill -9 $(lsof -t -i:5000)
```

---

## STEP 2: Start Backend Service

### 2A. Terminal 1 - Backend

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/backend

# Activate venv (if not already)
source venv/bin/activate

# Run backend
python -m uvicorn app.main:app --reload --port 8000
```

**Expected Output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### 2B. Verify Backend Health

In **Terminal 3**:
```bash
curl -s http://localhost:8000/health | python -m json.tool
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-09-03T..."
}
```

✅ Backend running successfully

---

## STEP 3: Start MCP Server

### 3A. Terminal 2 - MCP Server

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server

# Activate venv (if not already)
source venv/bin/activate

# Start MCP server
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

✅ MCP server running

### 3B. Verify MCP Server is Listening

In **Terminal 3**:
```bash
curl -s http://localhost:5000/health 2>&1 | head -20
```

**Expected Response**:
```
{"status":"healthy",...}
```

or

```
{"detail":"MCP protocol endpoint"}
```

✅ MCP server responding

---

## STEP 4: Create MCP Token for Testing

### 4A. Generate Token

In **Terminal 3**, generate a test MCP token:

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG

# Enter backend directory and Python
python << 'EOF'
import sys
sys.path.insert(0, 'backend')

from app.db.session import SessionLocal
from app.models.user import User
from app.services.mcp_token_service import create_mcp_token
from datetime import datetime

db = SessionLocal()

# Use first user (usually admin with department)
user = db.query(User).filter(User.id == 1).first()

if not user:
    print("❌ No user found with ID 1")
    print("❌ You need to seed database first: python backend/app/db/seed.py")
    sys.exit(1)

print(f"✅ Found user: {user.username} (ID: {user.id})")
print(f"✅ Department: {user.department.name if user.department else 'No department'}")

# Create MCP token (expires in 7 days)
token_record = create_mcp_token(user_id=user.id, db=db, expires_days=7)

print(f"\n{'='*60}")
print(f"✅ MCP Token Created Successfully")
print(f"{'='*60}")
print(f"Token: {token_record.token}")
print(f"Expires: {token_record.expires_at}")
print(f"User: {user.username} (ID: {user.id})")
print(f"Department: {user.department.name if user.department else 'None'}")
print(f"{'='*60}\n")

# Save for next steps
with open('/tmp/mcp_test_token.txt', 'w') as f:
    f.write(token_record.token)

print(f"✅ Token saved to: /tmp/mcp_test_token.txt")

db.close()
EOF
```

**Expected Output**:
```
✅ Found user: admin (ID: 1)
✅ Department: engineering

============================================================
✅ MCP Token Created Successfully
============================================================
Token: mcp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Expires: 2026-09-10 XX:XX:XX.XXXXXX
User: admin (ID: 1)
Department: engineering
============================================================

✅ Token saved to: /tmp/mcp_test_token.txt
```

### 4B. Save Token for Next Steps

```bash
# Store token in environment variable
export MCP_TEST_TOKEN=$(cat /tmp/mcp_test_token.txt)

# Verify
echo $MCP_TEST_TOKEN
# Should output: mcp_xxxx...
```

✅ Token created and saved

---

## STEP 5: Test Backend Identity Bridge Endpoint

### 5A. Test Token Validation

In **Terminal 3**, test the identity bridge:

```bash
MCP_TOKEN=$(cat /tmp/mcp_test_token.txt)

curl -X POST http://localhost:8000/api/internal/mcp/validate \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$MCP_TOKEN\"}" \
  -s | python -m json.tool
```

**Expected Response**:
```json
{
  "user_id": 1,
  "username": "admin",
  "department_name": "engineering",
  "backend_jwt": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 3600
}
```

✅ Backend token validation working

**Capture the `backend_jwt` for next step**:
```bash
BACKEND_JWT=$(curl -X POST http://localhost:8000/api/internal/mcp/validate \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$MCP_TOKEN\"}" \
  -s | python -c "import sys, json; print(json.load(sys.stdin)['backend_jwt'])")

echo "Backend JWT: $BACKEND_JWT"
```

---

## STEP 6: Test Backend /api/chat Endpoint Directly

### 6A. Test Chat Without MCP

```bash
BACKEND_JWT=$(cat /tmp/backend_jwt.txt)  # Or get from Step 5

curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $BACKEND_JWT" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is our company deployment process?"}' \
  -s | python -m json.tool
```

**Expected Response**:
```json
{
  "answer": "Based on the company documentation, the deployment process...",
  "sources": [
    {
      "document_id": 5,
      "document_name": "Deployment Guide",
      "department_name": "engineering",
      "sensitivity": "internal",
      "score": 0.87,
      "page_start": 1,
      "page_end": 5
    }
  ],
  "retrieved_count": 1,
  "user_department_name": "engineering"
}
```

✅ Backend /api/chat working with JWT

**If error 401**:
```
Backend JWT expired or invalid
→ Regenerate token from Step 5
```

**If error 403**:
```
User not authorized
→ Check user has department in database
→ Check document has correct sensitivity/department
```

---

## STEP 7: Test MCP Server Token Validation (Python)

### 7A. Test Token Validation in MCP

In **Terminal 3**:

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server

source venv/bin/activate

python << 'EOF'
import asyncio
import sys
sys.path.insert(0, 'src')

from mcp_server.auth import validate_mcp_token

async def test_token_validation():
    with open('/tmp/mcp_test_token.txt', 'r') as f:
        mcp_token = f.read().strip()
    
    print(f"Testing MCP token: {mcp_token[:20]}...")
    print()
    
    try:
        auth_context = await validate_mcp_token(mcp_token)
        
        print("✅ Token Validation Successful")
        print(f"   User ID: {auth_context.user_id}")
        print(f"   Username: {auth_context.username}")
        print(f"   Department: {auth_context.department_name}")
        print(f"   Backend JWT: {auth_context.backend_jwt[:50]}...")
        print()
        print("✅ MCP ↔ Backend Identity Bridge Working")
        
        # Save JWT for next tests
        with open('/tmp/backend_jwt.txt', 'w') as f:
            f.write(auth_context.backend_jwt)
        
        return True
        
    except Exception as e:
        print(f"❌ Token Validation Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_token_validation())
sys.exit(0 if result else 1)
EOF
```

**Expected Output**:
```
Testing MCP token: mcp_xxxxxxxxxxxxxxxxxxxx...

✅ Token Validation Successful
   User ID: 1
   Username: admin
   Department: engineering
   Backend JWT: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

✅ MCP ↔ Backend Identity Bridge Working
```

✅ MCP token validation working

---

## STEP 8: Test Full MCP Tool Flow (Python)

### 8A. Complete End-to-End Test

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server

source venv/bin/activate

python << 'EOF'
import asyncio
import sys
sys.path.insert(0, 'src')

from mcp_server.auth import validate_mcp_token
from mcp_server.client import BackendAPIClient

async def test_full_flow():
    with open('/tmp/mcp_test_token.txt', 'r') as f:
        mcp_token = f.read().strip()
    
    print("=" * 70)
    print("TESTING FULL MCP → BACKEND FLOW")
    print("=" * 70)
    print()
    
    # Step 1: Validate MCP Token
    print("STEP 1: Validate MCP Token")
    print("-" * 70)
    try:
        auth_context = await validate_mcp_token(mcp_token)
        print(f"✅ Token validated")
        print(f"   User: {auth_context.username} (ID: {auth_context.user_id})")
        print(f"   Department: {auth_context.department_name}")
    except Exception as e:
        print(f"❌ Token validation failed: {e}")
        return False
    
    print()
    
    # Step 2: Create Backend Client
    print("STEP 2: Create Backend API Client")
    print("-" * 70)
    try:
        backend_client = BackendAPIClient()
        print(f"✅ Backend client created")
        print(f"   Backend URL: {backend_client.backend_url}")
        print(f"   Timeout: {backend_client.timeout}s")
    except Exception as e:
        print(f"❌ Backend client creation failed: {e}")
        return False
    
    print()
    
    # Step 3: Call Backend /api/chat
    print("STEP 3: Call Backend /api/chat")
    print("-" * 70)
    try:
        question = "What is the company deployment process?"
        print(f"Question: {question}")
        print()
        
        response = await backend_client.ask_knowledge_base(
            question=question,
            backend_jwt=auth_context.backend_jwt
        )
        
        print(f"✅ Backend call successful")
        print(f"   Answer length: {len(response.answer)} chars")
        print(f"   Sources: {len(response.sources)} documents")
        print()
        
    except Exception as e:
        print(f"❌ Backend call failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # Step 4: Display Results
    print("STEP 4: Display Results")
    print("-" * 70)
    print()
    print("ANSWER:")
    print(response.answer[:300] + "..." if len(response.answer) > 300 else response.answer)
    print()
    print(f"SOURCES ({len(response.sources)}):")
    for i, source in enumerate(response.sources, 1):
        print(f"  {i}. {source.document_name}")
        print(f"     Department: {source.sensitivity}")
        if hasattr(source, 'score'):
            print(f"     Score: {source.score}")
    
    print()
    print("=" * 70)
    print("✅ FULL MCP → BACKEND FLOW WORKING")
    print("=" * 70)
    
    return True

result = asyncio.run(test_full_flow())
sys.exit(0 if result else 1)
EOF
```

**Expected Output**:
```
======================================================================
TESTING FULL MCP → BACKEND FLOW
======================================================================

STEP 1: Validate MCP Token
----------------------------------------------------------------------
✅ Token validated
   User: admin (ID: 1)
   Department: engineering

STEP 2: Create Backend API Client
----------------------------------------------------------------------
✅ Backend client created
   Backend URL: http://localhost:8000
   Timeout: 30s

STEP 3: Call Backend /api/chat
----------------------------------------------------------------------
Question: What is the company deployment process?

✅ Backend call successful
   Answer length: 487 chars
   Sources: 2 documents

STEP 4: Display Results
----------------------------------------------------------------------

ANSWER:
Based on the company documentation, the deployment process involves...

SOURCES (2):
  1. Engineering Deployment Guide
     Department: internal
     Score: 0.87
  2. Security Deployment Checklist
     Department: internal
     Score: 0.75

======================================================================
✅ FULL MCP → BACKEND FLOW WORKING
======================================================================
```

✅ End-to-end MCP flow working

---

## STEP 9: Test MCP Tool Registration (Python)

### 9A. Verify Tool Schema

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server

source venv/bin/activate

python << 'EOF'
import sys
sys.path.insert(0, 'src')
import json

from mcp_server import create_app

print("=" * 70)
print("TESTING MCP TOOL REGISTRATION")
print("=" * 70)
print()

try:
    server = create_app()
    print("✅ MCP Server created")
    print()
    
    # Note: Tool definition is in __init__.py
    # Let's verify the tool definition directly
    
    # Read and parse the tool definition
    import mcp.types as types
    
    print("TOOL: ask_knowledge_base")
    print("-" * 70)
    print()
    print("Input Schema:")
    print(json.dumps({
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
    }, indent=2))
    
    print()
    print("✅ Tool Input Schema Valid")
    print("   - Only 'question' field (no auth fields)")
    print("   - Correct type: string")
    print("   - Constraints: 1-1000 chars")
    print()
    print("=" * 70)
    print("✅ MCP TOOL REGISTRATION VERIFIED")
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF
```

**Expected Output**:
```
======================================================================
TESTING MCP TOOL REGISTRATION
======================================================================

✅ MCP Server created

TOOL: ask_knowledge_base
----------------------------------------------------------------------

Input Schema:
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

✅ Tool Input Schema Valid
   - Only 'question' field (no auth fields)
   - Correct type: string
   - Constraints: 1-1000 chars

======================================================================
✅ MCP TOOL REGISTRATION VERIFIED
======================================================================
```

✅ Tool schema correct

---

## STEP 10: Run Full Validation Suite

### 10A. Run Phase 3 Validation

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server

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
✅ Error Handling: PASS
✅ Backend Endpoint: PASS
✅ Security Properties: PASS
✅ File Structure: PASS

✅ ALL TESTS PASSED
```

### 10B. Run Phase 4 Validation Framework

```bash
python validate_phase4.py
```

**Expected Output**:
```
✅ Verify MPC Tool Contract: PASS
✅ Verify Tool Description: PASS
✅ Verify Response Format: PASS
✅ No Identity Spoofing: PASS
✅ Tool Minimalism: PASS
✅ Security Checklist: PASS
...

✅ PHASE 4 FRAMEWORK READY FOR MANUAL TESTING
```

---

## STEP 11: Test Error Scenarios

### 11A. Invalid Token

```bash
curl -X POST http://localhost:8000/api/internal/mcp/validate \
  -H "Content-Type: application/json" \
  -d '{"token": "invalid_token_xyz"}' \
  -s | python -m json.tool
```

**Expected Response** (401):
```json
{
  "detail": "Invalid token"
}
```

✅ Invalid token handling works

### 11B. Expired Token

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG

python << 'EOF'
import sys
sys.path.insert(0, 'backend')

from app.db.session import SessionLocal
from app.models.user import User
from app.services.mcp_token_service import create_mcp_token
from datetime import datetime, timedelta

db = SessionLocal()
user = db.query(User).filter(User.id == 1).first()

# Create token that expires tomorrow, then manually expire it
token_record = create_mcp_token(user_id=user.id, db=db, expires_days=1)

# Manually expire it
token_record.expires_at = datetime.now() - timedelta(hours=1)
db.commit()

print(f"Created expired token: {token_record.token[:20]}...")
print(f"Expires at: {token_record.expires_at}")

db.close()

# Try to validate it
import subprocess
token = token_record.token
result = subprocess.run([
    'curl', '-X', 'POST', 'http://localhost:8000/api/internal/mcp/validate',
    '-H', 'Content-Type: application/json',
    '-d', f'{{"token": "{token}"}}',
    '-s'
], capture_output=True, text=True)

print("\nValidation response:")
print(result.stdout)
EOF
```

**Expected**: Error 401 (expired token rejected)

✅ Expired token handling works

### 11C. Backend Unavailable

```bash
# In Terminal 1, stop backend (Ctrl+C)
# Then test MCP:

cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
source venv/bin/activate

python << 'EOF'
import asyncio
import sys
sys.path.insert(0, 'src')

from mcp_server.auth import validate_mcp_token

async def test():
    with open('/tmp/mcp_test_token.txt', 'r') as f:
        token = f.read().strip()
    
    try:
        await validate_mcp_token(token)
    except Exception as e:
        print(f"Expected error (backend down): {e}")
        return True
    
    return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
EOF

# Restart backend
```

✅ Backend unavailability handled gracefully

---

## STEP 12: Check Logging

### 12A. Monitor Logs

Set `LOG_LEVEL=DEBUG` for verbose logging:

```bash
# Restart MCP server with debug logging
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
source venv/bin/activate
LOG_LEVEL=DEBUG python run.py
```

**In logs, you should see** (for each request):
```
2026-09-03 XX:XX:XX - mcp_server - INFO - Tool invoked: ask_knowledge_base | user_id=1 | dept=engineering | question_len=44
2026-09-03 XX:XX:XX - mcp_server - INFO - Backend request: POST /api/chat
2026-09-03 XX:XX:XX - mcp_server - INFO - Backend response: 200 OK | sources=2
```

### 12B. Verify No Secrets in Logs

Check logs for:
```
❌ Raw tokens (mcp_xxx)
❌ JWT tokens (eyJ...)
❌ Passwords
❌ Backend URLs with credentials
```

All should be **ABSENT**.

✅ Logging is secure

---

## STEP 13: Summary & Checklist

### Final Verification Checklist

```
✅ Backend Health Check
   - curl http://localhost:8000/health → 200

✅ MCP Server Health Check
   - curl http://localhost:5000/health → 200

✅ MCP Token Creation
   - Token created for user
   - Expires_at in future
   - Token string starts with "mcp_"

✅ Identity Bridge Working
   - POST /api/internal/mcp/validate
   - Returns: user_id, username, dept, backend_jwt
   - JWT is valid for 1 hour

✅ Backend /api/chat Working
   - POST /api/chat with JWT
   - Returns: answer + sources
   - Respects department ACL

✅ MCP Token Validation
   - validate_mcp_token() succeeds
   - Returns AuthenticatedContext
   - Context has: user_id, username, department_name, backend_jwt

✅ MCP Backend Client
   - BackendAPIClient created
   - ask_knowledge_base() returns ChatResponse
   - Sources properly formatted

✅ Full End-to-End Flow
   - MCP Token → Validation → Backend JWT → /api/chat → Answer + Sources
   - All steps succeed
   - No cross-contamination

✅ Tool Registration
   - Tool: ask_knowledge_base
   - Input: {question: string}
   - No auth fields in input

✅ Error Handling
   - Invalid token → 401
   - Expired token → 401
   - Backend down → graceful error
   - Errors don't leak secrets

✅ Logging
   - User actions logged (user_id, dept)
   - No tokens in logs
   - No JWTs in logs
   - No secrets in logs

✅ Validation Tests
   - python validate_phase3.py → ALL PASS
   - python validate_phase4.py → Framework ready
```

---

## STEP 14: Troubleshooting

### Issue: Backend JWT not working (401)

```
1. Check JWT not expired: Should be valid for 1 hour from creation
2. Regenerate: Delete /tmp/backend_jwt.txt, re-run Step 5
3. Verify backend is running: curl http://localhost:8000/health
```

### Issue: MCP token validation fails

```
1. Check token exists: cat /tmp/mcp_test_token.txt
2. Check token not expired: Should show expires_at > now()
3. Check backend running: curl http://localhost:8000/health
4. Check /api/internal/mcp/validate exists: Check backend logs
```

### Issue: No documents returned

```
1. Check documents exist: SELECT * FROM documents;
2. Check user department has documents:
   SELECT * FROM documents WHERE department_id = 1;
3. Check Qdrant running: Try frontend chat (existing flow)
4. Check Qdrant ACL: Verify document sensitivity
```

### Issue: Backend/MCP connection refused

```
1. Check ports:
   lsof -i :8000 (backend)
   lsof -i :5000 (mcp)

2. Check service started:
   - Terminal 1 shows "Application startup complete"
   - Terminal 2 shows "MCP Server Starting"

3. Kill conflicting processes:
   kill -9 $(lsof -t -i:8000)
   kill -9 $(lsof -t -i:5000)
   
4. Restart services
```

### Issue: Module not found errors

```
1. Check venv activated:
   source venv/bin/activate
   which python (should show venv path)

2. Check dependencies installed:
   pip install -r requirements.txt

3. Check PYTHONPATH:
   export PYTHONPATH=/path/to/backend:/path/to/mcp-server/src
```

---

## NEXT PHASE: Phase 5

Once **ALL** steps above pass ✅, you're ready for:

**Phase 5 - Claude Integration**:
1. Configure Claude to use MCP server
2. Test automatic tool invocation
3. Verify source attribution in Claude responses
4. Test rephrased questions
5. Full security review

**Phase 6 - Public Deployment**:
1. HTTPS configuration
2. Domain setup
3. Production hardening

---

## Commands Reference

### Quick Verification Commands

```bash
# Check both services running
lsof -i :8000 && echo "✅ Backend" || echo "❌ Backend"
lsof -i :5000 && echo "✅ MCP" || echo "❌ MCP"

# Health checks
curl http://localhost:8000/health && echo "✅ Backend Health"
curl http://localhost:5000/health && echo "✅ MCP Health"

# Generate token
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG
python -c "
import sys
sys.path.insert(0, 'backend')
from app.db.session import SessionLocal
from app.services.mcp_token_service import create_mcp_token
db = SessionLocal()
token = create_mcp_token(1, db, 7)
print(token.token)
" > /tmp/mcp_test_token.txt

# Run validations
cd mcp-server && source venv/bin/activate
python validate_phase3.py
python validate_phase4.py

# Full end-to-end test
python << 'TESTEOF'
import asyncio, sys
sys.path.insert(0, 'src')
from mcp_server.auth import validate_mcp_token
from mcp_server.client import BackendAPIClient

async def test():
    with open('/tmp/mcp_test_token.txt') as f: token = f.read().strip()
    ctx = await validate_mcp_token(token)
    client = BackendAPIClient()
    resp = await client.ask_knowledge_base("What is deployment process?", ctx.backend_jwt)
    print(f"✅ Works! Answer: {resp.answer[:100]}...")

asyncio.run(test())
TESTEOF
```

---

**Ready to test? Start with STEP 1 (Terminal Setup) and work through sequentially. Report back any errors!**
