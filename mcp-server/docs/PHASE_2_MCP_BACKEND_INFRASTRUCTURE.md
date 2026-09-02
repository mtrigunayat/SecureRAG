# Phase 2 — MCP Backend Infrastructure Implementation

**Status**: ✅ COMPLETE

**Date**: 2026-09-02

**Scope**: Backend infrastructure for MCP (Model Context Protocol) token authentication

---

## Overview

Phase 2 implements a complete backend infrastructure for MCP token authentication. MCP tokens are long-lived, opaque credentials that allow remote MCP clients (e.g., Claude via MCP) to authenticate as specific users without exposing email/password or relying on short-lived JWT tokens.

**Key Principle**: MCP tokens enable a secure identity layer that bridges remote applications with the backend's department-based authorization system, without requiring modifications to existing auth or RAG logic.

---

## What Was Implemented

### 1. MCP Token Model (`backend/app/models/mcp_token.py`)

SQLAlchemy model representing MCP authentication tokens.

**Fields**:
- `id`: Primary key (Integer, auto-increment)
- `user_id`: FK to users (required, indexed)
- `token_hash`: SHA-256 hash of raw token (unique, indexed)
- `created_at`: Creation timestamp
- `expires_at`: Expiration timestamp (indexed for queries)
- `last_used_at`: Last successful validation (audit trail)
- `revoked_at`: Revocation timestamp if revoked (indexed)
- `description`: Human-readable label (optional)
- `created_by_user_id`: Admin who created token (optional)
- `created_via`: Creation method: 'cli', 'api', 'manual' (optional)

**Security Properties**:
- Raw token never stored (only cryptographic hash)
- Hash is one-way (SHA-256, cannot recover original)
- Token cannot be recovered from database
- Raw token returned only at creation time (one-time display)
- Revocation is immediate (database-driven)

**Audit Trail**:
- `created_at`: When issued
- `created_by_user_id`: Who issued
- `last_used_at`: When last used (detects anomalies)
- `revoked_at`: When revoked
- `description`: Purpose/context

**Relationships**:
- `user`: Relationship to User (token belongs to exactly one user)
- `created_by_user`: Optional relationship to admin who issued

### 2. Alembic Migration (`backend/alembic/versions/005_add_mcp_tokens_table.py`)

Database migration that creates `mcp_tokens` table with:
- Primary key constraint on `id`
- Foreign key constraints (CASCADE delete on user, SET NULL on created_by_user)
- Unique constraint on `token_hash`
- Indexes for common queries:
  - `ix_mcp_tokens_user_id`: For listing user's tokens
  - `ix_mcp_tokens_token_hash`: For validating tokens
  - `ix_mcp_tokens_expires_at`: For cleanup queries
  - `ix_mcp_tokens_revoked_at`: For filtering valid tokens

**Migration Files**:
- Up migration: Creates table and indexes
- Down migration: Drops all indexes and table (reversible)

**Naming Convention**: Following project pattern `00X_description.py`

### 3. MCP Token Service (`backend/app/services/mcp_token_service.py`)

Core service providing token lifecycle management.

**Token Generation** (`generate_mcp_token_string()`):
- Cryptographically secure random generation (32 bytes entropy)
- URL-safe alphabet (safe for logging, URLs, env vars)
- Opaque format: `mcp_<random-bytes>`
- No user/department/role encoded
- ~256 bits entropy (cannot be guessed)

**Token Hashing** (`hash_mcp_token()`):
- SHA-256 one-way function
- Hex-encoded output (64 characters)
- Deterministic (same token → same hash always)
- Suitable for database storage
- Cannot be reversed

**Token Creation** (`create_mcp_token_for_user()`):
1. Verify user exists (reject if not)
2. Generate random token string
3. Hash token (SHA-256)
4. Store hash in database with metadata
5. Return raw token ONE TIME
6. Log creation (user_id, token_id, admin, method)

