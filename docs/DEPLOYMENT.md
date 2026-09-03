# Deployment Guide - Phase 3 Ready

## Production Deployment to Render

### 1. Backend Deployment (FastAPI)

**Create render.yaml for backend:**
```yaml
services:
  - type: web
    name: securerag-backend
    runtime: python
    pythonVersion: 3.11
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        value: postgresql://user:password@host/securerag
      - key: QDRANT_URL
        value: http://qdrant:6333
      - key: ENVIRONMENT
        value: production
      - key: LOG_LEVEL
        value: INFO
    disk:
      name: securerag-data
      mountPath: /data
      sizeGB: 10
```

### 2. MCP Server Deployment (Python HTTP)

**Create render.yaml for mcp-server:**
```yaml
services:
  - type: web
    name: securerag-mcp
    runtime: python
    pythonVersion: 3.11
    buildCommand: pip install -r requirements.txt
    startCommand: python -m mcp_server.main
    envVars:
      - key: MCP_HOST
        value: 0.0.0.0
      - key: MCP_PORT
        value: "5000"
      - key: BACKEND_URL
        value: https://securerag-backend.onrender.com
      - key: ENVIRONMENT
        value: production
      - key: LOG_LEVEL
        value: INFO
```

### 3. Environment Variables (Render Dashboard)

Set these in your Render project settings:

**Backend Service:**
- `DATABASE_URL`: PostgreSQL connection string
- `QDRANT_URL`: Qdrant vector DB URL
- `SECRET_KEY`: JWT signing key
- `ENVIRONMENT`: production

**MCP Server:**
- `BACKEND_URL`: Production backend URL
- `MCP_PUBLIC_URL`: Public MCP server URL

### 4. Database Setup

Run migrations on production:
```bash
# After backend deployment
render shell --service securerag-backend
cd /app
alembic upgrade head
python -m app.db.seed  # Seed initial data
```

### 5. Deployment Steps

```bash
# 1. Ensure all code is committed
git status
git add .
git commit -m "Phase 3: Complete MCP integration with Claude connectivity"

# 2. Push to Render (if configured)
git push render main

# 3. Monitor deployment
# - Visit Render dashboard
# - Check backend logs
# - Check MCP server logs
```

### 6. Post-Deployment Verification

```bash
# Test health endpoints
curl https://securerag-backend.onrender.com/health
curl https://securerag-mcp.onrender.com/health

# Test MCP initialization
curl -X POST https://securerag-mcp.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"claude","version":"1.0"}}}'

# Test with token
curl -X POST https://securerag-mcp.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

## Local vs Production URLs

| Service | Local | Production |
|---------|-------|------------|
| Backend | http://localhost:8000 | https://securerag-backend.onrender.com |
| MCP Server | http://localhost:5001 | https://securerag-mcp.onrender.com |
| Database | localhost:5432 | Render Postgres |

## Monitoring & Logs

```bash
# Backend logs
# Render Dashboard → securerag-backend → Logs

# MCP Server logs
# Render Dashboard → securerag-mcp → Logs

# Database logs
# Render Dashboard → PostgreSQL → Logs
```

## Troubleshooting Deployment

**Issue: Service won't start**
- Check requirements.txt is complete
- Verify environment variables are set
- Check build command is correct

**Issue: Database connection fails**
- Verify DATABASE_URL format
- Check network access rules
- Ensure migrations ran

**Issue: MCP server can't reach backend**
- Verify BACKEND_URL is correct
- Check network policies allow outbound
- Review CORS settings if needed

---
For more details, see `PHASE_3_CLAUDE_INTEGRATION.md`
