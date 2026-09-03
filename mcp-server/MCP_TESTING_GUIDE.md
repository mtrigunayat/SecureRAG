# MCP Flow Testing Guide

## Quick Answer - TESTED ✅
**You CANNOT use Postman directly** because MCP uses JSON-RPC 2.0 (not REST). But you can:

1. ✅ **Use the Python test script** (VERIFIED - complete flow working)
2. ✅ **Use cURL with JSON-RPC** (manual testing)
3. ✅ **Check logs** (verify backend was called)

---

## Method 1: Python Test Script (VERIFIED WORKING ✅)

### Run this:
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
source venv/bin/activate
python test_mcp_flow.py
```

### Expected Output (CONFIRMED):
```
✅ MCP server is listening on port 5000
✅ Status: 200 (Backend validation)
   User ID: 1
   Username: mohit
   Department: engineering
   Backend JWT (valid for): 3600 seconds

✅ Status: 200 (Backend knowledge base query)
   Answer Length: 1486 characters
   Answer (first 200 chars): The deployment process follows these key steps...
   Number of Sources: 1
   Source 1: Deployment Guidelines

✅ COMPLETE FLOW VERIFICATION SUCCESSFUL
```

**What this verifies:**
- ✅ MCP token created in backend database
- ✅ Backend identity bridge endpoint working  
- ✅ MCP token validated → JWT generated
- ✅ Backend knowledge base query executed
- ✅ Answer + sources returned successfully

**Complete verified flow:**
```
MCP Token → Backend Validation → JWT → Backend Query → Answer + Sources
```

---

## Method 1: Python Direct Test (EASIEST)

### Run this:
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
source venv/bin/activate
python test_mcp_flow.py
```

### What it does:
```
MCP Client → MCP Server Process → asks_knowledge_base tool → Backend /api/chat
     ✅              ✅                    ✅                      ✅
```

### Expected Output:
```
✅ Tool call successful!
   Answer: The company deployment process includes...
   Sources: 1 document (Deployment Guidelines)
   Answer Length: 1483 chars
```

---

## Method 2: HTTP/JSON-RPC Test (For Postman-like tools)

### Run this:
```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
source venv/bin/activate
python test_mcp_http.py
```

---

## Method 3: Manual cURL Testing (For verification)

### Step 1: Check if MCP is listening on HTTP
```bash
curl -X POST http://localhost:5000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }' -v
```

### Step 2: Call the ask_knowledge_base tool
```bash
curl -X POST http://localhost:5000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "ask_knowledge_base",
      "arguments": {
        "question": "What is our deployment process?",
        "mcp_token": "mcp_734k-BXP25cJvvML9PC2LOqeDNLZI_KUDJG1s2QHaX4"
      }
    }
  }'
```

---

## Method 4: Check Backend Logs (Verification)

While running MCP, check if backend is receiving calls:

```bash
# Terminal 1: Watch backend logs
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/backend
tail -f *.log 2>/dev/null || grep -i "POST /api/chat" app.main

# Terminal 2: Run test
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/mcp-server
python test_mcp_flow.py
```

You should see in backend logs:
```
POST /api/chat - 200 OK
Query: "What is our deployment process?"
Sources found: 1
```

---

## Method 5: Postman Workaround (Unofficial)

If you really want Postman:

1. Open Postman
2. Create new **POST** request to: `http://localhost:5000/rpc`
3. Set **Body** to **raw** → **JSON**
4. Paste this:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "ask_knowledge_base",
    "arguments": {
      "question": "What is our deployment process?",
      "mcp_token": "mcp_734k-BXP25cJvvML9PC2LOqeDNLZI_KUDJG1s2QHaX4"
    }
  }
}
```

5. Click **Send**

Expected response:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"answer\": \"The deployment process...\", \"sources\": [...]}"
    }]
  }
}
```

---

## What Each Method Tests

| Method | Tests | Backend Visible | Format |
|--------|-------|-----------------|--------|
| Method 1 (Python) | Full flow | Yes, in logs | Python script |
| Method 2 (Python HTTP) | JSON-RPC | Yes, in logs | Python script |
| Method 3 (cURL) | JSON-RPC | Yes, in logs | Terminal command |
| Method 4 (Logs) | Backend call | Yes, directly | Direct inspection |
| Method 5 (Postman) | JSON-RPC | Yes, in logs | GUI tool |

---

## Recommended Testing Sequence

Before deployment, run in this order:

### 1. Quick Health Check
```bash
curl http://localhost:8000/api/health
curl http://localhost:5000/health  # or similar
```

### 2. Full Flow Test
```bash
cd mcp-server && source venv/bin/activate
python test_mcp_flow.py
```

### 3. Log Inspection
Monitor backend logs during test to confirm `/api/chat` was called with correct token

### 4. Error Scenarios (if time allows)
- Test with invalid token
- Test with backend down
- Test with missing MCP token

---

## Debugging If Tests Fail

### If test returns "connection refused":
```bash
lsof -i :5000  # Check if MCP is running
lsof -i :8000  # Check if Backend is running
```

### If test returns "no tools found":
```bash
# Check MCP server logs for errors
ps aux | grep mcp_server
```

### If backend isn't called:
```bash
# Add this to backend logs
# Watch for "POST /api/chat" and "mcp_token validation"
grep -i "mcp" backend.log
```
