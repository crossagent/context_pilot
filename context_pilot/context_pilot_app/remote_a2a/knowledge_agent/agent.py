import os
import logging
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import FunctionTool

from context_pilot.shared_libraries.constants import MODEL
from . import prompt

# Tools
from context_pilot.context_pilot_app.tools import (
    retrieve_rag_documentation_tool,
    initialize_rag_tool,
    extract_experience_tool,
    save_experience_tool,
)

# Skill Registries
from context_pilot.skill_library.extensions import (
    root_skill_registry,
    report_skill_registry,
    analyze_skill_registry,
)

logger = logging.getLogger(__name__)

# --- RAG Initialization ---
# Knowledge base is stored in ADK_DATA_DIR (mounted at /app/adk_data in Docker)
data_dir = os.getenv("ADK_DATA_DIR", "adk_data")
rag_storage_path = os.getenv("RAG_STORAGE_DIR", os.path.join(data_dir, "rag_storage"))

if not os.path.isabs(rag_storage_path):
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    rag_storage_path = os.path.join(base_dir, rag_storage_path)

try:
    initialize_rag_tool(rag_storage_path)
    logger.info("RAG Tool initialized with storage path: %s", rag_storage_path)
except Exception as e:
    logger.warning("RAG Initialization Warning: %s", e)

# Define Agent
knowledge_agent = LlmAgent(
    name="knowledge_agent",
    model=MODEL,
    description="Agent responsible for searching the knowledge base (RAG), tracking experiences, and managing knowledge.",
    instruction=prompt.get_prompt(),
    tools=[
        FunctionTool(retrieve_rag_documentation_tool),
        extract_experience_tool,
        save_experience_tool,
        root_skill_registry,
        report_skill_registry,
        analyze_skill_registry,
    ],
)

root_agent = knowledge_agent
