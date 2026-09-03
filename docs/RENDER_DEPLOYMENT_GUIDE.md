# Render.yaml Configuration Template

This file is a reference for deploying to Render. You can use `render.yaml` for infrastructure-as-code deployment, or manually configure services in the Render dashboard.

---

## Option 1: Using render.yaml (Recommended)

### Step 1: Create render.yaml in Repository Root

Create a file named `render.yaml` in the root of your repository:

```yaml
services:
  # PostgreSQL Database (Not configured here - use Neon instead)
  # Render charges for PostgreSQL, so we use Neon free tier

  # Backend Service
  - type: web
    name: secure-rag-backend
    runtime: python
    pythonVersion: 3.11
    
    buildCommand: |
      pip install --upgrade pip
      cd backend
      pip install -r requirements.txt
    
    startCommand: |
      cd backend
      uvicorn app.main:app --host 0.0.0.0 --port $PORT
    
    envVars:
      # Application
      - key: APP_ENV
        value: production
      - key: APP_HOST
        value: 0.0.0.0
      - key: LOG_LEVEL
        value: INFO
      
      # Database (from Neon)
      - key: DATABASE_URL
        sync: false  # Set this manually from Neon
      
      # Vector Database (from Qdrant Cloud)
      - key: QDRANT_URL
        sync: false  # Set this manually from Qdrant Cloud
      - key: QDRANT_API_KEY
        sync: false  # Set this manually from Qdrant Cloud
      - key: QDRANT_COLLECTION_NAME
        value: knowledge_chunks
      
      # Azure OpenAI
      - key: AZURE_OPENAI_API_KEY
        sync: false  # Set manually
      - key: AZURE_OPENAI_ENDPOINT
        sync: false  # Set manually
      - key: AZURE_OPENAI_DEPLOYMENT
        value: gpt-4.1-mini
      - key: AZURE_OPENAI_API_VERSION
        value: 2024-12-01-preview
      
      # Security
      - key: JWT_SECRET
        sync: false  # Generate and set manually
      - key: JWT_ALGORITHM
        value: HS256
      - key: JWT_EXPIRATION_HOURS
        value: "1"
      - key: MCP_TOKEN_EXPIRATION_DAYS
        value: "365"
      
      # CORS
      - key: CORS_ORIGINS
        sync: false  # Set to your frontend domains
    
    disk:
      name: backend_storage
      mountPath: /app
      sizeGB: 1
    
    healthCheckPath: /health
    healthCheckTimeout: 30
    
    autoDeploy: true

  # MCP Server Service
  - type: web
    name: secure-rag-mcp
    runtime: python
    pythonVersion: 3.11
    
    buildCommand: |
      pip install --upgrade pip
      cd mcp-server
      pip install -r requirements.txt
    
    startCommand: |
      cd mcp-server
      python -m mcp_server.main
    
    envVars:
      # MCP Server
      - key: MCP_HOST
        value: 0.0.0.0
      - key: LOG_LEVEL
        value: INFO
      
      # Backend Communication
      - key: BACKEND_URL
        sync: false  # Set to Backend service URL
      - key: BACKEND_API_TIMEOUT
        value: "30"
    
    disk:
      name: mcp_storage
      mountPath: /app
      sizeGB: 1
    
    healthCheckPath: /health
    healthCheckTimeout: 30
    
    autoDeploy: true
    
    depends_on:
      - secure-rag-backend

  # Frontend Service (Optional)
  - type: static
    name: secure-rag-frontend
    staticPublishPath: ./dist
    
    buildCommand: |
      cd frontend
      npm install
      VITE_API_URL=$VITE_API_URL npm run build
    
    envVars:
      - key: VITE_API_URL
        sync: false  # Set to Backend service URL
    
    autoDeploy: true
```

### Step 2: Deploy with render.yaml

