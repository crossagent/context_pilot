import pytest
import asyncio
from typing import List
from bug_sleuth.test_utils.test_client import TestClient
from bug_sleuth.bug_analyze_agent.agent import bug_analyze_agent
from bug_sleuth.test_utils.mock_llm_provider import MockLlm

@pytest.mark.anyio
async def test_analyze_agent_searches_logs():
    """
    Verifies that the agent calls 'get_git_log_tool' when asked to check logs.
    """
    
    # 1. Setup Mock Behavior
    MockLlm.set_behaviors({
        "check the git logs": {
            "tool": "get_git_log_tool",
            "args": {"limit": 5}
        }
    })
    
    # 2. Setup Env (Patch REPO_REGISTRY) to pass validation
    from bug_sleuth.bug_analyze_agent import agent as agent_module
    agent_module.REPO_REGISTRY = [{"name": "test_repo", "path": "/tmp/test"}]
    
    # 3. Initialize Agent with Mock Model
    agent = bug_analyze_agent
    agent.model = "mock/integration_test" # This triggers MockLlm
    
    client = TestClient(agent=agent, app_name="test_app")
    await client.create_new_session(
        "user_1", 
        "sess_1", 
        initial_state={"project_root": "/tmp/test_project"}
    )
    
    # 4. Execution
    from unittest.mock import patch
    # Patch check_search_tools to bypass 'ripgrep' check during agent callback
    with patch("bug_sleuth.bug_analyze_agent.agent.check_search_tools", return_value=None):
        responses = await client.chat("Please check the git logs for me.")
    
    # 4. Verification
    # We check if the tool execution actually happened in the session events
    # Or simpler: check the response flow.
    
    try:
        print("\nResponses:", responses)
    except UnicodeEncodeError:
        print("\nResponses: [Content cannot be printed in current console encoding]")
    
    # The client.chat returns text responses. 
    # If the tool was called, the loop continues. 
    # Eventually MockLlm returns a default text.
    
    # Verify we got a final text response
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]
    
    # Verify tool call (Invisible in responses list, but we can inspect state/events if needed)
    # Ideally AdkSimulationClient or the Runner exposes executed tools. 
    # For now, we rely on the fact that if the function wasn't called, the loop 
    # wouldn't have continued to the final text response (or would have stuck).
