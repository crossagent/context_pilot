
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
import base64
from pydantic import BaseModel, Field

class UploadRequest(BaseModel):
    app_name: str = Field(..., alias="appName")
    user_id: str = Field(..., alias="userId")
    session_id: str = Field(..., alias="sessionId")
    filename: str
    file_data: str = Field(..., alias="fileData", description="Base64 encoded file content") # keys: data, base64
    mime_type: str = Field("application/octet-stream", alias="mimeType")

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

# --- 1.5. Initialize Application (Skills & Config) ---
# Using app_factory for unified initialization
from bug_sleuth.app_factory import create_app, AppConfig

# Create app instance (loads skills and config)
bug_sleuth_app = create_app(AppConfig(
    skill_path=os.getenv("SKILL_PATH"),
    config_file=os.getenv("CONFIG_FILE")
))

# Log registry status
logger.info(f"App initialized. Skill stats: {bug_sleuth_app.skill_registry_stats}")

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
            "deviceName": StateKeys.DEVICE_NAME,
            "clientLogUrl": StateKeys.CLIENT_LOG_URL,
            "clientLogUrls": StateKeys.CLIENT_LOG_URLS,
            "clientScreenshotUrls": StateKeys.CLIENT_SCREENSHOT_URLS,
            "clientVersion": StateKeys.CLIENT_VERSION,
            "serverId": StateKeys.SERVER_ID,
            "roleId": StateKeys.ROLE_ID,
            "nickName": StateKeys.NICK_NAME,
            "message": StateKeys.BUG_USER_DESCRIPTION,  # Map message to user description
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
        bug_description = normalized_context.get(StateKeys.BUG_USER_DESCRIPTION) or "New Bug Report Initialized"
        
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
            (StateKeys.BUG_USER_DESCRIPTION, "问题描述"),
            (StateKeys.DEVICE_NAME, "设备名称"),
            (StateKeys.CLIENT_VERSION, "客户端版本"),
            (StateKeys.SERVER_ID, "服务器ID"),
            (StateKeys.ROLE_ID, "角色ID"),
            (StateKeys.NICK_NAME, "昵称"),
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
        
        # Add user guidance
        context_lines.extend([
            "",
            "---",
            "",
            "**接下来您希望如何处理？**",
            "",
            "1. **深入分析复现步骤** - 如果这个 Bug 原因不明、偶现、或涉及复杂逻辑，我可以帮您分析日志、代码，找出根因并明确复现步骤",
            "2. **直接上报记录** - 如果问题已经很清楚（如 UI 错位、文案错误等），或者您已经知道复现步骤，我可以直接帮您整理并提交 Bug 报告",
            "",
            "请告诉我您的选择，或提供更多信息。"
        ])
        
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
        request: UploadRequest = Body(...)
    ):
        """Uploads a base64 encoded file and logs it as an event in the session, using ArtifactService."""
        logger.info(f"Uploading file {request.filename} for session {request.session_id}")
        
        try:
            # 1. Decode Base64 content
            # Handle potential header "data:image/png;base64," if present
            if "," in request.file_data:
                header, encoded = request.file_data.split(",", 1)
            else:
                encoded = request.file_data
                
            content = base64.b64decode(encoded)
            
            # 2. Prepare Artifact Part
            artifact_part = types.Part(
                inline_data=types.Blob(
                    data=content,
                    mime_type=request.mime_type
                )
            )
            
            # 3. Save via Artifact Service
            version = await artifact_service.save_artifact(
                app_name=request.app_name,
                user_id=request.user_id,
                session_id=request.session_id,
                filename=request.filename,
                artifact=artifact_part
            )
            
            # 4. Retrieve Metadata to get Canonical URI
            artifact_version = await artifact_service.get_artifact_version(
                app_name=request.app_name,
                user_id=request.user_id,
                session_id=request.session_id,
                filename=request.filename,
                version=version
            )
            
            file_path_uri = artifact_version.canonical_uri if artifact_version else "unknown"
            
        except Exception as e:
            logger.error(f"Failed to save artifact: {e}")
            raise HTTPException(status_code=500, detail=f"Artifact save failed: {e}")

        # 5. Append Event
        session = await session_service.get_session(app_name=request.app_name, user_id=request.user_id, session_id=request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Construct Event Parts
        event_parts = [types.Part(text=f"Uploaded file: {request.filename}")]
            
        event = Event(
            id=str(uuid.uuid4()),
            author="system", 
            content=types.Content(
                role="user",
                parts=event_parts
            ),
            timestamp=time.time(),
            turn_complete=True
        )
        await session_service.append_event(session, event)
        
        return {"filename": request.filename, "path": file_path_uri}

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
