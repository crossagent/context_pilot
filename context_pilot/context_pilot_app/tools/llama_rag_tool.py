import os
import logging
import json
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
_LAST_BUILD_TIME = None

def initialize_rag_tool(storage_path: str):
    global _STORAGE_DIR, _INDEX, _LAST_BUILD_TIME
    _STORAGE_DIR = storage_path
    _INDEX = None
    _LAST_BUILD_TIME = None
    logger.info(f"RAG Tool initialized with storage path: {_STORAGE_DIR}")

def _get_current_build_time(storage_dir: str) -> Optional[str]:
    """Reads the build_time from the manifest file."""
    manifest_path = os.path.join(storage_dir, "index_meta.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                return data.get("build_time")
        except:
            pass
    return None

def _get_index():
    global _INDEX, _STORAGE_DIR, _LAST_BUILD_TIME
    
    if not _STORAGE_DIR:
        error_msg = "RAG Tool not initialized. Call `initialize_rag_tool(path)` first."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Check/Setup Storage
    storage_dir = _STORAGE_DIR
    if not os.path.exists(storage_dir):
        error_msg = f"RAG Storage not found at {storage_dir}. Please run 'python scripts/build_index.py' to generate it."
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Auto-reload logic
    current_build_time = _get_current_build_time(storage_dir)
    if _INDEX is not None:
        # If build time has changed, force reload
        if current_build_time != _LAST_BUILD_TIME:
            logger.info(f"Index update detected (Old: {_LAST_BUILD_TIME}, New: {current_build_time}). Reloading...")
            _INDEX = None
        else:
            return _INDEX

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

    logger.info(f"Loading persistent index from: {storage_dir}")
    try:
        storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
        _INDEX = load_index_from_storage(storage_context)
        _LAST_BUILD_TIME = current_build_time
        return _INDEX
    except Exception as e:
        logger.error(f"Failed to load index from storage: {e}")
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
        model="models/gemini-3-flash-preview", 
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
            tool_context.state[StateKeys.RAG_CONTEXT_NODES] = []
            return "No relevant documentation found."
            
        # Serialize nodes for UI
        ui_nodes = []
        results = []
        for node in nodes:
            # Format for LLM: [Score] Text
            results.append(f"--- [Relevance: {node.score:.4f}] ---\n{node.text}\n")
            
            # Format for UI
            ui_nodes.append({
                "text": node.text,
                "score": node.score if node.score else 0.0,
                "metadata": node.metadata or {}
            })
            
        # Update State for Frontend
        tool_context.state[StateKeys.RAG_CONTEXT_NODES] = ui_nodes
            
        return "\n".join(results)
    except Exception as e:
        logger.error(f"LlamaIndex retrieval failed: {e}")
        return f"Error retrieving documentation: {str(e)}"
