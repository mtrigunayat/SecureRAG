# Environment Variable Configuration Matrix

This document provides a complete matrix of all environment variables for different deployment scenarios.

---

## Quick Copy-Paste Template

### Local Development
```bash
# .env for local development
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=postgresql://rag_user:rag_password@localhost:5432/secure_rag
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
JWT_SECRET=dev-secret-minimum-32-characters-long
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
MCP_HOST=0.0.0.0
MCP_PORT=5000
BACKEND_URL=http://localhost:8000
LOG_LEVEL=INFO
```

### Cloud (Render + Neon + Qdrant Cloud)
```bash
# Render Environment Variables
# Backend Service
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000  # Will be overridden by Render's PORT env var
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require
QDRANT_URL=https://xxxxx.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
JWT_SECRET=generate-new-32-char-secret
CORS_ORIGINS=https://yourdomain.com,https://frontend.onrender.com
LOG_LEVEL=INFO

# MCP Service
BACKEND_URL=https://your-backend.onrender.com
MCP_HOST=0.0.0.0
MCP_PORT=5000  # Will be overridden by Render's PORT env var
BACKEND_API_TIMEOUT=30
LOG_LEVEL=INFO

# Frontend Build
VITE_API_URL=https://your-backend.onrender.com
```

---

## Detailed Variable Reference

### Application & Server

| Variable | Default | Production | Example | Purpose |
|----------|---------|-----------|---------|---------|
| `APP_ENV` | `development` | `production` | `production` | Controls logging verbosity, SQL echo, auto-reload |
| `APP_HOST` | `0.0.0.0` | `0.0.0.0` | `0.0.0.0` | Listen address (Render always uses 0.0.0.0) |
| `APP_PORT` | `8000` | `8000` | `8000` | **Ignored in cloud** - Render overrides via `PORT` env var |
| `MCP_HOST` | `0.0.0.0` | `0.0.0.0` | `0.0.0.0` | MCP server listen address |
| `MCP_PORT` | `5000` | `5000` | `5000` | **Ignored in cloud** - Render overrides via `PORT` env var |

### Database

| Variable | Default | Required | Example | Purpose |
|----------|---------|----------|---------|---------|
| `DATABASE_URL` | None | ✅ YES | `postgresql://rag_user:password@localhost:5432/secure_rag` | PostgreSQL connection string (REQUIRED) |
| | | | `postgresql://user:pass@host.neon.tech/dbname?sslmode=require` | Production (Neon) format |

**Connection String Formats**:
- **Local**: `postgresql://username:password@localhost:5432/dbname`
- **Neon Cloud**: `postgresql://username:password@project.neon.tech/dbname?sslmode=require`

### Vector Database (Qdrant)

| Variable | Default | Required | Example | Purpose |
|----------|---------|----------|---------|---------|
| `QDRANT_URL` | `http://localhost:6333` | ✅ YES (cloud) | `http://localhost:6333` | Local Qdrant instance |
| | | | `https://xxxxx-us-east1-0.qdrant.io:6333` | Qdrant Cloud instance |
| `QDRANT_API_KEY` | (empty) | ❌ NO (local) | (empty) | Not needed for local Qdrant |
| | | ✅ YES (cloud) | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | **Required for Qdrant Cloud** |
| `QDRANT_COLLECTION_NAME` | `knowledge_chunks` | ✅ YES | `knowledge_chunks` | Must match actual collection in Qdrant |

**Important**: If using Qdrant Cloud, you MUST create the collection manually before deploying:
- Go to Qdrant Cloud Dashboard
- Create collection with: **Vector Size: 384, Distance: Cosine**

### Azure OpenAI (LLM)

