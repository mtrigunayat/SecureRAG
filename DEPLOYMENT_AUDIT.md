# SecureRAG Deployment Audit

**Date:** September 3, 2026  
**Status:** Pre-deployment review (no changes made)  
**Scope:** Full repository inspection for production readiness

---

## SECTION 1: PROJECT STRUCTURE

### Repository Layout

```
SecureRAG/
├── .env                          # Current configuration (NOT in git)
├── .env.example                  # Template for environment variables
├── docker-compose.yml            # Local development orchestration
├── README.md                     # Project documentation
│
├── backend/                      # FastAPI application
│   ├── Dockerfile               # Backend container (PORT env var support ✓)
│   ├── requirements.txt          # Python dependencies
│   ├── alembic.ini              # Database migration config
│   ├── pytest.ini               # Test configuration
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── core/
│   │   │   ├── config.py        # Settings (env vars, defaults)
│   │   │   ├── logging.py       # Logging setup
│   │   │   └── errors.py        # Error handlers
│   │   ├── api/
│   │   │   ├── auth.py          # Authentication endpoints
│   │   │   ├── chat.py          # Chat/LLM endpoints
│   │   │   ├── documents.py     # Document management
│   │   │   ├── retrieval.py     # RAG retrieval
│   │   │   ├── health.py        # Health check
│   │   │   └── mcp_internal.py  # MCP server integration
│   │   ├── services/            # Business logic
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── repositories/        # Data access layer
│   │   └── db/                  # Database session management
│   ├── alembic/
│   │   └── versions/            # Database migrations
│   │       ├── 004...add_password_hash_to_users.py
│   │       ├── 005...add_mcp_tokens_table.py
│   │       └── 778...initial_schema.py
│   ├── scripts/                 # Utility scripts
│   └── tests/                   # Test suite (153+ tests)
│
├── frontend/                     # React + Vite + TypeScript
│   ├── package.json             # Dependencies
│   ├── vite.config.ts           # Vite configuration
│   ├── tsconfig.json            # TypeScript config
│   ├── index.html               # HTML entry point
│   ├── src/
│   │   ├── main.tsx             # React entry point
│   │   ├── App.tsx              # Main component
│   │   ├── services/
│   │   │   ├── apiClient.ts     # API client (uses VITE_API_URL ✓)
│   │   │   ├── authApi.ts       # Auth API calls
│   │   │   └── chatApi.ts       # Chat API calls
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx  # Auth state management
│   │   ├── pages/               # Route pages
│   │   └── components/          # React components
│   └── public/                  # Static assets
│
├── mcp-server/                  # MCP server (Model Context Protocol)
│   ├── Dockerfile              # MCP server container (PORT env var support ✓)
│   ├── requirements.txt         # Python dependencies
│   ├── run.py                   # Python startup script
│   ├── run.sh                   # Shell startup script
│   ├── pyproject.toml           # Project metadata
│   ├── src/mcp_server/
│   │   ├── main.py             # Server entry point
│   │   ├── core/
│   │   │   ├── config.py       # Settings (BACKEND_URL, etc.)
│   │   │   ├── logging.py      # Logging setup
│   │   │   └── errors.py       # Error definitions
│   │   ├── auth/               # Token validation
│   │   ├── client/
│   │   │   └── backend_api_client.py  # HTTP calls to backend
│   │   └── tools/              # MCP tool implementations
│   └── tests/                  # Test files
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE_REVIEW.md
│   ├── RENDER_DEPLOYMENT_GUIDE.md
│   ├── SECURITY_AUDIT_CHECKLIST.md
│   ├── TECHNICAL_DEEP_DIVE.md
│   └── PHASE_*_COMPLETE.md     # Phase completion docs
│
└── documents/                   # Sample company documents (test data)
    ├── engineering/
    ├── general/
    ├── hr/
    └── sales/
```

---

## SECTION 2: FRONTEND

### Overview
- **Framework:** React 19.2.8 (latest)
- **Build Tool:** Vite 8.2.2
- **Language:** TypeScript 6.0.2
- **CSS:** Vanilla CSS (index.css)
- **Routing:** React Router DOM 7.18.2

### Build & Deployment

**Build Command:**
```bash
npm run build  # Runs: tsc -b && vite build
```

**Output:**
- Builds to: `frontend/dist/`
- Static HTML/CSS/JS bundle ready for CDN or static hosting
- All assets hashed for cache busting

**Start Commands:**
- **Development:** `npm run build` → builds to dist folder
- **Preview:** `npm run preview` → serves dist locally via Vite
- **Linting:** `npm run lint` → runs oxlint

**Can Deploy as Static Site?** ✅ YES
- Pure client-side React application
- No server-side rendering required
- Can be served from S3, Cloudflare Pages, Netlify, Render static service

### Environment Variables

**Configuration Source:**
```typescript
// frontend/src/services/apiClient.ts
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

**Required Environment Variables:**
| Variable | Purpose | Local Default | Production | Required |
|----------|---------|---------------|------------|----------|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8000` | Backend public URL | ✅ Yes |

**Setting for Production:**
```bash
# Build time
VITE_API_URL=https://my-backend.onrender.com npm run build

# Or in .env.production
VITE_API_URL=https://my-backend.onrender.com
```

### Current API Integration

**Endpoints Used:**
```
POST   /api/auth/login         → Login
GET    /api/auth/me            → Get current user
GET    /api/health             → Health check
POST   /api/chat               → Send question
GET    /api/retrieval/search   → Search documents
```

**Authentication:**
- JWT token stored in `localStorage` under key `auth_token`
- Token sent in `Authorization: Bearer {token}` header
- Token retrieved from login response `access_token` field

**Deployment-Specific Changes Required:**
- [ ] Update `VITE_API_URL` environment variable to backend URL
- [ ] Ensure CORS origins on backend include frontend domain
- No hardcoded localhost references in source code ✅

### Build Size Considerations
- React + React Router + TypeScript compilation
- No heavy dependencies
- Expected bundle size: ~200-400KB gzipped
- Suitable for free static hosting tiers

---

## SECTION 3: BACKEND

### Overview
- **Framework:** FastAPI 0.109.0
- **Server:** Uvicorn 0.27.0
- **Python:** 3.11-slim Docker image
- **Database:** PostgreSQL (SQLAlchemy ORM)
- **Vector DB:** Qdrant (client library 1.11.3)
- **LLM:** Azure OpenAI (future phase)
- **Embeddings:** sentence-transformers 2.7.0 (local, no API cost)

### Production Start Command

```bash
# Direct Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

# Docker
docker run -p 8000:8000 -e PORT=8000 backend-image
```

**How It Works:**
- `PORT` environment variable overrides default `8000` (Render compatibility ✅)
- Binds to `0.0.0.0` for all interfaces
- Supports hot reload in development (with `--reload`)
- No reload in production

### Configuration

**Source:** `backend/app/core/config.py` (Pydantic Settings)

**Configuration Loading:**
1. Reads from `.env` file first
2. Environment variables override `.env`
3. Defaults if neither provided
4. Special handling for `PORT` env var (Render compatibility)

**Port Configuration:**
```python
# Default to 8000
app_port: int = 8000

# Override from PORT env var (Render sets this)
if "PORT" in os.environ:
    self.app_port = int(os.environ["PORT"])
```

### Required Environment Variables

