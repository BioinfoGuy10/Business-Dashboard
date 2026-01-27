"""
File ingestion module for Business Transcript Analyzer.
Handles file uploads, text extraction from multiple formats, and local storage.
"""

import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import re

# Document processing imports
import pdfplumber
from docx import Document

# Local imports
import sys
sys.path.append(str(Path(__file__).parent.parent))
import config


def get_file_hash(filepath: Path) -> str:
    """
    Generate SHA-256 hash of a file for duplicate detection.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Hex string of file hash
    """
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read file in chunks for memory efficiency
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text with normalized whitespace
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Normalize line breaks
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text


def extract_text_from_txt(filepath: Path) -> str:
    """
    Extract text from a plain text file.
    
    Args:
        filepath: Path to .txt file
        
    Returns:
        Extracted text content
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Fallback to latin-1 encoding if utf-8 fails
        with open(filepath, 'r', encoding='latin-1') as f:
            return f.read()


def extract_text_from_pdf(filepath: Path) -> str:
    """
    Extract text from a PDF file using pdfplumber.
    
    Args:
        filepath: Path to .pdf file
        
    Returns:
        Extracted text content from all pages
    """
    text_content = []
    
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
        
        return "\n\n".join(text_content)
    
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")


def extract_text_from_docx(filepath: Path) -> str:
    """
    Extract text from a Word document (.docx).
    
    Args:
        filepath: Path to .docx file
        
    Returns:
        Extracted text content from all paragraphs
    """
    try:
        doc = Document(filepath)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)
    
    except Exception as e:
        raise Exception(f"Error extracting text from DOCX: {str(e)}")


def check_duplicate(file_hash: str) -> Optional[str]:
    """
    Check if a file with this hash already exists in the transcripts directory.
    
    Args:
        file_hash: SHA-256 hash of the file
        
    Returns:
        Filename of existing file if duplicate found, None otherwise
    """
    for existing_file in config.TRANSCRIPTS_DIR.glob("*"):
        if existing_file.is_file():
            try:
                existing_hash = get_file_hash(existing_file)
                if existing_hash == file_hash:
                    return existing_file.name
            except Exception:
                continue
    return None


def process_upload(uploaded_file, file_content: bytes = None) -> Dict:
    """
    Main entry point for processing uploaded files.
    Handles file validation, text extraction, and storage.
    
    Args:
        uploaded_file: Streamlit UploadedFile object or file path
        file_content: Optional bytes content (for Streamlit uploads)
        
    Returns:
        Dictionary containing:
            - success: bool
            - message: str
            - data: dict with metadata and extracted text (if successful)
            - error: str (if failed)
    """
    try:
        # Handle different input types
        if hasattr(uploaded_file, 'name'):
            # Streamlit UploadedFile object
            filename = uploaded_file.name
            file_size_mb = uploaded_file.size / (1024 * 1024)
        else:
            # File path (for testing)
            filepath = Path(uploaded_file)
            filename = filepath.name
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
        
        # Validate file format
        file_ext = Path(filename).suffix.lower()
        if file_ext not in config.SUPPORTED_FORMATS:
            return {
                "success": False,
                "message": f"Unsupported file format: {file_ext}",
                "error": f"Supported formats: {', '.join(config.SUPPORTED_FORMATS)}"
            }
        
        # Validate file size
        if file_size_mb > config.MAX_FILE_SIZE_MB:
            return {
                "success": False,
                "message": f"File too large: {file_size_mb:.2f}MB",
                "error": f"Maximum file size: {config.MAX_FILE_SIZE_MB}MB"
            }
        
        # Create temporary file path
        temp_path = config.TRANSCRIPTS_DIR / filename
        
        # Save uploaded file
        if hasattr(uploaded_file, 'read'):
            # Streamlit UploadedFile
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.read())
        else:
            # Copy from source path
            shutil.copy2(uploaded_file, temp_path)
        
        # Check for duplicates
        file_hash = get_file_hash(temp_path)
        duplicate_file = check_duplicate(file_hash)
        
        if duplicate_file and duplicate_file != filename:
            return {
                "success": False,
                "message": f"Duplicate file detected",
                "error": f"This file already exists as: {duplicate_file}",
                "is_duplicate": True
            }
        
        # Extract text based on file type
        if file_ext == '.pdf':
            raw_text = extract_text_from_pdf(temp_path)
        elif file_ext == '.docx':
            raw_text = extract_text_from_docx(temp_path)
        elif file_ext == '.txt':
            raw_text = extract_text_from_txt(temp_path)
        else:
            return {
                "success": False,
                "message": "Unknown file format",
                "error": f"File extension {file_ext} not recognized"
            }
        
        # Clean the extracted text
        cleaned_text = clean_text(raw_text)
        
        if not cleaned_text or len(cleaned_text) < 50:
            return {
                "success": False,
                "message": "Insufficient text content",
                "error": "The file appears to be empty or contains too little text"
            }
        
        # Prepare metadata
        metadata = {
            "filename": filename,
            "file_type": file_ext,
            "file_size_mb": round(file_size_mb, 2),
            "file_hash": file_hash,
            "upload_date": datetime.now().isoformat(),
            "character_count": len(cleaned_text),
            "word_count": len(cleaned_text.split()),
            "filepath": str(temp_path)
        }
        
        return {
            "success": True,
            "message": f"Successfully processed {filename}",
            "data": {
                "text": cleaned_text,
                "metadata": metadata
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": "Error processing file",
            "error": str(e)
        }


def get_all_transcripts() -> list:
    """
    Get list of all stored transcript files.
    
    Returns:
        List of dictionaries with file information
    """
    transcripts = []
    
    for filepath in config.TRANSCRIPTS_DIR.glob("*"):
        if filepath.is_file() and filepath.suffix in config.SUPPORTED_FORMATS:
            transcripts.append({
                "filename": filepath.name,
                "file_type": filepath.suffix,
                "file_size_mb": round(filepath.stat().st_size / (1024 * 1024), 2),
                "modified_date": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
                "filepath": str(filepath)
            })
    
    # Sort by modified date (newest first)
    transcripts.sort(key=lambda x: x["modified_date"], reverse=True)
    
    return transcripts


if __name__ == "__main__":
    # Test the module
    print("🔧 Testing ingestion module...")
    print(f"✓ Transcripts directory: {config.TRANSCRIPTS_DIR}")
    print(f"✓ Supported formats: {config.SUPPORTED_FORMATS}")
    print(f"✓ Max file size: {config.MAX_FILE_SIZE_MB}MB")
    
    # Test text cleaning
    test_text = "  This   is   a  test\n\n\n\nwith    extra    whitespace  "
    cleaned = clean_text(test_text)
    print(f"\n✓ Text cleaning works: '{cleaned}'")
    
    print("\n✅ Ingestion module ready!")
