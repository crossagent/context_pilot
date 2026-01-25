import os
import shutil
from typing import Optional, Dict, Any, List
from fastapi.testclient import TestClient
from google.adk.cli.fast_api import get_fast_api_app
from google.genai import types
from context_pilot.testing import MockLlm

# New Imports for custom agent loading
from google.adk.apps.app import App
from google.adk.cli.adk_web_server import AdkWebServer
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader
from google.adk.evaluation.local_eval_sets_manager import LocalEvalSetsManager
from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager

class MockAgentLoader(BaseAgentLoader):
    """Loads a specific pre-defined list of Apps."""
    def __init__(self, apps: List[App]):
        self._apps = {app.name: app for app in apps}

    def load_agent(self, agent_name: str):
        if agent_name in self._apps:
            return self._apps[agent_name]
        raise ValueError(f"Agent/App '{agent_name}' not found in MockLoader.")

    def list_agents(self) -> List[str]:
        return sorted(list(self._apps.keys()))

class AdkApiTestClient:
    """
    The Next-Generation Integration Testing Framework for Context Pilot.
    
    This client bridges the gap between Unit Tests and End-to-End Tests by combining
    the **Real ADK Runtime** with a **Deterministic Simulation Layer**.

    **Core Advantages:**
    
    1.  **Production Fidelity (Real-World Simulation)**: 
        Runs the full `AdkWebServer` (FastAPI) stack locally.
        Verifies the entire request lifecycle: 
        *HTTP -> Routing -> Session Manager -> Agent Runner -> Tool Execution -> Event Output*.
        This ensures that if a test passes, the entire system configuration is valid.

    2.  **Deterministic & Zero-Cost (MockLlm)**:
        Integrated deeply with `MockLlm` to replace stochastic model calls with precise, scripted behaviors.
        *   **Stable**: Eliminates flakiness; tools are called strictly as defined.
        *   **Fast**: Tests execute in milliseconds without network latency.
        *   **Free**: No API token usage, perfect for high-frequency CI/CD execution.

    3.  **Complete & Isolated Coverage**:
        *   **Full Flow**: Validates edge cases like serialization, event compaction, and error handling.
        *   **Isolation**: Supports `agent_override` to spin up disposable apps on-the-fly, allowing 
            unit-level testing of sub-agents (e.g. `repo_explorer_agent`) within the real server context.

    4.  **No Port Conflicts (In-Memory execution)**:
        *   Uses `Starlette/FastAPI TestClient` to execute requests directly against the ASGI interface.
        *   **No physical TCP ports** are bound or consumed. Testing is safe to run alongside a running server.
    """

    def __init__(self, tmp_path, agent=None, app_name="context_pilot_app"):
        """
        Initialize the client.
        
        Args:
            tmp_path: pathlib.Path object (usually from pytest tmp_path fixture)
            agent: Optional. If provided, creates a server serving ONLY this agent (wrapped in an App).
                   Useful for unit testing sub-agents (like repo_explorer_agent) in isolation.
            app_name: Name of the app to target.
        """
        self.tmp_path = tmp_path
        self.app_name = app_name
        self.agent = agent
        self.client = self._create_client()
        self.user_id = "test_user"
        self.session_id = "test_session_001"
        
    def _create_client(self) -> TestClient:
        """Sets up the ADK FastAPI app."""
        
        project_root = os.getcwd()
        data_dir = self.tmp_path / "adk_data"
        data_dir.mkdir()
        artifacts_dir = data_dir / "artifacts"
        artifacts_dir.mkdir()
        
        session_db_path = data_dir / "sessions.db"
        session_service_uri = f"sqlite+aiosqlite:///{session_db_path.as_posix()}"
        artifact_service_uri = artifacts_dir.as_uri()

        # If agent is provided, we manually construct the server to serve it
        if self.agent:
            # --- MODE A: Unit/Component Test Mode ---
            # Scenario: You want to test a SPECIFIC Agent instance (e.g., a sub-agent, or a new agent not yet on disk).
            # Action: We manually construct a 'Fake' App wrapping just this agent and force the server to load it.
            # Benefit: Allows testing 'repo_explorer_agent' tools directly without going through the Root Agent's router.
            print(f"[AdkApiTestClient] Initializing Manual Server for Single Agent: {self.agent.name}")
            
            # 1. Create App Wrapper
            test_app = App(name=self.app_name, root_agent=self.agent)
            agent_loader = MockAgentLoader([test_app])
            
            # 2. Setup Services (Using In-Memory/Local logic similar to get_fast_api_app)
            # Use real implementation imports
            from google.adk.sessions.database_session_service import DatabaseSessionService
            
            session_service = DatabaseSessionService(db_url=session_service_uri)
            # Use InMemory Artifact service if URI schema not supported or complex? 
            # Actually URI file:// is supported by FileSystemArtifactService usuallly but ADK uses registry.
            # For simplicity in manual construction, InMemory is fine for unit tests unless we need artifact persistence.
            # But wait, create_adk_web_server expects configured services.
            # We'll use InMemoryArtifactService for simplicity unless URI is file:// then maybe FileSystem?
            # Let's use InMemory to be safe and fast for unit tests.
            artifact_service = InMemoryArtifactService() 
            memory_service = InMemoryMemoryService()
            credential_service = InMemoryCredentialService()
            
            eval_sets_manager = LocalEvalSetsManager(agents_dir=str(data_dir)) # Dummy dir
            eval_set_results_manager = LocalEvalSetResultsManager(agents_dir=str(data_dir))
            
            web_server = AdkWebServer(
                agent_loader=agent_loader,
                session_service=session_service,
                artifact_service=artifact_service,
                memory_service=memory_service,
                credential_service=credential_service,
                eval_sets_manager=eval_sets_manager,
                eval_set_results_manager=eval_set_results_manager,
                agents_dir=str(data_dir) # Dummy
            )
            
            app = web_server.get_fast_api_app()
            return TestClient(app)

        else:
            # --- MODE B: Integration/System Test Mode ---
            # Scenario: You want to test the REAL Application as configured in your project (task.md, main.py).
            # Action: We simulate the 'context-pilot serve' startup logic, scanning the agents directory.
            # Benefit: Verifies that directory structure, config files, and multi-agent routing are working correctly.
            agents_dir = os.path.join(project_root, "context_pilot")
            print(f"[AdkApiTestClient] Initializing Server with agents_dir: {agents_dir}")

            app = get_fast_api_app(
                agents_dir=agents_dir,
                session_service_uri=session_service_uri,
                artifact_service_uri=artifact_service_uri,
                web=True,
                a2a=False
            )
            return TestClient(app)

    # ... [Keep existing helper methods] ...
    def create_session(self, user_id: str, session_id: str):
        """Creates a new session via API."""
        self.user_id = user_id
        self.session_id = session_id
        
        # Try specific session endpoint first
        resp = self.client.post(f"/apps/{self.app_name}/users/{user_id}/sessions", json={"session_id": session_id})
        
        if resp.status_code == 404:
             # Fallback
             resp = self.client.post(f"/apps/{self.app_name}/users/{user_id}/sessions/{session_id}")
        
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to create session: {resp.status_code} - {resp.text}")
        return resp.json()

    def chat(self, text: str) -> List[Dict]:
        """Sends a text message to the agent and returns the event list."""
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=text)]
        )
        return self._send_run_request(new_message)

    def send_confirmation(self, confirmation_id: str, approved: bool = True, payload: Dict = None) -> List[Dict]:
        """Sends a tool confirmation response to resume execution."""
        if payload is None:
            payload = {"approved": approved}
            
        function_response_part = types.Part.from_function_response(
            name="adk_request_confirmation",
            response={
                "confirmed": True,
                "payload": payload
            }
        )
        function_response_part.function_response.id = confirmation_id
        
        new_message = types.Content(role="user", parts=[function_response_part])
        return self._send_run_request(new_message)

    def _send_run_request(self, message: types.Content) -> List[Dict]:
        """Internal helper to call /run endpoint."""
        message_dict = message.model_dump(exclude_none=True)
        
        payload = {
            "app_name": self.app_name,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "new_message": message_dict
        }
        
        resp = self.client.post("/run", json=payload)
        
        if resp.status_code != 200:
             raise RuntimeError(f"Run Request Failed: {resp.status_code} - {resp.text}")
             
        return resp.json()

    def get_tool_calls(self, events: List[Dict], tool_name: str = None) -> List[Dict]:
        """Extracts tool calls from a list of events."""
        calls = []
        for event in events:
            if 'content' in event and event['content'] and 'parts' in event['content']:
                for part in event['content']['parts']:
                    # Check for snake_case or camelCase
                    fc = part.get('functionCall') or part.get('function_call')
                    if fc:
                        # Normalize name check (MockLlm output vs real tool definition?)
                        name = fc.get('name')
                        if tool_name is None or name == tool_name:
                            calls.append(fc)
        return calls
        
    def get_agent_text_responses(self, events: List[Dict]) -> List[str]:
        """Extracts text responses from the agent."""
        texts = []
        for event in events:
            # Check author? Usually 'model' or agent name.
            # We assume if it has text part, we want it.
            if 'content' in event and event['content'] and 'parts' in event['content']:
                for part in event['content']['parts']:
                    if 'text' in part and part['text']:
                        texts.append(part['text'])
        return texts