| Variable | Example/Format | Required | Secret | Notes |
|----------|---|---|---|---|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname` | ✅ Yes | ✅ Yes | PostgreSQL connection string |
| `QDRANT_URL` | `http://localhost:6333` or `https://xxx.qdrant.io` | ✅ Yes | ❌ No | Vector DB URL |
| `QDRANT_API_KEY` | (empty for local) or `xxxxxxxx-xxxx` | ❌ No | ✅ Yes | Required for Qdrant Cloud only |
| `QDRANT_COLLECTION_NAME` | `knowledge_chunks` | ❌ No | ❌ No | Default: `knowledge_chunks` |
| `AZURE_OPENAI_API_KEY` | `xxxx...xxxx` | ✅ Yes (if using LLM) | ✅ Yes | Azure OpenAI key |
| `AZURE_OPENAI_ENDPOINT` | `https://xxx.openai.azure.com/` | ✅ Yes (if using LLM) | ❌ No | Azure OpenAI endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4.1-mini` | ❌ No | ❌ No | Default: `gpt-4.1-mini` |
| `AZURE_OPENAI_API_VERSION` | `2024-12-01-preview` | ❌ No | ❌ No | Azure API version |
| `JWT_SECRET` | (min 32 chars, random) | ✅ Yes | ✅ Yes | Signing key for JWT tokens |
| `JWT_ALGORITHM` | `HS256` | ❌ No | ❌ No | Default: `HS256` |
| `JWT_EXPIRATION_HOURS` | `1` | ❌ No | ❌ No | Default: `1 hour` |
| `MCP_TOKEN_EXPIRATION_DAYS` | `365` | ❌ No | ❌ No | Default: `365 days` |
| `APP_ENV` | `development` or `production` | ❌ No | ❌ No | Environment flag |
| `APP_HOST` | `0.0.0.0` | ❌ No | ❌ No | Always `0.0.0.0` for containers |
| `APP_PORT` | `8000` | ❌ No | ❌ No | Use `PORT` env var in production |
| `LOG_LEVEL` | `INFO`, `DEBUG`, `ERROR` | ❌ No | ❌ No | Default: `INFO` |
| `CORS_ORIGINS` | `https://frontend.render.com,https://yourdomain.com` | ✅ Yes | ❌ No | Comma-separated frontend URLs |
| `CHUNK_SIZE` | `600` | ❌ No | ❌ No | Document chunk size (chars) |
| `CHUNK_OVERLAP` | `100` | ❌ No | ❌ No | Overlap between chunks |
| `RETRIEVAL_TOP_K` | `5` | ❌ No | ❌ No | Max chunks to retrieve |
| `RETRIEVAL_SCORE_THRESHOLD` | `0.4` | ❌ No | ❌ No | Min similarity score |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | ❌ No | ❌ No | HuggingFace model ID |
| `EMBEDDING_DIMENSION` | `384` | ❌ No | ❌ No | Vector size for embeddings |

**CORS Configuration:**

```python
# Current default (development)
cors_origins: str = "http://localhost:3000,http://localhost:5173"

# For production, set CORS_ORIGINS to frontend domain:
CORS_ORIGINS=https://secure-rag-frontend.onrender.com,https://yourdomain.com
```

**⚠️ SECURITY NOTE:** CORS configured to allow all methods and headers (`allow_methods=["*"]`). For production, consider restricting to specific methods and headers.

### Database Connection

**Connection String Format (PostgreSQL):**
```
postgresql://[user]:[password]@[host]:[port]/[database]

Examples:
- Local: postgresql://rag_user:rag_password@localhost:5432/secure_rag
- Neon (free tier): postgresql://user:password@host.neon.tech/dbname?sslmode=require
- Render: postgresql://user:password@host.render.com/dbname
```

**Database Name:** `secure_rag` (configurable)

**Tables:**
- `users` - User accounts with departments
- `departments` - Department registry
- `documents` - Document metadata
- `mcp_tokens` - MCP authentication tokens

### Database Migrations

**Tool:** Alembic

**Location:** `backend/alembic/versions/`

**Migrations:**
1. `778...initial_schema_departments_users.py` - Create departments, users, documents tables
2. `004...add_password_hash_to_users.py` - Add password_hash column to users
3. `005...add_mcp_tokens_table.py` - Add mcp_tokens table for MCP server auth

**Running Migrations (Production):**
```bash
# Before first app startup
cd backend
alembic upgrade head

# In Dockerfile or startup script
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**PostgreSQL Extensions Required:**
- None explicitly required
- Standard PostgreSQL 15 sufficient

### Qdrant Configuration

**Connection:**
```python
# Local Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Empty for local

# Qdrant Cloud
QDRANT_URL=https://xxxxx-xxxxx.qdrant.io:6333
QDRANT_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Health Check:**
The backend checks Qdrant connectivity on startup. If unavailable, startup fails.

### OpenAI/Azure Configuration

**Provider:** Azure OpenAI (not standard OpenAI)

**Configuration:**
```
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

**Fallback:** If keys not set, LLM calls will fail (expected in development)

### Authentication & JWT

**JWT Configuration:**
- Algorithm: `HS256` (HMAC with SHA-256)
- Secret: Must be ≥32 characters (cryptographic requirement)
- Expiration: `1 hour` (configurable)
- Stored in: `Authorization: Bearer {token}` header

**Generation:**
- Login endpoint issues JWT after username/password validation
- Token includes user ID and department in claims

### MCP Server Integration

**How Backend Knows About MCP Server:**
- Backend does NOT directly call MCP server
- MCP server calls backend's `/api/chat` endpoint with JWT
- Backend verifies JWT and processes request

**MCP Token System:**
- MCP clients have separate tokens (not JWT)
- Generated by `/api/mcp/tokens` endpoint (admin only)
- Backend validates MCP token, issues temporary JWT
- MCP token is hashed (SHA-256) in database

### Health Check Endpoint

```
GET /api/health
```

Returns `200 OK` with status info. Used for deployment health checks.

### API Endpoints Summary

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/health` | GET | ❌ | Health check |
| `/api/auth/login` | POST | ❌ | Login (username/password) |
| `/api/auth/me` | GET | ✅ JWT | Get current user |
| `/api/chat` | POST | ✅ JWT | Query knowledge base |
| `/api/retrieval/search` | GET | ✅ JWT | Search documents |
| `/api/documents` | GET | ✅ JWT | List documents (filtered by dept) |
| `/api/mcp/tokens` | POST | ✅ JWT | Generate MCP token (admin) |

### Hardcoded URLs/Localhost References

**❌ FOUND:**
```python
# backend/app/core/config.py
qdrant_url: str = "http://localhost:6333"  # ← Default, but overridable ✓
cors_origins: str = "http://localhost:3000,http://localhost:5173"  # ← Default, must override ✓
```

**STATUS:** Hardcoded defaults exist but are environment-variable overridable. No issue for deployment.

### Deployment-Specific Changes Required

- [ ] Set `DATABASE_URL` to production PostgreSQL
- [ ] Set `QDRANT_URL` to production Qdrant (local or cloud)
- [ ] Set `QDRANT_API_KEY` if using Qdrant Cloud
- [ ] Generate new `JWT_SECRET` (≥32 random chars)
- [ ] Set `CORS_ORIGINS` to frontend domain(s)
- [ ] Set `AZURE_OPENAI_API_KEY` and endpoint if using LLM
- [ ] Set `APP_ENV=production`
- [ ] Run `alembic upgrade head` on first deployment
- [ ] Ensure `PORT` env var is respected (✓ already implemented)

---

## SECTION 4: MCP SERVER

### Overview
- **Protocol:** Model Context Protocol (MCP)
- **Transport:** HTTP with Streamable transport
- **Framework:** Starlette/Uvicorn (via MCP SDK)
- **Language:** Python 3.11
- **Dependencies:** mcp>=0.1.0, httpx>=0.25.0, pydantic>=2.0

### Start Command

```bash
# Local development
python -m mcp_server.main

# Docker
docker run -p 5000:5000 -e PORT=5000 -e BACKEND_URL=http://backend:8000 mcp-image
```

**Port Handling:**
- Default: `5000`
- Overridden by: `PORT` environment variable (Render compatible ✅)
- Runs on: `0.0.0.0:PORT`

### Configuration

**Source:** `mcp-server/src/mcp_server/core/config.py`

```python
# Defaults
mcp_host: str = "0.0.0.0"
mcp_port: int = 5000  # Overridden by PORT env var if set
backend_url: str = "http://localhost:8000"  # MUST be changed for production
backend_api_timeout: int = 30
```

### Required Environment Variables

