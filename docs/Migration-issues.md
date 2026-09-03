# SecureRAG — Database Migration, Seed & Qdrant Setup

## Why are we doing this?

SecureRAG has three main data layers:

* **Neon PostgreSQL** → users, departments, document metadata, chunks/mappings
* **Qdrant Cloud** → document embeddings/vectors used for semantic search
* **Application Backend** → connects both databases and uses them during authentication and RAG

The local project already had the database structure and seed data. Since we moved the application to cloud services, we needed to prepare the **Neon PostgreSQL database** and then populate **Qdrant Cloud** with the actual document vectors.

---

## 1. Python Environment

Initially, the local environment was using **Python 3.14**.

The project had an older `pydantic-core` dependency which was not compatible with Python 3.14. It attempted to compile the package using Rust and failed.

### Solution

We created a Python 3.11 virtual environment:

```bash
brew install python@3.11

python3.11 -m venv .venv

source .venv/bin/activate

pip install --upgrade pip

pip install -r backend/requirements.txt
```

Verified dependencies:

```bash
python -c "import pydantic; import pydantic_settings; print('Dependencies OK')"
```

Result:

```text
Dependencies OK
```

---

## 2. Database Migration

### Why?

Alembic migrations are used to keep track of the database schema version.

The project contains an initial migration:

```text
778ae405bfe0
```

Normally we would run:

```bash
python -m scripts.manage_db migrate
```

However, the Neon database already contained the tables:

```text
departments
users
documents
```

So Alembic tried to create `departments` again and returned:

```text
DuplicateTable: relation "departments" already exists
```

### Solution

Since the schema already existed, we did **not** recreate the tables.

Instead, we told Alembic that the existing database is already at the initial migration revision:

```bash
alembic stamp 778ae405bfe0
```

### Important

`stamp` does **not** create or modify the tables.

It only updates Alembic's migration tracking so that Alembic knows:

> "This database is already at migration `778ae405bfe0`."

---

## 3. Database Seed

### Why?

Migration creates/maintains the **database structure**.

It does not create the application's initial users, departments, and demo document metadata.

For that, the project provides a seed script.

We ran:

```bash
python -m scripts.manage_db seed
```

The seed completed successfully.

### Seeded Data

The seed created/populated:

* 4 departments
* 4 demo users
* 12 document metadata records

The document records initially had:

```text
indexed_at = NULL
```

This is expected because the documents had not yet been processed and indexed into Qdrant.

---

## 4. Qdrant Document Ingestion

### Why?

PostgreSQL stores information **about** the documents.

Qdrant stores the **vector embeddings** required for semantic/RAG search.

Therefore, simply seeding PostgreSQL is not enough.

The actual PDF files need to be:

```text
PDF
 ↓
Text extraction
 ↓
Chunking
 ↓
Embeddings
 ↓
Qdrant vectors
 ↓
PostgreSQL document/chunk mappings
```

---

## 5. Batch Ingestion

We found 10 PDF documents under:

```text
documents/
├── engineering/
├── sales/
├── hr/
└── general/
```

Instead of running the ingestion command individually for every PDF, we created:

```text
my_documents.json
```

This contains each document's:

* file path
* document name
* department
* sensitivity

Example:

```json
{
  "file_path": "../documents/engineering/eng-coding-standards.pdf",
  "name": "Coding Standards",
  "department": "engineering",
  "sensitivity": "internal"
}
```

Then all documents were ingested using:

```bash
python scripts/ingest_documents.py --batch my_documents.json
```

### What this does

The ingestion process:

1. Reads each PDF
2. Extracts its text
3. Splits the text into chunks
4. Generates embeddings
5. Stores embeddings in **Qdrant Cloud**
6. Stores/updates document and chunk information in **Neon PostgreSQL**
7. Marks successfully indexed documents accordingly

---

## 6. Final Architecture

```text
                    SecureRAG
                       │
                       ▼
                  FastAPI Backend
                   /           \
                  /             \
                 ▼               ▼
        Neon PostgreSQL      Qdrant Cloud
        ───────────────      ─────────────
        Users               Embeddings
        Departments         Vectors
        Documents           Semantic Search
        Chunks/Mappings
                  ▲
                  │
                  │
              PDF Ingestion
                  ▲
                  │
             10 PDF Files
```

### In short

**Migration** → prepares/tracks database schema.

**Seed** → creates initial users, departments and document metadata.

**Ingestion** → processes the actual PDFs and populates Qdrant with embeddings.

All three are required for the deployed SecureRAG application to work correctly end-to-end.
