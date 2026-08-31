# 📄 Document Management Guide

Complete guide for adding and managing documents in SecureRAG.

---

## 🚀 Quick Start: Add New Documents

### **Step 1: Place PDFs**

```bash
# Copy your PDF files to the appropriate department folder:
documents/
├── engineering/  ← Technical docs (Mohit & Deepak can access)
├── sales/        ← Sales docs (Karthik can access)
├── hr/           ← HR docs (Swathi can access)
└── general/      ← Public docs (Everyone can access)
```

### **Step 2: Create Config File**

```bash
cd backend
nano my_documents.json
```

**Example config:**
```json
[
  {
    "file_path": "../documents/engineering/api_guide.pdf",
    "name": "API Integration Guide",
    "department": "engineering",
    "sensitivity": "internal"
  },
  {
    "file_path": "../documents/sales/pricing.pdf",
    "name": "Pricing Strategy",
    "department": "sales",
    "sensitivity": "confidential"
  }
]
```

**Field Options:**
- `department`: `engineering`, `sales`, `hr`, `general`
- `sensitivity`: `public`, `internal`, `confidential`

### **Step 3: Run Ingestion**

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/backend
source venv/bin/activate
python scripts/ingest_documents.py --batch my_documents.json
```

**Output:**
```
Ingesting 10 documents...
[1/10] Processing API Integration Guide...
✓ SUCCESS: Document 'API Integration Guide' ingested and indexed
...
============================================================
Batch ingestion complete:
  ✓ Success: 10/10
  ✗ Failed: 0/10
============================================================
```

---

## 🗑️ Delete All Documents

**To clean everything and start fresh:**

```bash
cd /Users/mohittrigunayat/Desktop/personal/SecureRAG/backend
source venv/bin/activate
python scripts/cleanup_all_documents.py
```

**Confirmation required:** Type `DELETE ALL` when prompted.

**What it does:**
- ✅ Deletes all documents from PostgreSQL
- ✅ Deletes all vectors from Qdrant
- ✅ Resets system to clean state

---

## 📋 Available Scripts

### **1. Ingest Documents** (`scripts/ingest_documents.py`)

**Single document:**
```bash
python scripts/ingest_documents.py \
  ../documents/engineering/doc.pdf \
  --name "Document Title" \
  --department engineering \
  --sensitivity internal
```

**Batch mode (recommended):**
```bash
python scripts/ingest_documents.py --batch my_documents.json
```

**What it does:**
- Extracts text from PDF
- Cleans and chunks text
- Registers in PostgreSQL
- Generates embeddings (local, no cost)
- Indexes in Qdrant with ACL metadata

---

### **2. Cleanup All Documents** (`scripts/cleanup_all_documents.py`)

```bash
python scripts/cleanup_all_documents.py
```

**What it does:**
- Deletes ALL documents from PostgreSQL
- Deletes ALL vectors from Qdrant
- Recreates empty Qdrant collection
- Gives you a clean slate

**Use when:**
- Starting fresh with new documents
- Testing/development
- Removing old data

---

### **3. Database Management** (`scripts/manage_db.py`)

```bash
# Reset database schema
python scripts/manage_db.py reset

# Seed demo users (mohit, deepak, karthik, swathi)
python scripts/manage_db.py seed
```

**Use when:**
- Initial setup
- Database schema changes
- Resetting user data

---

## 🔄 Complete Workflow

### **Scenario: Replace All Documents**

```bash
# 1. Clean everything
cd backend
source venv/bin/activate
python scripts/cleanup_all_documents.py
# Type: DELETE ALL

