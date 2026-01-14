"""
Integration tests for Bug Sleuth analyze agent tools.
Tests each tool in the analyze_agent's toolset.

Model selection is handled via GOOGLE_GENAI_MODEL environment variable
(set in conftest.py to "mock/pytest" for all tests).
"""
import pytest
from bug_sleuth.testing import AgentTestClient, MockLlm
from bug_sleuth.bug_scene_app.bug_analyze_agent.agent import bug_analyze_agent


@pytest.fixture
async def mock_external_deps():
    """
    Only mock external tool availability checks.
    """
    # Explicitly import to ensure module is attached to parent package for patching
    # (Though direct import above might handle it, explicitly mocking check_search_tools is safer)
    from unittest.mock import patch
    with patch("bug_sleuth.bug_scene_app.bug_analyze_agent.tools.search_code.check_search_tools", 
               return_value=None):
        yield


@pytest.fixture
async def analyze_client(mock_external_deps):
    """Create a test client for bug_analyze_agent."""
    # Direct usage of the static agent instance
    client = AgentTestClient(agent=bug_analyze_agent, app_name="test_app")
    return client


# =============================================================================
# Agent Loading Test
# =============================================================================

@pytest.mark.anyio
async def test_agent_loading(mock_external_deps):
    """Basic test to verify agent loading."""
    assert bug_analyze_agent is not None
    assert bug_analyze_agent.name == "bug_analyze_agent"


# =============================================================================
# Git Tools Tests
# =============================================================================

@pytest.mark.anyio
async def test_tool_git_log(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'get_git_log_tool' when asked to check logs."""
    MockLlm.set_behaviors({
        "check the git logs": {
            "tool": "get_git_log_tool",
            "args": {"limit": 5}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_git_log", initial_state={})
    responses = await analyze_client.chat("Please check the git logs for me.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


@pytest.mark.anyio
async def test_tool_git_diff(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'get_git_diff_tool' for commit diffs."""
    MockLlm.set_behaviors({
        "show diff": {
            "tool": "get_git_diff_tool",
            "args": {"target": "HEAD"}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_git_diff", initial_state={})
    responses = await analyze_client.chat("Please show diff for HEAD commit.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


@pytest.mark.anyio
async def test_tool_git_blame(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'get_git_blame_tool' for blame info."""
    MockLlm.set_behaviors({
        "ownership analysis": {
            "tool": "get_git_blame_tool",
            "args": {"path": "d:/MyProject/bug_sleuth/README.md", "start_line": 1, "end_line": 10}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_git_blame", initial_state={})
    responses = await analyze_client.chat("Who wrote this? Please do ownership analysis on lines 1-10.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


# =============================================================================
# SVN Tools Tests
# =============================================================================


@pytest.mark.anyio
async def test_tool_svn_log(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'get_svn_log_tool' for SVN history."""
    MockLlm.set_behaviors({
        "svn log": {
            "tool": "get_svn_log_tool",
            "args": {"limit": 5}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_svn_log", initial_state={})
    responses = await analyze_client.chat("Check svn log for recent changes.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]



@pytest.mark.anyio
async def test_tool_svn_diff(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'get_svn_diff_tool' for SVN diffs."""
    MockLlm.set_behaviors({
        "svn diff": {
            "tool": "get_svn_diff_tool",
            "args": {"revision": "100"}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_svn_diff", initial_state={})
    responses = await analyze_client.chat("Show svn diff for revision 100.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


# =============================================================================
# File Tools Tests
# =============================================================================

@pytest.mark.anyio
async def test_tool_read_file(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'read_file_tool' to read files."""
    MockLlm.set_behaviors({
        "read file": {
            "tool": "read_file_tool",
            "args": {"path": "d:/MyProject/bug_sleuth/README.md", "start_line": 1, "end_line": 50}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_read_file", initial_state={})
    responses = await analyze_client.chat("Please read file lines 1-50.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


# =============================================================================
# Search Tools Tests
# =============================================================================

@pytest.mark.anyio
async def test_tool_search_code(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'search_code_tool' for code search."""
    MockLlm.set_behaviors({
        "search code": {
            "tool": "search_code_tool",
            "args": {"query": "InitPlayer", "file_pattern": "*.cs"}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_search_code", initial_state={})
    responses = await analyze_client.chat("Search code for InitPlayer function.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


@pytest.mark.anyio
async def test_tool_search_res(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'search_res_tool' for asset search."""
    MockLlm.set_behaviors({
        "search asset": {
            "tool": "search_res_tool",
            "args": {"name_pattern": "*Hero*.prefab"}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_search_res", initial_state={})
    responses = await analyze_client.chat("Search asset files for Hero prefab.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


# =============================================================================
# Plan Tools Tests
# =============================================================================

@pytest.mark.anyio
async def test_tool_update_plan(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'update_investigation_plan_tool' to update plan."""
    MockLlm.set_behaviors({
        "update plan": {
            "tool": "update_investigation_plan_tool",
            "args": {"content": "# Investigation Plan\n\n## Tasks\n- [ ] Task 1"}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_update_plan", initial_state={})
    responses = await analyze_client.chat("Update plan with new tasks.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


# =============================================================================
# Utility Tools Tests
# =============================================================================

@pytest.mark.anyio
async def test_tool_time_convert(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'time_convert_tool' for time conversion."""
    MockLlm.set_behaviors({
        "convert time": {
            "tool": "time_convert_tool",
            "args": {"time_str": "2026-01-10 14:00:00"}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_time_convert", initial_state={})
    responses = await analyze_client.chat("Convert time 2026-01-10 14:00:00 to timestamp.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


@pytest.mark.anyio
async def test_tool_run_bash(mock_external_deps, analyze_client):
    """Verifies that the agent calls 'run_bash_command' for shell commands."""
    MockLlm.set_behaviors({
        "run command": {
            "tool": "run_bash_command",
            "args": {"command": "dir"}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_run_bash", initial_state={})
    responses = await analyze_client.chat("Run command: dir")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]
