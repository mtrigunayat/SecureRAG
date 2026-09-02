# MCP Design Phase Summary

**Date**: 2026-09-02  
**Status**: ✅ Phase 1 Design Complete - Ready for Stakeholder Review

---

## Overview

This folder contains the complete architecture and design for integrating a remote MCP (Model Context Protocol) server with the existing Secure RAG Knowledge Assistant backend. 

**Key Point**: This is **design only**. No code has been implemented, no files modified, no databases changed.

---

## What's Included

### Primary Design Document
- **[PHASE_1_ARCHITECTURE_DESIGN.md](./PHASE_1_ARCHITECTURE_DESIGN.md)**
  - 13-step comprehensive architecture design
  - Authentication flow analysis and recommendation
  - Token model design with full specification
  - MCP tool definitions and behaviors
  - Error handling strategy
  - Security threat model (11 categories)
  - Deployment architecture
  - Final recommendations and implementation roadmap
  - **Size**: ~15,000 words, all sections detailed with diagrams

---

## Key Design Decisions

### 1. Authentication Architecture ✅
**Chosen**: Option A - MCP Token → User → Backend JWT
- User gets opaque MCP token (per-user, long-lived)
- MCP token maps to user identity in database
- MCP server obtains backend JWT for that user
- Backend validates JWT (existing flow)
- Backend loads user + department (trusted source)

**Security**: Prevents user impersonation and department spoofing attacks

### 2. MCP Tool Set ✅
**Chosen**: Single primary tool - `ask_knowledge_base`
- Claude calls with question
- MCP returns answer + trusted sources
- High-level, business-focused
- No implementation detail exposure

**Rationale**: Simplicity for MVP, sufficient for business requirement

### 3. Deployment Model ✅
**Chosen**: Separate, independently-scalable service
- MCP server: Public HTTPS (remote)
- Backend: Private/internal only
- Full network isolation
- Stateless MCP (scale horizontally)

### 4. Backend Changes ✅
**Chosen**: Minimal - Add only `mcp_tokens` table
- No existing backend code modifications
- Preserves security boundaries
- Existing endpoints reused as-is

---

## Architecture at a Glance

```
Claude
  ↓ HTTPS + MCP
MCP Server (ask_knowledge_base tool)
  ↓ HTTP + Backend JWT
FastAPI Backend (existing)
  ↓ ACL filtering + RAG
PostgreSQL + Qdrant + Azure OpenAI
```

**Authentication Flow**:
1. Claude connects with MCP token
2. MCP validates token → user_id
3. MCP obtains backend JWT for user
4. MCP calls backend with JWT
5. Backend validates JWT → loads user → applies ACL
6. Backend returns authorized results
7. MCP returns to Claude

---

## Security Model

### Threat Prevention
- ✅ User impersonation: MPC token → user_id binding (cryptographic)
- ✅ Department spoofing: Department loaded from database (not request)
- ✅ ACL bypass: Qdrant filter applied server-side (not post-retrieval)
- ✅ Token theft: Tokens are opaque, hashed at rest, support revocation
- ✅ MCP compromise: Backend JWT still required, ACL enforced at backend layer

### Defense in Depth
1. MCP validates token
2. Backend validates JWT
3. Backend applies ACL at Qdrant layer
4. System prompt backend-controlled
5. Sources backend-controlled

---

## MCP Token Model

**Format**: `mcp_user_<random_base64>_<timestamp>`
- Example: `mcp_user_xK9vL2mQ8pR5sTu_1725226800`

**Storage**: SHA256 hash in PostgreSQL `mcp_tokens` table
- Supports: Expiration, revocation, audit trail
- No stored passwords/sensitive data
- One-way hash (cannot forge without database)

**Lifecycle**:
```
Create (admin) → Active (Claude uses) → Expire/Revoke (end)
```

---

## What Stays Untouched

✅ Backend authentication, authorization, RAG pipeline
✅ Database models (User, Department, Document)
✅ API endpoints (/api/auth/login, /api/chat, /api/retrieval)
✅ Frontend (no changes)
✅ Qdrant vector database (no changes)
✅ LLM integration (no changes)

---

## What Will Be Added

📝 New in backend:
- `mcp_tokens` table (PostgreSQL)
- Alembic migration
- MCP token admin feature (CLI or endpoint)
- Optional: `/api/internal/mcp-token-to-jwt` endpoint

📝 New service:
- `mcp-server/` directory (separate service)
- MCP tool handlers
- Token validation service
- Backend API client
- Dockerfile, tests, documentation

---

## Implementation Roadmap

**Phase 2**: Backend Infrastructure
- Add `mcp_tokens` table
- Implement token admin feature

