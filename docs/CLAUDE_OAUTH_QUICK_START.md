# Quick Start: Configure Claude MCP with OAuth

## TL;DR (30 seconds setup)

### 1. Ensure Backend is Running
```bash
# Backend on port 8000
cd backend
python -m uvicorn app.main:app --port 8000 --reload
```

### 2. Ensure MCP Server is Running
```bash
# MCP on port 5001
cd mcp-server
python run.py
```

### 3. Create a Test User (if none exists)

**Option A: Via SQL**
```sql
-- Create department
INSERT INTO departments (name) VALUES ('Engineering') 
ON CONFLICT (name) DO NOTHING;

-- Create user
INSERT INTO users (username, password_hash, department_id) 
VALUES (
  'test.user',
  -- Hash of 'TestPassword123' using your password hasher
  '$2b$12$...',
  (SELECT id FROM departments WHERE name = 'Engineering')
);
```

**Option B: Via Backend API**
```bash
# First create department
curl -X POST http://localhost:8000/api/departments \
  -H "Content-Type: application/json" \
  -d '{"name": "Engineering"}'

# Then create user (requires admin token)
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test.user",
    "password": "TestPassword123",
    "department_id": 1
  }'
```

### 4. Test Login Page
```bash
# Visit login page
open http://localhost:5001/auth/login

# Test credentials
Username: test.user
Password: TestPassword123

# Should see MCP token displayed
```

### 5. Configure Claude

**Via Claude.ai:**
1. Go to **claude.ai** → **Account Settings**
2. Scroll to **Connected Integrations**
3. Click **+ Add custom connector**
4. Fill form:
   ```
   Name: Secure RAG
   URL: http://localhost:5001/mcp
   Authentication: "Always required" ⭐ (IMPORTANT!)
   ```
5. Click **Connect**

**Via Claude Desktop App:**
1. Open Claude app → **Settings** (gear icon)
2. Go to **Extensions**
3. Click **Add Custom MCP Server**
4. Choose **HTTP** transport:
   ```
   Name: Secure RAG
   URL: http://localhost:5001/mcp
   ```
5. Click **Add**

### 6. Test Authentication Flow

1. **In Claude**, ask a question like: "What documents do I have access to?"
2. Claude will redirect you to: `http://localhost:5001/auth/login?oauth_client_id=...`
3. **Login** with your test credentials
4. You'll be **auto-redirected back** to Claude
5. Claude will **ask your question** with your token
6. You'll get results **filtered by your department** ✅

## Expected OAuth Redirect Flow

```
You: "List my documents"
       ↓
Claude: Initiates OAuth (no token yet)
       ↓
Server: Redirects to login page
       ↓
You: Enter credentials & login
       ↓
Server: Validates, generates MCP token
       ↓
Server: Redirects back to Claude with auth code
       ↓
Claude: Exchanges code for token
       ↓
Claude: Calls MCP with token
       ↓
You: Get results filtered to your department
```

## Verify Each Component

### Check Backend
```bash
curl http://localhost:8000/api/health
# Should return: {"status":"ok"}
```

### Check MCP Health
```bash
curl http://localhost:5001/health
# Should return: {"status":"healthy","service":"MCP Server","version":"0.2.0"}
```

### Check OAuth Discovery
```bash
curl http://localhost:5001/.well-known/oauth-authorization-server | jq .token_endpoint
# Should return: "/oauth/token"
```

### Check Login Page
```bash
curl -s http://localhost:5001/auth/login | grep -i "secure rag"
# Should see HTML form
```

## Common Issues

| Issue | Fix |
|-------|-----|
| 401 Unauthorized | User token not found. Create a new user and login. |
| Login page doesn't load | Check MCP server is running on port 5001 |
| Wrong department documents | Verify backend ACL filtering in `retrieval.py` |
| "Connection refused" | Check both backend (8000) and MCP (5001) ports |
| Token keeps expiring | Normal - tokens expire after 7 days. Login again. |

## Production Deployment (Render)

### Update MCP_PUBLIC_URL
```bash
# In .env or Render settings
MCP_PUBLIC_URL=https://secure-rag-mcp.onrender.com
```

### Configure Claude with Production URL
```
Name: Secure RAG
URL: https://secure-rag-mcp.onrender.com/mcp
Authentication: "Always required"
```

### Test Production Flow
1. Configure Claude with production URL
2. Ask a question
3. Should redirect to production login page
4. After login, token should work with production MCP
5. Results filtered by department

## Architecture Summary

```
┌─────────────┐
│   Claude    │
└──────┬──────┘
       │ (1) OAuth initiate
       ▼
┌─────────────────────┐
│   MCP Server        │
│  (port 5001)        │
├─────────────────────┤
│ /oauth/authorize    │───┐
│ /auth/login         │   │ (2) Redirect to login
│ /oauth/token        │   │
│ /mcp                │   │
└─────────┬───────────┘   │
          │               │
          │ (3) User logs in
          ▼
┌─────────────────────┐
│   Login Form        │
│   (HTML)            │
└────────┬────────────┘
         │
         │ (4) Validate credentials
         ▼
┌─────────────────────┐
│  FastAPI Backend    │
│  (port 8000)        │
├─────────────────────┤
│ /api/auth/login     │
│ /api/chat           │
│ /api/retrieval      │
└────────┬────────────┘
         │
         │ (5) Query database
         ▼
┌─────────────────────┐
│   PostgreSQL        │
│   ┌─────────────┐   │
│   │ users       │   │
│   │ departments │   │
│   │ documents   │   │
│   │ mcp_tokens  │   │
│   └─────────────┘   │
└─────────────────────┘
         │
         │ (6) Check department
         │     Filter docs
         ▼
┌─────────────────────┐
│   Qdrant Vector DB  │
│   (with dept filter)│
└──────────┬──────────┘
           │
           │ (7) Return filtered results
           ▼
      Claude & You 🎉
```

## What's Happening Under the Hood

1. **OAuth Discovery** (`/.well-known/oauth-authorization-server`)
   - Claude reads this to find authorization and token endpoints
   - Tells Claude how to authenticate users

2. **Authorization Request** (`GET /oauth/authorize`)
   - Claude redirects to this endpoint
   - MCP redirects to login page with OAuth parameters

3. **User Authentication** (`POST /auth/login-api`)
   - Login form submits credentials
   - Backend validates password against bcrypt hash
   - Backend generates MCP token

4. **Token Exchange** (`POST /oauth/token`)
   - Claude sends authorization code
   - MCP decodes to get MCP token
   - Returns token to Claude

5. **MCP Requests** (`POST /mcp`)
   - Claude sends requests with `Authorization: Bearer mcp_...`
   - MCP validates token, gets user department
   - Backend filters results by department

6. **Department-Based ACL**
   - Every database query checks: `user.department_id`
   - Qdrant payloads include department filter
   - Users only see their department's documents

## Next Steps

- [ ] Create test users for each department
- [ ] Test login page with each user
- [ ] Test MCP with manual token requests
- [ ] Configure Claude connector
- [ ] Test end-to-end with Claude
- [ ] Create FAQ for users
- [ ] Set up monitoring/logging
- [ ] Configure token expiry policy

**Questions?** Check [CLAUDE_OAUTH_SETUP.md](./CLAUDE_OAUTH_SETUP.md) for detailed flow explanation.
