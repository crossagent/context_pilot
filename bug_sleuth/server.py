
import os
import sys
import logging
import shutil
import uuid
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import HTMLResponse

# ADK Imports
from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.cli.adk_web_server import AdkWebServer
from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.cli.service_registry import get_service_registry, load_services_module
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.evaluation.local_eval_sets_manager import LocalEvalSetsManager
from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from bug_sleuth.shared_libraries.state_keys import StateKeys
from google.genai import types

# Configure Logging
logger = logging.getLogger("bug_sleuth.server")

# 1. Path Configuration
PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))



data_dir_env = os.getenv("ADK_DATA_DIR")
if not data_dir_env:
    data_dir_env = "adk_data"

if not os.path.isabs(data_dir_env):
    DATA_DIR = os.path.abspath(data_dir_env)
else:
    DATA_DIR = data_dir_env

ARTIFACTS_DIR = os.path.join(DATA_DIR, "artifacts")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# Services Configuration
artifact_service_uri = Path(ARTIFACTS_DIR).resolve().as_uri()
session_db_path = os.path.join(DATA_DIR, "sessions.db")
session_service_uri = f"sqlite+aiosqlite:///{session_db_path}"

logger.info(f"Server Configuration:")
logger.info(f"  Package Root: {PACKAGE_ROOT}")

logger.info(f"  Artifacts:    {artifact_service_uri}")
logger.info(f"  Sessions:     {session_service_uri}")

# --- 1.5. Load Extensions (Services & Skills) ---
# Moved from agent.py to ensure global registration happens at startup
from bug_sleuth.skill_library.skill_loader import SkillLoader
from bug_sleuth.skill_library.extensions import root_skill_registry, report_skill_registry, analyze_skill_registry

skill_path = os.getenv("SKILL_PATH")
if skill_path and os.path.exists(skill_path):
    logger.info(f"Initializing Skill System from: {skill_path}")
    skill_loader = SkillLoader(skill_path)
    # Just run the skills; they will self-register into the global registries
    skill_loader.load_skills()
    
    # Log registry status explicitly for verification
    logger.info(f"Root Skill Registry has {len(root_skill_registry._tools)} tools.")
    logger.info(f"Report Skill Registry has {len(report_skill_registry._tools)} tools.")
    logger.info(f"Analyze Skill Registry has {len(analyze_skill_registry._tools)} tools.")
else:
    logger.info("No SKILL_PATH set or path does not exist. Skipping skill loading.")

