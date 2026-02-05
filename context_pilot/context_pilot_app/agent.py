import os
import json
import yaml
import logging
from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
# Note: Use LlmAgent for instantiation, but 'from google.adk import Agent' for sub-agents is fine if they prefer it.
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .prompt import ROOT_AGENT_PROMPT
from .repo_explorer_agent.agent import repo_explorer_agent
from .exp_recored_agent.agent import exp_recored_agent
from .tools import refine_bug_state, update_strategic_plan
from datetime import datetime
# from .skill_library.extensions import root_skill_registry, report_skill_registry, analyze_skill_registry
from context_pilot.skill_library.extensions import root_skill_registry, report_skill_registry, analyze_skill_registry
from context_pilot.shared_libraries import constants
from context_pilot.shared_libraries.state_keys import StateKeys
from context_pilot.shared_libraries.config_utils import load_and_inject_config

# RAG Imports
from .llama_rag_tool import retrieve_rag_documentation_tool, initialize_rag_tool
from dotenv import load_dotenv

load_dotenv()


logger = logging.getLogger(__name__)

# --- 1. Load Extensions (Services & Skills) ---
# Skill loading is now handled in server.py (or app.py) before agent initialization.

# Log registry status
# (Accessing private _tools for logging purpose is acceptable here, or add public property if preferred)
logger.info(f"Root Skill Registry has {len(root_skill_registry._tools)} tools.")
logger.info(f"Report Skill Registry has {len(report_skill_registry._tools)} tools.")
logger.info(f"Analyze Skill Registry has {len(analyze_skill_registry._tools)} tools.")

# --- 3. Callback Definition ---
async def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback function to be executed before each agent runs.
    """
    
    state = callback_context.state
    if not state.get("session_initialized"):
        # First interaction check
        if state.get("deviceInfo") is not None:
              state["session_initialized"] = True
              
    if not state.get(StateKeys.CUR_DATE_TIME):
        current_time = datetime.now(constants.USER_TIMEZONE)
        state[StateKeys.CUR_DATE_TIME] = current_time.strftime("%Y年%m月%d日 %H:%M:%S")

    # Initialize default values for required prompt keys to prevent KeyError
    # Initialize default values for required prompt keys to prevent KeyError
    defaults = {
        StateKeys.STRATEGIC_PLAN: "暂无计划"
    }

    # [NEW] Inject Configuration & Repositories (Using Shared Library)
    load_and_inject_config(state)

    # [NEW] Load Strategic Plan from Artifact if available
    # This ensures the root agent sees the persistent plan across turns/restarts if state was lost or just initialized.
    if StateKeys.STRATEGIC_PLAN not in state or state[StateKeys.STRATEGIC_PLAN] == "暂无计划":
        try:
            plan_file_name = "investigation_plan.md"
            # load_artifact returns types.Part or None
            artifact_part = await callback_context.load_artifact(plan_file_name)
            
            if artifact_part:
                 if artifact_part.text:
                     state[StateKeys.STRATEGIC_PLAN] = artifact_part.text
                 elif artifact_part.inline_data:
                     try:
                        state[StateKeys.STRATEGIC_PLAN] = artifact_part.inline_data.data.decode('utf-8')
                     except:
                        pass
        except Exception as e:
            logger.warning(f"Failed to load strategic plan artifact: {e}")

    for key, value in defaults.items():
        if state.get(key) is None:
            state[key] = value

    # RAG Initialization
    rag_storage_path = os.getenv("RAG_STORAGE_DIR")
    if not rag_storage_path:
        # Default: ProjectRoot/adk_data/rag_storage
        # Current file: .../context_pilot/context_pilot_app/agent.py
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        rag_storage_path = os.path.join(base_dir, "adk_data", "rag_storage")

    try:
        initialize_rag_tool(rag_storage_path)
    except Exception as e:
        logger.warning(f"RAG Initialization Warning: {e}")
        # Return a warning message to the model so it knows RAG is offline
        return types.Content(parts=[types.Part.from_text(
            text=f"⚠️ **System Warning**: Knowledge Base (RAG) is unavailable. "
                 f"Reason: {str(e)}. "
                 f"Please proceed using available tools only."
        )])

    return None


# --- RAG Tool Definition ---


from google.adk.tools import FunctionTool

# --- 4. Instantiate Root Agent (Global) ---
# Build tools list based on mode (Unified Mode)
# ADK-Web mode: Include all backend tools

context_pilot_agent = LlmAgent(
    name="context_pilot_agent",
    model=constants.MODEL,
    instruction=ROOT_AGENT_PROMPT,
    sub_agents=[
        repo_explorer_agent,
        #exp_recored_agent,
    ],
    tools=[
        FunctionTool(retrieve_rag_documentation_tool),  # Primary Knowledge Source
        #FunctionTool(refine_bug_state),
        root_skill_registry,
        FunctionTool(update_strategic_plan)
    ],
    before_agent_callback=before_agent_callback
)

