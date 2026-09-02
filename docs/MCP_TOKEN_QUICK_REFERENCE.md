# MCP Token System — Quick Reference

**Phase 2 Implementation**  
**Status**: ✅ Complete

---

## What is an MCP Token?

An MCP (Model Context Protocol) token is a **long-lived authentication credential** that allows remote applications (e.g., Claude via MCP) to authenticate as a specific user in the SecureRAG backend.

### Key Properties

| Property | Value |
|----------|-------|
| **Type** | Opaque, randomly generated |
| **Format** | `mcp_<32-bytes-random>` |
| **Lifetime** | 365 days (configurable) |
| **Storage** | Only cryptographic hash (SHA-256) |
| **Revocation** | Immediate, immutable |
| **Audit Trail** | Yes (created_by, last_used_at, revoked_at) |
| **User Binding** | Exactly one user per token |
| **Department** | From database (cannot override) |

---

## Token Lifecycle

```
1. ADMIN CREATES TOKEN
   └─ python -m scripts.mcp_token_manager --action create --user-id 1
   └─ Service: generates random string, hashes it, stores hash
   └─ Returns: raw token (only time it's shown)

2. USER STORES TOKEN SECURELY
   └─ In .env file, Anthropic platform, credential manager
   └─ NOT in code, NOT in git

3. MCP CLIENT USES TOKEN
   └─ Includes token in request to MCP server
   └─ MCP server passes token to backend

4. BACKEND VALIDATES TOKEN
   └─ Hash token
   └─ Look up hash in database
   └─ Check: not revoked, not expired, user exists, has department
   └─ Return: User object with department

5. MCP SERVER EXCHANGES FOR JWT (Phase 3)
   └─ Calls /internal/mcp/exchange with MCP token
   └─ Receives JWT (short-lived)
   └─ Uses JWT in requests to /api/chat, /api/retrieval

6. ADMIN REVOKES TOKEN (if needed)
   └─ python -m scripts.mcp_token_manager --action revoke --token-id 5
   └─ Immediate effect (no delay)
   └─ Cannot be undone
```

---

## Using the Service

### Generate Token (Admin)

```python
from app.db.session import SessionLocal
from app.services.mcp_token_service import create_mcp_token_for_user

db = SessionLocal()
raw_token = create_mcp_token_for_user(
    user_id=1,
    db=db,
    description="Claude personal",
    created_by_user_id=1,  # admin user
    created_via="cli"
)
print(raw_token)  # mcp_xK9vL2mQ8pR5sTu3VwXyZ1aB2cD4eF5gH6iJ7kL8mN9oP0qR
```

### Validate Token (MCP Server)

```python
from app.db.session import SessionLocal
from app.services.mcp_token_service import validate_mcp_token

db = SessionLocal()
try:
    user = validate_mcp_token(raw_token, db)
    print(f"Authenticated: {user.username}")
    print(f"Department: {user.department.name}")
except AuthenticationError:
    print("Invalid token")
```

### Revoke Token (Admin)

```python
from app.db.session import SessionLocal
from app.services.mcp_token_service import revoke_mcp_token, revoke_all_user_tokens

db = SessionLocal()

# Revoke single token
revoke_mcp_token(token_id=5, db=db)

# Revoke all tokens for user
revoke_all_user_tokens(user_id=1, db=db)
```

---

## Using the CLI

### Create Token

```bash
python -m scripts.mcp_token_manager --action create --user-id 1 --description "Claude personal"
```

**Output**:
```
Creating MCP token for: john.doe (john@company.com)

✅ Token created successfully!

Token: mcp_xK9vL2mQ8pR5sTu3VwXyZ1aB2cD4eF5gH6iJ7kL8mN9oP0qR

⚠️  IMPORTANT: Save this token securely. It will not be shown again.
   Store in: .env file, Anthropic platform, or secure credential manager
```

### List Tokens

```bash
# All tokens (including expired/revoked)
python -m scripts.mcp_token_manager --action list --user-id 1

# Only active (valid, not expired, not revoked)
python -m scripts.mcp_token_manager --action list --user-id 1 --active
```

**Output**:
```
📋 Active MCP tokens for john.doe:

   ID: 1
   Status: ✅ ACTIVE
   Description: Claude personal
   Created: 2026-09-02T12:00:00
   Expires: 2027-09-02T12:00:00
   Last Used: 2026-09-02T13:45:30
```

### Revoke Token

```bash
# Revoke single token
python -m scripts.mcp_token_manager --action revoke --token-id 5

# Revoke all tokens for user
python -m scripts.mcp_token_manager --action revoke-all --user-id 1
```

