
import os
import logging
from typing import Any, List, Optional
import httpx
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core import VectorStoreIndex, Settings, StorageContext, load_index_from_storage
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.llms.gemini import Gemini
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

class GeminiRawEmbedding(BaseEmbedding):
    """
    Custom Embedding class for Gemini that uses raw REST API to avoid 
    SDK dependency conflicts (google-generativeai vs google-adk/protobuf).
    """
    api_key: str
    model_name: str = "models/embedding-001"

    def __init__(self, api_key: str, model_name: str = "models/embedding-001", **kwargs: Any):
        super().__init__(model_name=model_name, api_key=api_key, **kwargs)

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._embed(text)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        # Simple Loop (Batching could be optimized but keep simple for now)
        return [self._embed(t) for t in texts]

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._embed(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:embedContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "content": {"parts": [{"text": text}]}
        }
        
        try:
            # Synchronous call for compatibility with base class synchronous methods
            with httpx.Client() as client:
                response = client.post(url, json=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                return data["embedding"]["values"]
        except Exception as e:
            logger.error(f"Gemini API Embedding failed: {e}")
            raise

# ... imports ...

# ... global variables ...
# Global index instance to avoid reloading
_INDEX: Optional[VectorStoreIndex] = None

# Define storage path relative to project root (or configured location)
def _get_storage_dir() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    # Use a dedicated folder for the index
    return os.path.join(base_dir, "adk_data", "rag_storage")

def _get_index() -> VectorStoreIndex:
    """
    Initializes and returns the global VectorStoreIndex.
    Tries to load from disk first. If missing, loads data from knowledge_base.jsonl and persists it.
    """
    global _INDEX
    if _INDEX is not None:
        return _INDEX

    # 1. Configure Settings (LLM & Embeddings)
    # Ensure GOOGLE_API_KEY is set in environment for AI Studio
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not found. RAG might fail.")

    # Use Native Gemini LLM
    Settings.llm = Gemini(
        model="models/gemini-2.0-flash-exp", 
        api_key=api_key
    )
    
    # Use Custom REST-based Gemini Embedding (No Conflict)
    Settings.embed_model = GeminiRawEmbedding(api_key=api_key)

    storage_dir = _get_storage_dir()

    # 2. Try Loading from Persistence
    if os.path.exists(storage_dir):
        logger.info(f"Loading persistent index from: {storage_dir}")
        try:
            storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
            _INDEX = load_index_from_storage(storage_context)
            return _INDEX
        except Exception as e:
             logger.warning(f"Failed to load index from storage: {e}. Rebuilding...")

    # 3. Build Fresh Index (Fallback or First Run)
    # Assuming run from project root, or adjust path relative to this file
    # data/knowledge_base.jsonl
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "knowledge_base.jsonl")
    
    if not os.path.exists(data_path):
        # Fallback for different CWD
        data_path = os.path.abspath("data/knowledge_base.jsonl")
    
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Could not find knowledge base at: {data_path}")

    logger.info(f"Loading knowledge base from: {data_path}")
    # SimpleDirectoryReader works well with JSONL if we just treat it as text or use a specific loader.
    # For now, default text loading is usually sufficient for simplistic RAG, 
    # but LlamaIndex JSONReader is better if we want to parse fields.
    # Let's use the valid default reader for simplicity first.
    documents = SimpleDirectoryReader(input_files=[data_path]).load_data()
    
    # 4. Create and Persist Index
    logger.info("Building VectorStoreIndex...")
    _INDEX = VectorStoreIndex.from_documents(documents)
    
    logger.info(f"Persisting index to: {storage_dir}")
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir, exist_ok=True)
    _INDEX.storage_context.persist(persist_dir=storage_dir)
    
    return _INDEX

def query_knowledge_base(query: str) -> str:
    """
    Retreives information from the local knowledge base (RAG) using LlamaIndex.
    
    Args:
        query: The question or search term.
    """
    try:
        index = _get_index()
        query_engine = index.as_query_engine()
        response = query_engine.query(query)
        return str(response)
    except Exception as e:
        logger.error(f"LlamaIndex query failed: {e}")
        return f"Error retrieving documentation: {str(e)}"

# Create the ADK-compatible tool
retrieve_rag_documentation_tool = FunctionTool(
    query_knowledge_base
)
