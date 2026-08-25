"""
Tests for content hashing utilities
"""
import pytest
from pathlib import Path
import tempfile

from app.utils.hashing import hash_file_content, hash_text_content


class TestHashFileContent:
    """Tests for file content hashing."""
    
    def test_hash_file_content_success(self, tmp_path):
        """Test hashing a file successfully."""
        # Create temporary file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        # Hash file
        hash_value = hash_file_content(test_file)
        
        # Verify hash
        assert len(hash_value) == 64  # SHA-256 produces 64 hex characters
        assert all(c in '0123456789abcdef' for c in hash_value)
    
    def test_hash_same_content_produces_same_hash(self, tmp_path):
        """Test that same content produces same hash."""
        content = "This is test content"
        
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text(content)
        file2.write_text(content)
        
        hash1 = hash_file_content(file1)
        hash2 = hash_file_content(file2)
        
        assert hash1 == hash2
    
    def test_hash_different_content_produces_different_hash(self, tmp_path):
        """Test that different content produces different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content A")
        file2.write_text("Content B")
        
        hash1 = hash_file_content(file1)
        hash2 = hash_file_content(file2)
        
        assert hash1 != hash2
    
    def test_hash_file_not_found(self):
        """Test hashing nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            hash_file_content("nonexistent_file.txt")
    
    def test_hash_directory_raises_error(self, tmp_path):
        """Test hashing a directory raises error."""
        with pytest.raises(ValueError, match="Not a file"):
            hash_file_content(tmp_path)


class TestHashTextContent:
    """Tests for text content hashing."""
    
    def test_hash_text_content_success(self):
        """Test hashing text successfully."""
        text = "Hello, World!"
        hash_value = hash_text_content(text)
        
        assert len(hash_value) == 64
        assert all(c in '0123456789abcdef' for c in hash_value)
    
    def test_hash_same_text_produces_same_hash(self):
        """Test that same text produces same hash."""
        text = "Test content"
        hash1 = hash_text_content(text)
        hash2 = hash_text_content(text)
        
        assert hash1 == hash2
    
    def test_hash_different_text_produces_different_hash(self):
        """Test that different text produces different hash."""
        hash1 = hash_text_content("Text A")
        hash2 = hash_text_content("Text B")
        
        assert hash1 != hash2
    
    def test_hash_empty_text(self):
        """Test hashing empty text."""
        hash_value = hash_text_content("")
        assert len(hash_value) == 64
    
    def test_hash_unicode_text(self):
        """Test hashing Unicode text."""
        text = "Hello 世界 🌍"
        hash_value = hash_text_content(text)
        assert len(hash_value) == 64
