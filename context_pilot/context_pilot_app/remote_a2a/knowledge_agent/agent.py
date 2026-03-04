import os
from context_pilot.shared_libraries.constants import MODEL
from google.adk import Agent
from google.adk.agents.llm_agent import LlmAgent
from typing import Optional
import logging
from . import prompt

# Tools
from context_pilot.context_pilot_app.tools import (
    retrieve_rag_documentation_tool,
    initialize_rag_tool,
    extract_experience_tool,
    save_experience_tool
)
from google.adk.tools import FunctionTool
# Skill Registries
from context_pilot.skill_library.extensions import root_skill_registry, report_skill_registry, analyze_skill_registry

logger = logging.getLogger(__name__)

# --- RAG Initialization ---
rag_storage_path = os.getenv("RAG_STORAGE_DIR")
if not rag_storage_path:
    # Default: ProjectRoot/adk_data/rag_storage
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    rag_storage_path = os.path.join(base_dir, "adk_data", "rag_storage")

try:
    initialize_rag_tool(rag_storage_path)
except Exception as e:
    logger.warning(f"RAG Initialization Warning: {e}")

# Define Agent
knowledge_agent = LlmAgent(
    name="knowledge_agent",
    model=MODEL,
    description="Agent responsible for searching the knowledge base (RAG), tracking experiences, and managing knowledge.",
    instruction=prompt.get_prompt(),
    tools=[
        # Knowledge Retrieval (RAG)
        FunctionTool(retrieve_rag_documentation_tool),
        
        # Experience Recording
        extract_experience_tool,
        save_experience_tool,
        
        # Skill Registries
        root_skill_registry,
        report_skill_registry,
        analyze_skill_registry
    ],
)

root_agent = knowledge_agent

# A2A app for remote access
# Usage: uvicorn context_pilot.context_pilot_app.remote_a2a.knowledge_agent.agent:app --host 0.0.0.0 --port 54090
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.runners import Runner
from google.adk.apps.app import App
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.adk.artifacts.file_artifact_service import FileArtifactService
from pathlib import Path
from google.adk.agents.context_cache_config import ContextCacheConfig

# --- Configuration for Persistence ---
# Define local data directory on the host machine
data_dir = os.path.abspath(os.getenv("ADK_DATA_DIR", "adk_data"))
knowledge_data_dir = os.path.join(data_dir, "knowledge_agent")
artifacts_dir = os.path.join(knowledge_data_dir, "artifacts")

os.makedirs(knowledge_data_dir, exist_ok=True)
os.makedirs(artifacts_dir, exist_ok=True)

session_db_path = os.path.join(knowledge_data_dir, "sessions.db")
session_service_uri = f"sqlite+aiosqlite:///{session_db_path}"
artifact_service_uri = Path(artifacts_dir).resolve().as_uri()

# Use an App instance to configure standard features like context caching.
# This ensures the Runner manages caching correctly via the App-to-Runner mapping.
knowledge_app = App(
    name="knowledge_app",
    root_agent=knowledge_agent,
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=600,
        cache_intervals=1,
    )
)

# A manual Runner requires a session_service explicitly.
runner = Runner(
    app=knowledge_app, 
    session_service=SqliteSessionService(db_path=session_db_path),
    artifact_service=FileArtifactService(root_dir=artifacts_dir)
)

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

# Configurable A2A host (docker default is typically 0.0.0.0 for bind, internal network name, or host.docker.internal)
_a2a_host = os.getenv("A2A_HOST", "0.0.0.0")
_a2a_port = int(os.getenv("A2A_PORT", 8003))
_agent_card = AgentCard(
    name=knowledge_agent.name,
    description=(
        "Agent responsible for searching the internal knowledge base (RAG), "
        "tracking experiences, and managing knowledge."
    ),
    url=f"http://{_a2a_host}:{_a2a_port}/",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[
        AgentSkill(
            id="knowledge_agent",
            name="knowledge_agent",
            description=(
                "Searches RAG, explores skill registries, and records solutions "
                "to the knowledge base automatically."
            ),
            tags=["llm", "knowledge", "rag", "experience-recording"],
        )
    ],
)

app = to_a2a(
    knowledge_agent,
    host=_a2a_host,
    port=_a2a_port,
    runner=runner,
    agent_card=_agent_card,
)
