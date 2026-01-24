
import pytest
import logging
import os
import sys
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from unittest.mock import patch

from context_pilot.context_pilot_app.llama_rag_tool import query_knowledge_base, initialize_rag_tool
from scripts.rag_config import RagConfig

# Force logging to see errors
logging.basicConfig(level=logging.ERROR)

@pytest.mark.asyncio
async def test_reproduce_rag_dimension_mismatch():
    """
    Tries to actually query the knowledge base using the local storage.
    This should reproduce the 'shapes (768,) and (3072,) not aligned' error
    if the index on disk is incompatible with the configured model.
    """
    print(f"\n[Test] Storage Dir: {RagConfig.STORAGE_DIR}")
    print(f"[Test] Embedding Model: {RagConfig.EMBEDDING_MODEL}")
    
    # Initialize the tool pointing to the REAL storage
    initialize_rag_tool(RagConfig.STORAGE_DIR)
    
    # Perform a query
    # We expect this to fail if the dimensions are wrong.
    # We catch the error string returned by the tool logic.
    result = query_knowledge_base("how does login work")
    
    print(f"\n[Test Result] {result}")
    
    # Assert failure logic:
    # If the user says it failed, the result likely starts with "Error retrieving documentation"
    # We WANT to see this failure to confirm reproduction.
    if "Error retrieving documentation" in result:
        print(">>> SUCCESS: Reproduced the runtime error!")
        if "not aligned" in result:
             print(">>> CONFIRMED: Dimension mismatch found.")
        else:
             print(f">>> NOTE: Different error: {result}")
        # Fail the test intentionally to signal we found the bug? 
        # Or pass it because we successfully reproduced it?
        # Let's pass if we reproduce it, but print clearly.
        pass 
    else:
        print(">>> FAILED to reproduce: Query seemed successful.")
        # If it works here, then the runtime environment is different from this test env.

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_reproduce_rag_dimension_mismatch())
