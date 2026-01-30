import os
import logging
from typing import Any, List, Optional
import httpx
from llama_index.core import VectorStoreIndex, Settings, StorageContext, load_index_from_storage
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding
from google.adk.tools import FunctionTool, ToolContext
from context_pilot.shared_libraries.state_keys import StateKeys

logger = logging.getLogger(__name__)

# Global state
_INDEX = None
_STORAGE_DIR = None

def initialize_rag_tool(storage_path: str):
    global _STORAGE_DIR, _INDEX
    _STORAGE_DIR = storage_path
    _INDEX = None
    logger.info(f"RAG Tool initialized with storage path: {_STORAGE_DIR}")

def _get_index():
    global _INDEX, _STORAGE_DIR
    if _INDEX is not None:
        return _INDEX

    if not _STORAGE_DIR:
        error_msg = "RAG Tool not initialized. Call `initialize_rag_tool(path)` first."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # 1. Configure Settings (LLM & Embeddings)
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not found. RAG might fail.")

    Settings.llm = Gemini(
        model="models/gemini-2.0-flash-exp", 
        api_key=api_key
    )
    
    Settings.embed_model = GeminiEmbedding(
        model_name="models/gemini-embedding-001",
        api_key=api_key
    )

    storage_dir = _STORAGE_DIR
    
    if not os.path.exists(storage_dir):
        error_msg = f"RAG Storage not found at {storage_dir}. Please run 'python scripts/build_index.py' to generate it."
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    logger.info(f"Loading persistent index from: {storage_dir}")
    try:
        storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
        _INDEX = load_index_from_storage(storage_context)
        return _INDEX
    except Exception as e:
        logger.error(f"Failed to load index from storage: {e}")
        raise


# Safe Tool Creation
retrieve_rag_documentation_tool = FunctionTool(retrieve_rag_documentation_tool)

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
    
    # Use Standard Gemini Embedding (SDK will upgrade to 3072 dims)
    Settings.embed_model = GeminiEmbedding(
        model_name="models/gemini-embedding-001",
        api_key=api_key
    )

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

def retrieve_rag_documentation_tool(query: str, tool_context: ToolContext) -> str:
    """
    Retreives information from the local knowledge base (RAG) using LlamaIndex.
    
    Args:
        query: The question or search term.
    """
    try:
        # [NEW] Capture Query for Insight
        tool_context.state[StateKeys.LAST_RAG_QUERY] = query
        
        index = _get_index()
        # Use retriever to get raw chunks instead of synthesized answer
        retriever = index.as_retriever(similarity_top_k=5)
        nodes = retriever.retrieve(query)
        
        if not nodes:
            return "No relevant documentation found."
            
        results = []
        for node in nodes:
            # Format: [Score] Text
            results.append(f"--- [Relevance: {node.score:.4f}] ---\n{node.text}\n")
            
        return "\n".join(results)
    except Exception as e:
        logger.error(f"LlamaIndex retrieval failed: {e}")
        return f"Error retrieving documentation: {str(e)}"

# Create the ADK-compatible tool
retrieve_rag_documentation_tool = FunctionTool(
    retrieve_rag_documentation_tool
)
