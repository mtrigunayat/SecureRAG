"""
Content hashing utilities

Provides deterministic content hashing for duplicate detection and re-ingestion.
"""
import hashlib
from pathlib import Path
from typing import Union

from app.core.logging import get_logger

logger = get_logger(__name__)


def hash_file_content(file_path: Union[str, Path]) -> str:
    """
    Calculate SHA-256 hash of file content.
    
    Args:
        file_path: Path to file
        
    Returns:
        Hexadecimal SHA-256 hash string
        
    Raises:
        FileNotFoundError: If file does not exist
        IOError: If file cannot be read
        
    Note:
        Uses streaming to handle large files efficiently.
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Not a file: {file_path}")
    
    sha256_hash = hashlib.sha256()
    
    # Stream file in chunks to handle large files
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    
    hash_value = sha256_hash.hexdigest()
    logger.debug(f"Calculated content hash for {file_path.name}: {hash_value[:16]}...")
    
    return hash_value


def hash_text_content(text: str) -> str:
    """
    Calculate SHA-256 hash of text content.
    
    Args:
        text: Text content
        
    Returns:
        Hexadecimal SHA-256 hash string
        
    Note:
        Uses UTF-8 encoding for deterministic hashing.
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(text.encode('utf-8'))
    hash_value = sha256_hash.hexdigest()
    
    logger.debug(f"Calculated text hash: {hash_value[:16]}...")
    
    return hash_value
