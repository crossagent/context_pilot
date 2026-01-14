"""
Integration tests for Bug Sleuth report agent.
Tests basic flow of report_agent.

Model selection is handled via GOOGLE_GENAI_MODEL environment variable
(set in conftest.py to "mock/pytest" for all tests).
"""
import pytest
from bug_sleuth.testing import AgentTestClient, MockLlm
from bug_sleuth.bug_scene_app.bug_report_agent.agent import bug_report_agent


@pytest.fixture
def report_client():
    """Create a test client for bug_report_agent."""
    client = AgentTestClient(agent=bug_report_agent, app_name="test_app_report")
    return client


@pytest.mark.anyio
async def test_agent_loading():
    """Basic test to verify agent loading."""
    assert bug_report_agent is not None
    assert bug_report_agent.name == "bug_report_agent"


@pytest.mark.anyio
async def test_chat_basic(report_client):
    """Verifies that the agent can receive a message and return a response."""
    await report_client.create_new_session("user_1", "sess_report_1", initial_state={})
    responses = await report_client.chat("Hello, I want to report a bug.")
    
    assert len(responses) > 0
    assert isinstance(responses[0], str)
