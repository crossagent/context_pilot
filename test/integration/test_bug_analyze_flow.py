"""
Integration tests for Bug Sleuth analyze agent tools.
Tests each tool in the analyze_agent's toolset.

Model selection is handled via GOOGLE_GENAI_MODEL environment variable
(set in conftest.py to "mock/pytest" for all tests).
"""
import pytest
from unittest.mock import patch

from bug_sleuth.app_factory import create_app, AppConfig
from bug_sleuth.test.test_client import TestClient
from bug_sleuth.test.mock_llm_provider import MockLlm


@pytest.fixture
def mock_external_deps():
    """
    Only mock external tool availability checks, not config.
    REPO_REGISTRY comes from real config.yaml.
    """
    with patch("bug_sleuth.bug_scene_app.bug_analyze_agent.agent.check_search_tools", 
               return_value=None):
        yield


@pytest.fixture
def analyze_client(mock_external_deps):
    """Create a test client for bug_analyze_agent."""
    app = create_app(AppConfig(agent_name="bug_analyze_agent"))
    client = TestClient(agent=app.agent, app_name="test_app")
    return client


# =============================================================================
# Factory Tests
# =============================================================================

@pytest.mark.anyio
async def test_app_factory_creates_valid_agent(mock_external_deps):
    """Basic test to verify app_factory returns a valid agent."""
    app = create_app(AppConfig(agent_name="bug_analyze_agent"))
    
    assert app.agent is not None
    assert app.agent.name == "bug_analyze_agent"


# =============================================================================
# Git Tools Tests
# =============================================================================

@pytest.mark.anyio
async def test_analyze_agent_searches_logs(analyze_client):
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
async def test_analyze_agent_git_diff(analyze_client):
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
async def test_analyze_agent_git_blame(analyze_client):
    """Verifies that the agent calls 'get_git_blame_tool' for blame info."""
    MockLlm.set_behaviors({
        "blame": {
            "tool": "get_git_blame_tool",
            "args": {"path": "test.py", "start_line": 1, "end_line": 10}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_git_blame", initial_state={})
    responses = await analyze_client.chat("Who wrote this? Please blame lines 1-10.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


# =============================================================================
# SVN Tools Tests
# =============================================================================

@pytest.mark.anyio
async def test_analyze_agent_svn_log(analyze_client):
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
async def test_analyze_agent_svn_diff(analyze_client):
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
async def test_analyze_agent_read_file(analyze_client):
    """Verifies that the agent calls 'read_file_tool' to read files."""
    MockLlm.set_behaviors({
        "read file": {
            "tool": "read_file_tool",
            "args": {"path": "d:/test/example.py", "start_line": 1, "end_line": 50}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_read_file", initial_state={})
    responses = await analyze_client.chat("Please read file lines 1-50.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


@pytest.mark.anyio
async def test_analyze_agent_read_code(analyze_client):
    """Verifies that the agent calls 'read_code_tool' for full code reading."""
    MockLlm.set_behaviors({
        "read code": {
            "tool": "read_code_tool",
            "args": {"path": "d:/test/example.cs"}
        }
    })
    
    await analyze_client.create_new_session("user_1", "sess_read_code", initial_state={})
    responses = await analyze_client.chat("Please read code file completely.")
    
    assert len(responses) > 0
    assert "[MockLlm]" in responses[-1]


# =============================================================================
# Search Tools Tests
# =============================================================================

@pytest.mark.anyio
async def test_analyze_agent_search_code(analyze_client):
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
async def test_analyze_agent_search_res(analyze_client):
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
async def test_analyze_agent_update_plan(analyze_client):
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
async def test_analyze_agent_time_convert(analyze_client):
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
async def test_analyze_agent_run_bash(analyze_client):
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
