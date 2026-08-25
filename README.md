# Secure RAG Knowledge Assistant

A production-quality Retrieval-Augmented Generation (RAG) system with document-level access control, prompt injection protection, and hallucination prevention.

## Project Overview

This is an internal company Knowledge Assistant that allows employees to query company documents with strict authorization controls. The system ensures users can only access documents they are authorized to see, protects against prompt injection attacks, and prevents hallucination through grounded generation.

## Architecture

### Technology Stack

- **Backend**: Python 3.11 + FastAPI
- **Database**: PostgreSQL 15
- **Vector Database**: Qdrant
- **LLM**: OpenAI GPT-4.1-mini
- **Embeddings**: OpenAI text-embedding-3-small
- **Containerization**: Docker Compose

### Core Architecture Flow

```
User Question
    ↓
FastAPI Backend
    ↓
Authentication (JWT)
    ↓
Authorization (Department-based)
    ↓
Query Embedding (OpenAI)
    ↓
Qdrant Vector Search + ACL Filter
    ↓
Authorized Chunks Only
    ↓
Relevance Validation
    ↓
Secure Prompt Construction
    ↓
GPT-4.1-mini Generation
    ↓
Answer + Authorized Sources
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
- OpenAI API key (for embeddings and LLM)

## Quick Start

### 1. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and set your configuration:

```bash
# Required: Set your OpenAI API key
OPENAI_API_KEY=sk-your-api-key-here

# Required: Set a strong JWT secret (minimum 32 characters)
JWT_SECRET=your-secret-key-minimum-32-characters-long

# Optional: Adjust other settings as needed
APP_ENV=development
LOG_LEVEL=INFO
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

### Planned Endpoints (Future Phases)

- `POST /api/auth/login` - User authentication
- `POST /api/chat` - Submit question, receive answer with sources
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

- `OPENAI_API_KEY`: OpenAI API key for embeddings and LLM
- `JWT_SECRET`: Secret key for JWT signing (minimum 32 characters)
- `JWT_ALGORITHM`: JWT signing algorithm (default: HS256)
- `JWT_EXPIRATION_HOURS`: JWT expiration time (default: 1 hour)

### RAG Settings

- `CHUNK_SIZE`: Document chunk size in characters (default: 600)
- `CHUNK_OVERLAP`: Chunk overlap in characters (default: 100)
- `RELEVANCE_THRESHOLD`: Minimum similarity score for retrieval (default: 0.7)

## Development Status

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

### Current Phase
- ✅ No secrets committed to Git
- ✅ Environment-based configuration
- ✅ Structured error handling (no internal details exposed)
- ✅ Logging infrastructure (prepared for sensitive data filtering)

### Future Phases
- 🔄 JWT authentication
- 🔄 Department-based authorization
- 🔄 Retrieval-time ACL filtering
- 🔄 Prompt injection protection
- 🔄 Hallucination prevention

## License

This is a technical evaluation project.

## Architecture Documentation

For detailed architecture review and decisions, see [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md).