**Inputs**:
- `user_id`: User to create token for
- `db`: Database session
- `description`: Optional label
- `created_by_user_id`: Optional admin
- `created_via`: Optional method ('cli', 'api')
- `expires_in_days`: Optional expiration (default from config)

**Returns**: Raw token string (not stored)

**Token Validation** (`validate_mcp_token()`):
1. Hash provided token
2. Look up hash in database
3. Check NOT revoked (`revoked_at IS NULL`)
4. Check NOT expired (`expires_at > NOW`)
5. Load user from database
6. Verify user exists
7. Verify department loaded
8. Update `last_used_at`
9. Return User object with department

**Validation Rules** (ALL required):
- Token must not be empty
- Token hash must exist in database
- Token must not be revoked
- Token must not be expired
- User must exist
- User must have department

**Security Property**: User identity resolved from persistent database record, never from token payload (prevents impersonation).

**Revocation Functions**:
- `revoke_mcp_token(token_id)`: Revoke single token
- `revoke_all_user_tokens(user_id)`: Revoke all tokens for user
- Revocation is immediate (immutable once set)
- Cannot be undone (audit trail preserved)

**Query Functions**:
- `get_user_mcp_tokens(user_id)`: All tokens (including expired/revoked)
- `get_active_user_mcp_tokens(user_id)`: Only valid tokens

### 4. Configuration Update (`backend/app/core/config.py`)

Added MCP token configuration:
```python
mcp_token_expiration_days: int = 365  # 1 year for long-lived clients
```

**Rationale**: 
- MCP clients (e.g., Claude integration) need long-lived credentials
- 1 year default supports sustained conversations
- Configurable per deployment
- Can be overridden in `.env` file

### 5. MCP Token Management CLI (`backend/scripts/mcp_token_manager.py`)

Admin utility for token lifecycle management.

**Commands**:

```bash
# Create token (admin generates, user stores)
python -m scripts.mcp_token_manager --action create --user-id 1 \
  --description "Claude personal"

# List tokens for user (status, expiration, usage)
python -m scripts.mcp_token_manager --action list --user-id 1
python -m scripts.mcp_token_manager --action list --user-id 1 --active

# Revoke specific token (immediate, immutable)
python -m scripts.mcp_token_manager --action revoke --token-id 5

# Revoke all tokens for user (e.g., compromised, user left)
python -m scripts.mcp_token_manager --action revoke-all --user-id 1
```

**Output**:
- ✅ Success indicators
- ❌ Clear error messages
- 📋 Token listings with status, expiration, last used
- ⚠️ Warnings and instructions

### 6. Comprehensive Tests (`backend/tests/services/test_mcp_token_service.py`)

Test coverage for all token functionality:

**Token Generation Tests**:
- Format validation (prefix, URL-safe)
- Randomness (different every time)
- Entropy verification (sufficient random bits)
- No secrets leaked (no user_id, department, role encoded)

**Hashing Tests**:
- Hex string output (64 characters)
- Deterministic (same token → same hash)
- One-way property (cannot reverse)
- Uniqueness (different tokens → different hashes)
- Immutability (hash never changes)

**Creation Tests**:
- Hash stored, raw not stored
- Expiration set correctly
- User validation (fails if user missing)
- Unique hashes (multiple tokens)
- Audit trail (created_by, created_via, description)

**Validation Tests**:
- Valid token returns user
- Invalid token rejected
- Empty/None tokens rejected
- Expired tokens rejected
- Revoked tokens rejected
- last_used_at updated
- User deletion causes validation failure
- Multiple tokens validated independently

**Revocation Tests**:
- Single token revocation
- Non-existent token handling
- Revoke all user tokens
- Immediate effect

**Department Integrity Tests**:
- User has department after validation
- Department from database (not token)
- Cannot override department

**Security Property Tests**:
- Token not reversible from hash
- Token format reveals no user info
- Cannot decode as JSON

---

