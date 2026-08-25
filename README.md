# Secure RAG Knowledge Assistant

A production-quality Retrieval-Augmented Generation (RAG) system with document-level access control, prompt injection protection, and hallucination prevention.

## Project Overview

This is an internal company Knowledge Assistant that allows employees to query company documents with strict authorization controls. The system ensures users can only access documents they are authorized to see, protects against prompt injection attacks, and prevents hallucination through grounded generation.

## Architecture

### Technology Stack

- **Backend**: Python 3.11 + FastAPI
- **Database**: PostgreSQL 15
- **Vector Database**: Qdrant
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (local, $0 cost)
- **Retrieval**: Qdrant vector search with department-based ACL filtering
- **LLM**: Azure OpenAI GPT-4.1-mini (Phase 9 complete)
- **Containerization**: Docker Compose

### Core Architecture Flow

```
User Question
    ↓
FastAPI Backend
    ↓
Authentication (JWT) ✅ Phase 4
    ↓
Authorization (Department-based) ✅ Phase 5
    ↓
Query Embedding (Local sentence-transformers) ✅ Phase 8
    ↓
Qdrant Vector Search + ACL Filter ✅ Phase 8
    ↓
Authorized Chunks Only ✅ Phase 8
    ↓
Relevance Validation ✅ Phase 8
    ↓
Secure Prompt Construction ✅ Phase 9
    ↓
Azure OpenAI GPT-4.1-mini Generation ✅ Phase 9
    ↓
Answer + Backend-Controlled Sources ✅ Phase 9
```

### Security Principles

1. **Retrieval-time ACL**: Authorization enforced during vector search, not post-retrieval
2. **Server-side filtering**: Client never specifies access scope
3. **Untrusted content**: Retrieved documents treated as data, not instructions
4. **Prompt injection protection**: Clear separation of system instructions and retrieved context
5. **Hallucination prevention**: Relevance thresholds and explicit grounding instructions

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Azure OpenAI API key (for LLM generation)

## Quick Start

### 1. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and set your configuration:

```bash
# Required: Set your Azure OpenAI credentials (Phase 9)
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Required: Set a strong JWT secret (minimum 32 characters)
JWT_SECRET=your-secret-key-minimum-32-characters-long

# Optional: Adjust other settings as needed
APP_ENV=development
LOG_LEVEL=INFO
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=1000
```

### 2. Start Services

Start all services using Docker Compose:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Qdrant (port 6333)
- FastAPI Backend (port 8000)

### 3. Verify Health

Check that all services are healthy:

```bash
curl http://localhost:8000/api/health
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

### 4. View API Documentation

Open your browser to view the interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Document Ingestion (Phase 6)

**Important:** Phase 6 implements ONLY the ingestion pipeline (PDF → chunks). It does NOT:
- Generate embeddings
- Insert vectors into Qdrant
- Implement retrieval
- Make any LLM calls

#### Ingestion Pipeline Flow

```
PDF File
  ↓
PDF Text Extraction (pypdf)
  ├─ Preserve page boundaries
  └─ Page-by-page extraction
  ↓
Text Cleaning (conservative)
  ├─ Normalize line endings
  ├─ Tabs → spaces
  ├─ Collapse multiple blank lines
  └─ NO AI rewriting, NO summarization
  ↓
Document Registration (PostgreSQL)
  ├─ Calculate SHA-256 content hash
  ├─ Validate department exists
  ├─ Validate sensitivity level
  └─ Store metadata (indexed_at=NULL)
  ↓
Text Chunking (RecursiveCharacterTextSplitter)
  ├─ chunk_size: 600 characters
  ├─ chunk_overlap: 100 characters
  ├─ Preserve page information
  └─ Add complete metadata
  ↓
Output: List[DocumentChunk]
  ├─ chunk_id: "{document_id}_{chunk_index}"
  ├─ document_id, document_name
  ├─ department_id, department_name
  ├─ sensitivity
  ├─ page_start, page_end (1-indexed)
  ├─ chunk_index (0-indexed)
  └─ text (ready for embedding)
```

#### CLI Usage

Ingest a PDF document (development only):

```bash
cd backend

