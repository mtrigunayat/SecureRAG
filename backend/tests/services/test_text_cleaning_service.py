"""
Tests for text cleaning service
"""
import pytest

from app.services.text_cleaning_service import TextCleaningService
from app.schemas.ingestion import ExtractedPage


class TestTextCleaningService:
    """Tests for text cleaning service."""
    
    @pytest.fixture
    def cleaner(self):
        """Create text cleaner instance."""
        return TextCleaningService()
    
    def test_clean_normalizes_line_endings(self, cleaner):
        """Test that line endings are normalized to Unix style."""
        text = "Line 1\r\nLine 2\rLine 3\nLine 4"
        cleaned = cleaner.clean_text(text)
        
        assert '\r\n' not in cleaned
        assert '\r' not in cleaned
        assert cleaned.count('\n') == 3
    
    def test_clean_normalizes_tabs_to_spaces(self, cleaner):
        """Test that tabs are converted to spaces."""
        text = "Column1\tColumn2\tColumn3"
        cleaned = cleaner.clean_text(text)
        
        assert '\t' not in cleaned
        assert 'Column1 Column2 Column3' == cleaned
    
    def test_clean_removes_excessive_blank_lines(self, cleaner):
        """Test that multiple blank lines are collapsed to single."""
        text = "Line 1\n\n\n\nLine 2\n\n\n\nLine 3"
        cleaned = cleaner.clean_text(text)
        
        # Should have at most one blank line between content
        assert '\n\n\n' not in cleaned
        assert 'Line 1\n\nLine 2\n\nLine 3' == cleaned
    
    def test_clean_normalizes_multiple_spaces(self, cleaner):
        """Test that multiple spaces are reduced to single space."""
        text = "Word1    Word2     Word3"
        cleaned = cleaner.clean_text(text)
        
        assert cleaned == "Word1 Word2 Word3"
    
    def test_clean_removes_trailing_whitespace(self, cleaner):
        """Test that trailing whitespace is removed."""
        text = "  Leading and trailing  \n  spaces  \n  everywhere  "
        cleaned = cleaner.clean_text(text)
        
        assert cleaned.startswith("Leading")
        assert cleaned.endswith("everywhere")
        assert not cleaned.endswith(" ")
    
    def test_clean_preserves_meaningful_content(self, cleaner):
        """Test that meaningful content is preserved."""
        text = "This is important text. Keep the punctuation!"
        cleaned = cleaner.clean_text(text)
        
        assert "important" in cleaned
        assert "punctuation!" in cleaned
        assert "." in cleaned
    
    def test_clean_empty_text_returns_empty(self, cleaner):
        """Test that empty text returns empty."""
        assert cleaner.clean_text("") == ""
        assert cleaner.clean_text("   ") == ""
        assert cleaner.clean_text("\n\n\n") == ""
    
    def test_clean_is_deterministic(self, cleaner):
        """Test that cleaning produces deterministic results."""
        text = "  Sample   text  \n\n\n  with   issues  "
        
        result1 = cleaner.clean_text(text)
        result2 = cleaner.clean_text(text)
        
        assert result1 == result2
    
    def test_clean_pages_success(self, cleaner):
        """Test cleaning multiple pages."""
        pages = [
            ExtractedPage(page_number=1, text="  Page 1  \n\n\n  text  "),
            ExtractedPage(page_number=2, text="  Page 2  \n\n  text  "),
        ]
        
        cleaned_pages = cleaner.clean_pages(pages)
        
        assert len(cleaned_pages) == 2
        assert cleaned_pages[0].page_number == 1
        assert cleaned_pages[1].page_number == 2
        assert "Page 1" in cleaned_pages[0].text
        assert "Page 2" in cleaned_pages[1].text
        assert "\n\n\n" not in cleaned_pages[0].text
    
    def test_clean_preserves_page_structure(self, cleaner):
        """Test that page structure is preserved."""
        pages = [
            ExtractedPage(page_number=1, text="Page 1"),
            ExtractedPage(page_number=2, text=""),
            ExtractedPage(page_number=3, text="Page 3"),
        ]
        
        cleaned_pages = cleaner.clean_pages(pages)
        
        assert len(cleaned_pages) == 3
        assert cleaned_pages[0].page_number == 1
        assert cleaned_pages[1].page_number == 2
        assert cleaned_pages[2].page_number == 3
