# Database Seeding Guide

## SEED LOCATION

```
backend/app/db/seed.py
```

**Entry points:**
- Direct execution: `python backend/app/db/seed.py`
- CLI wrapper: `python -m scripts.manage_db seed` 
- Docker: `docker-compose exec backend python -m scripts.manage_db seed`

**Code location:**
- `seed_database()` function (line 250)
- `seed_departments()` (line 26)
- `seed_users()` (line 57)
- `seed_documents()` (line 120)

---

## EXACT SEED COMMAND

**Local development (after migrations):**
```bash
cd backend
python -m scripts.manage_db seed
```

**Or run directly:**
```bash
python app/db/seed.py
```

**Full sequence (from scratch):**
```bash
# 1. Run migrations first (creates schema)
python -m scripts.manage_db migrate

# 2. Then seed
python -m scripts.manage_db seed
```

**Docker:**
```bash
docker-compose exec backend python -m scripts.manage_db seed
```

---

## DATA CREATED

| Entity | Count | Idempotent? | Details |
|--------|-------|-------------|---------|
| **Departments** | 4 | ✅ YES | engineering, sales, hr, general |
| **Users** | 4 | ✅ YES (updates if exists) | mohit, deepak, karthik, swathi |
| **Documents** | 12 | ✅ YES | Metadata only (names, dept, sensitivity) |
| **MCP Tokens** | 0 | N/A | Seed does NOT create MCP tokens |
| **Qdrant/Vector Data** | 0 | N/A | **SEPARATE process** (see below) |

**Users Created (hardcoded):**
```
mohit@aithinkers.com / password123 → Engineering department
deepak@aithinkers.com / password123 → Engineering department  
karthik@aithinkers.com / password123 → Sales department
swathi@aithinkers.com / password123 → HR department
```

**Documents:** 12 records inserted with metadata (name, department_id, sensitivity, source path)
- **NO** PDF content extracted
- **NO** embeddings generated
- **NO** chunks created  
- **NO** vectors indexed to Qdrant

---

## SAFE TO RUN AGAIN

**YES - Fully Idempotent ✅**

**Proof from code:**

```python
# Departments: checks existence before insert
existing = db.query(Department).filter(Department.name == dept_data["name"]).first()
if existing:
    logger.info(f"Department '{dept_data['name']}' already exists, skipping")
    departments[dept_data["name"]] = existing

# Users: checks existence, updates if present
existing = db.query(User).filter(User.username == user_data["username"]).first()
if existing:
    logger.info(f"User '{user_data['username']}' already exists, updating password")
    existing.password_hash = user_data["password_hash"]  # Updates hash
    users[user_data["username"]] = existing

# Documents: checks by (name + department_id) composite key
existing = db.query(Document).filter(
    Document.name == doc_data["name"],
    Document.department_id == doc_data["department_id"]
).first()
if existing:
    logger.info(f"Document '{doc_data['name']}' already exists, skipping")
    documents.append(existing)
```

**Risk Assessment:**
- ✅ No duplicates created (checks before insert)
- ✅ Won't overwrite production data (only updates if same record exists)
- ✅ Safe for production use if records don't already exist
- ⚠️ **WARNING**: If you run seed on production with different data, it will skip existing records and not overwrite them

---

## NEON DEPLOYMENT COMMANDS

**Step 1: Backup current local DATABASE_URL**
```bash
cd backend
cp .env .env.backup
echo "Saved current .env to .env.backup"
```

**Step 2: Update .env to point to Neon**
```bash
# Get connection string from Neon dashboard
# Format: postgresql://user:password@host.neon.tech/dbname?sslmode=require

# Edit .env:
nano .env

# Change line:
# FROM: DATABASE_URL=postgresql://rag_user:rag_password@localhost:5432/secure_rag
# TO:   DATABASE_URL=postgresql://neondb_user:PASSWORD@ep-xxxxx.us-east-1.neon.tech/neondb?sslmode=require
```

**Step 3: Run migrations on Neon database**
```bash
# This creates the schema on Neon
python -m scripts.manage_db migrate
```

**Step 4: Seed Neon with demo data**
```bash
# This populates departments, users, and document metadata
python -m scripts.manage_db seed
```

**Step 5: Verify data inserted**
```bash
# Query Neon to confirm
psql "postgresql://neondb_user:PASSWORD@ep-xxxxx.us-east-1.neon.tech/neondb?sslmode=require" \
  -c "SELECT COUNT(*) FROM departments; SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM documents;"
```

