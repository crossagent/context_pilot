import pytest
from context_pilot.testing import MockLlm

@pytest.fixture
def analyze_client(tmp_path):
    """
    Configure MockLlm and return client for Repo Explorer Agent.
    """
    from context_pilot.context_pilot_app.repo_explorer_agent.agent import repo_explorer_agent
    from context_pilot.testing.api_client import AdkApiTestClient
    from unittest.mock import patch

    MockLlm.set_behaviors({
        "check the git logs": {
            "tool": "get_git_log_tool",
            "args": {"limit": 5}
        },
        "show diff": {
            "tool": "get_git_diff_tool",
            "args": {"target": "HEAD"}
        },
        "ownership analysis": {
            "tool": "get_git_blame_tool",
            "args": {"path": "README.md", "start_line": 1, "end_line": 10}
        },
        "svn log": {
            "tool": "get_svn_log_tool",
            "args": {"limit": 5}
        },
        "read file": {
            "tool": "read_file_tool",
            "args": {"path": "README.md", "start_line": 1, "end_line": 50}
        },
        "search code": {
            "tool": "search_file_tool",
            "args": {"query": "InitPlayer", "search_type": "content", "file_pattern": "*.cs"}
        },
        "run command": {
            "tool": "run_bash_command",
            "args": {"command": "dir"}
        }
    })
    
    with patch("shutil.which", return_value="rg_mock_path"):
        # Initialize client with manual agent
        client = AdkApiTestClient(tmp_path, agent=repo_explorer_agent, app_name="context_pilot_app")
        yield client

def test_analyze_agent_tools(analyze_client):
    """
    Test various tools in the analyze agent (Git, SVN, File, Search).
    """
    analyze_client.create_session("user_analyze", "sess_analyze_001")
    
    # Git Log
    print("\n--- Testing Git Log ---")
    events = analyze_client.chat("Please check the git logs for me.")
    
    # Debug: Print all tool calls if not found
    calls = analyze_client.get_tool_calls(events, "get_git_log_tool")
    if len(calls) == 0:
        print("DEBUG: All Tool Calls found:", analyze_client.get_tool_calls(events))
        # If call failed at runtime inside runner, we might see error event?
        # Actually, if the tool name is wrong in MockLlm, Runner will fail to find it.
        # Let's check if the agent actually has this tool.
        # We can't easily accessing the agent instance inside the running server process from here.
        pass
        
    assert len(calls) > 0, "Expected get_git_log_tool call"
    
    # Git Diff
    print("\n--- Testing Git Diff ---")
    events = analyze_client.chat("Please show diff for HEAD commit.")
    calls = analyze_client.get_tool_calls(events, "get_git_diff_tool")
    assert len(calls) > 0, "Expected get_git_diff_tool call"

    # Git Blame
    print("\n--- Testing Git Blame ---")
    events = analyze_client.chat("Who wrote this? Please do ownership analysis on lines 1-10.")
    calls = analyze_client.get_tool_calls(events, "get_git_blame_tool")
    assert len(calls) > 0, "Expected get_git_blame_tool call"

    # SVN Log (Mocked at tool level usually? API client uses real tools)
    # The real tool will try to run svn command. Since we don't mock the subprocess inside the REAL tool 
    # (unless we patch inside the app process space, which is hard in integration tests),
    # the tool execution might fail. BUT the tool call itself should happen via MockLlm.
    print("\n--- Testing SVN Log ---")
    events = analyze_client.chat("Check svn log for recent changes.")
    calls = analyze_client.get_tool_calls(events, "get_svn_log_tool")
    assert len(calls) > 0, "Expected get_svn_log_tool call"
    
    # File Read
    print("\n--- Testing Read File ---")
    events = analyze_client.chat("Please read file lines 1-50.")
    calls = analyze_client.get_tool_calls(events, "read_file_tool")
    assert len(calls) > 0, "Expected read_file_tool call"
    
    # Search
    print("\n--- Testing Search ---")
    events = analyze_client.chat("Search code for InitPlayer function.")
    calls = analyze_client.get_tool_calls(events, "search_file_tool")
    assert len(calls) > 0, "Expected search_file_tool call"

    # Run Command
    print("\n--- Testing Run Command ---")
    events = analyze_client.chat("Run command: dir")
    calls = analyze_client.get_tool_calls(events, "run_bash_command")
    assert len(calls) > 0, "Expected run_bash_command call"
