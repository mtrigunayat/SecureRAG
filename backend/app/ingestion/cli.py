"""
Document ingestion and indexing CLI

Development tool for ingesting documents and indexing them into Qdrant.
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService
from app.services.vector_indexing_service import VectorIndexingService
from app.core.logging import setup_logging, get_logger
from app.core.errors import IngestionError, VectorDBError, EmbeddingError

setup_logging()
logger = get_logger(__name__)


def ingest_document(
    file_path: str,
    document_name: str,
    department: str,
    sensitivity: str
) -> None:
    """
    Ingest a single document.
    
    Args:
        file_path: Path to PDF file
        document_name: Document name/title
        department: Department name (must exist in database)
        sensitivity: Sensitivity level (public/internal/confidential)
    """
    logger.info("=" * 60)
    logger.info("DOCUMENT INGESTION")
    logger.info("=" * 60)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create ingestion service
        ingestion_service = IngestionService(db)
        
        # Ingest document
        result = ingestion_service.ingest_document(
            file_path=file_path,
            document_name=document_name,
            department_name=department,
            sensitivity=sensitivity
        )
        
        # Display result
        logger.info("=" * 60)
        logger.info("INGESTION RESULT")
        logger.info("=" * 60)
        logger.info(f"Document:         {result.document_name}")
        logger.info(f"Document ID:      {result.document_id}")
        logger.info(f"Department:       {result.department_name}")
        logger.info(f"Sensitivity:      {result.sensitivity}")
        logger.info(f"Pages:            {result.page_count}")
        logger.info(f"Characters:       {result.character_count}")
        logger.info(f"Chunks:           {result.chunk_count}")
        logger.info(f"Content Hash:     {result.content_hash[:32]}...")
        logger.info(f"Status:           {result.status}")
        logger.info("=" * 60)
        
        if result.status == "UNCHANGED_SKIP_INGESTION":
            logger.info("✓ Document unchanged - ingestion skipped")
        else:
            logger.info("✓ Document ready for embedding (Phase 7)")
            
            # Show sample chunks
            if result.chunks:
                logger.info("")
                logger.info("Sample chunks:")
                for i, chunk in enumerate(result.chunks[:3], 1):
                    logger.info(f"\nChunk {i}:")
                    logger.info(f"  ID:        {chunk.chunk_id}")
                    logger.info(f"  Pages:     {chunk.page_start}-{chunk.page_end}")
                    logger.info(f"  Length:    {len(chunk.text)} chars")
                    logger.info(f"  Preview:   {chunk.text[:100]}...")
                
                if len(result.chunks) > 3:
                    logger.info(f"\n... and {len(result.chunks) - 3} more chunks")
        
    except IngestionError as e:
        logger.error(f"✗ Ingestion failed: {e.message}")
        if e.details:
            logger.error(f"  Details: {e.details}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        sys.exit(1)
        
    finally:
        db.close()


def index_document(document_id: int) -> None:
    """
    Index a document's chunks into Qdrant.
    
    Document must already be ingested (Phase 6).
    Generates local embeddings and indexes to Qdrant.
    
    Args:
        document_id: PostgreSQL document ID to index
    """
    logger.info("=" * 60)
    logger.info("VECTOR INDEXING")
    logger.info("=" * 60)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get ingestion result from database
        from app.repositories.document_repository import DocumentRepository
        from app.services.ingestion_service import IngestionService
        
        doc_repo = DocumentRepository(db)
        document = doc_repo.get_by_id(document_id)
        
        if not document:
            logger.error(f"✗ Document ID {document_id} not found")
            sys.exit(1)
        
        # Re-run ingestion to get chunks (in production, chunks would be stored)
        ingestion_service = IngestionService(db)
        
        # Find original source file
        if not document.source:
            logger.error(f"✗ Document {document_id} has no source file path")
            sys.exit(1)
        
        logger.info(f"Re-processing document for indexing: {document.name}")
        ingestion_result = ingestion_service.ingest_document(
            file_path=document.source,
            document_name=document.name,
            department_name=document.department.name,
            sensitivity=document.sensitivity
        )
        
        # Create indexing service
        indexing_service = VectorIndexingService(db)
        
        # Index document
        logger.info(f"Indexing {len(ingestion_result.chunks)} chunks...")
        result = indexing_service.index_document(ingestion_result)
        
        # Display result
        logger.info("=" * 60)
        logger.info("INDEXING RESULT")
        logger.info("=" * 60)
        logger.info(f"Document:         {result.document_name}")
        logger.info(f"Document ID:      {result.document_id}")
        logger.info(f"Department:       {result.department_name}")
        logger.info(f"Chunks:           {result.chunk_count}")
        logger.info(f"Embeddings:       {result.embedded_count}")
        logger.info(f"Indexed:          {result.indexed_count}")
        logger.info(f"Model:            {result.embedding_model}")
        logger.info(f"Dimension:        {result.vector_dimension}")
        logger.info(f"Collection:       {result.collection}")
        logger.info(f"Status:           {result.status}")
        logger.info("=" * 60)
        logger.info("✓ Document indexed successfully")
        logger.info("")
        logger.info("Embedding API cost: $0 (local model)")
        
        # Show collection info
        collection_info = indexing_service.get_collection_info()
        logger.info("")
        logger.info("Collection info:")
        logger.info(f"  Total vectors: {collection_info['points_count']}")
        logger.info(f"  Dimension:     {collection_info['vector_size']}")
        logger.info(f"  Distance:      {collection_info['distance']}")
        
    except (VectorDBError, EmbeddingError, IngestionError) as e:
        logger.error(f"✗ Indexing failed: {e.message}")
        if hasattr(e, 'details') and e.details:
            logger.error(f"  Details: {e.details}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        db.close()


def ingest_and_index(
    file_path: str,
    document_name: str,
    department: str,
    sensitivity: str
) -> None:
    """
    Ingest and index a document in one operation.
    
    Combines Phase 6 (ingestion) and Phase 7 (indexing).
    
    Args:
        file_path: Path to PDF file
        document_name: Document name/title
        department: Department name
        sensitivity: Sensitivity level
    """
    logger.info("=" * 60)
    logger.info("DOCUMENT INGESTION & INDEXING")
    logger.info("=" * 60)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Step 1: Ingest
        logger.info("Step 1: Ingesting document...")
        ingestion_service = IngestionService(db)
        ingestion_result = ingestion_service.ingest_document(
            file_path=file_path,
            document_name=document_name,
            department_name=department,
            sensitivity=sensitivity
        )
        
        logger.info(f"✓ Ingestion complete: {ingestion_result.chunk_count} chunks")
        
        if ingestion_result.status == "UNCHANGED_SKIP_INGESTION":
            logger.info("Document unchanged - skipping re-indexing")
            return
        
        # Step 2: Index
        logger.info("")
        logger.info("Step 2: Generating embeddings and indexing...")
        indexing_service = VectorIndexingService(db)
        indexing_result = indexing_service.index_document(ingestion_result)
        
        # Display combined result
        logger.info("")
        logger.info("=" * 60)
        logger.info("COMPLETE RESULT")
        logger.info("=" * 60)
        logger.info(f"Document:         {indexing_result.document_name}")
        logger.info(f"Document ID:      {indexing_result.document_id}")
        logger.info(f"Department:       {indexing_result.department_name}")
        logger.info(f"Pages:            {ingestion_result.page_count}")
        logger.info(f"Characters:       {ingestion_result.character_count}")
        logger.info(f"Chunks:           {indexing_result.chunk_count}")
        logger.info(f"Indexed Vectors:  {indexing_result.indexed_count}")
        logger.info(f"Embedding Model:  {indexing_result.embedding_model}")
        logger.info(f"Vector Dimension: {indexing_result.vector_dimension}")
        logger.info(f"Collection:       {indexing_result.collection}")
        logger.info("=" * 60)
        logger.info("✓ Document ingested and indexed successfully")
        logger.info("")
        logger.info("Embedding API cost: $0 (local model)")
        
        # Show collection info
        collection_info = indexing_service.get_collection_info()
        logger.info("")
        logger.info("Collection info:")
        logger.info(f"  Total vectors: {collection_info['points_count']}")
        
    except (IngestionError, VectorDBError, EmbeddingError) as e:
        logger.error(f"✗ Operation failed: {e.message}")
        if hasattr(e, 'details') and e.details:
            logger.error(f"  Details: {e.details}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        db.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest and index documents into the knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  ingest              Ingest document (Phase 6 only)
  index               Index document to Qdrant (Phase 7 only)
  ingest-and-index    Ingest and index in one operation

Examples:
  # Ingest only (Phase 6)
  python -m app.ingestion.cli ingest docs/deployment.pdf \\
      --name "Deployment Guidelines" \\
      --department engineering \\
      --sensitivity internal
  
  # Index only (Phase 7) - requires document already ingested
  python -m app.ingestion.cli index --document-id 1
  
  # Ingest and index together
  python -m app.ingestion.cli ingest-and-index docs/deployment.pdf \\
      --name "Deployment Guidelines" \\
      --department engineering \\
      --sensitivity internal

Valid departments: engineering, sales, hr, general
Valid sensitivity levels: public, internal, confidential
        """
    )
    
    parser.add_argument(
        "command",
        choices=["ingest", "index", "ingest-and-index"],
        help="Command to run"
    )
    
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to PDF file (required for ingest/ingest-and-index)"
    )
    
    parser.add_argument(
        "--name",
        help="Document name/title (required for ingest/ingest-and-index)"
    )
    
    parser.add_argument(
        "--department",
        help="Department name (required for ingest/ingest-and-index)"
    )
    
    parser.add_argument(
        "--sensitivity",
        choices=["public", "internal", "confidential"],
        help="Document sensitivity level (required for ingest/ingest-and-index)"
    )
    
    parser.add_argument(
        "--document-id",
        type=int,
        help="Document ID to index (required for index command)"
    )
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        if not all([args.file, args.name, args.department, args.sensitivity]):
            parser.error("ingest requires: file, --name, --department, --sensitivity")
        ingest_document(
            file_path=args.file,
            document_name=args.name,
            department=args.department,
            sensitivity=args.sensitivity
        )
    
    elif args.command == "index":
        if not args.document_id:
            parser.error("index requires: --document-id")
        index_document(document_id=args.document_id)
    
    elif args.command == "ingest-and-index":
        if not all([args.file, args.name, args.department, args.sensitivity]):
            parser.error("ingest-and-index requires: file, --name, --department, --sensitivity")
        ingest_and_index(
            file_path=args.file,
            document_name=args.name,
            department=args.department,
            sensitivity=args.sensitivity
        )


if __name__ == "__main__":
    main()
