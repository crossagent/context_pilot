"""
Integration tests for Bug Sleuth report agent.
Tests basic flow of report_agent.

Model selection is handled via GOOGLE_GENAI_MODEL environment variable
(set in conftest.py to "mock/pytest" for all tests).
"""
import pytest
from context_pilot.testing import AgentTestClient, MockLlm
from unittest.mock import MagicMock
# from context_pilot.context_pilot_app.bug_report_agent.agent import bug_report_agent
from context_pilot.context_pilot_app.exp_recored_agent.agent import exp_recored_agent

def test_report_agent_tools():
    # tools = bug_report_agent.tools
    tools = exp_recored_agent.tools
    # Assert relevant tools are present (e.g. record_experience_tool)
    tool_names = [getattr(t, 'name', str(t)) for t in tools]
    # Note: Refactor changed tools from report_skill_registry to record_experience_tool
    assert "record_experience" in tool_names


@pytest.fixture
def report_client():
    """Create a test client for exp_recored_agent."""
    client = AgentTestClient(agent=exp_recored_agent, app_name="test_app_report")
    return client


@pytest.mark.anyio
async def test_agent_loading():
    """Basic test to verify agent loading."""
    assert exp_recored_agent is not None
    assert exp_recored_agent.name == "exp_recored_agent"


@pytest.mark.anyio
async def test_chat_basic(report_client):
    """Verifies that the agent can receive a message and return a response."""
    await report_client.create_new_session("user_1", "sess_report_1", initial_state={})
    responses = await report_client.chat("Hello, I want to report a bug.")
    
    assert len(responses) > 0
    assert isinstance(responses[0], str)
