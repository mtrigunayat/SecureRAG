# Multi-User Authentication & ACL Integration for Claude

## Problem Statement

Previously, we had a 401 Unauthorized issue because:
- Claude's "None Detected" auth option has no UI field for Bearer tokens
- MCP server required Bearer tokens for tool access
- Users couldn't authenticate, so tools failed with 401

## Solution: User Authentication Flow

Now we have a **complete authentication system** that solves this:

### Step 1: User Authentication Portal
Users visit: `http://localhost:5001/auth/login` (or production URL)

Features:
- Beautiful login form (styled web UI)
- Enter username/password
- Backend validates credentials against user database
- If valid: Generate MCP token and display it
- User copies the token

### Step 2: Department-Based Token
When a token is generated:
```
Token Format: mcp_<random-32-bytes-base64>
Associated With: User ID → Department (via database)
```

Example:
- User: "john" (department: "Engineering")
- Token: `mcp_ABC123...XYZ`
- When used in MCP: Gets "Engineering" department context
- RAG backend filters documents by department

### Step 3: Claude Configuration with Real Tokens

**Current Status:**
- MCP server accepts requests without tokens (demo user for testing)
- MCP server also accepts valid Bearer tokens from authenticated users

**For Real Users:**
1. User logs in at `/auth/login`
2. Copies their token
3. In Claude: Model Settings → Connected Applications → Secure RAG
4. Click Edit → Click "Edit" on Authentication
5. Select an auth method that supports Bearer tokens
6. Paste token value
7. Save

**Note:** Claude's "None Detected" option still has no field for tokens, so we need to use an alternative auth method in Claude's UI (custom auth, basic auth, or similar).

### Step 4: Department-Based Access Control

When user queries Claude:
```
User: "What deployment process should I follow?"
    ↓
Claude sends tool call to MCP: `ask_knowledge_base`
    ↓
MCP server validates token → Gets user context (user_id, dept="Engineering")
    ↓
Sends to backend with authenticated JWT
    ↓
Backend queries Qdrant for documents WHERE department="Engineering"
    ↓
Returns only Engineering documents + sources
    ↓
Claude displays answer with proper attribution
```

## Architecture: Authentication Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Claude (via MCP)                                            │
└────────────┬────────────────────────────────────────────────┘
             │ Request with Bearer token
             ▼
┌─────────────────────────────────────────────────────────────┐
│ MCP Server (/mcp)                                           │
│ - Validates token against backend                           │
│ - Creates AuthenticatedContext                              │
│ - Stores in request scope via ContextVar                    │
└────────────┬────────────────────────────────────────────────┘
             │ Makes API call with JWT
             ▼
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Backend (/api/chat)                                 │
│ - Receives JWT from MCP                                     │
│ - Extracts user_id, department                              │
│ - Queries database for user/department                      │
│ - Filters documents by department                           │
│ - Returns filtered results                                  │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Qdrant Vector DB (document search)                          │
│ - Semantic search by embedding                              │
│ - Filter by department (payload metadata)                   │
└─────────────────────────────────────────────────────────────┘
```

## User Flows

### Flow 1: New User Getting Started

```
1. User visits: http://localhost:5001/auth/login

2. User enters credentials:
   - Username: john
   - Password: secret123

3. Backend validates → Success!
   - User found in database
   - Password matches (hashed comparison)
   - Department: Engineering

4. MCP generates token:
   - Creates new entry in mcp_tokens table
   - Stores user_id, token_hash, expires_at
   - Returns token: mcp_TLDwkb...sIw

5. User copies token and saves it

6. User configures Claude:
   - Opens Claude Settings
   - Finds "Secure RAG" MCP connection
   - Enters token in auth field
   - Saves

7. User asks Claude a question
   → Claude queries MCP with token
   → MCP validates token → user = Engineering
   → Backend returns Engineering docs only
   → Claude displays answer
