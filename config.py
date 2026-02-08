"""
Central configuration management for the Business Transcript Analyzer.
Handles environment variables, paths, and application settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Streamlit Secrets Support
import streamlit as st

def get_config(key, default=None):
    """Get configuration from env vars or streamlit secrets."""
    # 1. Try environment variable
    value = os.getenv(key)
    if value is not None:
        return value
    
    # 2. Try Streamlit secrets
    try:
        # Direct match
        if key in st.secrets:
            return st.secrets[key]
            
        # Case-insensitive match for root keys
        # e.g. 'openai_api_key' in secrets maps to 'OPENAI_API_KEY' request
        for secret_key in st.secrets:
            if secret_key.lower() == key.lower():
                return st.secrets[secret_key]

        # Check for nested secrets (e.g. OPENAI.API_KEY)
        parts = key.split('_')
        if len(parts) > 1:
            section = parts[0]
            subsection = '_'.join(parts[1:])
            
            # Check for section match (case-insensitive)
            for secret_section in st.secrets:
                if secret_section.lower() == section.lower():
                    # Check for subsection match in this section
                    section_data = st.secrets[secret_section]
                    if isinstance(section_data, dict): # Ensure it is a dict
                         if subsection in section_data:
                             return section_data[subsection]
                         # Case-insensitive subsection
                         for sub_key in section_data:
                             if sub_key.lower() == subsection.lower():
                                 return section_data[sub_key]
    except Exception as e:
        print(f"Error accessing secrets for {key}: {e}")
        
    print(f"⚠️ Config key '{key}' not found in env or secrets.")
    return default

# Base Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
INSIGHTS_DIR = DATA_DIR / "insights"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
EXAMPLES_DIR = BASE_DIR / "examples"

# Create directories if they don't exist
for dir_path in [TRANSCRIPTS_DIR, INSIGHTS_DIR, VECTOR_STORE_DIR, EXAMPLES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# LLM Configuration
LLM_PROVIDER = get_config("LLM_PROVIDER", "openai")  # "openai" or "ollama"
OPENAI_API_KEY = get_config("OPENAI_API_KEY")
OPENAI_BASE_URL = get_config("OPENAI_BASE_URL")  # Custom base URL for Groq or other APIs
OPENAI_MODEL = get_config("OPENAI_MODEL", "gpt-3.5-turbo")
OLLAMA_MODEL = get_config("OLLAMA_MODEL", "llama2")
OLLAMA_BASE_URL = get_config("OLLAMA_BASE_URL", "http://localhost:11434")

# Embedding Configuration
EMBEDDING_PROVIDER = get_config("EMBEDDING_PROVIDER", "local")  # Default to local now
EMBEDDING_MODEL = get_config("EMBEDDING_MODEL", "all-MiniLM-L6-v2")  # Fast local model
OPENAI_EMBEDDING_BASE_URL = get_config("OPENAI_EMBEDDING_BASE_URL")  # Separate for embeddings

# Vector Store Configuration
VECTOR_STORE_TYPE = get_config("VECTOR_STORE_TYPE", "faiss")  # "faiss" or "chroma"
FAISS_INDEX_PATH = VECTOR_STORE_DIR / "index.faiss"
FAISS_METADATA_PATH = VECTOR_STORE_DIR / "metadata.pkl"

# News API Configuration
NEWS_API_KEY = get_config("NEWS_API_KEY")

# Processing Configuration
MAX_FILE_SIZE_MB = int(get_config("MAX_FILE_SIZE_MB", "10"))
SUPPORTED_FORMATS = [".txt", ".pdf", ".docx"]

# Validation
if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    print("⚠️  Warning: OPENAI_API_KEY not set. LLM features will not work.")
    print("   Please set it in your .env file or use OLLAMA as LLM_PROVIDER.")
