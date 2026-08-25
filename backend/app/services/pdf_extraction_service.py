"""
PDF text extraction service

Extracts text from PDF files while preserving page information.
"""
from pathlib import Path
from typing import List, Union

from pypdf import PdfReader

from app.schemas.ingestion import ExtractedPage
from app.core.errors import InvalidPDFError, EmptyDocumentError, TextExtractionError
from app.core.logging import get_logger

logger = get_logger(__name__)


class PDFExtractionService:
    """
    Service for extracting text from PDF files.
    
    Preserves page boundaries for source attribution in RAG responses.
    """
    
    def extract_text(self, file_path: Union[str, Path]) -> List[ExtractedPage]:
        """
        Extract text from PDF file, preserving page information.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of ExtractedPage objects, one per page
            
        Raises:
            InvalidPDFError: If PDF is invalid or cannot be parsed
            EmptyDocumentError: If no extractable text found (image-only PDF)
            TextExtractionError: If extraction fails
            
        Security:
            - PDF content is treated as untrusted data
            - Text is never executed or interpreted as instructions
            - Extraction errors are caught and logged safely
        """
        file_path = Path(file_path)
        
        logger.info(f"Extracting text from PDF: {file_path.name}")
        
        try:
            reader = PdfReader(str(file_path))
        except Exception as e:
            logger.error(f"Failed to open PDF {file_path.name}: {e}")
            raise InvalidPDFError(f"Cannot read PDF: {str(e)}")
        
        # Extract text from each page
        extracted_pages: List[ExtractedPage] = []
        total_text_length = 0
        
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text()
                
                # Handle empty pages gracefully
                if text:
                    extracted_pages.append(ExtractedPage(
                        page_number=page_num,
                        text=text
                    ))
                    total_text_length += len(text)
                else:
                    logger.debug(f"Page {page_num} is empty")
                    # Still add empty page to preserve page numbering
                    extracted_pages.append(ExtractedPage(
                        page_number=page_num,
                        text=""
                    ))
                    
            except Exception as e:
                logger.error(f"Failed to extract text from page {page_num}: {e}")
                raise TextExtractionError(f"Page {page_num}: {str(e)}")
        
        # Validate that we extracted some text
        if total_text_length == 0:
            logger.warning(f"No text extracted from {file_path.name} - may be image-only PDF")
            raise EmptyDocumentError()
        
        logger.info(
            f"Extracted {total_text_length} characters from "
            f"{len(extracted_pages)} pages in {file_path.name}"
        )
        
        return extracted_pages
