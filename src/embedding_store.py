"""
Vector storage and semantic search module using FAISS.
Enables semantic search across all transcripts using embeddings.
"""

import pickle
import sys
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

# Vector storage imports
import faiss
from openai import OpenAI

# Local imports
sys.path.append(str(Path(__file__).parent.parent))
import config


class EmbeddingStore:
    """
    Manages FAISS vector store for semantic search over transcripts.
    """
    
    def __init__(self):
        """Initialize the embedding store, loading existing index if available."""
        self.index = None
        self.metadata = []  # List of metadata dicts for each document
        self.openai_client = None
        self.local_model = None
        
        # Initialize appropriate embedding provider
        if config.EMBEDDING_PROVIDER == "openai":
            self.dimension = 1536  # OpenAI ada-002 dimension
            if not config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY required for OpenAI embeddings")
            
            # Use separate base URL for embeddings (allows OpenAI embeddings with Groq LLM)
            client_kwargs = {"api_key": config.OPENAI_API_KEY}
            if config.OPENAI_EMBEDDING_BASE_URL:
                client_kwargs["base_url"] = config.OPENAI_EMBEDDING_BASE_URL
            
            self.openai_client = OpenAI(**client_kwargs)
        elif config.EMBEDDING_PROVIDER == "local":
            print(f"📦 Loading local embedding model: {config.EMBEDDING_MODEL}...")
            from sentence_transformers import SentenceTransformer
            self.local_model = SentenceTransformer(config.EMBEDDING_MODEL)
            # Get dimension from the model itself
            self.dimension = self.local_model.get_sentence_embedding_dimension()
            print(f"✓ Local model loaded (Dimension: {self.dimension})")
        else:
            raise ValueError(f"Unsupported embedding provider: {config.EMBEDDING_PROVIDER}")
        
        # Load existing index if available
        self.load_index()
    
    def _create_new_index(self):
        """Create a new FAISS index."""
        # Using L2 (Euclidean) distance
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        print("✓ Created new FAISS index")
    
    def save_index(self):
        """Save FAISS index and metadata to disk."""
        try:
            faiss.write_index(self.index, str(config.FAISS_INDEX_PATH))
            with open(config.FAISS_METADATA_PATH, 'wb') as f:
                pickle.dump(self.metadata, f)
            print(f"💾 Saved index with {len(self.metadata)} documents")
        except Exception as e:
            print(f"❌ Error saving index: {e}")
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text using the selected provider.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of embedding vector
        """
        try:
            if config.EMBEDDING_PROVIDER == "openai":
                # Truncate text if too long (OpenAI limit is ~8k tokens)
                text = text[:8000]
                
                response = self.openai_client.embeddings.create(
                    model=config.EMBEDDING_MODEL,
                    input=text
                )
                
                embedding = np.array(response.data[0].embedding, dtype=np.float32)
            else:
                # Use local model
                embedding = self.local_model.encode(text)
                embedding = np.array(embedding, dtype=np.float32)
                
            return embedding
        
        except Exception as e:
            raise Exception(f"Error generating embedding: {e}")
    
    def load_index(self):
        """Load existing FAISS index and metadata from disk."""
        if config.FAISS_INDEX_PATH.exists() and config.FAISS_METADATA_PATH.exists():
            try:
                self.index = faiss.read_index(str(config.FAISS_INDEX_PATH))
                # Check for dimension mismatch (e.g., switched from OpenAI to Local)
                if self.index.d != self.dimension:
                    print(f"⚠️  Index dimension mismatch ({self.index.d} vs {self.dimension}). Creating new index.")
                    self._create_new_index()
                    return

                with open(config.FAISS_METADATA_PATH, 'rb') as f:
                    self.metadata = pickle.load(f)
                print(f"✓ Loaded existing index with {len(self.metadata)} documents")
            except Exception as e:
                print(f"⚠️  Could not load existing index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def add_document(self, text: str, metadata: Dict) -> str:
        """
        Add a document to the vector store.
        
        Args:
            text: Full text content
            metadata: Document metadata (filename, date, etc.)
            
        Returns:
            Document ID (index position as string)
        """
        try:
            print(f"📝 Adding document to vector store: {metadata.get('filename', 'unknown')}")
            
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Add to FAISS index
            self.index.add(np.array([embedding]))
            
            # Store metadata
            doc_id = len(self.metadata)
            metadata['doc_id'] = doc_id
            metadata['text_preview'] = text[:500]  # Store preview for search results
            self.metadata.append(metadata)
            
            # Save updated index
            self.save_index()
            
            print(f"✅ Document added (ID: {doc_id})")
            return str(doc_id)
        
        except Exception as e:
            print(f"❌ Error adding document: {e}")
            raise
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """
        Perform semantic search over stored documents.
        
        Args:
            query: Search query text
            k: Number of results to return
            
        Returns:
            List of dictionaries with search results and metadata
        """
        try:
            if len(self.metadata) == 0:
                return []
            
            print(f"🔍 Searching for: '{query[:100]}...'")
            
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Search FAISS index
            k = min(k, len(self.metadata))  # Don't request more than available
            distances, indices = self.index.search(np.array([query_embedding]), k)
            
            # Compile results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):
                    result = {
                        'rank': i + 1,
                        'score': float(1 / (1 + distance)),  # Convert distance to similarity score
                        'distance': float(distance),
                        **self.metadata[idx]
                    }
                    results.append(result)
            
            print(f"✓ Found {len(results)} results")
            return results
        
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def get_all_documents(self) -> List[Dict]:
        """
        Retrieve all stored documents with metadata.
        
        Returns:
            List of all document metadata
        """
        return self.metadata.copy()
    
    def document_exists(self, filename: str) -> bool:
        """
        Check if a document already exists in the store.
        
        Args:
            filename: Filename to check
            
        Returns:
            True if document exists, False otherwise
        """
        for doc in self.metadata:
            if doc.get('filename') == filename:
                return True
        return False
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with store statistics
        """
        return {
            'total_documents': len(self.metadata),
            'index_size': self.index.ntotal if self.index else 0,
            'dimension': self.dimension
        }