**Phase 3**: MCP Server Core
- Token validation service
- JWT manager
- Backend API client
- Unit tests

**Phase 4**: MCP Tools
- `ask_knowledge_base` tool implementation
- Integration tests

**Phase 5**: Deployment & Testing
- Docker, health checks
- End-to-end testing

**Phase 6**: Production Deployment
- HTTPS setup
- Monitoring, auto-scaling

**Phase 7+**: Expansion
- Additional tools (retrieve, search)
- Enhanced analytics

---

## Design Validation

### Security ✅
- Threat model covers 11 categories
- No single point of failure (defense in depth)
- Existing security principles preserved
- Token model suitable for production

### Scalability ✅
- Stateless MCP server (horizontal scaling)
- Independent from backend scaling
- Database-backed token lookup (no shared state)

### Compatibility ✅
- No existing backend code changes
- Uses existing API endpoints
- JWT-based auth (proven pattern)
- Backward compatible

### Auditability ✅
- All MCP token usage logged
- Correlation via user_id
- Backend logs unchanged
- Compliance-friendly design

---

## Open Questions for Stakeholders

1. **JWT Obtention Method** (Phase 2):
   - Option A: MCP calls new backend endpoint (requires shared secret or cert auth)
   - Option B: Pre-generate JWTs when MCP token created (separate backend process)
   - Recommendation: Option B (simpler, no new endpoint)

2. **MCP Token Expiration**:
   - Default: 1 year (long-lived)
   - Consider: Should it be shorter? (e.g., 90 days for rotation)
   - Recommendation: Start with 1 year, monitor usage

3. **MCP Admin Interface**:
   - Option A: CLI tool
   - Option B: Admin web portal
   - Option C: REST API endpoint
   - Recommendation: Start with CLI (simpler for POC)

4. **Additional Tools** (Phase 2+):
   - Should we add retrieve_documents? search_documents?
   - Recommendation: Wait for user feedback, add in Phase 2+

5. **Hosting Provider** (Phase 6):
   - AWS? Google Cloud? On-premises? Anthropic platform?
   - Recommendation: Decision deferred, architecture supports any

---

## How to Use This Design

1. **Review**: Read PHASE_1_ARCHITECTURE_DESIGN.md (sections you care about)
2. **Validate**: Check security, scalability, implementation plans
3. **Approve**: Stakeholders approve design
4. **Proceed**: Move to Phase 2 implementation

**For Developers**: Design provides clear implementation targets and security boundaries

**For Ops**: Design provides deployment model and scaling strategy

**For Security**: Design provides threat model and mitigation strategies

---

## Related Documents

**Previous Phase**:
- `../PHASE_0_AUDIT.md` - Backend audit (security, architecture, risks)

**Next Phases** (to be created during implementation):
- `PHASE_2_IMPLEMENTATION.md` - Backend infrastructure work
- `PHASE_3_IMPLEMENTATION.md` - MCP server core
- `PHASE_4_IMPLEMENTATION.md` - MCP tools
- `PHASE_5_DEPLOYMENT.md` - Testing and deployment
- `PHASE_6_PRODUCTION.md` - Production rollout

---

## Quick Reference: Architecture Diagram

```
Claude
  │ HTTPS + MCP Token
  │
  ▼
┌──────────────────┐
│  MCP Server      │
│ (ask_knowledge   │
│  _base tool)     │
└────────┬─────────┘
         │ HTTP + Backend JWT
         │
         ▼
┌──────────────────────────┐
│  FastAPI Backend         │
│  (existing, unchanged)   │
│  ├─ /api/chat           │
│  ├─ /api/retrieval      │
│  └─ /api/auth/*         │
└────────┬─────────────────┘
         │
    ┌────┼────┐
    ▼    ▼    ▼
   PG   QD   AZURE
   (auth) (retrieval) (LLM)
```

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Document size | ~15,000 words |
| Sections covered | 13 (all comprehensive) |
| Security threats analyzed | 11 categories |
| Design options evaluated | 4 architectures |
| Components unchanged | 10+ |
| New components | 3 (mcp-server/, mcp_tokens table, admin feature) |
| Estimated Phase 2-6 effort | 3-4 weeks (developer dependent) |

---

## Status

✅ **Design Phase Complete**
- All 13 steps completed with detailed analysis
- Recommendations provided for all major decisions
- Security model validated
- Ready for implementation
- Awaiting stakeholder approval

🔄 **Next**: Stakeholder review and approval

---

## Questions?

Refer to the detailed sections in PHASE_1_ARCHITECTURE_DESIGN.md for:
- Section 3: Authentication architecture options
- Section 4: Token model details
- Section 11: Security threat model
- Section 13: Final recommendations
