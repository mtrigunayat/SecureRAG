# Phase 5: Cloud Deployment Preparation Guide

**Status**: Repository is deployment-ready for free-tier cloud services  
**Target Services**: Render + Neon + Qdrant Cloud + Azure OpenAI  
**Last Updated**: Phase 5 implementation complete  

> **IMPORTANT**: This guide prepares the repository for deployment. It does NOT perform actual deployment. You will:
> 1. Create cloud accounts manually
> 2. Deploy services manually
> 3. Configure environment variables manually
> 4. Verify deployments manually

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Configuration Reference](#configuration-reference)
4. [Deployment Order](#deployment-order)
5. [Environment Variables](#environment-variables)
6. [Troubleshooting](#troubleshooting)
7. [Security Checklist](#security-checklist)

---

## Architecture Overview

### Free-Tier Services

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude (MCP Client)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ MCP over HTTPS
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    MCP Server (Render)                          │
│                    - Python 3.11                                │
│                    - Streamable HTTP transport                  │
│                    - authenticate with Backend                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API (HTTPS)
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                  Backend (Render Web Service)                   │
│                  - FastAPI (Python 3.11)                        │
│                  - PostgreSQL (Neon)                            │
│                  - Qdrant (Qdrant Cloud)                        │
│                  - Azure OpenAI (LLM)                           │
└──────┬─────────────┬────────────────────┬──────────────────────┘
       │             │                    │
       ▼             ▼                    ▼
   ┌────────┐   ┌──────────┐        ┌──────────────┐
   │  Neon  │   │  Qdrant  │        │ Azure OpenAI │
   │   DB   │   │  Cloud   │        │ (LLM Engine) │
   └────────┘   └──────────┘        └──────────────┘
       │             │
       └─────┬───────┘
             │
   Embeddings: sentence-transformers/all-MiniLM-L6-v2
   (downloaded at backend startup)
```

### Key Deployment Decision: How They Work Together

- **Backend initiates** all external service connections at startup
- **MCP Server** is a thin HTTP client that calls the Backend's `/api/chat` endpoint
- **Database migrations** are applied during Backend startup
- **Qdrant indexing** happens when documents are ingested
- **Azure OpenAI** is called on-demand for LLM responses

---

## Prerequisites

Before deploying to the cloud, verify your local setup works:

```bash
# 1. Backend
cd backend
python -m pytest tests/ -v

# 2. MCP Server
cd mcp-server
python validate_phase3.py

# 3. Local integration
python validate_phase4.py
```

All tests must pass before proceeding to cloud deployment.

---

## Configuration Reference

### Backend Application (`backend/app/core/config.py`)

| Variable | Local | Cloud | Notes |
|----------|-------|-------|-------|
| `APP_ENV` | `development` | `production` | Controls logging, reload behavior |
| `APP_HOST` | `0.0.0.0` | `0.0.0.0` | Render sets this |
| `APP_PORT` | `8000` | Override via `PORT` | Render injects `PORT` env var |
| `DATABASE_URL` | `postgresql://rag_user:rag_password@localhost:5432/secure_rag` | `postgresql://user:password@host.neon.tech/dbname?sslmode=require` | **REQUIRED** for cloud |
| `QDRANT_URL` | `http://localhost:6333` | `https://xxxxx.qdrant.io:6333` | **REQUIRED** for cloud |
| `QDRANT_API_KEY` | (empty) | (Qdrant API key) | **REQUIRED** for Qdrant Cloud |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | `https://yourdomain.com,https://frontend.onrender.com` | Environment-driven parsing |
| `AZURE_OPENAI_API_KEY` | Set locally | Set in cloud | **REQUIRED** |
| `AZURE_OPENAI_ENDPOINT` | Set locally | Set in cloud | **REQUIRED** |
| `JWT_SECRET` | 32+ chars | 32+ chars (DIFFERENT!) | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |

### MCP Server Configuration (`mcp-server/src/mcp_server/core/config.py`)

| Variable | Local | Cloud | Notes |
|----------|-------|-------|-------|
| `MCP_HOST` | `0.0.0.0` | `0.0.0.0` | Render sets this |
| `MCP_PORT` | `5000` | Override via `PORT` | Render injects `PORT` env var |
| `BACKEND_URL` | `http://localhost:8000` | `https://my-backend.onrender.com` | **CRITICAL**: Must point to deployed Backend |
| `LOG_LEVEL` | `INFO` | `INFO` | Set to `DEBUG` only for troubleshooting |

### Frontend Configuration (`frontend/.env.example`)

| Variable | Local | Cloud | Notes |
|----------|-------|-------|-------|
| `VITE_API_URL` | `http://localhost:8000` | `https://my-backend.onrender.com` | Required for frontend builds |

---

## Deployment Order

### ✅ Step 1: Create Neon Account & Database

**Purpose**: Persistent PostgreSQL for production

**Steps**:
1. Create account at https://console.neon.tech
2. Create a new project (free-tier)
3. Create a database named `secure_rag`
4. Create a role with password
5. **Copy the connection string** (looks like: `postgresql://user:password@host.neon.tech/dbname?sslmode=require`)

**Environment Variable**:
```bash
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require
```

---

### ✅ Step 2: Create Qdrant Cloud Account & Instance

**Purpose**: Vector database for RAG

**Steps**:
1. Create account at https://cloud.qdrant.io
2. Create a new cluster (free-tier available)
3. Create a collection named `knowledge_chunks` with:
   - Vector size: **384** (for all-MiniLM-L6-v2)
   - Distance: **Cosine**
   - Quantization: Optional (but recommended for free tier)
4. **Copy the cluster URL** (looks like: `https://xxxxx-us-east1-0.qdrant.io:6333`)
5. **Copy the API key** (create in cluster settings)

**Environment Variables**:
```bash
QDRANT_URL=https://xxxxx-us-east1-0.qdrant.io:6333
QDRANT_API_KEY=your-api-key-here
QDRANT_COLLECTION_NAME=knowledge_chunks
```

---

### ✅ Step 3: Deploy Backend to Render

**Purpose**: FastAPI server with RAG pipeline

**Preparation**:
- [x] `backend/Dockerfile` configured for PORT env var
- [x] `backend/app/core/config.py` reads all cloud variables
- [x] `backend/app/main.py` uses environment-driven CORS
- [x] Qdrant service supports API key authentication
- [x] `.env.example` documents all variables

**Manual Steps**:
1. Push repository to GitHub (with `.gitignore` preventing `.env` upload)
2. Create Render account at https://render.com
3. Create new "Web Service"
4. Connect GitHub repository
5. Configure build settings:
   ```
   Runtime: Python 3.11
   Build command: pip install -r requirements.txt
   Start command: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
6. Set environment variables:
   ```
   DATABASE_URL=postgresql://...  (from Neon)
   QDRANT_URL=https://...          (from Qdrant Cloud)
   QDRANT_API_KEY=...              (from Qdrant Cloud)
   AZURE_OPENAI_API_KEY=...
   AZURE_OPENAI_ENDPOINT=...
   JWT_SECRET=...                  (NEW 32+ char value)
   CORS_ORIGINS=https://your-domain.com,https://frontend.onrender.com
   APP_ENV=production
   LOG_LEVEL=INFO
   ```
7. Deploy and wait for startup logs
8. **Test**: Visit `https://your-backend.onrender.com/health`
9. Expected response:
   ```json
   {
     "status": "healthy",
     "services": {
       "database": "ok",
       "vector_db": "ok"
     }
   }
   ```

**Database Migrations**:
- Automatic during Backend startup via `init_db()` in `app/main.py`
- For manual Alembic migration (if needed):
  ```bash
  cd backend
  alembic upgrade head
  ```

---

### ✅ Step 4: Deploy MCP Server to Render

**Purpose**: HTTP interface for Claude to query knowledge base

**Preparation**:
- [x] `mcp-server/Dockerfile` configured for PORT env var
- [x] `mcp-server/src/mcp_server/core/config.py` supports PORT override
- [x] `.env.example` documents all variables

**Manual Steps**:
1. Create new "Web Service" in Render
2. Connect to same GitHub repository
3. Configure build settings:
   ```
   Runtime: Python 3.11
   Root directory: mcp-server
   Build command: pip install -r requirements.txt
   Start command: python -m mcp_server.main
   ```
4. Set environment variables:
   ```
   BACKEND_URL=https://your-backend.onrender.com  (from Step 3)
   MCP_HOST=0.0.0.0
   MCP_PORT=5000
   LOG_LEVEL=INFO
   ```
5. Deploy and wait for startup logs
6. **Test**: Visit `https://your-mcp-server.onrender.com/health`
7. Expected response (simple health check):
   ```json
   {"status": "healthy"}
   ```

---

### ✅ Step 5: Deploy Frontend (Optional)

**Purpose**: Web UI for testing (not required for MCP usage)

**Preparation**:
- [x] `frontend/src/services/apiClient.ts` uses `VITE_API_URL`
- [x] `frontend/vite.config.ts` configured
- [x] `frontend/.env.example` documents variable

**Manual Steps** (if desired):
1. Create new "Static Site" in Render
2. Connect GitHub repository
3. Configure build settings:
   ```
   Build command: cd frontend && npm install && npm run build
   Publish directory: frontend/dist
   ```
4. Set build environment variable:
   ```
   VITE_API_URL=https://your-backend.onrender.com
   ```
5. Deploy

---

## Environment Variables

### Backend Variables (Complete Reference)

**Database & External Services**:
```bash
# REQUIRED (no default, must be set for cloud)
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require

# OPTIONAL (defaults shown, override for cloud)
QDRANT_URL=https://xxxxx.qdrant.io:6333
QDRANT_API_KEY=your-api-key  # REQUIRED for Qdrant Cloud
QDRANT_COLLECTION_NAME=knowledge_chunks
```

**Azure OpenAI**:
```bash
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

**Authentication & Security**:
```bash
JWT_SECRET=your-32-char-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=1
MCP_TOKEN_EXPIRATION_DAYS=365
```

**CORS & Origins**:
```bash
CORS_ORIGINS=https://yourdomain.com,https://frontend.onrender.com
```

**Application**:
```bash
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000  # Overridden by PORT env var
LOG_LEVEL=INFO
```

---

### MCP Server Variables

```bash
# Backend communication
BACKEND_URL=https://your-backend.onrender.com
BACKEND_API_TIMEOUT=30

# Server
MCP_HOST=0.0.0.0
MCP_PORT=5000  # Overridden by PORT env var

# Logging
LOG_LEVEL=INFO
```

---

### Frontend Variables

```bash
VITE_API_URL=https://your-backend.onrender.com
```

---

## Troubleshooting

### Backend Health Check Fails

**Symptoms**: `GET /health` returns error or unreachable

**Diagnostics**:
```bash
# Check backend logs in Render dashboard
# Look for startup errors in:
# 1. Database connection errors
# 2. Qdrant connection errors
# 3. Missing environment variables
```

**Common Issues**:

| Error | Cause | Fix |
|-------|-------|-----|
| `could not translate host name "host.neon.tech"` | Invalid DATABASE_URL | Verify exact string from Neon dashboard |
| `ConnectionError to Qdrant` | Invalid QDRANT_URL or API key | Verify Qdrant Cloud credentials |
| `No module named 'azure'` | Missing Azure OpenAI package | Check requirements.txt updated |
| `jwt_secret is required` | JWT_SECRET not set | Generate and set environment variable |

---

### MCP Server Cannot Reach Backend

**Symptoms**: MCP health check passes, but `/api/chat` fails

**Diagnostics**:
```bash
# Verify BACKEND_URL is correct
echo $BACKEND_URL
# Should be: https://your-backend.onrender.com

# Check Backend accessibility
curl https://your-backend.onrender.com/health
```

**Common Issues**:

| Error | Cause | Fix |
|-------|-------|-----|
| `Connection refused` | Backend not running | Check Backend deployment status in Render |
| `404 Not Found on /api/chat` | Incorrect Backend URL | Verify BACKEND_URL matches Backend's URL |
| `Connection timeout` | Cold start or overloaded | Render may be starting service, wait 30s |

---

### Database Migrations Fail

**Symptoms**: Backend startup logs show migration errors

**Solution**:
1. Check Neon dashboard for database connectivity
2. Verify `DATABASE_URL` includes `?sslmode=require`
3. If needed, manually run in Backend container:
   ```bash
   cd backend
   alembic upgrade head
   ```

---

### Qdrant Collection Not Found

**Symptoms**: Backend startup shows "Collection not found"

**Solution**:
1. Create collection in Qdrant Cloud Dashboard:
   - Name: `knowledge_chunks`
   - Vector Size: `384`
   - Distance: `Cosine`
2. Verify `QDRANT_URL` and `QDRANT_API_KEY` in environment variables
3. Check Backend logs for API key authentication errors

---

## Security Checklist

Before marking deployment as complete:

### ✅ Environment Variables

- [ ] `JWT_SECRET` is 32+ characters and generated (not default)
- [ ] `QDRANT_API_KEY` is set and strong
- [ ] `AZURE_OPENAI_API_KEY` is set and valid
- [ ] `.env` file is in `.gitignore` (NOT committed to GitHub)
- [ ] `.env.example` is committed (no secrets, only templates)
- [ ] `DATABASE_URL` uses `sslmode=require` for Neon

### ✅ CORS Configuration

- [ ] `CORS_ORIGINS` restricted to known domains
- [ ] No `*` (wildcard) in production
- [ ] Frontend domain registered in `CORS_ORIGINS`

### ✅ Logging

- [ ] `LOG_LEVEL=INFO` in production (not DEBUG)
- [ ] No credentials ever logged in application code
- [ ] Render audit logs enabled for API access

### ✅ Azure OpenAI

- [ ] API key is for correct Azure subscription
- [ ] Deployment name matches deployed model
- [ ] API version is recent (2024-12-01-preview or later)

### ✅ Database

- [ ] Neon backup enabled (automatic with free tier)
- [ ] Database user password is strong (random)
- [ ] No connection string in application code

### ✅ Render Configuration

- [ ] Auto-deploy on main branch enabled (recommended)
- [ ] Build command does NOT include secrets
- [ ] Start command does NOT include hardcoded values
- [ ] Environment variables NOT in Dockerfile CMD

---

## Next Steps

Once deployment is complete:

1. **Test MCP Integration**: Use `mcp-server/docs/PHASE_4_VALIDATION.md` to test cloud deployment
2. **Ingest Documents**: Upload documents to backend for indexing in Qdrant Cloud
3. **Test RAG Pipeline**: Verify Claude can query knowledge base through MCP
4. **Monitor Resources**: Watch Render CPU/memory and Neon usage (free tier limits)
5. **Scale if Needed**: Upgrade services if hitting free-tier limits

---

## Free-Tier Limitations

Be aware of these constraints:

| Service | Free Tier Limit | Impact | Mitigation |
|---------|-----------------|--------|-----------|
| **Render** | 0.5 CPU, 512MB RAM | Slow cold starts | Pre-warm by periodic pings |
| **Neon** | 1 project, 256MB storage | Small dataset only | Monitor row counts |
| **Qdrant Cloud** | 1GB vectors + metadata | ~2-3M documents (384-dim) | Use quantization or chunking |
| **Azure OpenAI** | Rate limits per tier | Throttling possible | Implement retry logic |

---

## Files Modified in Phase 5

### Configuration Files
- ✅ `backend/app/core/config.py` - Added CORS and Qdrant API key support
- ✅ `backend/app/main.py` - Made CORS environment-driven
- ✅ `mcp-server/src/mcp_server/core/config.py` - Enhanced documentation, PORT override
- ✅ `.env.example` - Comprehensive variable documentation

### Docker Files
- ✅ `backend/Dockerfile` - PORT environment variable support
- ✅ `mcp-server/Dockerfile` - PORT environment variable support

### Services
- ✅ `backend/app/services/qdrant_service.py` - API key authentication support

### Documentation
- ✅ Created `docs/PHASE_5_DEPLOYMENT_GUIDE.md` (this file)

---

## Summary

Your repository is now **deployment-ready**. All components are configured to work with:

✅ Render Web Services (Backend + MCP)  
✅ Neon PostgreSQL (Cloud Database)  
✅ Qdrant Cloud (Vector Database)  
✅ Azure OpenAI (LLM Service)  
✅ Environment-driven configuration  
✅ Security-first practices  

**You are responsible for**:
1. Creating cloud accounts
2. Setting environment variables
3. Performing deployments
4. Verifying services
5. Monitoring costs (especially free-tier limits)

All code and configuration changes are complete and ready for your manual deployment.