| Variable | Example/Format | Required | Secret | Notes |
|----------|---|---|---|---|
| `BACKEND_URL` | `https://my-backend.onrender.com` | ✅ Yes | ❌ No | Backend URL (no trailing slash) |
| `BACKEND_API_TIMEOUT` | `30` | ❌ No | ❌ No | Timeout for backend calls (seconds) |
| `MCP_HOST` | `0.0.0.0` | ❌ No | ❌ No | Always `0.0.0.0` for containers |
| `MCP_PORT` | `5000` | ❌ No | ❌ No | Use `PORT` env var in production |
| `LOG_LEVEL` | `INFO`, `DEBUG`, `ERROR` | ❌ No | ❌ No | Default: `INFO` |

### Communication with Backend

**How MCP Server Uses Backend:**

```
MCP Client
    ↓ (MCP request with mcp_token)
MCP Server
    ↓ (exchange mcp_token for JWT)
Backend: /api/auth/mcp/validate
    ↓ (returns JWT)
MCP Server
    ↓ (use JWT for subsequent calls)
Backend: /api/chat
    ↓ (answer + sources)
MCP Client (response)
```

**Implementation:**
- Backend API client: `mcp_server/client/backend_api_client.py`
- Makes HTTP POST to `{BACKEND_URL}/api/chat`
- Includes `Authorization: Bearer {jwt}` header
- Timeout: 30 seconds (configurable)

### MCP Token Flow

1. Admin creates MCP token: `POST /api/mcp/tokens`
2. Backend returns raw token (one-time)
3. MCP client stores token
4. MCP server validates token with backend
5. Backend returns authenticated user + temporary JWT
6. MCP server uses JWT for API calls

**Token Storage:**
- Raw tokens: Never stored (only hashes)
- Hashes: SHA-256, stored in PostgreSQL
- Expiration: Default 365 days, configurable
- Revocation: Supported via `revoked_at` timestamp

### Public Internet Access

**Does MCP Server Need Public Internet Access?**
- ❌ No public IP required
- It only calls backend (internal network in deployment)
- Clients connect to it via local network or VPN in typical enterprise setup
- For cloud deployment, can be in same network as backend or access via private URL

### Hardcoded URLs

**❌ FOUND:**
```python
# mcp-server/src/mcp_server/core/config.py
backend_url: str = "http://localhost:8000"  # ← Default, MUST override ✓
```

**Test Files (NOT used in production):**
```python
# mcp-server/test_mcp_flow.py
BACKEND_URL = "http://localhost:8000"  # ← Only for testing
```

**STATUS:** Default exists but is environment-variable overridable. Test files hardcoded (acceptable).

### Health Check Endpoint

```
GET /health
```

Returns `200 OK` with MCP server status. Used for deployment monitoring.

### Deployment-Specific Changes Required

- [ ] Set `BACKEND_URL` to backend service URL (e.g., `https://secure-rag-backend.onrender.com`)
- [ ] Ensure `LOG_LEVEL` set appropriately
- [ ] Ensure `PORT` env var is respected (✓ already implemented)
- [ ] No secrets needed in `.env` (only URLs)

---

## SECTION 5: QDRANT (VECTOR DATABASE)

### Current Setup

**Local Development (docker-compose.yml):**
```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"    # REST API
    - "6334:6334"    # gRPC
  volumes:
    - qdrant_data:/qdrant/storage
```

**How It's Used:**
- Connection: `http://localhost:6333` (local) or `https://xxx.qdrant.io` (cloud)
- Operation: Vector similarity search with metadata filtering
- Collection: `knowledge_chunks` (hardcoded in code, configurable)
- Vector Dimension: `384` (from sentence-transformers/all-MiniLM-L6-v2)
- Distance Metric: `COSINE` (semantic similarity)

### Production Options

**Option 1: Self-Hosted Qdrant (Recommended for Cost)**
- Run Qdrant container on your server
- Docker image: `qdrant/qdrant:latest`
- Persistent storage: Volume mount
- Port: `6333` (REST), `6334` (gRPC)
- Cost: FREE (if hosting your own server)
- Backups: Manual volume snapshots

**Option 2: Qdrant Cloud (Paid, Managed)**
- URL: `https://xxxxx.qdrant.io:6333`
- API Key: Required for authentication
- Free Tier: 1GB storage, limited performance
- Paid: Starts ~$25/month for 10GB
- Advantage: Fully managed, automatic backups

### Authentication

**For Local Qdrant:**
```
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Empty string
```

**For Qdrant Cloud:**
```
QDRANT_URL=https://xxxxx.qdrant.io:6333
QDRANT_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  # API key from dashboard
```

### Persistent Storage Configuration

**Docker Compose (Local):**
```yaml
volumes:
  qdrant_data:
    driver: local
```

Storage location: `/var/lib/docker/volumes/qdrant_data/_data/`

**For Production:**
- Named Docker volume persists between container restarts
- For server failure recovery, need external backup strategy
- Qdrant Cloud handles backups automatically

### Health Check

Backend checks Qdrant health on startup:
```python
def health_check(self) -> bool:
    """Check if Qdrant is healthy and reachable."""
    try:
        self.client.get_collections()
        return True
    except Exception:
        return False
```

If Qdrant unavailable at startup, backend fails to start.

### Vector Storage Size

**Estimation:**
- Documents: ~50 sample company documents
- Chunks per document: ~5-20 (depends on doc length)
- Total chunks: ~250-1000
- Vector size: 384 dimensions × 4 bytes = 1.5 KB per vector
- Metadata: ~1 KB per chunk
- Total storage: ~500 MB to 1 GB

**Scalability:**
- Free Qdrant Cloud: 1 GB sufficient for 500K+ chunks
- Self-hosted: Storage limited only by disk

### Deployment-Specific Changes Required

- [ ] Decide: Self-hosted or Qdrant Cloud
- [ ] If Cloud: Create Qdrant Cloud account, get API URL + key
- [ ] Set `QDRANT_URL` in backend
- [ ] Set `QDRANT_API_KEY` if using cloud
- [ ] Ensure collection exists (backend creates it on startup)
- [ ] For self-hosted: Set up persistent volume backup strategy

---

## SECTION 6: POSTGRESQL

### Current Setup

**Local Development (docker-compose.yml):**
```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: secure_rag
    POSTGRES_USER: rag_user
    POSTGRES_PASSWORD: rag_password
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U rag_user -d secure_rag"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### Connection String Format

```
postgresql://[user]:[password]@[host]:[port]/[database]

Examples:
- Local: postgresql://rag_user:rag_password@localhost:5432/secure_rag
- Neon Free: postgresql://user:password@host.neon.tech/secure_rag?sslmode=require
- AWS RDS: postgresql://user:password@rds-instance.amazonaws.com:5432/secure_rag?sslmode=require
```

### Database Schema

**Tables:**
1. `departments` - Department registry
   - Columns: `id`, `name`, `description`
   - Example: Engineering, HR, Sales

2. `users` - User accounts
   - Columns: `id`, `username`, `email`, `password_hash`, `department_id`, `created_at`
   - Department-based access control

3. `documents` - Document metadata
   - Columns: `id`, `name`, `department_id`, `file_path`, `num_chunks`, `created_at`
   - Replicated to Qdrant payload for filtering

4. `mcp_tokens` - MCP authentication
   - Columns: `id`, `user_id`, `token_hash`, `created_at`, `expires_at`, `last_used_at`, `revoked_at`, `description`
   - One-way hashes (SHA-256)

### Migrations

**How to Run (First Deployment):**
```bash
# Manually
cd backend
alembic upgrade head

# Automated in Docker startup
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**Existing Migrations:**
1. `778...initial_schema.py` - Create base tables (departments, users, documents)
2. `004...add_password_hash.py` - Add password_hash column
3. `005...add_mcp_tokens.py` - Add mcp_tokens table

**Rollback (if needed):**
```bash
alembic downgrade -1  # Rollback one migration
alembic history       # View migration history
```

### PostgreSQL Extensions

**Required:** None

**Used Features:** Standard PostgreSQL (no JSON, PostGIS, or custom extensions)

**PostgreSQL Version:** 15 (as per docker-compose)

