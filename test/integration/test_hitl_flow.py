import pytest
from context_pilot.testing import MockLlm

@pytest.fixture
def hitl_client(api_client):
    """
    Configure MockLlm for HITL test and return the api_client.
    """
    MockLlm.set_behaviors({
        "how does login work": {
            "tool": "update_strategic_plan",
            "args": {
                "plan_content": "- [ ] Check login code logic\n- [ ] Check auth config"
            }
        },
    })
    return api_client

def test_hitl_flow(hitl_client):
    """
    Test HITL via HTTP endpoints using the standardized AdkApiTestClient.
    """
    
    # 1. Create Session
    hitl_client.create_session(user_id="hitl_user", session_id="hitl_sess_001")
    
    # 2. Trigger Plan Update
    print("\n--- Sending Chat Request ---")
    events = hitl_client.chat("How does login work?")
    
    # print events for debug
    for i, ev in enumerate(events):
         if 'content' in ev and ev['content'] and 'parts' in ev['content']:
             for part in ev['content']['parts']:
                 fc = part.get('functionCall') or part.get('function_call')
                 if fc:
                     print(f"[{i}] Function Call: {fc.get('name')} ID: {fc.get('id')}")

    # 3. Find Confirmation ID
    tool_calls = hitl_client.get_tool_calls(events, "adk_request_confirmation")
    
    assert len(tool_calls) > 0, "Confirmation tool call not found"
    confirm_req_id = tool_calls[0].get('id')
    print(f"Found Confirmation Request ID: {confirm_req_id}")

    # 4. Send Confirmation
    print(f"\n--- Sending Confirmation (ID: {confirm_req_id}) ---")
    
    resume_events = hitl_client.send_confirmation(
        confirmation_id=confirm_req_id, 
        approved=True
    )
    
    # 5. Verify Resumption (Final Tool Call Logic)
    # The tool should return success message properly
    responses = hitl_client.get_agent_text_responses(resume_events)
    print(f"Resume Responses: {responses}")
    
    assert len(responses) > 0, "Expected text response after resumption"
    # The MockLlm returns a default message because it doesn't parse FunctionResponse parts
    # So we just verify we got a response from the model.
    assert "[MockLlm]" in responses[0], "Expected MockLlm response"
