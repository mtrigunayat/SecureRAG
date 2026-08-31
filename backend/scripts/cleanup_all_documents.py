"""
Cleanup script - Delete ALL documents and vectors

This script will:
1. Delete all vectors from Qdrant
2. Delete all documents from PostgreSQL
3. Reset the system to a clean state

WARNING: This is irreversible!

Usage:
    python scripts/cleanup_all_documents.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logging import setup_logging, get_logger
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.qdrant_service import get_qdrant_service
from app.core.config import settings

setup_logging()
logger = get_logger(__name__)


def cleanup_all():
    """Delete all documents and vectors."""
    
    print("=" * 60)
    print("WARNING: This will delete ALL documents and vectors!")
    print("=" * 60)
    
    # Ask for confirmation
    response = input("\nType 'DELETE ALL' to confirm: ")
    if response != "DELETE ALL":
        print("❌ Cancelled - no changes made")
        return
    
    print("\n🗑️  Starting cleanup...\n")
    
    # Step 1: Delete all vectors from Qdrant
    print("Step 1: Deleting vectors from Qdrant...")
    try:
        qdrant = get_qdrant_service()
        collection_name = settings.qdrant_collection_name
        
        # Delete the entire collection and recreate it
        try:
            qdrant.client.delete_collection(collection_name)
            logger.info(f"Deleted Qdrant collection: {collection_name}")
            print(f"  ✓ Deleted collection '{collection_name}'")
        except Exception as e:
            logger.warning(f"Collection doesn't exist or error deleting: {e}")
            print(f"  ℹ️  Collection didn't exist or was already empty")
        
        # Recreate empty collection
        from qdrant_client.models import Distance, VectorParams
        qdrant.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Recreated empty collection: {collection_name}")
        print(f"  ✓ Recreated empty collection")
        
    except Exception as e:
        logger.error(f"Error cleaning Qdrant: {e}", exc_info=True)
        print(f"  ❌ Error: {e}")
        return
    
    # Step 2: Delete all documents from PostgreSQL
    print("\nStep 2: Deleting documents from PostgreSQL...")
    db = SessionLocal()
    try:
        # Count before deletion
        count_before = db.query(Document).count()
        print(f"  Found {count_before} documents")
        
        # Delete all documents
        db.query(Document).delete()
        db.commit()
        
        count_after = db.query(Document).count()
        print(f"  ✓ Deleted {count_before} documents")
        print(f"  Remaining: {count_after} documents")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning PostgreSQL: {e}", exc_info=True)
        print(f"  ❌ Error: {e}")
        return
    finally:
        db.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 60)
    print("\nYour system is now clean and ready for new documents.")
    print("\nNext steps:")
    print("  1. Place your PDF files in documents/ folders")
    print("  2. Create your my_documents.json config")
    print("  3. Run: python scripts/ingest_documents.py --batch my_documents.json")
    print("\nSee QUICK_START_INGESTION.md for details.")
    print("=" * 60)


def verify_cleanup():
    """Verify that cleanup was successful."""
    print("\n🔍 Verifying cleanup...\n")
    
    # Check PostgreSQL
    db = SessionLocal()
    try:
        doc_count = db.query(Document).count()
        if doc_count == 0:
            print("✓ PostgreSQL: 0 documents (clean)")
        else:
            print(f"⚠️  PostgreSQL: {doc_count} documents remain")
    finally:
        db.close()
    
    # Check Qdrant
    try:
        qdrant = get_qdrant_service()
        collection_info = qdrant.client.get_collection(settings.qdrant_collection_name)
        vector_count = collection_info.points_count
        if vector_count == 0:
            print("✓ Qdrant: 0 vectors (clean)")
        else:
            print(f"⚠️  Qdrant: {vector_count} vectors remain")
    except Exception as e:
        print(f"⚠️  Qdrant: Could not verify ({e})")
    
    print()


def main():
    """Main entry point."""
    cleanup_all()
    verify_cleanup()


if __name__ == "__main__":
    main()