```bash
# Commit render.yaml
git add render.yaml
git commit -m "Add Render deployment configuration"
git push

# In Render dashboard:
# 1. Click "New" → "Blueprint"
# 2. Connect GitHub repository
# 3. Select branch (main)
# 4. Render will read render.yaml and create services
# 5. Configure manual environment variables as needed
```

---

## Option 2: Manual Configuration (Dashboard)

If you prefer to configure services manually:

### Backend Service Configuration

**Basic Settings**:
- Name: `secure-rag-backend`
- Environment: `Python 3`
- Build Command:
  ```
  cd backend && pip install -r requirements.txt
  ```
- Start Command:
  ```
  cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

**Environment Variables** (in Render Dashboard Settings):

| Key | Value | Source |
|-----|-------|--------|
| APP_ENV | production | Static |
| DATABASE_URL | postgresql://... | From Neon |
| QDRANT_URL | https://... | From Qdrant Cloud |
| QDRANT_API_KEY | xxxx | From Qdrant Cloud |
| AZURE_OPENAI_API_KEY | xxxx | From Azure Portal |
| AZURE_OPENAI_ENDPOINT | https://... | From Azure Portal |
| JWT_SECRET | (generated 32+ chars) | Generate new value |
| CORS_ORIGINS | https://yourdomain.com | Your frontend URL |
| LOG_LEVEL | INFO | Static |

### MCP Server Configuration

**Basic Settings**:
- Name: `secure-rag-mcp`
- Environment: `Python 3`
- Root Directory: `mcp-server`
- Build Command:
  ```
  pip install -r requirements.txt
  ```
- Start Command:
  ```
  python -m mcp_server.main
  ```

**Environment Variables**:

| Key | Value | Source |
|-----|-------|--------|
| BACKEND_URL | https://secure-rag-backend.onrender.com | Backend service URL |
| LOG_LEVEL | INFO | Static |

### Frontend Service (Optional)

**Basic Settings**:
- Name: `secure-rag-frontend`
- Environment: `Static Site`
- Build Command:
  ```
  cd frontend && npm install && VITE_API_URL=$VITE_API_URL npm run build
  ```
- Publish Directory: `frontend/dist`

**Environment Variables**:

| Key | Value | Source |
|-----|-------|--------|
| VITE_API_URL | https://secure-rag-backend.onrender.com | Backend service URL |

---

## Health Check Configuration

All services should have health checks enabled:

### Backend Health Check
```
Path: /health
Timeout: 30 seconds
Check Interval: 10 seconds
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "database": "ok",
    "vector_db": "ok"
  }
}
```

### MCP Health Check
```
Path: /health
Timeout: 30 seconds
Check Interval: 10 seconds
```

Expected response:
```json
{"status": "healthy"}
```

---

## Deployment Procedure (Manual)

### Step 1: Prepare Repository

```bash
# Ensure all changes are committed
git add .
git commit -m "Phase 5: Cloud deployment preparation"
git push origin main
```

### Step 2: Create Render Account

1. Go to https://render.com
2. Sign up with GitHub
3. Grant repository access

### Step 3: Create Database Service

1. In Render Dashboard → New+ → Web Service
2. Connect GitHub → Select `SecureRAG` repository
3. Choose `main` branch
4. Set up **Backend** service (see configuration above)
5. Deploy

**Wait for startup** (2-5 minutes)

### Step 4: Verify Backend Deployment

```bash
# Test health endpoint
curl https://your-backend-xxxxx.onrender.com/health

# Expected response
{
  "status": "healthy",
  "services": {
    "database": "ok",
    "vector_db": "ok"
  }
}
```

### Step 5: Deploy MCP Service

1. In Render Dashboard → New+ → Web Service
2. Connect GitHub → Select `SecureRAG` repository
3. Set up **MCP** service (see configuration above)
4. **Importantly**: Set `BACKEND_URL` to the Backend service URL from Step 4
5. Deploy

**Wait for startup** (2-5 minutes)

### Step 6: Verify MCP Deployment

```bash
# Test MCP health
curl https://your-mcp-xxxxx.onrender.com/health