```

### Flow 2: Invalid Credentials

```
1. User enters wrong password
2. Backend returns: 401 Unauthorized
3. Login page shows error
4. User can retry
5. No token generated
```

### Flow 3: Token Expiry

```
1. Token created with 7-day expiry
2. After 7 days, token is invalid
3. MCP returns: 401 Invalid token
4. Claude tools stop working
5. User logs in again to get new token
6. Updates Claude configuration
```

## Authentication States

### State 1: No Token (Demo Mode)
```
Request: POST /mcp (no Authorization header)
Response: Uses demo context (user_id=1, department="Engineering")
Use Case: Testing, development
Security: Limited to Engineering documents
```

### State 2: Valid Token (Authenticated User)
```
Request: POST /mcp with Authorization: Bearer mcp_ABC123...
MCP validates token → Gets user context
Response: Uses real user context (user_id from DB, dept from DB)
Use Case: Production Claude usage
Security: Full department-based ACL
```

### State 3: Invalid/Expired Token
```
Request: POST /mcp with Authorization: Bearer mcp_INVALID
MCP tries to validate → Backend returns 401
Response: Error response to Claude
Use Case: Token expired or wrong
Security: Denied access
```

## Environment Variables Needed

Add to `.env` or production configuration:

```bash
# MCP Server Config
MCP_HOST=0.0.0.0
MCP_PORT=5001
MCP_PUBLIC_URL=http://localhost:5001  # or production URL

# Backend Connection
BACKEND_URL=http://localhost:8000     # or production URL
BACKEND_TIMEOUT=30

# Optional: Internal service key for token generation
INTERNAL_SERVICE_KEY=mcp-internal-key-12345
```

## Testing the Authentication

### Test 1: Login and Get Token

```bash
# Visit the login page
open http://localhost:5001/auth/login

# Or test via API
curl -X POST http://localhost:5001/auth/login-api \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "engineering123"}'

# Response:
{
  "success": true,
  "message": "Login successful...",
  "mcp_token": "mcp_TLDwkb...",
  "user_id": 2,
  "username": "john",
  "department": "Engineering"
}
```

### Test 2: Use Token in MCP Request

```bash
curl -X POST http://localhost:5001/mcp \
  -H "Authorization: Bearer mcp_TLDwkb..." \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'

# Response: Tools available (authenticated as Engineering user)
```

### Test 3: Invalid Token

```bash
curl -X POST http://localhost:5001/mcp \
  -H "Authorization: Bearer mcp_INVALID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Response: 401 Unauthorized
```

## Security Considerations

### Token Storage
- ✅ Tokens stored as SHA-256 hashes in database
- ✅ Raw token never stored
- ✅ Only token provider knows the real token

### Token Expiry
- ✅ Tokens expire after 7 days
- ✅ Database can revoke tokens immediately
- ✅ Users get new tokens by logging in again

### ACL Enforcement
- ✅ Backend validates user department on every request
- ✅ User cannot override their department
- ✅ User cannot see other department's documents

### Transport Security
- ✅ Tokens sent via HTTPS (on production)
- ✅ Bearer tokens in Authorization header (not in URL)
- ✅ MCP server validates token before processing

## Next Steps

### 1. Verify Login Page Works
```bash
# Make sure MCP server is running
cd mcp-server && python run.py

# Visit login page
open http://localhost:5001/auth/login

# Test login with a database user
```

### 2. Generate User Tokens
```bash
# Create test users if needed
python backend/scripts/manage_db.py --seed

# Login and get tokens for each user
```

### 3. Configure Claude
- Open Claude/AI client settings
- Find "Secure RAG" MCP connection
- Update with real token (not demo token)
- Save and test

### 4. Monitor ACL Enforcement
- Log in as Engineering user → should see Engineering docs
- Log in as Sales user → should see Sales docs only
- Verify cross-department documents are filtered

## Troubleshooting

### Issue: Login page shows "Backend service unavailable"
- **Cause**: FastAPI backend not running
- **Fix**: `cd backend && python run.py`

### Issue: Login fails with "Invalid username or password"
- **Cause**: Wrong credentials OR user doesn't exist
- **Fix**: Check database for user record, verify password

### Issue: Token works locally but not on production
- **Cause**: MCP_PUBLIC_URL or BACKEND_URL misconfigured
- **Fix**: Check environment variables on Render deployment

### Issue: Claude still gets "No Tools" after token entry
- **Cause**: Token format wrong or Claude UI auth incompatible
- **Fix**: Verify token starts with `mcp_`, check Claude auth method

## Summary

**Before**: Unauthenticated requests → single demo user → all users see same documents

**After**: 
- Users authenticate via `/auth/login`
- Each user gets their own department-specific token
- Claude sends token when querying MCP
- Backend enforces ACL: "You can only see your department's documents"
- Multi-user, multi-department RAG system ✅