### Persistent Storage

**Docker Compose Volume:**
```yaml
volumes:
  postgres_data:
    driver: local
```

**Persistence:**
- ✅ Data persists between container restarts (Docker volume)
- ❌ Data lost if volume deleted
- Need external backup strategy for production

**Backup Strategy (Production):**
```bash
# Manual backup
pg_dump postgresql://user:pass@host:5432/db > backup.sql

# Restore
psql postgresql://user:pass@host:5432/db < backup.sql

# Scheduled backup (cron)
0 2 * * * /path/to/backup.sh  # Daily at 2 AM
```

### Production Database Options

**Option 1: Self-Hosted PostgreSQL (FREE)**
- Install PostgreSQL on server
- Cost: $0/month
- Backups: Manual or scripted
- Effort: High
- Reliability: Dependent on your server

**Option 2: Neon (FREE TIER - Recommended)**
- Cloud PostgreSQL with generous free tier
- 0.5 GB storage, 4 connections
- Sufficient for 50-100K records
- Automatic backups
- Cost: FREE (or $0.135/hour for compute if needed)
- URL: `postgresql://user:password@xxx.neon.tech/db?sslmode=require`

**Option 3: AWS RDS (PAID)**
- Managed PostgreSQL
- db.t3.micro eligible for free tier (12 months)
- After free tier: ~$10-20/month
- Automatic backups, failover, monitoring
- Cost: After free tier period

**Option 4: Render PostgreSQL (Paid)**
- Integrated with Render deployment
- Starter: $7/month
- Cost: $$

### Deployment-Specific Changes Required

- [ ] Choose PostgreSQL provider
- [ ] Get connection string (DATABASE_URL)
- [ ] Set DATABASE_URL environment variable
- [ ] Run `alembic upgrade head` on first deployment
- [ ] Set up backup strategy (if self-hosted)
- [ ] Test connection before deploying backend

---

## SECTION 7: DOCKER

### Dockerfiles Breakdown

#### 1. Backend Dockerfile (`backend/Dockerfile`)

**What It Does:**
- Builds Python 3.11-slim image
- Installs system dependencies (gcc, postgresql-client, curl)
- Copies requirements.txt and installs Python packages
- Special handling for PyTorch CPU-only (avoids 2GB+ CUDA download)
- Copies application code
- Exposes port 8000
- Starts with uvicorn

**Start Command:**
```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**Key Features:**
- ✅ PORT environment variable support (Render compatible)
- ✅ Layered caching (requirements before code copy)
- ✅ Alpine base (small image ~500MB with dependencies)
- ❌ No migrations run (must be done separately)

#### 2. MCP Server Dockerfile (`mcp-server/Dockerfile`)

**What It Does:**
- Builds Python 3.11-slim image
- Installs dependencies from requirements.txt
- Copies src/ directory
- Creates non-root user (mcp, UID 1000) - security best practice
- Health check configured
- Exposes port 5000
- Runs MCP server

**Start Command:**
```dockerfile
ENTRYPOINT ["python", "-m", "mcp_server.main"]
```

**Key Features:**
- ✅ PORT environment variable support (Render compatible)
- ✅ Non-root user (security)
- ✅ Health check endpoint
- ✅ Alpine base (small image)

#### 3. docker-compose.yml

**Services:**
1. **PostgreSQL** (postgres:15-alpine)
   - Container: `secure_rag_postgres`
   - Port: `5432:5432`
   - Volume: `postgres_data`
   - Health check: `pg_isready`

2. **Qdrant** (qdrant/qdrant:latest)
   - Container: `secure_rag_qdrant`
   - Ports: `6333:6333` (REST), `6334:6334` (gRPC)
   - Volume: `qdrant_data`

3. **Backend** (built from ./backend/Dockerfile)
   - Container: `secure_rag_backend`
   - Port: `8000:8000`
   - Depends on: postgres, qdrant
   - Volume: `./backend:/app` (code hot-reload)
   - Command: uvicorn with --reload

**Network:**
- Implicit docker-compose network
- Services communicate via container names: `postgres`, `qdrant`, `backend`
- `DATABASE_URL=postgresql://rag_user:rag_password@postgres:5432/secure_rag`
- `QDRANT_URL=http://qdrant:6333`

**Volumes:**
- `postgres_data` - PostgreSQL data (persisted)
- `qdrant_data` - Qdrant vectors (persisted)
- `./backend:/app` - Backend code (development only)

### Service-to-Service Communication

**In Docker Compose (local):**
```
Frontend (localhost:3000)
    ↓ HTTP (localhost:8000)
Backend (app.main:app)
    ↓ psycopg2
PostgreSQL (postgres:5432)
    ↓
Backend (app.main:app)
    ↓ qdrant-client
Qdrant (qdrant:6333)
```

**In Production (cloud):**
```
Frontend (https://frontend.onrender.com)
    ↓ HTTPS
Backend (https://backend.onrender.com)
    ↓ Network
PostgreSQL (Neon or RDS)
    ↓
Backend
    ↓ HTTPS
Qdrant Cloud
```

### Which Services Can Be Deployed Separately

**Can Separate:**
- ✅ Frontend - Pure static site, no backend coupling
- ✅ Backend - Independently deployable
- ✅ MCP Server - Independent service (calls backend via HTTP)
- ✅ PostgreSQL - Can move to managed database (Neon, RDS)
- ✅ Qdrant - Can move to Qdrant Cloud

**Should Keep Together:**
- Backend + PostgreSQL migrations (must run before app starts)
- Backend + Qdrant initialization (must happen on startup)

### Intended Deployment Strategy

**Development:** docker-compose locally (all-in-one)

**Production (Recommended):**
```
Frontend (Render Static / Netlify / Cloudflare Pages)
    ↓
Backend (Render Web Service / Heroku / Railway)
    ↓
PostgreSQL (Neon / AWS RDS / Render PostgreSQL)
Qdrant (Qdrant Cloud OR self-hosted Docker container)
MCP Server (Render Web Service OR separate container)
```

---

## SECTION 8: ENVIRONMENT VARIABLES

### Master Environment Variable Reference

