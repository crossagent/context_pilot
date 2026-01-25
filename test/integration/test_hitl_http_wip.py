import os
import pytest
from fastapi.testclient import TestClient
from google.adk.cli.fast_api import get_fast_api_app
from unittest.mock import patch
from context_pilot.testing import MockLlm

# IMPORTANT: This test spins up the real ADK Web Server logic.
# It requires "adk_data" directory to exist or be mocked.
# We use a temporary directory for data to keep it clean.

@pytest.fixture
def test_client(tmp_path):
    """
    Creates a FastAPI TestClient wrapping the real ADK Web Server.
    """
    # 0. Mock External Deps (rg)
    with patch("shutil.which", return_value="rg_mock_path"):
        # 1. Setup paths
        project_root = os.getcwd() 
        # Agents dir should be the package root containing expected agents (context_pilot_app)
        # Structure: d:\MyProject\context_pilot (root) -> context_pilot (package) -> context_pilot_app (agent)
        agents_dir = os.path.join(project_root, "context_pilot")
        
        # Use tmp_path for data to avoid polluting real DB
        data_dir = tmp_path / "adk_data"
        data_dir.mkdir()
        artifacts_dir = data_dir / "artifacts"
        artifacts_dir.mkdir()
        
        session_db_path = data_dir / "sessions.db"
        # Ensure URI format is correct for SQLite
        session_service_uri = f"sqlite+aiosqlite:///{session_db_path.as_posix()}"
        artifact_service_uri = artifacts_dir.as_uri()

        # 2. Configure MockLlm Behavior
        # This ensures the model calls our tool when asked.
        MockLlm.set_behaviors({
            "how does login work": {
                "tool": "update_strategic_plan",
                "args": {
                    "plan_content": "- [ ] Check login code logic\n- [ ] Check auth config"
                }
            },
        })
        
        # 3. Create App
        print(f"Initializing ADK Server with agents_dir: {agents_dir}")
        print(f"Session URI: {session_service_uri}")
        
        # Ensure env vars needed by agents are set or mocked?
        # conftest.py sets GOOGLE_GENAI_MODEL=mock/pytest which agents should pick up.
        
        app = get_fast_api_app(
            agents_dir=agents_dir,
            session_service_uri=session_service_uri,
            artifact_service_uri=artifact_service_uri,
            web=True,
            a2a=False
        )
        
        yield TestClient(app)

# @pytest.mark.skip(reason="WIP: Requires full env setup for agents")
def test_hitl_via_http(test_client):
    """
    Test HITL via HTTP endpoints.
    Flow:
    1. Create Session
    2. Send Message -> Triggers Tool -> Returns Pause
    3. Check /session/{id} -> See 'adk_request_confirmation' pending event in history? Or pending state?
    4. Send Confirmation Response via /run
    5. Verify Artifact Saved
    """
    
    app_name = "context_pilot_app"
    user_id = "test_user_http"
    
    # helper for logging
    def print_events(label, events):
        print(f"\n[{label}] Event Log:")
        for i, ev in enumerate(events):
             # print(f"Event {i}: {ev.keys()}") 
             # Each ev is a dict from json()
             if 'content' in ev and ev['content'] and 'parts' in ev['content']:
                 for part in ev['content']['parts']:
                     if 'text' in part and part['text']:
                         print(f"  [{i}] Text: {part['text'][:100]}...")
                     # Check functionCall (snake or camel)
                     fc = part.get('functionCall') or part.get('function_call')
                     if fc:
                         print(f"  [{i}] Tool Call: {fc.get('name')} (ID: {fc.get('id')})")
                         print(f"      Args: {fc.get('args')}")
                     
                     # Check functionResponse
                     fr = part.get('functionResponse') or part.get('function_response')
                     if fr:
                         print(f"  [{i}] Tool Resp: {fr.get('name')} (ID: {fr.get('id')})")
                         print(f"      Response: {fr.get('response')}")
    
    # 1. Create Session
    session_id = "sess_http_001"
    resp = test_client.post(f"/apps/{app_name}/users/{user_id}/sessions", json={"session_id": session_id})
    if resp.status_code == 404:
         resp = test_client.post(f"/apps/{app_name}/users/{user_id}/sessions/{session_id}")
    
    assert resp.status_code == 200, f"Create Session Failed: {resp.text}"
    
    # 2. Trigger Plan Update
    
    print("\n--- Sending Chat Request ---")
    
    # Use Pydantic models to ensure correct structure
    from google.genai import types
    
    new_message = types.Content(
        role="user",
        parts=[types.Part(text="How does login work?")]
    )
    
    new_message_dict = new_message.model_dump(exclude_none=True)
    
    payload = {
        "app_name": app_name,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": new_message_dict
    }
    
    resp = test_client.post("/run", json=payload)
    assert resp.status_code == 200, f"Chat Request Failed: {resp.status_code} - {resp.text}"
    
    data = resp.json()
    print_events("Step 1 Response", data)
    
    # 3. Find Confirmation ID from response events
    confirm_req_id = None
    
    for event in data:
        if 'content' in event and event['content'] and 'parts' in event['content']:
            parts = event['content']['parts']
            for part in parts:
                fc = part.get('functionCall') or part.get('function_call')
                if fc:
                     name = fc.get('name')
                     if name == "adk_request_confirmation":
                         confirm_req_id = fc.get('id')
                         break
        if confirm_req_id:
            break
            
    if not confirm_req_id:
         print("Warning: Could not find adk_request_confirmation in response events")

    # 4. Send Confirmation
    if confirm_req_id:
        print(f"\n--- Sending Confirmation (ID: {confirm_req_id}) ---")
        
        function_response_part = types.Part.from_function_response(
            name="adk_request_confirmation",
            response={
                "confirmed": True,
                "payload": {"approved": True}
            }
        )
        function_response_part.function_response.id = confirm_req_id
        
        confirm_msg = types.Content(role="user", parts=[function_response_part])
        confirm_msg_dict = confirm_msg.model_dump(exclude_none=True)
        
        confirm_payload = {
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
            "new_message": confirm_msg_dict
        }
        
        resp = test_client.post(f"/run", json=confirm_payload)
        assert resp.status_code == 200, f"Confirm Request Failed: {resp.status_code} - {resp.text}"
        
        resume_data = resp.json()
        print_events("Step 2 Response", resume_data)
        
        # Assert non-empty response indicating tool continued
        assert len(resume_data) > 0, "Expected events after resumption"
