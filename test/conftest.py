import os
import pytest
from google.adk.models import LLMRegistry
from context_pilot.testing import MockLlm
import sys
from unittest.mock import MagicMock

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

@pytest.fixture
def api_client(tmp_path):
    """
    Fixture to provide the standardized AdkApiTestClient.
    Mocks external dependencies like 'rg'.
    """
    from unittest.mock import patch
    from context_pilot.testing.api_client import AdkApiTestClient
    # Use package-based loading to ensure consistency with production
    # Import the main app definition
    from context_pilot.context_pilot_app.app import app as main_app
    
    with patch("shutil.which", return_value="rg_mock_path"):
        # We pass the root agent from the main app. 
        # AdkApiTestClient will wrap it in a test App instance.
        yield AdkApiTestClient(tmp_path, agent=main_app.root_agent, app_name=main_app.name)