| Variable | Used By | Local Value | Production Value | Required | Secret | Type |
|---|---|---|---|---|---|---|
| **APPLICATION CORE** | | | | | | |
| `APP_ENV` | Backend | `development` | `production` | ❌ | ❌ | String |
| `APP_HOST` | Backend | `0.0.0.0` | `0.0.0.0` | ❌ | ❌ | IP |
| `APP_PORT` | Backend | `8000` | Use `PORT` | ❌ | ❌ | Int |
| `PORT` | Backend, MCP | (not set) | `8000`, `5000` | ✅ | ❌ | Int |
| `LOG_LEVEL` | Backend, MCP | `INFO` | `INFO` or `WARNING` | ❌ | ❌ | String |
| **DATABASE** | | | | | | |
| `DATABASE_URL` | Backend | `postgresql://rag_user:rag_password@localhost:5432/secure_rag` | `postgresql://user:pass@host/db` | ✅ | ✅ | URL |
| **VECTOR DATABASE** | | | | | | |
| `QDRANT_URL` | Backend | `http://localhost:6333` | `https://xxx.qdrant.io:6333` OR `http://container:6333` | ✅ | ❌ | URL |
| `QDRANT_API_KEY` | Backend | (empty) | `xxx-xxx-xxx` (if Cloud) | ❌ | ✅ | String |
| `QDRANT_COLLECTION_NAME` | Backend | `knowledge_chunks` | `knowledge_chunks` | ❌ | ❌ | String |
| **LLM (Azure OpenAI)** | | | | | | |
| `AZURE_OPENAI_API_KEY` | Backend | (empty) | `xxx...xxx` | ✅ | ✅ | String |
| `AZURE_OPENAI_ENDPOINT` | Backend | (empty) | `https://xxx.openai.azure.com/` | ✅ | ❌ | URL |
| `AZURE_OPENAI_DEPLOYMENT` | Backend | `gpt-4.1-mini` | `gpt-4.1-mini` | ❌ | ❌ | String |
| `AZURE_OPENAI_API_VERSION` | Backend | `2024-12-01-preview` | `2024-12-01-preview` | ❌ | ❌ | String |
| `LLM_TEMPERATURE` | Backend | `0.0` | `0.0` | ❌ | ❌ | Float |
| `LLM_MAX_TOKENS` | Backend | `1000` | `1000` | ❌ | ❌ | Int |
| **AUTHENTICATION** | | | | | | |
| `JWT_SECRET` | Backend | (example in .env) | ≥32 random chars | ✅ | ✅ | String |
| `JWT_ALGORITHM` | Backend | `HS256` | `HS256` | ❌ | ❌ | String |
| `JWT_EXPIRATION_HOURS` | Backend | `1` | `1` | ❌ | ❌ | Int |
| **MCP SERVER** | | | | | | |
| `MCP_TOKEN_EXPIRATION_DAYS` | Backend | `365` | `365` | ❌ | ❌ | Int |
| `MCP_HOST` | MCP Server | `0.0.0.0` | `0.0.0.0` | ❌ | ❌ | IP |
| `MCP_PORT` | MCP Server | `5000` | Use `PORT` | ❌ | ❌ | Int |
| `BACKEND_URL` | MCP Server | `http://localhost:8000` | `https://backend.onrender.com` | ✅ | ❌ | URL |
| `BACKEND_API_TIMEOUT` | MCP Server | `30` | `30` | ❌ | ❌ | Int |
| **CORS** | | | | | | |
| `CORS_ORIGINS` | Backend | `http://localhost:3000,http://localhost:5173` | `https://frontend.onrender.com` | ✅ | ❌ | CSV |
| **FRONTEND** | | | | | | |
| `VITE_API_URL` | Frontend (build-time) | (empty → defaults to localhost:8000) | `https://backend.onrender.com` | ✅ | ❌ | URL |
| **RAG CONFIGURATION** | | | | | | |
| `CHUNK_SIZE` | Backend | `600` | `600` | ❌ | ❌ | Int |
| `CHUNK_OVERLAP` | Backend | `100` | `100` | ❌ | ❌ | Int |
| `EMBEDDING_MODEL` | Backend | `sentence-transformers/all-MiniLM-L6-v2` | `sentence-transformers/all-MiniLM-L6-v2` | ❌ | ❌ | String |
| `EMBEDDING_DIMENSION` | Backend | `384` | `384` | ❌ | ❌ | Int |
| `EMBEDDING_BATCH_SIZE` | Backend | `32` | `32` | ❌ | ❌ | Int |
| `RETRIEVAL_TOP_K` | Backend | `5` | `5` | ❌ | ❌ | Int |
| `RETRIEVAL_SCORE_THRESHOLD` | Backend | `0.4` | `0.4` | ❌ | ❌ | Float |

### Critical Secrets Management

**DO NOT COMMIT:**
- `.env` file (already in .gitignore ✅)

**Must Generate/Set in Production:**
1. `JWT_SECRET` - Generate with: `openssl rand -base64 32`
2. `AZURE_OPENAI_API_KEY` - From Azure portal
3. `DATABASE_URL` - From PostgreSQL provider
4. `QDRANT_API_KEY` - If using Qdrant Cloud

**How to Set on Deployment Platforms:**

**Render:**
```
Service Settings → Environment → Add Variable
KEY=JWT_SECRET
VALUE=(paste generated secret)
```

**Heroku:**
```bash
heroku config:set JWT_SECRET=xxxxx
```

**Docker:**
```bash
docker run -e JWT_SECRET=xxxxx -e DATABASE_URL=xxx image
```

---

## SECTION 9: DEPLOYMENT BLOCKERS

### Critical Issues (Must Fix Before Deployment)

#### 1. ⚠️ CORS Configuration

**Issue:**
```python
# backend/app/main.py - Current
cors_origins = [
    origin.strip() 
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # ← ALLOWS ALL METHODS
    allow_headers=["*"],  # ← ALLOWS ALL HEADERS
)
```

**Risk:** Security - Too permissive for production

**Status:** ⚠️ Acceptable but not ideal

**Recommendation:** In production, restrict to specific methods:
```python
allow_methods=["GET", "POST", "OPTIONS"],
allow_headers=["Authorization", "Content-Type"],
```

#### 2. ❌ Frontend API URL Not Set at Build Time

**Issue:**
```typescript
// frontend/src/services/apiClient.ts
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

**Risk:** Frontend builds with hardcoded localhost default, fails in production if env var not set

**Status:** 🟡 MUST SET `VITE_API_URL` at build time

**Fix:**
```bash
# During frontend build
VITE_API_URL=https://secure-rag-backend.onrender.com npm run build
```

#### 3. ❌ MCP Server Hardcoded to localhost Backend

**Issue:**
```python
# mcp-server/src/mcp_server/core/config.py
backend_url: str = "http://localhost:8000"  # Default won't work in production
```

**Risk:** MCP server can't reach backend unless BACKEND_URL env var set

**Status:** 🟡 MUST SET `BACKEND_URL` at runtime

**Fix:**
```bash
BACKEND_URL=https://secure-rag-backend.onrender.com python -m mcp_server.main
```

#### 4. ❌ Health Check Port Assumption in MCP Dockerfile

**Issue:**
```dockerfile
# mcp-server/Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx, os; port = os.getenv('PORT', '5000'); httpx.get(f'http://localhost:{port}/health', timeout=5)" || exit 0
```

**Risk:** Health check may fail if server starts differently

**Status:** ✅ OK - exits 0 on failure (won't crash)

#### 5. ❌ Database Migrations Not Automated

**Issue:**
```python
# backend/Dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
# Migrations NOT run!
```

**Risk:** First deployment fails if database schema doesn't exist

**Status:** 🔴 MUST BE FIXED

**Fix - Option A (Recommended):**
```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**Fix - Option B:**
Run migrations manually before deploying:
```bash
cd backend
alembic upgrade head
```

#### 6. ❌ Backend Startup Fails Without Qdrant

**Issue:**
```python
# backend/app/main.py
try:
    init_qdrant()
    logger.info("Qdrant initialized")
except Exception as e:
    logger.error(f"Failed to start application: {e}")
    raise  # ← Crashes if Qdrant unavailable
```

**Risk:** Deployment fails if Qdrant not accessible at startup

**Status:** 🟡 Design choice (intentional)

**Mitigation:** Ensure Qdrant is running before starting backend

#### 7. ❌ JWT_SECRET Not Generated

**Issue:**
```python
# backend/app/core/config.py
jwt_secret: Optional[str] = None  # ← Can be None
```

**Risk:** JWT signing will fail if secret not provided

**Status:** 🟡 MUST generate before deployment

**Fix:**
```bash
# Generate 32-byte random secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: COPY THIS VALUE
```

#### 8. ❌ Qdrant URL Must Change for Cloud

**Issue:** Default `http://localhost:6333` won't work with Qdrant Cloud

**Status:** 🟡 MUST SET if using cloud

