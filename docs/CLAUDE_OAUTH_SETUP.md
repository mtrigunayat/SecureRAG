# Claude MCP Integration via OAuth - Complete Setup Guide

## The Answer: OAuth "Always Required" Flow ✅

Claude offers an **"Always required" authentication option** that uses OAuth 2.0. This is **exactly what we need** to handle multi-user authentication!

### How It Works

```
Claude                          Your MCP Server               Your Backend
  │                                   │                            │
  ├─ Initiates OAuth ────────────────>│                            │
  │  (wants authorization code)       │                            │
  │                                   │                            │
  │<──────────── Redirect to Login ────┤                            │
  │  (https://server/auth/login)       │                            │
  │                                   │                            │
  ├─ User enters credentials ────────>│                            │
  │                                   ├─ Validate password ───────>│
  │                                   │<─ OK, issue MCP token ─────┤
  │                                   │                            │
  │<───── Authorization Code ─────────┤                            │
  │  (base64-encoded MCP token)        │                            │
  │                                   │                            │
  ├─ Exchange code for token ────────>│                            │
  │                                   ├─ Decode code ─────────────>│
  │<─── Access Token (MCP Token) ──────┤                            │
  │                                   │                            │
  ├─ Use token in requests ──────────>│                            │
  │  (Authorization: Bearer mcp_...) │                            │
  │                                   ├─ Validate token ──────────>│
  │<──── Tool Results + ACL Filter ────┤<─ Check department ────────┤
  │                                   │                            │
```

## Step-by-Step: Connect Claude via OAuth

### Step 1: Configure MCP in Claude

1. Open Claude (claude.ai or Claude desktop app)
2. Go to **Model Settings** → **Connected Applications**
3. Click **+ Add custom connector**
4. Fill in:
   - **Name**: `Secure RAG`
   - **URL**: `https://secure-rag-mcp.onrender.com/mcp` (or your production URL)
   - **Authentication**: Select **"Always required"** ⭐ (This is the key!)

### Step 2: Test OAuth Discovery

The "Always required" option will:
1. Auto-discover OAuth metadata from `/.well-known/oauth-authorization-server`
2. Display settings for OAuth client configuration
3. Choose: **"Use Anthropic's hosted client metadata"** (default is fine)

### Step 3: User Authentication Flow

When you first ask Claude a question:

1. Claude initiates OAuth authorization request
2. **You're redirected to login page**: `https://secure-rag-mcp.onrender.com/auth/login`
3. **Enter your credentials** (username/password from database)
4. **Backend validates** against PostgreSQL user table
5. **MCP token generated** with your department info
6. **Auto-redirected back** to Claude with authorization code
7. **Claude exchanges code for token** (happens automatically)
8. **Claude now has your department-specific token** ✅

### Step 4: Department-Based Access Control

After authentication:
- Token contains: `user_id`, `username`, `department`
- When you ask questions, token is sent with every request
- Backend filters documents: `WHERE department = user's_department`
- You only see your department's documents!

## Authentication Architecture

### Three Layers of Security

```
Layer 1: OAuth 2.0 (Public)
├─ Endpoint: /oauth/authorize (public)
├─ Endpoint: /oauth/token (public)
└─ Endpoint: /.well-known/oauth-authorization-server (public)
    → Handles authentication flow and token exchange

Layer 2: MCP Token (Semi-Public)
├─ Format: mcp_<32-random-bytes>
├─ Stored: SHA-256 hash in database
├─ Expires: 7 days
└─ Used: In Authorization header for all MCP requests
    → Identifies user and department

Layer 3: Backend ACL (Private)
├─ Database: PostgreSQL
├─ Check: User department on every query
├─ Filter: Documents by department
└─ Enforce: Cannot access other departments
    → Data is source of truth for access control
```

## Detailed Flow Explanation

### Phase 1: OAuth Authorization

```
GET /oauth/authorize
  ?response_type=code
  &client_id=claude
  &redirect_uri=https://claude.ai/callback
  &scope=mcp:ask_knowledge_base
  &state=<random>

Response: 302 Redirect to /auth/login
```

MCP Server redirects user to login page with OAuth parameters.

### Phase 2: User Authentication

```
User visits: /auth/login?oauth_client_id=claude&...

User submits form:
  POST /auth/login-api
  {
    "username": "john",
    "password": "secret123"
  }

Backend validates:
  ✓ User exists in database
  ✓ Password matches (bcrypt comparison)
  ✓ Department found

Server generates MCP token:
  Token: mcp_ABC123...XYZ
  Hash: SHA256(token)
  Store in database with user_id, department_id, expiry
```

### Phase 3: Authorization Code Response

```
Login successful!

Server encodes token as authorization code:
  code = base64(mcp_token)
  code = "bWNwX0FCQzEyMz4uLi5YWVo="

Redirect to Claude callback:
  302 https://claude.ai/callback?code=bWNwX0FCQzEyMz4uLi5YWVo=&state=...

Claude receives authorization code ✅
```

### Phase 4: Token Exchange