| Variable | Default | Required | Example | Purpose |
|----------|---------|----------|---------|---------|
| `AZURE_OPENAI_API_KEY` | None | ✅ YES | `abcd1234efgh5678...` | API key from Azure Portal |
| `AZURE_OPENAI_ENDPOINT` | None | ✅ YES | `https://my-resource.openai.azure.com/` | Resource endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4.1-mini` | ❌ NO | `gpt-4.1-mini` | Must match deployed model name |
| `AZURE_OPENAI_API_VERSION` | `2024-12-01-preview` | ❌ NO | `2024-12-01-preview` | API version (keep current) |

**Where to find**:
1. Azure Portal → Azure OpenAI Service
2. Click your resource
3. Keys and Endpoint section
4. Copy Key1 and Endpoint URL

### Authentication & Security

| Variable | Default | Required | Example | Purpose |
|----------|---------|----------|---------|---------|
| `JWT_SECRET` | None | ✅ YES | `a1b2c3d4e5f6...` (32+ chars) | Signing key for JWT tokens |
| `JWT_ALGORITHM` | `HS256` | ❌ NO | `HS256` | JWT signing algorithm |
| `JWT_EXPIRATION_HOURS` | `1` | ❌ NO | `1` | Backend JWT lifetime |
| `MCP_TOKEN_EXPIRATION_DAYS` | `365` | ❌ NO | `365` | MCP token lifetime |

**Generating JWT_SECRET**:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**⚠️ SECURITY**: Use DIFFERENT `JWT_SECRET` values for local and production!

### CORS Configuration

| Variable | Default | Required | Example | Purpose |
|----------|---------|----------|---------|---------|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | ❌ NO | `https://yourdomain.com,https://frontend.onrender.com` | Comma-separated allowed origins |

**⚠️ SECURITY**: In production, specify only known domains. Never use wildcard `*`!

### Backend Connection (MCP Server)

| Variable | Default | Required | Example | Purpose |
|----------|---------|----------|---------|---------|
| `BACKEND_URL` | `http://localhost:8000` | ✅ YES (cloud) | `https://my-backend.onrender.com` | MCP server's backend endpoint |
| `BACKEND_API_TIMEOUT` | `30` | ❌ NO | `30` | Request timeout in seconds |

**Important**: MCP server reads this to call Backend. Must be deployed Backend URL in cloud!

### Frontend (Vite)

| Variable | Default | Required | Example | Purpose |
|----------|---------|----------|---------|---------|
| `VITE_API_URL` | `http://localhost:8000` | ✅ YES (cloud) | `https://my-backend.onrender.com` | API endpoint for frontend (build-time) |

**Note**: This is a **build-time** variable. Set it when building for production:
```bash
VITE_API_URL=https://my-backend.onrender.com npm run build
```

### Embedding & Retrieval

| Variable | Default | Required | Example | Purpose |
|----------|---------|----------|---------|---------|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | ❌ NO | (same) | Model name - **DO NOT CHANGE** |
| `EMBEDDING_DIMENSION` | `384` | ❌ NO | `384` | Vector dimension - **DO NOT CHANGE** |
| `RETRIEVAL_TOP_K` | `5` | ❌ NO | `5` | Number of documents to retrieve |
| `RETRIEVAL_SCORE_THRESHOLD` | `0.7` | ❌ NO | `0.4` - `0.9` | Minimum similarity score (0.0-1.0) |

**⚠️ WARNING**: Do NOT change embedding model or dimension - will break existing vectors!

### Logging

| Variable | Default | Required | Example | Purpose |
|----------|---------|----------|---------|---------|
| `LOG_LEVEL` | `INFO` | ❌ NO | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Logging verbosity |

**Recommended**:
- Local: `DEBUG` or `INFO`
- Production: `INFO` (never DEBUG - leaks details)

---

## Environment Variable Checklist

### Pre-Deployment

- [ ] All required variables documented above are set
- [ ] `DATABASE_URL` includes `?sslmode=require` (Neon requirement)
- [ ] `QDRANT_API_KEY` is set (if using Qdrant Cloud)
- [ ] `AZURE_OPENAI_API_KEY` is valid
- [ ] `JWT_SECRET` is 32+ characters (generated, not default)
- [ ] Different `JWT_SECRET` for local vs. production
- [ ] `CORS_ORIGINS` restricted to known domains (no wildcard)
- [ ] `.env` file is in `.gitignore` (NEVER commit secrets!)
- [ ] `.env.example` is committed (template only, no secrets)

### Render Setup

**Backend Service**:
- [ ] Created .env file with all Backend variables
- [ ] `DATABASE_URL` from Neon
- [ ] `QDRANT_URL` and `QDRANT_API_KEY` from Qdrant Cloud
- [ ] `AZURE_OPENAI_*` variables set
- [ ] `JWT_SECRET` generated (not default)
- [ ] `CORS_ORIGINS` includes frontend domain

