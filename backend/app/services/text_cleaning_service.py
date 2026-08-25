"""
Text cleaning service

Normalizes and cleans extracted text from PDFs.
"""
import re
from typing import List

from app.schemas.ingestion import ExtractedPage
from app.core.logging import get_logger

logger = get_logger(__name__)


class TextCleaningService:
    """
    Service for cleaning and normalizing extracted text.
    
    Handles common PDF extraction artifacts while preserving
    meaningful content and structure.
    
    Philosophy:
        - Conservative cleaning (preserve meaning)
        - No AI rewriting
        - No summarization
        - Deterministic output
    """
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
            
        Cleaning steps:
            1. Normalize line endings to Unix style
            2. Remove excessive blank lines (max 1 blank line)
            3. Normalize whitespace (tabs → spaces, multiple spaces → single)
            4. Remove trailing/leading whitespace per line
            5. Remove overall leading/trailing whitespace
            
        Note:
            - Does NOT remove punctuation
            - Does NOT change casing
            - Does NOT rewrite content
            - Does NOT use LLM
        """
        if not text:
            return ""
        
        # 1. Normalize line endings to Unix style
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 2. Normalize tabs to spaces
        text = text.replace('\t', ' ')
        
        # 3. Remove trailing whitespace from each line
        lines = [line.rstrip() for line in text.split('\n')]
        
        # 4. Remove excessive blank lines (collapse multiple blank lines to single)
        cleaned_lines = []
        prev_blank = False
        for line in lines:
            is_blank = len(line.strip()) == 0
            if is_blank:
                if not prev_blank:
                    cleaned_lines.append('')
                prev_blank = True
            else:
                cleaned_lines.append(line)
                prev_blank = False
        
        # 5. Join lines
        text = '\n'.join(cleaned_lines)
        
        # 6. Normalize multiple spaces to single space within lines
        # But preserve intentional line breaks
        text = re.sub(r' +', ' ', text)
        
        # 7. Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def clean_pages(self, pages: List[ExtractedPage]) -> List[ExtractedPage]:
        """
        Clean text from all pages.
        
        Args:
            pages: List of extracted pages
            
        Returns:
            List of pages with cleaned text
            
        Note:
            Preserves page structure and numbering.
        """
        logger.info(f"Cleaning text from {len(pages)} pages")
        
        cleaned_pages = [
            ExtractedPage(
                page_number=page.page_number,
                text=self.clean_text(page.text)
            )
            for page in pages
        ]
        
        # Calculate statistics
        original_chars = sum(len(p.text) for p in pages)
        cleaned_chars = sum(len(p.text) for p in cleaned_pages)
        
        logger.info(
            f"Cleaned {original_chars} → {cleaned_chars} characters "
            f"({cleaned_chars - original_chars:+d})"
        )
        
        return cleaned_pages
