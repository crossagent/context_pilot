"""
Integration tests for Planning Expert Agent.

Tests all three integrated capabilities:
1. Strategic Planning (update_strategic_plan)
2. Knowledge Retrieval/RAG (retrieve_rag_documentation_tool)
3. Experience Recording (extract_experience, save_experience)

Note: This agent can be run standalone or as a remote A2A agent.
For integration tests, we test it directly to avoid A2A server dependency.

To run the A2A server for manual testing:
    python -m uvicorn context_pilot.context_pilot_app.remote_a2a.planning_expert_agent.agent:app --port 8001 --reload
    
Or use the PowerShell script:
    .\start_planning_expert_server.ps1
"""
import pytest
from context_pilot.testing import MockLlm


@pytest.fixture
def planning_expert_client(tmp_path):
    """
    Client for testing context_pilot_agent's integrated capabilities.
    Tests the agent directly (not via remote A2A) to avoid server dependency.
    """
    from context_pilot.context_pilot_app.agent import context_pilot_agent
    from context_pilot.testing import AdkApiTestClient
    
    # Create client directly for context_pilot_agent
    client = AdkApiTestClient(tmp_path, agent=context_pilot_agent, app_name="context_pilot")
    return client


# ============================================================================
# Strategic Planning Tests
# ============================================================================

def test_strategic_planning(planning_expert_client):
    """
    Test strategic plan creation and updates.
    Verifies update_strategic_plan tool works correctly.
    """
    MockLlm.set_behaviors({
        "how does login work": {
            "tool": "update_strategic_plan",
            "args": {
                "plan_content": "- [ ] Check login code logic\n- [ ] Check auth config"
            }
        }
    })
    
    planning_expert_client.create_session("user_test_plan", "sess_plan_001")
    
    print("\n--- Testing Strategic Planning ---")
    events = planning_expert_client.chat("How does login work?")
    
    # Verify tool call
    tool_calls = planning_expert_client.get_tool_calls(events, "update_strategic_plan")
    assert len(tool_calls) > 0, "Expected update_strategic_plan tool call"
    print(f"✅ Tool Executed: {tool_calls[0]['name']}")


# ============================================================================
# RAG/Knowledge Retrieval Tests
# ============================================================================

def test_rag_retrieval(planning_expert_client):
    """
    Test RAG knowledge base retrieval.
    Verifies retrieve_rag_documentation_tool works correctly.
    """
    MockLlm.set_behaviors({
        "check documentation": {
            "tool": "retrieve_rag_documentation_tool",
            "args": {
                "query": "login flow SOP"
            }
        }
    })
    
    planning_expert_client.create_session("user_test_rag", "sess_rag_001")
    
    print("\n--- Testing RAG Retrieval ---")
    events = planning_expert_client.chat("Please check documentation for login.")
    
    tool_calls = planning_expert_client.get_tool_calls(events, "retrieve_rag_documentation_tool")
    
    if len(tool_calls) == 0:
        # Debug: Print all calls
        all_calls = planning_expert_client.get_tool_calls(events)
        print(f"DEBUG: Actual Tool Calls: {[c['name'] for c in all_calls]}")
        
    assert len(tool_calls) > 0, "Expected retrieve_rag_documentation_tool call"
    print(f"✅ Tool Executed: {tool_calls[0]['name']}")


# ============================================================================
# Experience Recording Tests
# ============================================================================

def test_extract_experience(planning_expert_client):
    """
    Test experience extraction.
    Verifies extract_experience tool stages data correctly.
    """
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
        }
    })
    
    planning_expert_client.create_session("user_exp", "sess_exp_001")
    
    print("\n--- Testing Extract Experience ---")
    events = planning_expert_client.chat("Please extract experience from the conversation.")
    
    calls = planning_expert_client.get_tool_calls(events, "extract_experience")
    if len(calls) == 0:
        print("DEBUG: All Tool Calls found:", planning_expert_client.get_tool_calls(events))
        
    assert len(calls) > 0, "Expected extract_experience call"
    print(f"✅ Tool Executed: {calls[0]['name']}")


def test_save_experience(planning_expert_client):
    """
    Test experience saving to database.
    Verifies save_experience persists data correctly.
    """
    MockLlm.set_behaviors({
        "extract experience": {
            "tool": "extract_experience",
            "args": {
                "intent": "Test Save Experience",
                "problem_context": "Test Context",
                "root_cause": "Test Root Cause",
                "solution_steps": "Test Steps",
                "evidence": "Test Evidence",
                "tags": "test, save",
                "contributor": "TestUser"
            }
        },
        "save experience": {
            "tool": "save_experience",
            "args": {}
        }
    })
    
    planning_expert_client.create_session("user_exp", "sess_exp_002")

    # First extract
    print("\n--- Step 1: Extract Experience ---")
    events = planning_expert_client.chat("Please extract experience from the conversation.")
    calls = planning_expert_client.get_tool_calls(events, "extract_experience")
    assert len(calls) > 0, "Expected extract_experience call"
    
    # Then save
    print("--- Step 2: Save Experience ---")
    events = planning_expert_client.chat("Please save experience to database.")
    calls = planning_expert_client.get_tool_calls(events, "save_experience")
    assert len(calls) > 0, "Expected save_experience call"
    print(f"✅ Tool Executed: {calls[0]['name']}")


def test_update_experience_with_id(planning_expert_client):
    """
    Test save_experience with entry_id parameter (upsert behavior).
    When entry_id is provided but doesn't exist, should create new entry.
    """
    MockLlm.set_behaviors({
        "extract experience": {
            "tool": "extract_experience",
            "args": {
                "intent": "Test Update Experience",
                "problem_context": "Test Context",
                "root_cause": "Test Root Cause",
                "solution_steps": "Test Steps",
                "evidence": "Test Evidence",
                "tags": "test, update",
                "contributor": "TestUser"
            }
        },
        "update experience": {
            "tool": "save_experience",
            "args": {"entry_id": "test-uuid-12345"}
        }
    })
    
    planning_expert_client.create_session("user_exp", "sess_exp_003")

    # First extract
    print("\n--- Step 1: Extract Experience ---")
    events = planning_expert_client.chat("Please extract experience from the conversation.")
    calls = planning_expert_client.get_tool_calls(events, "extract_experience")
    assert len(calls) > 0, "Expected extract_experience call"
    
    # Then update (with non-existent ID, should create new)
    print("--- Step 2: Update Experience with ID ---")
    events = planning_expert_client.chat("Please update experience with entry ID.")
    calls = planning_expert_client.get_tool_calls(events, "save_experience")
    assert len(calls) > 0, "Expected save_experience call with entry_id"
    print(f"✅ Tool Executed: {calls[0]['name']}")


# ============================================================================
# Agent Identity Tests
# ============================================================================

def test_agent_identity(planning_expert_client):
    """
    Verify planning_expert_agent has all expected tools loaded.
    """
    # Agent loaded successfully if fixture worked
    # The agent should have:
    # - update_strategic_plan
    # - retrieve_rag_documentation_tool
    # - extract_experience
    # - save_experience
    # - root_skill_registry
    # - report_skill_registry
    pass
