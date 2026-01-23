
import os
import logging
from typing import Optional
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.google import GoogleGenerativeAIEmbeddings
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

# Global index instance to avoid reloading
_INDEX: Optional[VectorStoreIndex] = None

def _get_index() -> VectorStoreIndex:
    """
    Initializes and returns the global VectorStoreIndex.
    Loads data from data/knowledge_base.jsonl.
    """
    global _INDEX
    if _INDEX is not None:
        return _INDEX

    # 1. Configure Settings (LLM & Embeddings)
    # Ensure GOOGLE_API_KEY is set in environment for AI Studio
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not found. LlamaIndex might fail if not using Vertex.")

    # Use Gemini Flash (AI Studio) - Matches the user's non-Vertex intent
    Settings.llm = Gemini(model="models/gemini-2.0-flash-exp", api_key=api_key)
    
    # Use Google Embeddings (AI Studio)
    Settings.embed_model = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001", 
        api_key=api_key
    )

    # 2. Load Data
    # Assuming run from project root, or adjust path relative to this file
    # data/knowledge_base.jsonl
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
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
    
    # 3. Create Index
    logger.info("Building VectorStoreIndex...")
    _INDEX = VectorStoreIndex.from_documents(documents)
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
    query_knowledge_base,
    description="Use this tool to retrieve documentation and reference materials from the knowledge base."
)
