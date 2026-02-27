import os
import json
import yaml
import logging
from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
# Note: Use LlmAgent for instantiation, but 'from google.adk import Agent' for sub-agents is fine if they prefer it.
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .prompt import PLANNING_EXPERT_PROMPT
# repo_explorer_agent accessed as remote sub_agent via A2A (runs on local machine)
# Tools now loaded from the dedicated tools folder
from .tools import (
    refine_bug_state,
    update_strategic_plan,
    retrieve_rag_documentation_tool,
    initialize_rag_tool,
    extract_experience_tool,
    save_experience_tool
)
from google.adk.tools import FunctionTool
from datetime import datetime
# from .skill_library.extensions import root_skill_registry, report_skill_registry, analyze_skill_registry
from context_pilot.skill_library.extensions import root_skill_registry, report_skill_registry, analyze_skill_registry
from context_pilot.shared_libraries import constants
from context_pilot.shared_libraries.state_keys import StateKeys
from context_pilot.shared_libraries.config_utils import load_and_inject_config

# Shared Configuration
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

    # Initialize experience recording state keys
    exp_keys_to_init = [
        StateKeys.EXP_INTENT,
        StateKeys.EXP_PROBLEM_CONTEXT,
        StateKeys.EXP_ROOT_CAUSE,
        StateKeys.EXP_SOLUTION_STEPS,
        StateKeys.EXP_EVIDENCE,
        StateKeys.EXP_TAGS,
        StateKeys.EXP_CONTRIBUTOR
    ]
    
    for key in exp_keys_to_init:
        if key not in state:
            state[key] = None

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

    # --- RAG Initialization ---
    rag_storage_path = os.getenv("RAG_STORAGE_DIR")
    if not rag_storage_path:
        # Default: ProjectRoot/adk_data/rag_storage
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rag_storage_path = os.path.join(base_dir, "adk_data", "rag_storage")
    
    try:
        initialize_rag_tool(rag_storage_path)
    except Exception as e:
        logger.warning(f"RAG Initialization Warning: {e}")
        # Not returning a system warning part here to avoid blocking UI immediately,
        # but could optionally append one.

    return None


from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

# --- 4. Instantiate Root Agent (Global) ---
# Build tools list based on mode (Unified Mode)
# ADK-Web mode: Include all backend tools

# Remote Repo Explorer Agent via A2A (runs on local machine, needs local file system access)
repo_explorer_url = os.getenv("REPO_EXPLORER_URL", "http://localhost:8002")
repo_explorer_agent = RemoteA2aAgent(
    name="repo_explorer_agent",
    description="Agent to explore the repository context and gather facts (file reading, search, git/svn, bash commands).",
    agent_card=f"{repo_explorer_url}{AGENT_CARD_WELL_KNOWN_PATH}"
)

context_pilot_agent = LlmAgent(
    name="context_pilot_agent",
    model=constants.MODEL,
    instruction=PLANNING_EXPERT_PROMPT,
    sub_agents=[
        repo_explorer_agent,
    ],
    tools=[
        # Strategic Planning
        FunctionTool(update_strategic_plan),
        
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
    before_agent_callback=before_agent_callback
)