# Module-level singleton instance
_store_instance = None


def initialize_store() -> EmbeddingStore:
    """
    Initialize or retrieve the global embedding store instance.
    
    Returns:
        EmbeddingStore instance
    """
    global _store_instance
    if _store_instance is None:
        _store_instance = EmbeddingStore()
    return _store_instance


def add_document(text: str, metadata: Dict) -> str:
    """
    Add a document to the global embedding store.
    
    Args:
        text: Document text
        metadata: Document metadata
        
    Returns:
        Document ID
    """
    store = initialize_store()
    return store.add_document(text, metadata)


def search(query: str, k: int = 5) -> List[Dict]:
    """
    Search the global embedding store.
    
    Args:
        query: Search query
        k: Number of results
        
    Returns:
        List of search results
    """
    store = initialize_store()
    return store.search(query, k)


def get_all_documents() -> List[Dict]:
    """
    Get all documents from the global store.
    
    Returns:
        List of all documents
    """
    store = initialize_store()
    return store.get_all_documents()


def get_stats() -> Dict:
    """
    Get statistics about the global store.
    
    Returns:
        Statistics dictionary
    """
    store = initialize_store()
    return store.get_stats()


if __name__ == "__main__":
    # Test the module
    print("🔧 Testing embedding store module...")
    print(f"✓ Vector store directory: {config.VECTOR_STORE_DIR}")
    print(f"✓ Embedding provider: {config.EMBEDDING_PROVIDER}")
    print(f"✓ Embedding model: {config.EMBEDDING_MODEL}")
    
    # Initialize store
    store = initialize_store()
    stats = get_stats()
    print(f"\n✓ Store initialized:")
    print(f"  - Total documents: {stats['total_documents']}")
    print(f"  - Dimension: {stats['dimension']}")
    
    print("\n✅ Embedding store module ready!")