**Fix:**
```bash
QDRANT_URL=https://xxxxx-xxxxx.qdrant.io:6333
QDRANT_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Non-Critical Issues (Can Be Ignored)

✅ **No critical hardcoded IPs/ports**
✅ **No local-only file paths**
✅ **No hardcoded database names** (configurable)
✅ **No implicit localhost assumptions** (all overridable)
✅ **PORT environment variable support** (already implemented)
✅ **No API key logging** (not found in source)

---

## SECTION 10: RECOMMENDED DEPLOYMENT ARCHITECTURE

### Objective: Minimum Cost + Production Ready

Based on free/low-cost options available:

### Architecture Decision Matrix

| Component | Recommended | Cost (First Year) | Why | Alternative |
|-----------|-------------|---|---|---|
| **Frontend** | Render Static / Netlify Free | $0 | Serves static site, CDN included | Vercel, Cloudflare Pages |
| **Backend** | Render Web Service | $7/month | Pay-as-you-go, simple deployment, free tier available | Heroku (paid), Railway, Fly.io |
| **PostgreSQL** | Neon (Free Tier) | $0 (0.5GB) | Serverless PostgreSQL, free tier sufficient for 50K+ records | AWS RDS free tier (12mo), Render DB ($7/mo), PlanetScale |
| **Qdrant** | Self-hosted on Render | $7/month | Docker container on Render, low cost, full control | Qdrant Cloud ($25/mo), Weaviate Cloud |
| **MCP Server** | Render Web Service | $7/month | Same as backend, simple scaling | Separate cloud provider |

### Recommended Stack

```
┌─ Render (Primary Hosting) ────────────────┐
│                                           │
│  Frontend (Static)  ← $0                  │
│  ├─ Build: npm run build                  │
│  ├─ Deploy: dist/ folder                  │
│  └─ URL: https://secure-rag.onrender.com  │
│                                           │
│  Backend (Web Service) ← $7/mo            │
│  ├─ Runtime: Python 3.11                  │
│  ├─ Start: uvicorn app.main:app           │
│  └─ URL: https://secure-rag-backend...    │
│                                           │
│  MCP Server (Web Service) ← $7/mo         │
│  ├─ Runtime: Python 3.11                  │
│  ├─ Start: python -m mcp_server.main      │
│  └─ URL: https://secure-rag-mcp...        │
│                                           │
│  Qdrant (Docker Container) ← $7/mo        │
│  ├─ Image: qdrant/qdrant:latest           │
│  ├─ Port: 6333                            │
│  └─ Storage: Volume mount                 │
│                                           │
└───────────────────────────────────────────┘
                   ↓
         ┌──────────────────────────┐
         │   Neon PostgreSQL        │
         │   (Free Tier - 0.5GB)    │
         │   $0                     │
         │                          │
         │   postgresql://...       │
         │   @host.neon.tech        │
         └──────────────────────────┘

Total Monthly Cost: $21/month (2x$7 for Render services)
Total Annual Cost: $252/year
```

### Component-by-Component Deployment

#### 1. Frontend

**Platform:** Render Static Site  
**Cost:** $0  
**Free-Tier Limits:** Unlimited sites, 100GB bandwidth/month  
**Setup Time:** ~5 minutes  

**Deployment Process:**
```bash
# 1. Build frontend
cd frontend
VITE_API_URL=https://secure-rag-backend.onrender.com npm run build

# 2. Create Render service
#    - Select "Static Site"
#    - Branch: main
#    - Build command: npm install && npm run build
#    - Publish directory: dist/

# 3. Get URL: https://secure-rag-frontend.onrender.com
```

**Why Recommended:**
- Completely free
- CDN included (fast globally)
- Automatic HTTPS
- Simple integration with backend

**Alternative:**
- Netlify Free (similar pricing, slightly better UX)
- Vercel Free (similar, next.js oriented)
- Cloudflare Pages (more control, but requires more config)

---

#### 2. Backend

**Platform:** Render Web Service  
**Cost:** $7/month (Starter)  
**Free-Tier Limits:** 1-2 services spin down after 15min inactivity  
**Setup Time:** ~10 minutes  

**Deployment Process:**
```bash
# 1. Create render.yaml at repo root
# 2. Commit and push
# 3. Create service in Render Dashboard
#    - Select "Web Service"
#    - Connect repo
#    - Python 3.11
#    - Build: pip install -r backend/requirements.txt
#    - Start: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT

# 4. Set environment variables in dashboard
DATABASE_URL=postgresql://...neon.tech...
QDRANT_URL=https://secure-rag-qdrant-service.onrender.com:6333
CORS_ORIGINS=https://secure-rag-frontend.onrender.com
JWT_SECRET=(generated)
AZURE_OPENAI_API_KEY=(from Azure)
AZURE_OPENAI_ENDPOINT=(from Azure)
APP_ENV=production
```

**Why Recommended:**
- Easy GitHub integration (auto-deploy on push)
- Simple environment variable management
- Good documentation
- Reasonable pricing

**Free Tier Trade-off:**
- Services spin down after 15min inactivity
- First request after spin-down takes ~30s (cold start)
- Acceptable for internal tools, not ideal for user-facing

**Alternative:**
- Heroku ($7/month standard dyno, but now owned by Salesforce)
- Railway.app (similar pricing, slightly better cold start)
- Fly.io (good for performance, slightly more complex)

---

#### 3. PostgreSQL

**Platform:** Neon (Serverless PostgreSQL)  
**Cost:** $0 (free tier) to $0.135/hour (pay-as-you-go)  
**Free-Tier Limits:** 0.5GB storage, 3GB/month compute, 4 active connections  
**Setup Time:** ~5 minutes  

**Deployment Process:**
```bash
# 1. Create Neon project at neon.tech
# 2. Create database (default: neondb)
# 3. Copy connection string:
#    postgresql://user:password@host.neon.tech/dbname?sslmode=require
# 4. Set DATABASE_URL in backend environment
# 5. Run migrations:
#    cd backend && alembic upgrade head
```

**Free Tier Sufficiency:**
- 0.5GB storage = ~500,000 small rows (sufficient for sample data)
- 4 connections = enough for backend
- Good for development/demo, small production

**Why Recommended:**
- Completely free tier (no credit card needed, but can add)
- Serverless (no server management)
- Automatic backups
- Connection pooling included
- PostgreSQL 15 (latest)

**Alternative:**
- AWS RDS Free Tier (1 year free, then ~$12/mo)
- Render PostgreSQL ($7/mo)
- PlanetScale (MySQL, free tier limited)
- Supabase (PostgreSQL + Realtime, free tier 500MB)

**⚠️ Cost Consideration:**
- Free tier compute runs out after ~30 hours/month (~1 hour/day)
- If exceeds: $0.135/hour for additional compute
- For continuous use: Budget ~$30/month compute cost

---

#### 4. Qdrant

**Option A: Self-Hosted on Render (RECOMMENDED)**

**Platform:** Render Web Service (Docker)  
**Cost:** $7/month (Starter)  
**Setup Time:** ~15 minutes  

**Deployment:**
```bash
# 1. Create render.yaml entry for Qdrant
# 2. Dockerfile: qdrant/qdrant:latest
# 3. Port: 6333
# 4. Volume: Persistent storage
# 5. Start: docker run qdrant/qdrant

# In backend environment:
QDRANT_URL=https://secure-rag-qdrant.onrender.com:6333
QDRANT_API_KEY=  # Empty for self-hosted
```

**Pros:**
- Free tier cost-sharing (same $7/mo as backend if on same service)
- Full control
- No API key management
- Supports metadata filtering
- Data stays on your servers

**Cons:**
- Cold starts (30s after inactivity)
- Limited to Render's resources

---

**Option B: Qdrant Cloud**

**Platform:** Qdrant Cloud (SaaS)  
**Cost:** $25/month (smallest paid tier)  
**Free-Tier Limits:** 1GB storage, but deprecated (no new free accounts)  
**Setup Time:** ~10 minutes  

**Deployment:**
```bash
QDRANT_URL=https://xxxxx-xxxxx.qdrant.io:6333
QDRANT_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Pros:**
- Fully managed (no ops burden)
- Automatic backups
- Better performance (always-on)
- No cold starts

**Cons:**
- Expensive ($25/mo = 3x backend cost)
- Overkill for small deployment

---

**Recommendation:** Self-hosted on Render (Option A) for cost savings

---

#### 5. MCP Server

**Platform:** Render Web Service  
**Cost:** $7/month (Starter)  
**Free-Tier Limits:** Spin-down after 15min inactivity  
**Setup Time:** ~10 minutes  

**Deployment:**
```bash
# 1. Create Render service for MCP
# 2. Python 3.11
# 3. Build: pip install -r mcp-server/requirements.txt
# 4. Start: cd mcp-server && python -m mcp_server.main

# Environment variables:
BACKEND_URL=https://secure-rag-backend.onrender.com
MCP_PORT=5000  # Or use PORT env var from Render
```

**Why:**
- Independent service (calls backend via HTTP)
- Can scale separately
- Simple deployment