## Architecture Decision: MCP Token vs Backend JWT

**Two Separate Authentication Systems**:

1. **Backend JWT** (existing, unchanged):
   - Short-lived (1 hour default)
   - Used for browser/SPA authentication
   - Created by `/api/auth/login`
   - Valid only during conversation
   - Refreshed per-session

2. **MCP Token** (new):
   - Long-lived (1 year default)
   - Used for remote MPC clients
   - Created by admin (CLI or future endpoint)
   - Valid across multiple sessions
   - Can be revoked at any time

**Why Separate?**:
- Different trust models (user vs admin)
- Different lifetimes (session vs long-term)
- Different revocation strategies
- Independent security layers
- Clean separation of concerns

**Identity Bridge** (Phase 3):
The MCP server receives MCP token from client, but must exchange it for a backend JWT before calling `/api/chat`, `/api/retrieval`, etc. This exchange ensures:
- MCP token proves client is authorized (by admin)
- Backend JWT proves request is fresh (within session)
- Existing auth layer stays unchanged
- RAG logic unchanged
- Department ACL still enforced

---

## Security Analysis

### Token Security

**Raw Token**:
- Generated by `secrets.token_urlsafe()` (cryptographically secure)
- 32 bytes entropy (256 bits)
- URL-safe alphabet (no special escaping needed)
- Returned only once at creation time
- Never persisted in database
- Never logged (service design)

**Stored Hash**:
- SHA-256 one-way function
- Cannot recover original token
- 64-character hex string
- Unique constraint in database
- Indexed for fast lookup
- Suitable for authentication comparison

**Validation Process**:
1. Client provides raw token
2. Server hashes it (same process)
3. Server looks up hash in database
4. Comparison is hash-to-hash (not plaintext)
5. Additional checks: not revoked, not expired, user exists, department loaded

**No Information Leakage**:
- Token format: `mcp_<random>` (opaque)
- No user_id in token
- No department_id in token
- No role/permissions in token
- No expiration in token (stored in database)
- Cannot decode as JWT or JSON

### User Identity Security

**Identity Resolution** (server-side, TRUSTED):
```
Token Hash → MCPToken.user_id → User → Department
```

- Token points to specific user_id (immutable in database)
- User loaded from PostgreSQL (authoritative)
- Department loaded via SQLAlchemy relationship (trusted)
- MCP client cannot override any of these
- Prevents user impersonation via token forgery

### Department-Based Access Control

**Authorization Remains Unchanged**:
- Existing `/api/chat`, `/api/retrieval` enforce department ACL
- MCP token only handles authentication (who is the user)
- Authorization (what can they access) stays in RAG/retrieval services
- Department comes from User.department relationship (database-driven)
- Cannot be overridden by MCP client
- Server-side filtering in Qdrant (not post-hoc)

### Audit Trail

**Created**:
- `created_at`: When issued
- `created_by_user_id`: Who issued (admin)
- `description`: Purpose
- `created_via`: Method (cli/api)

**Used**:
- `last_used_at`: When last validated
- Helps detect compromised tokens (anomalies)
- Enables usage reporting

**Revoked**:
- `revoked_at`: When revoked
- Immutable once set
- Immediate effect (no delay)
- Audit trail preserved

### Threat Model

**Threats Mitigated**:
1. **Token Interception**: 
   - Requires HTTPS (application responsibility)
   - Raw token never in logs/errors
   - Hash in database cannot recover token

2. **Token Forgery**:
   - Token is cryptographically random (256 bits)
   - Cannot guess (2^256 possible values)
   - Client cannot create valid tokens

3. **User Impersonation**:
   - User identity from database (not from token)
   - Cannot encode user_id in token that overrides database
   - Department ACL enforced by RAG layer

4. **Token Replay**:
   - Each use updates `last_used_at` (not useful for replay, but tracks usage)
   - Existing backend JWT session control prevents replay attacks
   - Token expiration enforced