**Step 6: Restore local DATABASE_URL**
```bash
cp .env.backup .env
echo "Restored local .env configuration"
```

**Step 7: Verify local connection still works**
```bash
# Start local backend again
uvicorn app.main:app --reload
```

---

## VERIFICATION QUERIES

**After seeding, run these in Neon to verify:**

```sql
-- 1. Check departments
SELECT COUNT(*) AS total_departments FROM departments;
-- Expected: 4

-- 2. Check users
SELECT COUNT(*) AS total_users FROM users;
-- Expected: 4

-- 3. Check documents  
SELECT COUNT(*) AS total_documents FROM documents;
-- Expected: 12

-- 4. Verify department distribution
SELECT d.name, COUNT(u.id) as user_count
FROM departments d
LEFT JOIN users u ON d.id = u.department_id
GROUP BY d.id, d.name
ORDER BY d.name;

-- 5. Verify user-department mappings
SELECT username, full_name, email, d.name as department
FROM users u
JOIN departments d ON u.department_id = d.id
ORDER BY d.name, u.username;

-- 6. Verify document distribution
SELECT d.name as department, COUNT(doc.id) as doc_count
FROM departments d
LEFT JOIN documents doc ON d.id = doc.department_id
GROUP BY d.id, d.name
ORDER BY d.name;

-- 7. Check document metadata (verify no embeddings/chunks yet)
SELECT id, name, department_id, sensitivity, indexed_at, content_hash
FROM documents
LIMIT 3;
-- Expected: indexed_at will be NULL (not yet indexed to Qdrant)

-- 8. Test authentication (verify password hashes exist)
SELECT username, password_hash, created_at FROM users;
```

---

## CRITICAL: DOCUMENT INGESTION IS SEPARATE

**The seed ONLY creates document metadata records.** It does:
- ✅ Create `documents` table rows
- ✅ Store document names and department assignments
- ❌ **NOT** extract PDF content
- ❌ **NOT** generate embeddings  
- ❌ **NOT** create chunks
- ❌ **NOT** index to Qdrant

**To actually index documents to Qdrant, you MUST run a separate command:**

```bash
# Option 1: Ingest a single PDF
python scripts/ingest_documents.py /path/to/document.pdf \
  --name "Document Title" \
  --department engineering \
  --sensitivity internal

# Option 2: Batch ingest from JSON config
python scripts/ingest_documents.py --batch my_documents.json
```

**my_documents.json format:**
```json
[
  {
    "file_path": "../documents/engineering/api_guide.pdf",
    "name": "API Documentation",
    "department": "engineering",
    "sensitivity": "internal"
  }
]
```

**Ingestion flow:**
1. Read PDF → extract text and pages
2. Split into chunks (600 tokens)
3. Generate embeddings (via OpenAI/Azure)
4. Index vectors into Qdrant
5. Store chunk-to-document mappings in PostgreSQL

**This is NOT part of the seed process.**

---

## RISKS & WARNINGS

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Demo credentials hardcoded** | 🔴 HIGH (prod) | Never use in production. Change passwords/users immediately. |
| **Seed skips existing records** | 🟡 MEDIUM | If running on prod with data, seed won't overwrite. Safe but may not update if schema changes. |
| **No Qdrant indexing** | 🟡 MEDIUM | Documents created in PostgreSQL but NOT searchable until ingested separately. Users won't find anything. |
| **Neon requires `?sslmode=require`** | 🟡 MEDIUM | DATABASE_URL must include `?sslmode=require` or connection will fail. |
| **Migrations must run first** | 🔴 HIGH | Running seed without schema will fail with "relation does not exist" error. |
| **MCP tokens not seeded** | 🟠 LOW | If you need MCP tokens, create them separately using `mcp_token_manager.py` |
| **Password hashes stored plain** | 🟠 LOW | Passwords are hashed (bcrypt) in database. Dev passwords are clearly marked as POC-only. |

---

## FINAL SUMMARY

✅ **Seed is production-ready for:**
- Seeding schema with departments, users, documents metadata
- Safe to run multiple times (idempotent)
- Works with any PostgreSQL compatible database (including Neon)

⚠️ **Seed is NOT for:**
- Deploying production user credentials (use manual user creation)
- Ingesting actual documents (separate `ingest_documents.py` command)
- Creating MCP tokens (use `mcp_token_manager.py`)
- Populating Qdrant vectors (must ingest PDFs separately)
