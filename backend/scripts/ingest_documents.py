"""
Document ingestion script

Ingest PDF documents into the system with automatic embedding and indexing.

Usage:
    python scripts/ingest_documents.py <pdf_path> --name "Document Name" --department engineering --sensitivity internal

Example:
    python scripts/ingest_documents.py docs/my_document.pdf --name "API Documentation" --department engineering --sensitivity internal
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logging import setup_logging, get_logger
from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService
from app.services.vector_indexing_service import VectorIndexingService
from app.core.errors import (
    UnsupportedFileError,
    DepartmentNotFoundError,
    InvalidSensitivityError,
    IngestionError
)

setup_logging()
logger = get_logger(__name__)


def ingest_document(
    file_path: str,
    document_name: str,
    department_name: str,
    sensitivity: str
) -> None:
    """
    Ingest a single document through the complete pipeline.
    
    Args:
        file_path: Path to PDF file
        document_name: Document name/title
        department_name: Department (engineering/sales/hr/general)
        sensitivity: Sensitivity level (public/internal/confidential)
    """
    db = SessionLocal()
    try:
        # Step 1: Ingest document (PDF → chunks)
        logger.info(f"Step 1: Ingesting {file_path}...")
        ingestion_service = IngestionService(db)
        ingestion_result = ingestion_service.ingest_document(
            file_path=file_path,
            document_name=document_name,
            department_name=department_name,
            sensitivity=sensitivity
        )
        
        if ingestion_result.status == "UNCHANGED_SKIP_INGESTION":
            logger.info(f"Document unchanged (hash match) - skipping embedding")
            print(f"✓ Document '{document_name}' already indexed (ID={ingestion_result.document_id})")
            return
        
        logger.info(
            f"Ingestion complete: {ingestion_result.page_count} pages, "
            f"{ingestion_result.chunk_count} chunks"
        )
        
        # Step 2: Generate embeddings and index in Qdrant
        logger.info(f"Step 2: Generating embeddings and indexing in Qdrant...")
        indexing_service = VectorIndexingService(db)
        indexing_result = indexing_service.index_document(ingestion_result)
        
        logger.info(
            f"Indexing complete: {indexing_result.vector_count} vectors indexed"
        )
        
        # Success summary
        print(f"\n✓ SUCCESS: Document '{document_name}' ingested and indexed")
        print(f"  - Document ID: {ingestion_result.document_id}")
        print(f"  - Department: {department_name}")
        print(f"  - Sensitivity: {sensitivity}")
        print(f"  - Pages: {ingestion_result.page_count}")
        print(f"  - Chunks: {ingestion_result.chunk_count}")
        print(f"  - Vectors: {indexing_result.vector_count}")
        print(f"  - Collection: {indexing_result.collection_name}")
        
    except UnsupportedFileError as e:
        logger.error(f"Unsupported file type: {e.message}")
        print(f"✗ ERROR: {e.message}")
        print(f"  Only PDF files are currently supported")
        sys.exit(1)
    
    except DepartmentNotFoundError as e:
        logger.error(f"Department not found: {e.message}")
        print(f"✗ ERROR: {e.message}")
        print(f"  Valid departments: engineering, sales, hr, general")
        sys.exit(1)
    
    except InvalidSensitivityError as e:
        logger.error(f"Invalid sensitivity: {e.message}")
        print(f"✗ ERROR: {e.message}")
        print(f"  Valid sensitivity levels: public, internal, confidential")
        sys.exit(1)
    
    except IngestionError as e:
        logger.error(f"Ingestion error: {e.message}")
        print(f"✗ ERROR: {e.message}")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"✗ ERROR: {e}")
        sys.exit(1)
    
    finally:
        db.close()


def ingest_batch(documents_file: str) -> None:
    """
    Ingest multiple documents from a configuration file.
    
    Args:
        documents_file: Path to JSON file with document list
        
    Example JSON format:
        [
            {
                "file_path": "docs/doc1.pdf",
                "name": "Document 1",
                "department": "engineering",
                "sensitivity": "internal"
            },
            {
                "file_path": "docs/doc2.pdf",
                "name": "Document 2",
                "department": "sales",
                "sensitivity": "confidential"
            }
        ]
    """
    import json
    
    with open(documents_file, 'r') as f:
        documents = json.load(f)
    
    total = len(documents)
    success = 0
    failed = 0
    
    print(f"Ingesting {total} documents...\n")
    
    for i, doc in enumerate(documents, 1):
        print(f"[{i}/{total}] Processing {doc['name']}...")
        try:
            ingest_document(
                file_path=doc['file_path'],
                document_name=doc['name'],
                department_name=doc['department'],
                sensitivity=doc['sensitivity']
            )
            success += 1
        except SystemExit:
            failed += 1
            print(f"  Skipping to next document...\n")
            continue
    
    print(f"\n{'='*60}")
    print(f"Batch ingestion complete:")
    print(f"  ✓ Success: {success}/{total}")
    print(f"  ✗ Failed: {failed}/{total}")
    print(f"{'='*60}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into SecureRAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Single document:
    python scripts/ingest_documents.py docs/api_guide.pdf \\
        --name "API Documentation" \\
        --department engineering \\
        --sensitivity internal

  Batch ingestion:
    python scripts/ingest_documents.py --batch documents.json

Valid departments: engineering, sales, hr, general
Valid sensitivity: public, internal, confidential
        """
    )
    
    parser.add_argument(
        "file_path",
        nargs="?",
        help="Path to PDF file to ingest"
    )
    
    parser.add_argument(
        "--name",
        help="Document name/title"
    )
    
    parser.add_argument(
        "--department",
        choices=["engineering", "sales", "hr", "general"],
        help="Department name"
    )
    
    parser.add_argument(
        "--sensitivity",
        choices=["public", "internal", "confidential"],
        help="Sensitivity level"
    )
    
    parser.add_argument(
        "--batch",
        help="Path to JSON file with multiple documents to ingest"
    )
    
    args = parser.parse_args()
    
    if args.batch:
        # Batch mode
        ingest_batch(args.batch)
    elif args.file_path and args.name and args.department and args.sensitivity:
        # Single document mode
        ingest_document(
            file_path=args.file_path,
            document_name=args.name,
            department_name=args.department,
            sensitivity=args.sensitivity
        )
    else:
        parser.print_help()
        print("\n✗ ERROR: Either provide all required arguments or use --batch")
        sys.exit(1)


if __name__ == "__main__":
    main()
