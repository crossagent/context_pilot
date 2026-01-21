
import pytest
import os
import logging
import asyncio
from dotenv import load_dotenv

# Load env before importing agent to ensure config is correct
load_dotenv()

from bug_sleuth.bug_scene_app.agent import retrieve_rag_documentation
from google.adk.agents.callback_context import CallbackContext

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
@pytest.mark.live
async def test_retrieve_rag_documentation_live():
    """
    Live test against Vertex AI RAG.
    Requires valid GCP credentials and populated RAG Corpus.
    """
    query = "验证测试记录"
    
    logger.info(f"Testing RAG retrieval with query: {query}")
    
    try:
        # ADK tools use run_async with proper context
        # Create minimal tool context
        from unittest.mock import MagicMock
        mock_context = MagicMock()
        
        # Call the tool's run_async method
        result = await retrieve_rag_documentation.run_async(
            args={'query': query},
            tool_context=mock_context
        )
            
        logger.info(f"RAG Result: {result}")
        
        # Validation
        assert result is not None, "Result should not be None"
        # We expect the content we added to be present
        result_str = str(result)
        assert "验证" in result_str or "Vertex AI RAG" in result_str or "测试" in result_str, f"Expected content not found. Got: {result_str[:200]}"
        
        logger.info("✅ RAG Tool test passed!")
        
    except Exception as e:
        logger.error(f"❌ RAG Tool execution failed: {e}")
        pytest.fail(f"RAG Tool execution failed: {e}")

if __name__ == "__main__":
    # Allow running directly
    asyncio.run(test_retrieve_rag_documentation_live())
