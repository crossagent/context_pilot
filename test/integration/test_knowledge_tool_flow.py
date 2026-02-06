import pytest
from context_pilot.testing import MockLlm

@pytest.fixture
def exp_record_client(tmp_path):
    """
    Configure MockLlm and return client for Experience Recording Agent.
    """
    from context_pilot.context_pilot_app.exp_recored_agent.agent import exp_recored_agent
    from context_pilot.testing import AdkApiTestClient
    
    MockLlm.set_behaviors({
        "extract experience": {
            "tool": "extract_experience",
            "args": {
                "intent": "Test Intent from MockLlm",
                "problem_context": "Test Problem Context",
                "root_cause": "Test Root Cause",
                "solution_steps": "Test Solution Steps",
                "evidence": "Test Evidence",
                "tags": "test, integration",
                "contributor": "TestUser"
            }
        },
        "save experience": {
            "tool": "save_experience",
            "args": {}
        },
        "update experience": {
            "tool": "save_experience",
            "args": {"entry_id": "test-uuid-12345"}
        }
    })
    
    client = AdkApiTestClient(tmp_path, agent=exp_recored_agent, app_name="context_pilot_app")
    yield client


def test_extract_experience_tool(exp_record_client):
    """
    Test extract_experience tool via app integration.
    This will validate that the agent callbacks (like initialize_experience_state) work correctly.
    """
    exp_record_client.create_session("user_exp", "sess_exp_001")
    
    print("\n--- Testing Extract Experience ---")
    events = exp_record_client.chat("Please extract experience from the conversation.")
    
    calls = exp_record_client.get_tool_calls(events, "extract_experience")
    if len(calls) == 0:
        print("DEBUG: All Tool Calls found:", exp_record_client.get_tool_calls(events))
        
    assert len(calls) > 0, "Expected extract_experience call"


def test_save_experience_tool(exp_record_client):
    """
    Test save_experience tool via app integration.
    First extract then save to test full flow.
    """
    exp_record_client.create_session("user_exp", "sess_exp_002")

    # First extract
    print("\n--- Step 1: Extract Experience ---")
    events = exp_record_client.chat("Please extract experience from the conversation.")
    calls = exp_record_client.get_tool_calls(events, "extract_experience")
    assert len(calls) > 0, "Expected extract_experience call"
    
    # Then save
    print("\n--- Step 2: Save Experience ---")
    events = exp_record_client.chat("Please save experience to database.")
    calls = exp_record_client.get_tool_calls(events, "save_experience")
    assert len(calls) > 0, "Expected save_experience call"


def test_update_experience_tool(exp_record_client):
    """
    Test save_experience tool with entry_id parameter (upsert behavior).
    When entry_id is provided but doesn't exist, it should create new entry.
    """
    exp_record_client.create_session("user_exp", "sess_exp_003")

    # First extract
    print("\n--- Step 1: Extract Experience ---")
    events = exp_record_client.chat("Please extract experience from the conversation.")
    calls = exp_record_client.get_tool_calls(events, "extract_experience")
    assert len(calls) > 0, "Expected extract_experience call"
    
    # Then update (with non-existent ID, should create new)
    print("\n--- Step 2: Update Experience with ID ---")
    events = exp_record_client.chat("Please update experience with entry ID.")
    calls = exp_record_client.get_tool_calls(events, "save_experience")
    assert len(calls) > 0, "Expected save_experience call with entry_id"