# Expected response
{"status": "healthy"}
```

### Step 7: Deploy Frontend (Optional)

1. In Render Dashboard → New+ → Static Site
2. Connect GitHub → Select `SecureRAG` repository
3. Set up **Frontend** service (see configuration above)
4. Deploy

---

## Environment Variable Setup Checklist

### Before Deploying Backend

- [ ] Neon database created and connection string copied
- [ ] Qdrant Cloud instance created with API key
- [ ] Qdrant collection created (name: `knowledge_chunks`, vectors: 384)
- [ ] Azure OpenAI credentials obtained
- [ ] JWT_SECRET generated (32+ characters)
- [ ] CORS_ORIGINS list prepared

### Before Deploying MCP

- [ ] Backend service deployed and healthy
- [ ] Backend service URL copied
- [ ] BACKEND_URL environment variable configured

---

## Service Dependencies

```
MCP Server
    ↓ depends on
Backend Service
    ↓ depends on
Neon Database + Qdrant Cloud + Azure OpenAI
```

**Deploy in this order**:
1. Neon database (no deployment, just setup)
2. Qdrant Cloud (no deployment, just setup)
3. Backend service
4. MCP service (after Backend is healthy)
5. Frontend service (optional, after Backend exists)

---

## Auto-Deploy Configuration

For automatic deployments on git push:

1. In each service's Settings:
2. Find "Auto-Deploy" section
3. Enable "Auto-deploy new push"
4. Select branch (main)

Now, every push to main automatically triggers deployment.

---

## Monitoring & Logs

### View Backend Logs

1. Render Dashboard → Backend Service
2. Click "Logs" tab
3. Watch for startup messages:
   ```
   Database initialized
   Qdrant initialized
   Application startup complete
   ```

### View MCP Logs

1. Render Dashboard → MCP Service
2. Click "Logs" tab
3. Watch for:
   ```
   MCP Server Starting
   Backend: https://...
   ```

### Common Startup Issues

| Log Message | Problem | Fix |
|-------------|---------|-----|
| `could not translate host name` | DATABASE_URL wrong | Copy exact string from Neon |
| `ConnectionError` to Qdrant | QDRANT_API_KEY wrong | Verify in Qdrant Cloud |
| `ModuleNotFoundError: azure` | requirements.txt missing package | Ensure `azure-ai-openai` in requirements |
| `Timeout connecting to backend` | BACKEND_URL wrong in MCP | Use exact Backend service URL |

---

## Scaling & Resource Limits

### Free-Tier Limits (Render)

- **Memory**: 512MB
- **CPU**: 0.5 vCPU
- **Storage**: 1GB
- **Connections**: 100
- **Builds**: 750 free minutes/month

### Monitoring Usage

1. Render Dashboard → Account Settings → Usage
2. Watch for:
   - CPU percentage
   - Memory percentage
   - Build minutes
   - Free tier status

If limits approached, upgrade to paid plan.

---

## Disaster Recovery

### Backup Strategy

**Database**:
- Neon automatic backups (every 24 hours, retained 7 days free)
- Manual backup: Export from Neon dashboard if needed

**Vector DB**:
- Qdrant Cloud automatic backups (retention policy configurable)
- Manual backup: Export collection snapshot if needed

### Restore Procedure

1. Create new Neon database
2. Import backup/schema
3. Create new Qdrant instance
4. Re-upload vectors (consider running ingestion pipeline)
5. Update Backend environment variables
6. Redeploy Backend and MCP services

---

## Summary

This template provides:
- ✅ Complete render.yaml for infrastructure-as-code deployment
- ✅ Manual configuration guide for dashboard setup
- ✅ Health check configuration
- ✅ Environment variable mapping
- ✅ Deployment order and procedures
- ✅ Monitoring and troubleshooting guide

Choose either `render.yaml` (recommended) or manual dashboard configuration, but not both.
