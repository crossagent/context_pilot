import os
import pytest
from google.adk.models import LLMRegistry
from bug_sleuth.testing import MockLlm
import sys
from unittest.mock import MagicMock

# --- Global Mock for RAG to prevent Import-Time/Init-Time Network Calls ---
# This must run before any test imports agent.py
mock_rag_module = MagicMock()
# Create a mock class that returns a configured instance
from google.adk.tools import BaseTool

class MockRagTool(BaseTool):
    def __init__(self, *args, **kwargs):
        self.name = "retrieve_rag_documentation"
        self.description = "Mock RAG Tool"
    
    async def run_async(self, *, args, tool_context):
        return "Mock RAG Retrieval Result: Document content found."
    
    def _get_declaration(self):
        # Return a dummy declaration to satisfy AgentTool registration
        from google.genai.types import FunctionDeclaration
        return FunctionDeclaration(name=self.name, description=self.description)

mock_rag_module.VertexAiRagRetrieval = MockRagTool
sys.modules["google.adk.tools.retrieval.vertex_ai_rag_retrieval"] = mock_rag_module
sys.modules["vertexai.preview.rag"] = MagicMock()
# --------------------------------------------------------------------------

def pytest_configure(config):
    """
    Set up environment for testing BEFORE any imports happen.
    This ensures constants.py picks up the mock model.
    """
    # Set mock model for all tests by default
    os.environ["GOOGLE_GENAI_MODEL"] = "mock/pytest"
    print(">>> [conftest] Set GOOGLE_GENAI_MODEL=mock/pytest")


@pytest.fixture(scope="session", autouse=True)
def register_mock_llm():
    """
    Automatically register the MockLlm provider at the start of the test session.
    This ensures 'mock/...' models are available to all tests.
    """
    print(">>> [conftest] Registering MockLlm...")
    LLMRegistry.register(MockLlm)
    

@pytest.fixture(autouse=True)
def reset_mock_behaviors():
    """
    Reset mock behaviors before each test to ensure isolation.
    """
    MockLlm.clear_behaviors()
