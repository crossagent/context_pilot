
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
# ... global variables ...
# Global index instance to avoid reloading
_INDEX: Optional[VectorStoreIndex] = None
# Global storage path
_STORAGE_DIR: Optional[str] = None

def initialize_rag_tool(storage_path: str):
    """
    Initializes the RAG tool with a specific storage path.
    Should be called during application startup (e.g. in agent callback).
    """
    global _STORAGE_DIR, _INDEX
    _STORAGE_DIR = storage_path
    # Reset index to force reload if path changes (though usually init is called once)
    _INDEX = None
    logger.info(f"RAG Tool initialized with storage path: {_STORAGE_DIR}")

def _get_index() -> VectorStoreIndex:
    """
    Initializes and returns the global VectorStoreIndex.
    READ-ONLY MODE: Loads from pre-built storage. 
    Run `python scripts/build_index.py` to update the index.
    """
    global _INDEX, _STORAGE_DIR
    if _INDEX is not None:
        return _INDEX

    if not _STORAGE_DIR:
        # Fallback logic removed as per user request to be explicit, but user mentioned default value in `agent.py`.
        # However, it's safer to raise error here if not initialized.
        error_msg = "RAG Tool not initialized. Call `initialize_rag_tool(path)` first."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

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

    storage_dir = _STORAGE_DIR
    
    if not os.path.exists(storage_dir):
        error_msg = f"RAG Storage not found at {storage_dir}. Please run 'python scripts/build_index.py' to generate it."
        logger.error(error_msg)
        # Raise specific error that can be caught by caller to return friendly message
        raise FileNotFoundError(error_msg)

    logger.info(f"Loading persistent index from: {storage_dir}")
    try:
        storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
        _INDEX = load_index_from_storage(storage_context)
        return _INDEX
    except Exception as e:
        logger.error(f"Failed to load index from storage: {e}")
        raise

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
