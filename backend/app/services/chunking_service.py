"""
Document chunking service

Splits cleaned text into chunks for embedding and retrieval.
"""
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.schemas.ingestion import ExtractedPage, DocumentChunk
from app.core.config import settings
from app.core.errors import ChunkingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChunkingService:
    """
    Service for chunking documents using RecursiveCharacterTextSplitter.
    
    Configuration:
        - chunk_size: Target chunk size in characters (default: 600)
        - chunk_overlap: Overlap between chunks in characters (default: 100)
        
    Strategy:
        - Preserves page information for source attribution
        - Creates deterministic chunk IDs (document_id + chunk_index)
        - Maintains chunk ordering
        - Handles page-spanning chunks
    """
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """
        Initialize chunking service.
        
        Args:
            chunk_size: Target chunk size (uses config default if None)
            chunk_overlap: Chunk overlap (uses config default if None)
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        logger.info(
            f"Initialized chunking service: size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}"
        )
        
        # Create text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
    
    def chunk_document(
        self,
        pages: List[ExtractedPage],
        document_id: int,
        document_name: str,
        department_id: int,
        department_name: str,
        sensitivity: str
    ) -> List[DocumentChunk]:
        """
        Chunk document pages into retrievable chunks.
        
        Args:
            pages: List of cleaned extracted pages
            document_id: PostgreSQL document ID
            document_name: Document name
            department_id: Department ID (for ACL)
            department_name: Department name (for display)
            sensitivity: Document sensitivity level
            
        Returns:
            List of document chunks with metadata
            
        Raises:
            ChunkingError: If chunking fails
            
        Note:
            - Preserves page information for each chunk
            - Chunks may span multiple pages
            - Empty chunks are filtered out
            - Chunk IDs are deterministic: f"{document_id}_{chunk_index}"
        """
        logger.info(
            f"Chunking document '{document_name}' (ID={document_id}): "
            f"{len(pages)} pages"
        )
        
        try:
            # Build page-aware text with markers
            # Format: page text with newlines preserved
            # We'll track which characters belong to which pages
            full_text = ""
            page_boundaries = []  # List of (start_char, end_char, page_num)
            current_pos = 0
            
            for page in pages:
                if not page.text:
                    continue
                
                start_pos = current_pos
                full_text += page.text
                end_pos = current_pos + len(page.text)
                page_boundaries.append((start_pos, end_pos, page.page_number))
                current_pos = end_pos
                
                # Add separator between pages (unless last page)
                if page != pages[-1]:
                    full_text += "\n\n"
                    current_pos += 2
            
            if not full_text.strip():
                logger.warning(f"Document '{document_name}' has no text after cleaning")
                return []
            
            # Split text into chunks
            chunk_texts = self.text_splitter.split_text(full_text)
            
            # Create DocumentChunk objects with metadata
            chunks = []
            current_search_pos = 0
            
            for chunk_index, chunk_text in enumerate(chunk_texts):
                # Skip empty chunks
                if not chunk_text.strip():
                    continue
                
                # Find where this chunk appears in the full text
                chunk_start = full_text.find(chunk_text, current_search_pos)
                if chunk_start == -1:
                    # Fallback: use current position
                    chunk_start = current_search_pos
                chunk_end = chunk_start + len(chunk_text)
                current_search_pos = chunk_start + 1
                
                # Determine which pages this chunk spans
                page_start = None
                page_end = None
                
                for start, end, page_num in page_boundaries:
                    # Chunk overlaps with this page if:
                    # chunk_start < page_end AND chunk_end > page_start
                    if chunk_start < end and chunk_end > start:
                        if page_start is None:
                            page_start = page_num
                        page_end = page_num
                
                # Fallback if we couldn't determine pages
                if page_start is None:
                    page_start = 1
                    page_end = len(pages)
                
                # Create deterministic chunk ID
                chunk_id = f"{document_id}_{chunk_index}"
                
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_name=document_name,
                    department_id=department_id,
                    department_name=department_name,
                    sensitivity=sensitivity,
                    page_start=page_start,
                    page_end=page_end,
                    chunk_index=chunk_index,
                    text=chunk_text.strip()
                )
                
                chunks.append(chunk)
            
            logger.info(
                f"Created {len(chunks)} chunks for document '{document_name}' "
                f"({len(full_text)} characters)"
            )
            
            return chunks
            
        except Exception as e:
            logger.error(f"Chunking failed for document '{document_name}': {e}")
            raise ChunkingError(str(e))