# Basic ingestion
python -m app.ingestion.cli ingest path/to/document.pdf \
  --name "Document Name" \
  --department engineering \
  --sensitivity internal

# Example with test fixtures
python -m app.ingestion.cli ingest tests/fixtures/pdfs/coding_standards.pdf \
  --name "Coding Standards" \
  --department engineering \
  --sensitivity internal
```

**Supported Parameters:**
- `--department`: Must be one of: engineering, sales, hr, general
- `--sensitivity`: Must be one of: public, internal, confidential

**Re-ingestion Behavior:**
- Same content hash + same name → UNCHANGED_SKIP_INGESTION (no processing)
- Different content hash + same name → Updates document, processes new chunks
- This is deterministic - same PDF always produces same hash

**Output Example:**
```
================================================================================
INGESTION RESULT
================================================================================
Document:         Coding Standards
Document ID:      2
Department:       engineering
Sensitivity:      internal
Pages:            2
Characters:       575
Chunks:           1
Content Hash:     9e00c0622908bc6ec4...
Status:           READY_FOR_EMBEDDING
================================================================================
✓ Document ready for embedding (Phase 7)

Sample chunks:

Chunk 1:
  ID:        2_0
  Pages:     1-2
  Length:    577 chars
  Preview:   Coding Standards
```

#### Chunk Metadata Contract (Phase 6 → Phase 7)

Each `DocumentChunk` contains all metadata needed for Qdrant indexing:

```python
DocumentChunk(
    chunk_id="2_0",              # Unique ID: {document_id}_{chunk_index}
    document_id=2,               # PostgreSQL document.id
    document_name="Coding Standards",
    department_id=1,             # For ACL filtering in Qdrant
    department_name="engineering",
    sensitivity="internal",      # For future sensitivity-based filtering
    page_start=1,                # 1-indexed page number
    page_end=2,                  # Inclusive
    chunk_index=0,               # 0-indexed position in document
    text="Coding Standards\nPage 1\n..."  # Ready for embedding
)
```

**Phase 7 will:**
1. Generate embedding for `chunk.text`
2. Insert into Qdrant with:
   - Vector: embedding
   - Payload: all chunk metadata
   - Filter field: `department_id` (for ACL)

### Local Development Setup

For local development without Docker:

```bash
# Create virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Qdrant via Docker
docker-compose up -d postgres qdrant

# Run the backend locally
uvicorn app.main:app --reload
```

### Running Tests

```bash
cd backend
pytest
```

For verbose output:
```bash
pytest -v
```

For specific test categories:
```bash
pytest -m unit
pytest -m integration
```

### Project Structure

```
SecureRAG/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   │   └── health.py     # Health check endpoint
│   │   ├── core/             # Core configuration
│   │   │   ├── config.py     # Application settings
│   │   │   ├── logging.py    # Logging configuration
│   │   │   └── errors.py     # Error handling
│   │   ├── db/               # Database
│   │   │   └── session.py    # SQLAlchemy session management
│   │   ├── services/         # Business logic services
│   │   │   └── qdrant_service.py  # Qdrant client wrapper
│   │   └── main.py           # Application entry point
│   ├── tests/                # Test suite
│   │   ├── conftest.py       # Pytest configuration
│   │   ├── test_health.py    # Health endpoint tests
│   │   └── test_config.py    # Configuration tests
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile            # Backend Docker image
│   └── pytest.ini            # Pytest configuration
├── docker-compose.yml        # Docker orchestration
├── .env.example              # Example environment variables
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## API Endpoints

### Current Endpoints (Phase 2)

#### `GET /api/health`
Health check endpoint that verifies all services are running.

**Response:**
```json
{
  "status": "healthy|degraded",
  "services": {
    "database": "ok|unavailable",
    "vector_db": "ok|unavailable"
  }
}
```

#### `POST /api/auth/login` (Phase 4)
User authentication endpoint.