**MCP Service**:
- [ ] Created .env file with MCP variables
- [ ] `BACKEND_URL` points to deployed Backend service
- [ ] `LOG_LEVEL` set (INFO for production)

**Frontend Build** (if deploying):
- [ ] `VITE_API_URL` set to Backend URL
- [ ] Build command includes this variable

### Post-Deployment Testing

- [ ] Backend health check passes: `GET /health` → `{"status": "healthy"}`
- [ ] Database connection works: Check logs for "Database initialized"
- [ ] Qdrant connection works: Check logs for "Qdrant initialized"
- [ ] MCP server reaches Backend: `GET /health` on MCP server passes
- [ ] CORS configured correctly: Frontend can call Backend

---

## Variable Dependencies

### Variable Chains (Set together)

**Database Setup**:
```
DATABASE_URL (Neon connection)
  ↓
Alembic migrations run at Backend startup
  ↓
All database tables created
```

**Vector Database Setup**:
```
QDRANT_URL + QDRANT_API_KEY (Qdrant Cloud)
  ↓
QDRANT_COLLECTION_NAME (must exist in Qdrant)
  ↓
Vectors stored and retrieved from collection
```

**MCP to Backend Communication**:
```
MCP: BACKEND_URL
  ↓
Backend: APP_HOST + APP_PORT (or PORT env var)
  ↓
MCP calls Backend on BACKEND_URL
```

**Frontend to Backend Communication**:
```
Frontend build: VITE_API_URL
  ↓
Frontend: apiClient.ts uses VITE_API_URL
  ↓
Backend: CORS_ORIGINS must include frontend domain
```

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Missing `QDRANT_API_KEY` | "Qdrant authentication failed" | Set API key from Qdrant Cloud |
| Wrong `DATABASE_URL` format | "could not translate host name" | Copy exact string from Neon dashboard |
| `QDRANT_COLLECTION_NAME` doesn't exist | "Collection not found" | Create collection in Qdrant Cloud first |
| `BACKEND_URL` wrong in MCP | "MCP health OK but /api/chat fails" | Verify exact URL of Backend service |
| `JWT_SECRET` too short | "Secret must be at least 32 chars" | Generate with secrets.token_hex(32) |
| Same `JWT_SECRET` local and prod | Security vulnerability | Generate different secret for each |
| `CORS_ORIGINS` using wildcard `*` | Security vulnerability | Specify exact domains only |
| `.env` committed to GitHub | Credentials leaked | Add `.env` to `.gitignore` immediately |

---

## Migration Examples

### From Local to Neon

```bash
# OLD (Local PostgreSQL)
DATABASE_URL=postgresql://rag_user:rag_password@localhost:5432/secure_rag

# NEW (Neon)
DATABASE_URL=postgresql://neondb_owner:xxxxx@ep-xxxxx.us-east-1.neon.tech/neondb?sslmode=require
```

### From Local Qdrant to Qdrant Cloud

```bash
# OLD (Local)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# NEW (Cloud)
QDRANT_URL=https://xxxxx-us-east1-0.qdrant.io:6333
QDRANT_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### From Local Backend to Render

```bash
# OLD (Local MCP)
BACKEND_URL=http://localhost:8000

# NEW (Render)
BACKEND_URL=https://my-backend-xxxxx.onrender.com
```

---

## Debugging Environment Variables

### Check if variable is set
```bash
# Local
echo $DATABASE_URL

# Render (SSH into dyno)
echo $DATABASE_URL
```

### List all environment variables
```bash
# Local .env file
cat .env

# Render dashboard: Settings → Environment Variables
```

### Update environment variable in Render
1. Go to Service Settings
2. Select "Environment" tab
3. Edit variable
4. Save (triggers redeploy)

---

## Summary Table

| Scenario | Variables to Set | Minimum Count |
|----------|------------------|---------------|
| Local Development | APP_ENV, DATABASE_URL, AZURE_OPENAI_*, JWT_SECRET | 6 |
| Cloud Backend (Render) | All Backend variables in table above | 15+ |
| Cloud MCP (Render) | All MCP variables in table above | 5+ |
| Cloud Frontend (Static) | VITE_API_URL (at build time) | 1 |
