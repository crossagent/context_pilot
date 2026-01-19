"""
Integration tests for Bug Sleuth root agent flow.
Uses direct agent import for unified initialization.

Model selection is handled via GOOGLE_GENAI_MODEL environment variable
(set in conftest.py to "mock/pytest" for all tests).

Note: Tests use real config.yaml for REPO_REGISTRY.
Only external tool checks (ripgrep) are mocked.
"""
import pytest
import logging
from unittest.mock import patch

from bug_sleuth.testing import AgentTestClient, MockLlm
from bug_sleuth.shared_libraries.state_keys import StateKeys
from bug_sleuth.bug_scene_app.agent import context_pilot_agent as bug_scene_agent
from bug_sleuth.bug_scene_app.bug_analyze_agent.agent import bug_analyze_agent

logging.basicConfig(level=logging.INFO)


@pytest.fixture
def mock_external_deps():
    """
    Only mock external tool availability checks.
    """
    with patch("shutil.which", return_value="rg_mock_path"):
        yield


@pytest.mark.anyio
async def test_root_agent_refine_bug_state_tool(mock_external_deps):
    """
    Test that root agent can call refine_bug_state tool.
    Verifies: Agent receives input -> Calls tool -> Returns response
    """
    MockLlm.set_behaviors({
        "logo is overlapping": {
            "tool": "refine_bug_state",
            "args": {
                "device_name": "Pixel 6"
            }
        }
    })
    
    # Use direct agent instance
    client = AgentTestClient(agent=bug_scene_agent, app_name="bug_sleuth_app")
    await client.create_new_session("user_test", "sess_001")
    
    responses = await client.chat("The logo is overlapping text on the login screen, Android, Branch A.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


@pytest.mark.anyio
async def test_root_agent_question_answer_flow(mock_external_deps):
    """
    Test Q&A flow: Agent asks for clarification, user responds.
    """
    MockLlm.set_behaviors({
        "It's broken": {
            "text": "What device are you using?"
        },
        "Pixel 6": {
            "tool": "refine_bug_state",
            "args": {
                "device_name": "Pixel 6"
            }
        }
    })
    
    client = AgentTestClient(agent=bug_scene_agent, app_name="bug_sleuth_app")
    await client.create_new_session("user_test", "sess_002")
    
    resp1 = await client.chat("It's broken")
    assert len(resp1) > 0
    assert "What device" in resp1[-1]
    
    resp2 = await client.chat("I use a Pixel 6")
    assert len(resp2) > 0


@pytest.mark.anyio
async def test_root_agent_dispatch_to_analyze_agent(mock_external_deps):
    """
    Test agent delegation: Root agent dispatches to analyze agent.
    """
    MockLlm.set_behaviors({
        "crashes sometimes": {
            "tool": "refine_bug_state",
            "args": {
                "device_name": "PC"
            }
        },
        "success": {
            "text": "[MockLlm] Delegating to bug_analyze_agent for deep analysis..."
        }
    })
    
    client = AgentTestClient(agent=bug_scene_agent, app_name="bug_sleuth_app")
    await client.create_new_session("user_test", "sess_complex")
    
    responses = await client.chat("Game crashes sometimes when opening bag, PC.")
    
    assert len(responses) > 0


@pytest.mark.anyio
async def test_analyze_agent_git_log_tool(mock_external_deps):
    """
    Test that analyze agent can call get_git_log_tool.
    This tests the analyze agent directly (as a standalone unit), or could be reached via root.
    Here we test it standalone for simplicity like before.
    """
    MockLlm.set_behaviors({
        "check the git logs": {
            "tool": "get_git_log_tool",
            "args": {"limit": 5}
        }
    })
    
    client = AgentTestClient(agent=bug_analyze_agent, app_name="test_app")
    await client.create_new_session("user_1", "sess_1", initial_state={})
    
    responses = await client.chat("Please check the git logs for me.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


@pytest.mark.anyio
async def test_loading_valid_root_agent(mock_external_deps):
    """
    Basic test to verify returning valid root agent with sub-agents.
    """
    assert bug_scene_agent is not None
    assert bug_scene_agent.name == "context_pilot_agent"
    
    # Verify sub-agents are accessible
    # With direct imports, we know they are there, but good to check list
    sub_names = [sub.name for sub in bug_scene_agent.sub_agents]
    assert "bug_analyze_agent" in sub_names
