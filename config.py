"""
Central configuration management for the Business Transcript Analyzer.
Handles environment variables, paths, and application settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "ollama"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # Custom base URL for Groq or other APIs
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Embedding Configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")  # Default to local now
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")  # Fast local model
OPENAI_EMBEDDING_BASE_URL = os.getenv("OPENAI_EMBEDDING_BASE_URL")  # Separate for embeddings

# Vector Store Configuration
VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "faiss")  # "faiss" or "chroma"
FAISS_INDEX_PATH = VECTOR_STORE_DIR / "index.faiss"
FAISS_METADATA_PATH = VECTOR_STORE_DIR / "metadata.pkl"

# News API Configuration
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Processing Configuration
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
SUPPORTED_FORMATS = [".txt", ".pdf", ".docx"]

# Validation
if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    print("⚠️  Warning: OPENAI_API_KEY not set. LLM features will not work.")
    print("   Please set it in your .env file or use OLLAMA as LLM_PROVIDER.")