5. **Compromised Token**:
   - Can be revoked immediately
   - No delayed effect
   - Cannot be recovered
   - All future validations fail

6. **Token Leakage in Logs**:
   - Service design prevents logging raw tokens
   - Only hash and metadata logged
   - Token IDs used in audit logs (not hashes)

---

## Database Schema

```sql
CREATE TABLE mcp_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_used_at DATETIME,
    revoked_at DATETIME,
    description VARCHAR(255),
    created_by_user_id INTEGER,
    created_via VARCHAR(50),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (token_hash)
);

CREATE INDEX ix_mcp_tokens_id ON mcp_tokens(id);
CREATE INDEX ix_mcp_tokens_user_id ON mcp_tokens(user_id);
CREATE INDEX ix_mcp_tokens_token_hash ON mcp_tokens(token_hash);
CREATE INDEX ix_mcp_tokens_expires_at ON mcp_tokens(expires_at);
CREATE INDEX ix_mcp_tokens_revoked_at ON mcp_tokens(revoked_at);
```

---

## Integration Points (For Future Phases)

### Phase 3 — Backend JWT Exchange

**What Happens in Phase 3**:
- MCP server receives MCP token from client
- MCP server calls new internal endpoint: `POST /internal/mcp/exchange`
- Endpoint validates MCP token → loads User
- Endpoint creates backend JWT for that user
- Endpoint returns JWT to MCP server
- MCP server includes JWT in requests to `/api/chat`, etc.
- Existing auth flow validates JWT (unchanged)

**Why Separate Endpoint?**:
- `/internal/mcp/exchange` (new, internal, MCP-only)
- Not exposed to frontend
- Not used by browser auth
- Trades MCP token for JWT
- Short-lived JWT for session
- MCP token remains in MCP server (not client)

**Security**:
- MCP token proves "admin authorized this user"
- JWT proves "this request is fresh and from this session"
- No change to existing `/api/chat`, `/api/retrieval`
- Department ACL still enforced
- No RAG logic changes

---

## Configuration

### Default Settings (`.env` or environment)

```bash
# MCP Token Configuration (Phase 2)
MCP_TOKEN_EXPIRATION_DAYS=365
```

### Existing Settings (Unchanged)

```bash
# These remain for existing auth
JWT_SECRET=<your-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=1
```

---

## API Specification (NOT in Phase 2)

**Deferred to Phase 3**:
- `POST /internal/mcp/exchange` — Trade MCP token for JWT
- `GET /api/mcp/tokens` — List user's tokens
- `POST /api/mcp/tokens` — Create token
- `DELETE /api/mcp/tokens/{id}` — Revoke token
- `DELETE /api/mcp/tokens` — Revoke all tokens for user

**Phase 2 Provides**:
- Service layer (mcp_token_service.py)
- Database layer (mcp_tokens table)
- CLI (mcp_token_manager.py)
- Tests (test_mcp_token_service.py)

---

## Testing

### Test Coverage

**Unit Tests**: `backend/tests/services/test_mcp_token_service.py`

**Test Classes**:
1. `TestTokenGeneration` — Token generation randomness, format, entropy
2. `TestTokenHashing` — Hashing determinism, one-way, uniqueness
3. `TestTokenCreation` — Database persistence, expiration, audit trail
4. `TestTokenValidation` — Validation rules, user resolution, error cases
5. `TestTokenRevocation` — Revocation immediate effect
6. `TestDepartmentIntegrity` — Department from database (not token)
7. `TestSecurityProperties` — Security invariants

**Test Count**: 25+ comprehensive tests

**Running Tests**:
```bash
# All tests
pytest backend/tests/services/test_mcp_token_service.py -v

# Specific test class
pytest backend/tests/services/test_mcp_token_service.py::TestTokenValidation -v

# With coverage
pytest backend/tests/services/test_mcp_token_service.py --cov=app.services.mcp_token_service
```

### Manual Testing