try:
    # 2. Manual Bootstrapping of ADK Services
    # This logic replicates google.adk.cli.fast_api.get_fast_api_app
    
    # Initialize Eval Managers
    eval_sets_manager = LocalEvalSetsManager(agents_dir=PACKAGE_ROOT)
    eval_set_results_manager = LocalEvalSetResultsManager(agents_dir=PACKAGE_ROOT)

    # Initialize Agent Loader
    agent_loader = AgentLoader(PACKAGE_ROOT)

    # Load Custom Services (services.py is at PACKAGE_ROOT level)
    load_services_module(PACKAGE_ROOT)
    service_registry = get_service_registry()

    # Build Memory Service
    memory_service = InMemoryMemoryService() # Defaulting to InMemory for now as in get_fast_api_app default

    # Build Session Service
    if session_service_uri:
        session_service = service_registry.create_session_service(
             session_service_uri, agents_dir=PACKAGE_ROOT
        )
        if not session_service:
            session_service = DatabaseSessionService(db_url=session_service_uri)
    else:
        session_service = InMemorySessionService()

    # Build Artifact Service
    if artifact_service_uri:
        artifact_service = service_registry.create_artifact_service(
            artifact_service_uri, agents_dir=PACKAGE_ROOT
        )
        if not artifact_service:
             # Fallback manual creation if registry fails (though registry should handle file://)
             from google.adk.artifacts.file_artifact_service import FileArtifactService
             artifact_service = FileArtifactService(root_dir=Path(ARTIFACTS_DIR))
    else:
        artifact_service = InMemoryArtifactService()

    # Build Credential Service
    credential_service = InMemoryCredentialService()

    # Create AdkWebServer
    adk_web_server = AdkWebServer(
        agent_loader=agent_loader,
        session_service=session_service,
        artifact_service=artifact_service,
        memory_service=memory_service,
        credential_service=credential_service,
        eval_sets_manager=eval_sets_manager,
        eval_set_results_manager=eval_set_results_manager,
        agents_dir=PACKAGE_ROOT,
    )

    # Create FastAPI App
    # We pass web_assets_dir to get_fast_api_app if we want the standard ADK UI, 
    # but here we are using a custom reporter UI, so we might ommit it or pass it if we want both.
    # Assuming we want standard dev-ui capabilities potentially.
    
    # Locate ADK web assets for dev-ui
    import google.adk.cli.fast_api
    adk_fast_api_dir = Path(google.adk.cli.fast_api.__file__).parent
    adk_web_assets = adk_fast_api_dir / "browser"

    app = adk_web_server.get_fast_api_app(
        web_assets_dir=adk_web_assets,
        otel_to_cloud=False
    )

    # 3. Register Custom Endpoints

    @app.post("/init")
    async def init_session(
        app_name: str = Body(..., embed=True),
        user_id: str = Body(..., embed=True),
        context: Dict[str, Any] = Body(..., embed=True)
    ):
        """Initializes a new session context (state) and optionally a user message."""
        logger.info(f"Initializing session for user {user_id} in app {app_name}")
        
        # Map camelCase input keys to snake_case StateKeys
        KEY_MAPPING = {
            "deviceInfo": StateKeys.DEVICE_INFO,
            "deviceName": StateKeys.DEVICE_NAME,
            "productBranch": StateKeys.PRODUCT_BRANCH,
            "clientLogUrl": StateKeys.CLIENT_LOG_URL,
            "clientLogUrls": StateKeys.CLIENT_LOG_URLS,
            "clientScreenshotUrls": StateKeys.CLIENT_SCREENSHOT_URLS,
            "clientVersion": StateKeys.CLIENT_VERSION,
            "serverId": StateKeys.SERVER_ID,
            "roleId": StateKeys.ROLE_ID,
            "nickName": StateKeys.NICK_NAME,
            "message": StateKeys.BUG_DESCRIPTION,  # Alias
            "occurrence_time": StateKeys.BUG_OCCURRENCE_TIME,  # Map to full key
            "bug_description": StateKeys.BUG_DESCRIPTION,  # Ensure consistency
        }
        
        # Transform context keys to snake_case
        normalized_context = {}
        for key, value in context.items():
            snake_key = KEY_MAPPING.get(key, key)  # Use mapping or keep original if already snake_case
            normalized_context[snake_key] = value
        
        # 1. Create or Get Session
        session = await session_service.create_session(
            app_name=app_name,
            user_id=user_id
        )

        # 2. Extract specific fields for the event text
        bug_description = normalized_context.get(StateKeys.BUG_DESCRIPTION) or "New Bug Report Initialized"
        
        # 3. Create First Event: State Update (System-side, invisible in chat usually)
        # This event carries the payload to update the session state.
        state_event = Event(
            id=str(uuid.uuid4()),
            author="system",
            # We provide minimal content or None. If strict validation requires content, we provide a hidden system note.
            # But Event model allows optional content/parts. Let's start with empty content to be "invisible".
            # If that fails validation, we'll add a system log message.
            actions=EventActions(state_delta=normalized_context),
            timestamp=time.time(),
            turn_complete=False # Not turning over to agent yet
        )
        await session_service.append_event(session, state_event)

        # 4. Create Second Event: Visible User Message
        # This event is what the Agent and User "see" in the chat transcript.
        # Format all context fields for display
        context_lines = ["**Bug Report 初始化完毕**", ""]
        
        # Define display order and labels for better readability
        display_fields = [
            (StateKeys.BUG_DESCRIPTION, "问题描述"),
            (StateKeys.DEVICE_INFO, "设备信息"),
            (StateKeys.DEVICE_NAME, "设备名称"),
            (StateKeys.PRODUCT_BRANCH, "产品分支"),
            (StateKeys.CLIENT_VERSION, "客户端版本"),
            (StateKeys.SERVER_ID, "服务器ID"),
            (StateKeys.ROLE_ID, "角色ID"),
            (StateKeys.NICK_NAME, "昵称"),
            (StateKeys.BUG_OCCURRENCE_TIME, "发生时间"),
            (StateKeys.CLIENT_LOG_URL, "客户端日志"),
            (StateKeys.CLIENT_LOG_URLS, "客户端日志列表"),
            (StateKeys.CLIENT_SCREENSHOT_URLS, "截图列表"),
        ]
        
        for key, label in display_fields:
            value = normalized_context.get(key)
            if value:
                if isinstance(value, list):
                    context_lines.append(f"- **{label}**: {', '.join(str(v) for v in value)}")
                else:
                    context_lines.append(f"- **{label}**: {value}")
        
        # Include any extra fields not in the predefined list
        known_keys = {k for k, _ in display_fields}
        for key, value in normalized_context.items():
            if key not in known_keys and value:
                if isinstance(value, list):
                    context_lines.append(f"- **{key}**: {', '.join(str(v) for v in value)}")
                else:
                    context_lines.append(f"- **{key}**: {value}")
        
        visible_message = "\n".join(context_lines)
        
        message_event = Event(
            id=str(uuid.uuid4()),
            author="system",
            content=types.Content(
                role="user",
                parts=[types.Part(text=visible_message)]
            ),
            timestamp=time.time(),
            turn_complete=True 
        )
        await session_service.append_event(session, message_event)
        
        return {"session_id": session.id}

    @app.post("/upload")
    async def upload_file(
        file: UploadFile = File(...),
        app_name: str = Form(...),
        user_id: str = Form(...),
        session_id: str = Form(...)
    ):
        """Uploads a file and logs it as an event in the session."""
        logger.info(f"Uploading file {file.filename} for session {session_id}")
        
        # 1. Save artifact
        file_path = Path(ARTIFACTS_DIR) / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Append Event
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        event = Event(
            id=str(uuid.uuid4()),
            author="system", 
            content=types.Content(
                role="user",
                parts=[types.Part(text=f"Uploaded file: {file.filename}")]
            ),
            timestamp=time.time(),
            turn_complete=True
        )
        await session_service.append_event(session, event)
        
        return {"filename": file.filename, "path": str(file_path)}

    # 4. Register UI Endpoint (Restoring original UI)
    @app.get("/reporter", response_class=HTMLResponse)
    async def get_reporter_ui():
        """Serve the embedded bug reporter UI."""
        ui_path = os.getenv("BUG_SLEUTH_UI_PATH")
        
        if ui_path and os.path.exists(ui_path):
             with open(ui_path, "r", encoding="utf-8") as f:
                return f.read()
        
        return f"<h1>Bug Sleuth UI Not Found</h1><p>Please configure BUG_SLEUTH_UI_PATH environment variable or use --ui-path CLI option.</p>"

except Exception as e:
    logger.error(f"Failed to create app: {e}")
    raise e