---

## Security Summary

### What MCP Token Does
- ✅ Proves user is authorized (by admin)
- ✅ Long-lived (doesn't expire every hour)
- ✅ Can be revoked immediately
- ✅ Binds MCP client to specific user

### What MCP Token Does NOT Do
- ❌ Does not contain user_id/department (opaque)
- ❌ Cannot be forged (cryptographically random)
- ❌ Cannot be guessed (256 bits entropy)
- ❌ Cannot override user identity (database is source of truth)
- ❌ Cannot bypass department ACL (still enforced)

### Security Properties
- **Storage**: Only hash (SHA-256, one-way)
- **Validation**: Strict checks (not revoked, not expired, user exists)
- **Identity**: From database (prevents impersonation)
- **Department**: From database (prevents escalation)
- **Revocation**: Immediate (no delay)
- **Audit Trail**: Complete (created, used, revoked)

---

## Validation Checklist

During token validation, ALL of these must be true:

1. ✅ Token provided (not empty, not None)
2. ✅ Token hash found in database
3. ✅ Token not revoked (`revoked_at IS NULL`)
4. ✅ Token not expired (`expires_at > NOW`)
5. ✅ User exists in database
6. ✅ User has department
7. ✅ Validation updates `last_used_at`

If ANY check fails → `AuthenticationError` (generic message, no details)

---

## Configuration

### Default Settings

```python
# In backend/app/core/config.py
mcp_token_expiration_days: int = 365  # 1 year
```

### Environment Variable

```bash
# Override in .env
MCP_TOKEN_EXPIRATION_DAYS=730  # 2 years
```

---

## Database Schema

```sql
CREATE TABLE mcp_tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    last_used_at DATETIME,
    revoked_at DATETIME,
    description VARCHAR(255),
    created_by_user_id INTEGER,
    created_via VARCHAR(50),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX ix_mcp_tokens_user_id ON mcp_tokens(user_id);
CREATE INDEX ix_mcp_tokens_token_hash ON mcp_tokens(token_hash);
CREATE INDEX ix_mcp_tokens_expires_at ON mcp_tokens(expires_at);
CREATE INDEX ix_mcp_tokens_revoked_at ON mcp_tokens(revoked_at);
```

---

## Common Operations

### List Tokens for User
```python
from app.services.mcp_token_service import get_user_mcp_tokens
tokens = get_user_mcp_tokens(user_id=1, db=db)
```

### List Active Tokens for User
```python
from app.services.mcp_token_service import get_active_user_mcp_tokens
active_tokens = get_active_user_mcp_tokens(user_id=1, db=db)
```

### Check Token Status
```python
token_record = db.query(MCPToken).filter(MCPToken.id == 5).first()
print(f"Valid: {token_record.is_valid()}")
print(f"Expired: {token_record.is_expired()}")
print(f"Revoked: {token_record.is_revoked()}")
```

---

## Error Handling

All authentication errors raise `AuthenticationError` with generic message:

```python
try:
    user = validate_mcp_token(raw_token, db)
except AuthenticationError:
    # Raised for: invalid, expired, revoked, missing, user not found
    # Always responds with generic "Invalid token" (no information leakage)
    return {"error": "Invalid token"}, 401
```

---

## Testing

### Run Tests
```bash
pytest backend/tests/services/test_mcp_token_service.py -v
```

### Run Specific Test Class
```bash
pytest backend/tests/services/test_mcp_token_service.py::TestTokenValidation -v
```

### With Coverage
```bash
pytest backend/tests/services/test_mcp_token_service.py --cov=app.services.mcp_token_service
```

---

## Files

| File | Purpose |
|------|---------|
| `app/models/mcp_token.py` | MCPToken SQLAlchemy model |
| `app/services/mcp_token_service.py` | Token lifecycle service |
| `alembic/versions/005_add_mcp_tokens_table.py` | Database migration |
| `scripts/mcp_token_manager.py` | Admin CLI utility |
| `tests/services/test_mcp_token_service.py` | 25+ comprehensive tests |
| `docs/PHASE_2_MCP_BACKEND_INFRASTRUCTURE.md` | Full documentation |

---

## Next Steps (Phase 3)

1. Create MCP server implementation
2. Implement `/internal/mcp/exchange` endpoint
3. MCP server validates MCP token → exchanges for JWT
4. MCP server uses JWT in requests to existing endpoints
5. Integration tests

**Phase 2 is ready for Phase 3 integration! ✅**