# 2. Copy new PDFs to documents/ folders
cp ~/Downloads/*.pdf ../documents/engineering/

# 3. Create config
nano my_documents.json
# (Add your document list)

# 4. Ingest
python scripts/ingest_documents.py --batch my_documents.json

# 5. Verify
psql postgresql://rag_user:rag_password@localhost:5432/secure_rag \
  -c "SELECT id, name, department_id FROM documents;"
```

---

## ✅ Verification Commands

### **Check PostgreSQL Documents**
```bash
psql postgresql://rag_user:rag_password@localhost:5432/secure_rag \
  -c "SELECT id, name, department_id, indexed_at FROM documents ORDER BY id;"
```

### **Check Qdrant Vectors**
```bash
curl -s http://localhost:6333/collections/knowledge_chunks | python3 -m json.tool | grep points_count
```

### **Count by Department**
```bash
psql postgresql://rag_user:rag_password@localhost:5432/secure_rag \
  -c "SELECT d.name as department, COUNT(*) as doc_count FROM documents doc JOIN departments d ON doc.department_id = d.id GROUP BY d.name ORDER BY d.name;"
```

---

## 🎯 One-Command Examples

### **Add Single Document (Quick Test)**
```bash
cd backend && source venv/bin/activate && \
python scripts/ingest_documents.py \
  ../documents/engineering/test.pdf \
  --name "Test Document" \
  --department engineering \
  --sensitivity internal
```

### **Full Cleanup + Fresh Ingest**
```bash
cd backend && source venv/bin/activate && \
echo "DELETE ALL" | python scripts/cleanup_all_documents.py && \
python scripts/ingest_documents.py --batch my_documents.json
```

---

## 📂 File Locations Reference

```
SecureRAG/
├── documents/                          # ← PUT YOUR PDFs HERE
│   ├── engineering/
│   ├── sales/
│   ├── hr/
│   └── general/
│
├── backend/
│   ├── my_documents.json              # ← YOUR BATCH CONFIG
│   └── scripts/
│       ├── ingest_documents.py        # ← ADD DOCUMENTS
│       ├── cleanup_all_documents.py   # ← DELETE ALL
│       └── manage_db.py               # ← DATABASE ADMIN
│
└── DOCUMENT_MANAGEMENT.md             # ← THIS FILE
```

---

## 🔒 Access Control (Automatic)

Documents are automatically restricted by department:

| Department | Users | Can Access |
|------------|-------|------------|
| **engineering** | Mohit, Deepak | Engineering + General docs |
| **sales** | Karthik | Sales + General docs |
| **hr** | Swathi | HR + General docs |
| **general** | Everyone | General docs only |

**No code changes needed!** The system enforces ACL automatically during:
- Document retrieval
- Vector search
- Chat/RAG responses

---

## ⚠️ Important Notes

### **File Requirements:**
- ✅ Only PDF files supported
- ✅ Files must exist before running ingestion
- ✅ Use relative paths from `backend/` folder: `../documents/...`

### **Department Names (Exact Match):**
- ✅ `engineering` (lowercase)
- ✅ `sales`
- ✅ `hr`
- ✅ `general`
- ❌ NOT: `Engineering`, `SALES`, etc.

### **Sensitivity Levels:**
- `public` - Can share externally
- `internal` - Company-wide only
- `confidential` - Department-restricted + extra sensitive

### **Re-ingestion:**
- Documents with same content hash are skipped automatically
- Change PDF content → Re-run ingestion → Automatically updates

---

## 🐛 Troubleshooting

### **Error: "Department not found"**
**Fix:** Use exact department names: `engineering`, `sales`, `hr`, `general`

### **Error: "File not found"**
**Fix:** Use paths relative to `backend/` folder:
```json
"file_path": "../documents/engineering/doc.pdf"  // ✅ Correct
"file_path": "documents/doc.pdf"                 // ❌ Wrong
```

### **Error: "Unsupported file type"**
**Fix:** Only PDF files supported. Convert Word/Excel to PDF first.

### **Qdrant connection error**
**Fix:** Make sure Qdrant is running:
```bash
docker ps | grep qdrant
# If not running:
docker-compose up qdrant -d
```

### **PostgreSQL connection error**
**Fix:** Check PostgreSQL is running and accessible:
```bash
psql postgresql://rag_user:rag_password@localhost:5432/secure_rag -c "SELECT 1;"
```

---

## 📊 Performance

| Documents | Processing Time | Vectors Created |
|-----------|----------------|-----------------|
| 1 doc (10 pages) | ~5-10 seconds | ~25 vectors |
| 10 docs (100 pages) | ~1-2 minutes | ~250 vectors |
| 50 docs (500 pages) | ~5-10 minutes | ~1,250 vectors |

**No API costs** - embeddings are generated locally using `sentence-transformers`.

---

## 📚 Summary

**To add documents:**
1. Copy PDFs to `documents/` folders
2. Create `my_documents.json` config
3. Run `python scripts/ingest_documents.py --batch my_documents.json`

**To delete all:**
1. Run `python scripts/cleanup_all_documents.py`
2. Type `DELETE ALL` to confirm

**That's it!** 🎉