**Request:**
```json
{
  "username": "alice",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

#### `POST /api/chat` (Phase 9)
RAG generation endpoint. Requires JWT authentication.

**Request:**
```json
{
  "question": "What is our deployment process?"
}
```

**Response:**
```json
{
  "answer": "The deployment process has three stages: build, test, and deploy...",
  "sources": [
    {
      "document_id": 1,
      "document_name": "Engineering Handbook",
      "department_name": "engineering",
      "sensitivity": "internal",
      "page_start": 5,
      "page_end": 6,
      "score": 0.87
    }
  ],
  "retrieved_count": 1,
  "user_department_name": "engineering",
  "model": "gpt-4.1-mini"
}
```

**Headers:**
```
Authorization: Bearer eyJ...
```

### Planned Endpoints (Future Phases)

- `POST /api/documents/ingest` - Upload and index documents (internal only)

## Configuration

All configuration is managed through environment variables (`.env` file).

### Application Settings

- `APP_ENV`: Environment (development/production)
- `APP_HOST`: API host (default: 0.0.0.0)
- `APP_PORT`: API port (default: 8000)
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)

### Database Settings

- `DATABASE_URL`: PostgreSQL connection string

### Vector Database Settings

- `QDRANT_URL`: Qdrant server URL

### Security Settings

- `JWT_SECRET`: Secret key for JWT signing (minimum 32 characters)
- `JWT_ALGORITHM`: JWT signing algorithm (default: HS256)
- `JWT_EXPIRATION_HOURS`: JWT expiration time (default: 1 hour)

### LLM Settings (Phase 9)

- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint URL
- `AZURE_OPENAI_DEPLOYMENT`: Azure OpenAI deployment name (default: gpt-4.1-mini)
- `AZURE_OPENAI_API_VERSION`: Azure OpenAI API version (default: 2024-12-01-preview)
- `LLM_TEMPERATURE`: LLM temperature (default: 0.0 for deterministic responses)
- `LLM_MAX_TOKENS`: Maximum tokens for LLM responses (default: 1000)

### RAG Settings

- `CHUNK_SIZE`: Document chunk size in characters (default: 600)
- `CHUNK_OVERLAP`: Chunk overlap in characters (default: 100)
- `RELEVANCE_THRESHOLD`: Minimum similarity score for retrieval (default: 0.7)

## Development Status

### Completed Phases

## ✅ Phase 2: Backend Foundation — COMPLETE
- FastAPI application setup
- Database session management (SQLAlchemy)
- Qdrant service wrapper
- Configuration management (Pydantic Settings)
- Error handling framework
- Health check endpoint (`GET /api/health`)
- Docker Compose orchestration
- Test infrastructure
- **Details:** [PHASE_2_COMPLETE.md](PHASE_2_COMPLETE.md)

## ✅ Phase 3: Data Model & Database Schema — COMPLETE
- SQLAlchemy models (Department, User, Document)
- Entity relationships (department → users, department → documents)
- Alembic migrations
- Repository pattern (clean data access layer)
- Seed data (3 departments, 3 users, 12 documents)
- Database tests (models, repositories, seed)
- PostgreSQL-Qdrant contract defined
- **Details:** [PHASE_3_COMPLETE.md](PHASE_3_COMPLETE.md)

## ✅ Phase 6: Document Ingestion Pipeline — COMPLETE
- PDF text extraction with page preservation
- Conservative text cleaning (normalization only, no AI rewriting)
- Document chunking with RecursiveCharacterTextSplitter (600 chars, 100 overlap)
- Complete metadata enrichment (department, sensitivity, page ranges)
- Deterministic content hashing for duplicate detection
- Re-ingestion handling (unchanged content skipped)
- CLI tool for development ingestion
- 52 comprehensive tests (extraction, cleaning, chunking, full pipeline)
- **Status:** Documents ready for Phase 7 embedding
- **Output:** DocumentChunk schema with complete metadata for Qdrant indexing

## ✅ Phase 7: Vector Embeddings and Indexing — COMPLETE
- **Local embedding generation using sentence-transformers/all-MiniLM-L6-v2**
- **Zero-cost embeddings: NO external API calls, NO API keys required**
- 384-dimensional vectors with Cosine distance
- Qdrant collection creation and management (knowledge_chunks)
- Idempotent vector indexing (upsert semantics)
- Clean re-indexing (old vectors deleted first)
- ACL foundation (department_id in every vector payload)
- VectorIndexingService orchestrator
- EmbeddingService abstraction (supports multiple providers)
- CLI tool extended with `index` and `ingest-and-index` commands
- Comprehensive tests (embedding service, indexing service)
- **Embedding API cost: $0**
- **Details:** [PHASE_7_COMPLETE.md](PHASE_7_COMPLETE.md)

## ✅ Phase 8: Secure Vector Retrieval with ACL Filtering — COMPLETE
- **CRITICAL security guarantee: Users can NEVER retrieve documents from unauthorized departments**
- Retrieval-time ACL filtering inside Qdrant (NOT post-retrieval)
- Department resolution from PostgreSQL (never from client)
- Same embedding model as indexing (sentence-transformers/all-MiniLM-L6-v2)
- **Embedding cost: $0** (local execution)
- RetrievalService orchestrator with secure department resolution
- QdrantService.search() method with ACL filtering
- POST /api/retrieval endpoint (question → authorized chunks)
- Top-K configuration (5 chunks)
- Relevance threshold (0.7 cosine similarity)
- Comprehensive security tests (23 tests, all passing)
  - Cross-department isolation tests
  - Client cannot bypass ACL
  - Filter presence verification
  - No post-retrieval filtering
- **Details:** [PHASE_8_COMPLETE.md](backend/PHASE_8_COMPLETE.md)

## ✅ Phase 9: RAG Generation with Azure OpenAI — COMPLETE
- **CRITICAL security guarantee: NO UNAUTHORIZED CONTENT REACHES LLM**
- LLM service abstraction (provider-agnostic architecture)
- Azure OpenAI GPT-4.1-mini integration
- Secure prompt construction with prompt injection defense
- Three-message architecture (system/context/question separation)
- Hallucination prevention (empty retrieval = no LLM call)
- Backend-controlled sources (LLM cannot invent citations)
- POST /api/chat endpoint (question → answer + sources)
- Configuration: Temperature 0.0, Max Tokens 1000
- Comprehensive security tests (20 tests, all passing)
  - Cross-department LLM isolation
  - Prompt injection defense verification
  - Empty retrieval handling
  - LLM failure handling
- **Embedding cost: $0** (local sentence-transformers)
- **LLM cost: ~$0.0001 per query** (Azure GPT-4.1-mini)
- **Details:** [PHASE_9_COMPLETE.md](backend/PHASE_9_COMPLETE.md)

### Pending Phases

## 🔄 Phase 4: Authentication & Authorization — PENDING

**Current Phase**: Phase 2 - Project Foundation & Backend Infrastructure ✅

**Implemented:**
- ✅ FastAPI application structure
- ✅ PostgreSQL connection and session management
- ✅ Qdrant client integration
- ✅ Configuration management
- ✅ Logging infrastructure
- ✅ Error handling framework
- ✅ Health check endpoint
- ✅ Docker Compose orchestration
- ✅ Test infrastructure

**Upcoming Phases:**
- Phase 3: Database Models & Schema
- Phase 4: Authentication & Authorization
- Phase 5: Document Ingestion Pipeline
- Phase 6: Embeddings & Vector Storage
- Phase 7: RAG Query Pipeline
- Phase 8: Prompt Security & LLM Integration
- Phase 9: Frontend UI
- Phase 10: Security Testing
- Phase 11: Documentation & Deployment

## Security Considerations

### Implemented Security (Phases 1-9)
- ✅ No secrets committed to Git
- ✅ Environment-based configuration
- ✅ Structured error handling (no internal details exposed)
- ✅ Logging infrastructure (sensitive data filtering)
- ✅ JWT authentication with secure password hashing (bcrypt)
- ✅ Department-based authorization (PostgreSQL-enforced)
- ✅ Retrieval-time ACL filtering (Qdrant-level, not post-retrieval)
- ✅ Prompt injection protection (system message defense)
- ✅ Hallucination prevention (empty retrieval = no LLM call)
- ✅ Backend-controlled sources (LLM cannot invent citations)
- ✅ Error sanitization (no API keys or prompts exposed)
- ✅ **CRITICAL**: NO UNAUTHORIZED CONTENT REACHES LLM

## License

This is a technical evaluation project.

## Architecture Documentation

For detailed architecture review and decisions, see [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md).