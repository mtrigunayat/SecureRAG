"""
Document ingestion CLI

Development tool for ingesting documents into the knowledge base.
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService
from app.core.logging import setup_logging, get_logger
from app.core.errors import IngestionError

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


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into the knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest engineering document
  python -m app.ingestion.cli ingest docs/deployment.pdf \\
      --name "Deployment Guidelines" \\
      --department engineering \\
      --sensitivity internal
  
  # Ingest sales document
  python -m app.ingestion.cli ingest docs/playbook.pdf \\
      --name "Sales Playbook" \\
      --department sales \\
      --sensitivity confidential

Valid departments: engineering, sales, hr, general
Valid sensitivity levels: public, internal, confidential
        """
    )
    
    parser.add_argument(
        "command",
        choices=["ingest"],
        help="Command to run"
    )
    
    parser.add_argument(
        "file",
        help="Path to PDF file"
    )
    
    parser.add_argument(
        "--name",
        required=True,
        help="Document name/title"
    )
    
    parser.add_argument(
        "--department",
        required=True,
        help="Department name (must exist in database)"
    )
    
    parser.add_argument(
        "--sensitivity",
        required=True,
        choices=["public", "internal", "confidential"],
        help="Document sensitivity level"
    )
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        ingest_document(
            file_path=args.file,
            document_name=args.name,
            department=args.department,
            sensitivity=args.sensitivity
        )


if __name__ == "__main__":
    main()