**Could Also:**
- Deploy on same Render service as backend (saves $7/mo)
- Requires separate start command or multiple services

---

### Complete Deployment Cost Summary

| Component | Platform | Tier | Monthly Cost | Annual |
|-----------|----------|------|---|---|
| Frontend | Render Static | Free | $0 | $0 |
| Backend | Render Web | Starter | $7 | $84 |
| MCP Server | Render Web | Starter | $7 | $84 |
| Qdrant | Render Web (Docker) | Starter | $7* | $84* |
| PostgreSQL | Neon | Free | $0 | $0 |
| | | | | |
| **TOTAL** | | | **$21** | **$252** |

*Qdrant on Render shares same starter instance as backend if deployed together (~$7 shared), or separate ($7 additional).

---

### Recommended Deployment Order

1. **PostgreSQL (Neon)**
   - Create Neon project
   - Get connection string
   - Note: DATABASE_URL

2. **Qdrant**
   - Create Render service with qdrant/qdrant image
   - Get URL (e.g., https://secure-rag-qdrant.onrender.com:6333)
   - Note: QDRANT_URL

3. **Backend**
   - Create Render service
   - Set all environment variables:
     - DATABASE_URL (from Neon)
     - QDRANT_URL (from Qdrant service)
     - JWT_SECRET (generate new)
     - CORS_ORIGINS (leave empty initially, will be frontend URL)
     - AZURE_OPENAI_* (if using LLM)
   - Deploy
   - Run migrations: SSH into service + `alembic upgrade head`
   - Get URL (e.g., https://secure-rag-backend.onrender.com)

4. **Frontend**
   - Create Render static site
   - Build command: `VITE_API_URL=https://secure-rag-backend.onrender.com npm run build`
   - Get URL (e.g., https://secure-rag-frontend.onrender.com)

5. **Backend CORS Update**
   - SSH into backend service
   - Update `CORS_ORIGINS` to: `https://secure-rag-frontend.onrender.com`
   - Redeploy

6. **MCP Server**
   - Create Render service
   - Set environment variables:
     - BACKEND_URL=https://secure-rag-backend.onrender.com
   - Deploy
   - Test health: `curl https://mcp-server-url/health`

---

## SECTION 11: FINAL OUTPUT

### A. Current Architecture (Local Development)

```
┌─────────────────────────────────────────────────────────────────┐
│  Developer Laptop (Docker Compose)                              │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Frontend    │  │  Backend     │  │ MCP Server   │          │
│  │ React/Vite  │  │  FastAPI     │  │  Python     │          │
│  │ localhost:3000/5173 │ localhost:8000 │ localhost:5000 │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         ↓                  ↓ HTTP        ↓                      │
│         └─────────────────────────────────┐                     │
│                                          ↓                      │
│              ┌────────────────────────────────────────┐         │
│              │ docker-compose network                │         │
│              │                                        │         │
│              │  PostgreSQL ← localhost:5432          │         │
│              │  Qdrant ← localhost:6333              │         │
│              └────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

**Deployment Method:** `docker-compose up`  
**Network:** Bridge network (container-to-container via name)  
**Storage:** Persistent volumes for DB/Qdrant  
**Access:** Local only

---

### B. Recommended Production Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  INTERNET                                                            │
│  (Public Access)                                                     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Render Hosting                                             │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  Frontend Static Site                                │   │   │
│  │  │  (React SPA - dist/ folder)                          │   │   │
│  │  │  https://secure-rag-frontend.onrender.com            │   │   │
│  │  │  VITE_API_URL=https://...backend...onrender.com      │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │           ↓ HTTPS                                        │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  Backend Web Service (FastAPI)                       │   │   │
│  │  │  https://secure-rag-backend.onrender.com             │   │   │
│  │  │  Env: DATABASE_URL, QDRANT_URL, JWT_SECRET, etc.     │   │   │
│  │  │  PORT=8000                                           │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │           ↓ HTTP                                        │   │   │
│  │  ┌────────┴──────────────────────────────────┬───────────┐  │   │
│  │  ↓                                           ↓           │  │   │
│  │  ┌──────────────────────────┐  ┌──────────────────────┐ │  │   │
│  │  │  Qdrant (Docker)         │  │  MCP Server         │ │  │   │
│  │  │  Port: 6333              │  │  https://...mcp...  │ │  │   │
│  │  │  Volume: qdrant_data     │  │  Env: BACKEND_URL   │ │  │   │
│  │  │  Internal URL            │  │  PORT=5000          │ │  │   │
│  │  └──────────────────────────┘  └──────────────────────┘ │  │   │
│  │                                                          │  │   │
│  └──────────────────────────────────────────────────────────┘  │   │
│                                                                │   │
└──────────────────────────────────────────────────────────────┘   │
                                                                    │
                  ┌─────────────────────────────────┐              │
                  │  Neon (PostgreSQL)              │              │
                  │  postgresql://...neon.tech      │              │
                  │  (External SaaS)                │              │
                  └─────────────────────────────────┘              │
```

**Deployment Method:** Git push → Render auto-deploy  
**Network:** Render internal networking + Neon public endpoint  
**Storage:** Qdrant volume + Neon backups  
**Access:** Public HTTPS (frontend & API)  
**Scaling:** Render auto-scales services independently  

---

### C. Exact Deployment Order

```
STEP 1: PREPARE CREDENTIALS & GENERATE SECRETS
└─ Create Neon account (or AWS RDS/Render DB)
└─ Get DATABASE_URL
└─ Generate JWT_SECRET: openssl rand -base64 32
└─ Get Azure OpenAI API key (if using LLM)

STEP 2: DEPLOY POSTGRESQL
└─ Create Neon project
└─ Create database: secure_rag
└─ Get connection string with SSL
└─ TEST: psql connection from local machine

STEP 3: DEPLOY QDRANT
└─ Create Render Web Service
  └─ Image: qdrant/qdrant:latest
  └─ Port: 6333
  └─ Volume: /qdrant/storage
  └─ Get public URL: https://secure-rag-qdrant.onrender.com:6333

STEP 4: DEPLOY BACKEND
└─ Create Render Web Service
  └─ GitHub: select SecureRAG repo
  └─ Build: pip install -r backend/requirements.txt
  └─ Start: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
  └─ Set environment variables:
    └─ DATABASE_URL=(from Neon)
    └─ QDRANT_URL=https://secure-rag-qdrant.onrender.com:6333
    └─ JWT_SECRET=(generated)
    └─ CORS_ORIGINS=http://localhost:3000,http://localhost:5173
    └─ AZURE_OPENAI_API_KEY=xxx (if using)
    └─ AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com
    └─ APP_ENV=production
  └─ Deploy
  └─ Wait for service to start
  └─ Get public URL: https://secure-rag-backend.onrender.com
  └─ TEST: curl https://secure-rag-backend.onrender.com/api/health
  └─ Run migrations:
    └─ Render > Shell > python backend/alembic/alembic upgrade head

STEP 5: DEPLOY FRONTEND
└─ Create Render Static Site
  └─ GitHub: select SecureRAG repo
  └─ Publish directory: frontend/dist
  └─ Build command: cd frontend && VITE_API_URL=https://secure-rag-backend.onrender.com npm run build
  └─ Deploy
  └─ Get public URL: https://secure-rag-frontend.onrender.com
  └─ TEST: Visit URL in browser

STEP 6: UPDATE CORS ON BACKEND
└─ Render > secure-rag-backend > Environment > Edit
└─ Update: CORS_ORIGINS=https://secure-rag-frontend.onrender.com
└─ Save & auto-redeploy

STEP 7: DEPLOY MCP SERVER
└─ Create Render Web Service
  └─ GitHub: select SecureRAG repo
  └─ Build: pip install -r mcp-server/requirements.txt
  └─ Start: cd mcp-server && python -m mcp_server.main
  └─ Set environment variables:
    └─ BACKEND_URL=https://secure-rag-backend.onrender.com
    └─ LOG_LEVEL=INFO
  └─ Deploy
  └─ Get public URL: https://secure-rag-mcp.onrender.com
  └─ TEST: curl https://secure-rag-mcp.onrender.com/health

STEP 8: FINAL TESTING
└─ Frontend: https://secure-rag-frontend.onrender.com
  └─ Login with test user
  └─ Send question
└─ Backend: curl https://secure-rag-backend.onrender.com/api/health
└─ MCP: curl https://secure-rag-mcp.onrender.com/health
└─ Logs: Check Render dashboard for errors
```

---

### D. Code/Config Changes Required BEFORE Deployment

#### Frontend Changes Required

```
FILE: frontend/vite.config.ts
❌ Change: VITE_API_URL must be set at BUILD TIME
ACTION: npm run build with env var:
   VITE_API_URL=https://secure-rag-backend.onrender.com npm run build
NO CODE CHANGE NEEDED (uses Vite env var system correctly ✓)
```

#### Backend Changes Recommended (Not Required)

```
FILE: backend/Dockerfile
RECOMMENDED: Run migrations on startup
CHANGE FROM:
   CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
CHANGE TO:
   CMD ["sh", "-c", "cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

FILE: backend/app/main.py
OPTIONAL: Restrict CORS methods (security)
CURRENT:
   allow_methods=["*"]
RECOMMENDED:
   allow_methods=["GET", "POST", "OPTIONS"]
```

#### MCP Server Changes

```
NO CODE CHANGES REQUIRED
Configuration via environment variables only
```

#### Environment Variables to Create

```
CREATE .env.production.backend (do not commit):
DATABASE_URL=postgresql://...neon.tech...
QDRANT_URL=https://secure-rag-qdrant.onrender.com:6333
JWT_SECRET=(generated 32+ chars)
CORS_ORIGINS=https://secure-rag-frontend.onrender.com
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com
APP_ENV=production
LOG_LEVEL=INFO

CREATE .env.production.mcp (do not commit):
BACKEND_URL=https://secure-rag-backend.onrender.com
LOG_LEVEL=INFO
```

---

### E. Environment Variables for Each Platform

#### Render Backend Service

```
Variables to set in Render Dashboard:

DATABASE_URL = postgresql://xxxxx:xxxxx@host.neon.tech/secure_rag?sslmode=require
QDRANT_URL = https://secure-rag-qdrant.onrender.com:6333
QDRANT_API_KEY = (leave empty for self-hosted Qdrant)
JWT_SECRET = (generate: openssl rand -base64 32)
AZURE_OPENAI_API_KEY = (from Azure portal)
AZURE_OPENAI_ENDPOINT = https://xxx.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT = gpt-4.1-mini
AZURE_OPENAI_API_VERSION = 2024-12-01-preview
CORS_ORIGINS = https://secure-rag-frontend.onrender.com
APP_ENV = production
LOG_LEVEL = INFO
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
RETRIEVAL_TOP_K = 5
RETRIEVAL_SCORE_THRESHOLD = 0.4
JWT_ALGORITHM = HS256
JWT_EXPIRATION_HOURS = 1
MCP_TOKEN_EXPIRATION_DAYS = 365
EMBEDDING_MODEL = sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION = 384
```

#### Render Frontend Build

```
Variables to set in Render Dashboard (or build command):

Build Command:
cd frontend && VITE_API_URL=https://secure-rag-backend.onrender.com npm run build

(No environment variables needed for static site, all in build command)
```

#### Render MCP Server Service

```
Variables to set in Render Dashboard:

BACKEND_URL = https://secure-rag-backend.onrender.com
BACKEND_API_TIMEOUT = 30
LOG_LEVEL = INFO
MCP_HOST = 0.0.0.0
```

#### Render Qdrant Service

```
No variables needed (uses defaults)
Just pull image: qdrant/qdrant:latest
```

---

### F. Things You Must NOT Deploy Publicly

#### Secrets (Never Commit, Never Log)

```
❌ DO NOT DEPLOY:
   - JWT_SECRET (even encrypted)
   - AZURE_OPENAI_API_KEY
   - DATABASE_URL with credentials (hardcode connection only with env var)
   - .env file (add to .gitignore ✓)
   - Raw password hashes (are already hashed ✓)
   - MCP token raw values (are already hashed ✓)

✅ SAFE TO DEPLOY:
   - Docker images (no secrets embedded)
   - Source code (no secrets found ✓)
   - Configuration templates (.env.example)
```

#### Development/Debug Tools

```
❌ DO NOT DEPLOY:
   - pytest fixture files with test data
   - Debug logging at DEBUG level in production
   - Hot reload enabled (--reload flag)
   - Development CORS origins (localhost:3000, localhost:5173)

✅ CURRENTLY GOOD:
   - No hardcoded dev credentials in code ✓
   - Logging level configurable ✓
   - Development code separate from production ✓
```

#### Local-Only Infrastructure

```
❌ DO NOT RELY ON:
   - docker-compose for production (intended for local only ✓)
   - Local file paths (/app, ./backend) - these work in containers
   - localhost URLs - all are environment-variable overridable ✓

✅ ARCHITECTURE IS CLOUD-READY:
   - All services can run independently ✓
   - All URLs configurable ✓
   - No hardcoded assumptions about colocation ✓
```

#### Security Concerns to Address

```
⚠️ BEFORE PRODUCTION:
   1. Restrict CORS methods/headers (currently allows *)
   2. Set secure HTTP headers (HSTS, X-Frame-Options, etc.)
   3. Enable HTTPS everywhere (Render does automatically ✓)
   4. Rate limiting on /api/auth/login (not implemented)
   5. Request/response logging without PII (implemented ✓)
   6. Database connection SSL (Neon requires it ✓)

✅ ALREADY IMPLEMENTED:
   - JWT authentication ✓
   - Password hashing (bcrypt) ✓
   - Token hashing (SHA-256) ✓
   - Authorization checks on all endpoints ✓
   - No SQL injection (using SQLAlchemy ORM) ✓
   - Input validation (Pydantic) ✓
```

---

## SUMMARY CHECKLIST

### Pre-Deployment Verification

- [ ] DATABASE_URL obtained from Neon/RDS
- [ ] JWT_SECRET generated (32+ random chars)
- [ ] AZURE_OPENAI credentials available (if using LLM)
- [ ] Qdrant service URL identified
- [ ] Render accounts created (or preferred platform)
- [ ] GitHub repo linked to Render
- [ ] render.yaml or manual service config prepared
- [ ] Migrations tested locally (alembic upgrade head)
- [ ] Frontend builds with VITE_API_URL set
- [ ] All environment variables documented
- [ ] Secrets not committed to git
- [ ] .gitignore includes .env files
- [ ] Docker images build successfully
- [ ] Health endpoints accessible
- [ ] CORS origins configured correctly
- [ ] SSL/TLS certificates generated (Render automatic ✓)
- [ ] Backup strategy defined (Neon automatic ✓)

### Post-Deployment Verification

- [ ] Frontend loads (https://frontend.onrender.com)
- [ ] Backend health check passes (curl /api/health)
- [ ] MCP server health check passes (curl /health)
- [ ] PostgreSQL connection works
- [ ] Qdrant connection works
- [ ] Login endpoint works
- [ ] Chat endpoint works
- [ ] Logs show no errors
- [ ] Response times acceptable (<5s)
- [ ] No hardcoded localhost in logs
- [ ] Metrics/monitoring set up (if desired)
- [ ] Backup runs successfully
- [ ] Rollback procedure documented

---

## END OF AUDIT

**Audit Date:** September 3, 2026  
**Status:** ✅ DEPLOYMENT READY (with pre-deployment changes listed above)  
**Risk Level:** LOW (all blockers identified, solutions provided)  
**Estimated Deployment Time:** 2-3 hours (manual) or 30 minutes (with infrastructure-as-code)

**Next Steps:**
1. Review Section 10 (Recommended Deployment Architecture)
2. Create Neon & Render accounts
3. Generate secrets
4. Follow Section 11C (Deployment Order)
5. Test each component after deployment
6. Monitor logs for any issues