**Using CLI**:
```bash
# Create token
cd backend
python -m scripts.mcp_token_manager --action create --user-id 1

# List tokens
python -m scripts.mcp_token_manager --action list --user-id 1

# Revoke token
python -m scripts.mcp_token_manager --action revoke --token-id 1
```

**Using Python**:
```python
from app.db.session import SessionLocal
from app.services.mcp_token_service import create_mcp_token_for_user, validate_mcp_token

db = SessionLocal()
raw_token = create_mcp_token_for_user(user_id=1, db=db, description="Test")
print(raw_token)  # Token returned once

user = validate_mcp_token(raw_token, db)
print(f"Authenticated as: {user.username} ({user.department.name})")
```

---

## Verification Checklist

**Database**:
- ✅ Migration file created (005_add_mcp_tokens_table.py)
- ✅ Table definition correct (user_id FK, token_hash unique, indexes)
- ✅ Indexes on user_id, token_hash, expires_at, revoked_at
- ✅ CASCADE delete on user deletion

**Model**:
- ✅ MCPToken SQLAlchemy model created
- ✅ Relationships to User (user, created_by_user)
- ✅ All fields with correct types and constraints
- ✅ Helper methods: is_valid(), is_expired(), is_revoked(), revoke()
- ✅ Imported in app/models/__init__.py

**Service**:
- ✅ Token generation (cryptographically secure)
- ✅ Token hashing (SHA-256, one-way)
- ✅ Token creation (store hash, return raw once)
- ✅ Token validation (all checks)
- ✅ User resolution (from database)
- ✅ Revocation (immediate, immutable)
- ✅ Query functions (active, all, per-user)

**Configuration**:
- ✅ MCP_TOKEN_EXPIRATION_DAYS added to settings
- ✅ Default value: 365 days
- ✅ Configurable via environment

**CLI**:
- ✅ Create tokens
- ✅ List tokens (all, active)
- ✅ Revoke tokens (single, all for user)
- ✅ User feedback (✅, ❌, ⚠️)

**Tests**:
- ✅ Token generation tests
- ✅ Hashing tests
- ✅ Creation tests
- ✅ Validation tests
- ✅ Revocation tests
- ✅ Department integrity tests
- ✅ Security property tests

**Security**:
- ✅ Raw token never stored
- ✅ Hash is one-way (SHA-256)
- ✅ Token cannot encode user/department
- ✅ User identity from database (not token)
- ✅ Department ACL not bypassed
- ✅ Revocation immediate
- ✅ Audit trail complete
- ✅ No secrets in logs

**Integration**:
- ✅ Existing `/api/auth/login` unchanged
- ✅ Existing `/api/chat` unchanged
- ✅ Existing `/api/retrieval` unchanged
- ✅ Department ACL unchanged
- ✅ Qdrant filtering unchanged
- ✅ JWT auth unchanged

---

## Migration Instructions

### For Existing Database

```bash
cd backend

# Apply migration
alembic upgrade head

# Verify table created
alembic current
```

### Rollback

```bash
# If needed to rollback
alembic downgrade -1
```

---

## What Phase 2 Does NOT Do

**Explicitly Out of Scope** (for Phase 3+):
- ❌ MCP server creation
- ❌ MCP SDK integration
- ❌ Claude connector
- ❌ OAuth/email-password MCP auth
- ❌ API endpoints (saved for Phase 3)
- ❌ Backend JWT exchange logic (saved for Phase 3)
- ❌ Frontend integration (for future phases)
- ❌ Duplicate RAG logic (uses existing)
- ❌ Modifications to existing auth flow

**What Stays in RAG/Auth Layers**:
- Existing `/api/auth/login` (browser, email/password)
- Existing `/api/chat` (requires JWT)
- Existing `/api/retrieval` (requires JWT)
- Existing department ACL (Qdrant filtering)
- Existing user/department relationship
- Existing password hashing
- Existing JWT creation/validation

---

