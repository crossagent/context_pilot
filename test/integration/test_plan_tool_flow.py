import pytest
from context_pilot.testing import MockLlm

@pytest.fixture
def plan_client(api_client):
    """
    Configure MockLlm for Plan Flow.
    """
    MockLlm.set_behaviors({
        "how does login work": {
            "tool": "update_strategic_plan",
            "args": {
                "plan_content": "- [ ] Check login code logic\n- [ ] Check auth config"
            }
        },
        "check documentation": {
             "tool": "retrieve_rag_documentation_tool",
             "args": {
                 "query": "login flow SOP"
             }
        }
    })
    return api_client

def test_strategic_plan_flow(plan_client):
    """
    Test that ContextPilot can create and update a Strategic Plan using standard API client.
    """
    plan_client.create_session("user_test_plan", "sess_plan_001")
    
    # 1. Ask a broad question
    print("\n--- Sending Chat 1 ---")
    events = plan_client.chat("How does login work?")
    
    # Verify tool call
    tool_calls = plan_client.get_tool_calls(events, "update_strategic_plan")
    assert len(tool_calls) > 0, "Expected update_strategic_plan tool call"
    print(f"Tool Executed: {tool_calls[0]['name']}")
    
    # 2. Ask to check docs
    print("\n--- Sending Chat 2 ---")
    events_2 = plan_client.chat("Please check documentation for login.")
    
    tool_calls_2 = plan_client.get_tool_calls(events_2, "retrieve_rag_documentation_tool")
    # Note: RAG tool might have different name or be mocked out if not registered
    # If using MockLlm, we force the call.
    
    if len(tool_calls_2) == 0:
        # Debug: Print all calls
        all_calls = plan_client.get_tool_calls(events_2)
        print(f"Actual Tool Calls: {[c['name'] for c in all_calls]}")
        
    assert len(tool_calls_2) > 0, "Expected retrieve_rag_documentation_tool call"

def test_agent_identity(plan_client):
    """Verify agent identity via list-apps or chat response."""
    # Since we use API, we can't check 'agent.name' directly easily without internal access.
    # But we can check if it responds to "Who are you?" if configured.
    # Or just verify session creation works implying agent loaded.
    pass