```
Claude sends to MCP Server:
  POST /oauth/token
  {
    "grant_type": "authorization_code",
    "code": "bWNwX0FCQzEyMz4uLi5YWVo=",
    "client_id": "claude"
  }

Server decodes:
  mcp_token = base64_decode(code)
  Validates token exists in database
  Validates not expired, not revoked

Server responds:
  {
    "access_token": "mcp_ABC123...XYZ",
    "token_type": "Bearer",
    "expires_in": 604800
  }

Claude stores token ✅
```

### Phase 5: MCP Requests with Token

```
Claude sends question to MCP:
  POST /mcp
  Authorization: Bearer mcp_ABC123...XYZ
  {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "ask_knowledge_base",
      "arguments": {
        "question": "What's the deployment process?"
      }
    }
  }

MCP Server:
  ✓ Validates token from header
  ✓ Gets user_id and department
  ✓ Calls backend with authenticated context
  
Backend:
  ✓ Queries Qdrant for documents
  ✓ Filters: WHERE department = 'Engineering'
  ✓ Returns only Engineering documents
  
Claude receives answer ✅
```

## Key Benefits of This Approach

| Aspect | Benefit |
|--------|---------|
| **No Manual Token Copy** | Token automatically handled via OAuth |
| **Multi-User Support** | Each user has their own token |
| **Department-Based ACL** | Users only see their department's docs |
| **Automatic Expiry** | Tokens expire after 7 days (secure) |
| **Revocation Support** | Admin can revoke tokens immediately |
| **Standard OAuth** | Compatible with Claude's UI |
| **Stateless** | Token carries all needed info |

## Troubleshooting OAuth Flow

### Issue: "Connect without credentials first"
- **Cause**: Selected wrong auth option
- **Fix**: Make sure you selected **"Always required"** OAuth option

### Issue: Redirect loops
- **Cause**: OAuth state mismatch
- **Fix**: Check if `oauth_state` parameter is preserved through redirect

### Issue: "Invalid authorization code"
- **Cause**: Code encoding/decoding issue
- **Fix**: Check base64 encoding in login form and token endpoint

### Issue: Token works once then fails
- **Cause**: Token expired or revoked
- **Fix**: Log in again to get fresh token

### Issue: Wrong department documents showing
- **Cause**: ACL not enforced in backend
- **Fix**: Verify backend filters by department on every query

## Testing the Complete Flow

### Test 1: Login Page Direct Access
```bash
# Visit login page directly
open http://localhost:5001/auth/login

# Enter test credentials
Username: john
Password: engineering123

# Should see token with department info
```

### Test 2: OAuth Discovery
```bash
# Check OAuth metadata
curl -s http://localhost:5001/.well-known/oauth-authorization-server | jq

# Should show:
# - token_endpoint: /oauth/token
# - authorization_endpoint: /oauth/authorize
```

### Test 3: Full OAuth Flow (Manual)
```bash
# Step 1: Start authorization
curl -L "http://localhost:5001/oauth/authorize?response_type=code&client_id=test&redirect_uri=http://localhost:3000/callback"

# Should redirect to login page
# Login, get authorization code
# Code will be in URL: http://localhost:3000/callback?code=...

# Step 2: Exchange code for token
curl -X POST http://localhost:5001/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "code": "<authorization-code-from-step-1>",
    "client_id": "test"
  }'

# Should receive access_token
```

### Test 4: Claude Integration
1. Configure MCP with "Always required" OAuth
2. Ask a question in Claude
3. Claude redirects you to login
4. Login and authorize
5. Claude gets token and asks your question
6. Answer returned with department filter applied ✅

## Production Deployment Checklist

- [ ] HTTPS enabled (OAuth requires secure URLs)
- [ ] Backend `/api/auth/login` endpoint working
- [ ] Database users created with departments
- [ ] MCP token generation tested
- [ ] OAuth metadata accessible
- [ ] Login page accessible
- [ ] Token exchange working
- [ ] ACL filtering in backend verified
- [ ] Token expiry set (7 days default)
- [ ] MCP public URL set correctly

## Quick Reference: URLs

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `GET /health` | Health check | No |
| `GET /auth/login` | Login form | No |
| `POST /auth/login-api` | Submit credentials | No |
| `GET /oauth/authorize` | OAuth start | No |
| `POST /oauth/token` | Exchange code for token | No |
| `GET /.well-known/oauth-authorization-server` | OAuth metadata | No |
| `POST /mcp` | MCP requests | **Yes** (Bearer token) |

## Summary

**You were right to ask about token delivery!** The answer is Claude's **OAuth "Always required"** option:

1. ✅ User doesn't enter token manually
2. ✅ OAuth handles authentication flow
3. ✅ Token generated after login
4. ✅ Token automatically sent with requests
5. ✅ Department-based ACL enforced
6. ✅ Multi-user support built-in
7. ✅ Tokens expire automatically
8. ✅ Users can log in anytime to get new token

**Next step**: Select **"Always required"** OAuth when configuring Claude connector! 🎯