## Documentation Structure

- **This File**: Phase 2 overview, decisions, implementation summary
- **Code Docstrings**: In-code documentation for each function/class
- **Tests**: Executable examples of correct usage
- **CLI Help**: `python -m scripts.mcp_token_manager --help`
- **Service Module**: Docstrings explain token lifecycle, security

---

## Success Criteria (ALL MET)

1. ✅ MCP tokens are opaque, randomly generated (no user_id/department encoded)
2. ✅ Raw tokens never stored (only cryptographic hash)
3. ✅ Token validation resolves identity from database (prevents impersonation)
4. ✅ User's department comes from database relationship (not from token)
5. ✅ Tokens can expire (configurable TTL)
6. ✅ Tokens can be revoked immediately (immutable once set)
7. ✅ Existing auth flow unchanged (`/api/auth/login`, JWT, etc.)
8. ✅ Existing RAG pipeline unchanged (same `/api/chat`, `/api/retrieval`)
9. ✅ Department ACL still enforced by backend (server-side Qdrant filtering)
10. ✅ Comprehensive tests (25+ test cases)
11. ✅ Audit trail (created_by, created_via, last_used_at, revoked_at)
12. ✅ Admin CLI for token management
13. ✅ Clear documentation (this file + docstrings)
14. ✅ Database migration (up/down, reversible)
15. ✅ Configuration (MCP_TOKEN_EXPIRATION_DAYS, default 365)
16. ✅ No breaking changes to existing backend
17. ✅ Ready for Phase 3 (MCP server integration can proceed)

---

## Next Steps (Phase 3)

**Phase 3 Focus**: MCP server integration and JWT exchange

1. Create MCP server (Python implementation)
2. Implement MCP handler functions (stub, echo, retrieve)
3. Create `/internal/mcp/exchange` endpoint
4. MCP server calls exchange endpoint with MCP token
5. Exchange endpoint returns JWT to MCP server
6. MCP server uses JWT to call `/api/chat`, `/api/retrieval`
7. Integration tests (MCP server + backend)
8. Documentation (MCP protocol, Claude connector)

---

## Files Created/Modified

**Created**:
- `backend/app/models/mcp_token.py` — MCPToken SQLAlchemy model
- `backend/alembic/versions/005_add_mcp_tokens_table.py` — Database migration
- `backend/app/services/mcp_token_service.py` — Token lifecycle service
- `backend/scripts/mcp_token_manager.py` — Admin CLI utility
- `backend/tests/services/test_mcp_token_service.py` — Comprehensive tests

**Modified**:
- `backend/app/models/__init__.py` — Added MCPToken import
- `backend/app/core/config.py` — Added MCP_TOKEN_EXPIRATION_DAYS setting

**Unchanged** (explicitly verified):
- `backend/app/api/auth.py` — Login endpoint unchanged
- `backend/app/api/chat.py` — Chat endpoint unchanged
- `backend/app/api/retrieval.py` — Retrieval endpoint unchanged
- `backend/app/services/authorization_service.py` — ACL unchanged
- `backend/app/services/retrieval_service.py` — Retrieval ACL unchanged
- All other existing code

---

## Summary

Phase 2 implements a complete, secure backend infrastructure for MCP token authentication. The system:

1. **Generates** cryptographically secure, opaque tokens
2. **Stores** only cryptographic hashes (never raw tokens)
3. **Validates** tokens with strict checks (not expired, not revoked, user exists)
4. **Resolves** user identity from persistent database (prevents impersonation)
5. **Preserves** department-based access control (unchanged)
6. **Audits** all operations (created_by, last_used_at, revoked_at)
7. **Revokes** tokens immediately (immutable, irreversible)
8. **Integrates** with existing auth without modifications
9. **Provides** CLI for token management
10. **Tests** all functionality comprehensively

The infrastructure is ready for Phase 3, which will implement the MCP server and JWT exchange logic that completes the MCP integration.
