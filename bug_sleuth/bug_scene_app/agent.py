import os
import logging
from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
# Note: Use LlmAgent for instantiation, but 'from google.adk import Agent' for sub-agents is fine if they prefer it.
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .prompt import ROOT_AGENT_PROMPT
from .bug_analyze_agent.agent import bug_analyze_agent

from .bug_report_agent.agent import bug_report_agent
from .tools import update_bug_info_tool
from datetime import datetime
from .skill_library.skill_loader import SkillLoader
from .skill_library.extensions import root_skill_registry, report_skill_registry
from .shared_libraries import constants
from .shared_libraries.state_keys import StateKeys

logger = logging.getLogger(__name__)

# --- 1. Load Extensions (Services & Skills) ---
skill_loader = None
skill_path = os.getenv("SKILL_PATH")

if skill_path and os.path.exists(skill_path):
    logger.info(f"Initializing Skill System from: {skill_path}")
    skill_loader = SkillLoader(skill_path)
    # Just run the skills; they will self-register into the singletons imported above
    skill_loader.load_skills()
    
# Log registry status
# (Accessing private _tools for logging purpose is acceptable here, or add public property if preferred)
logger.info(f"Root Skill Registry has {len(root_skill_registry._tools)} tools.")
logger.info(f"Report Skill Registry has {len(report_skill_registry._tools)} tools.")

# --- 2. Create Sub-Agents ---
# bug_report_agent now has report_skill_registry pre-embedded.
pass

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

    return None

# --- 4. Instantiate Root Agent (Global) ---
bug_scene_agent = LlmAgent(
    name="bug_scene_agent",
    model=constants.MODEL,
    instruction=ROOT_AGENT_PROMPT,
    sub_agents=[
        bug_analyze_agent,
        bug_report_agent,
    ],
    tools=[update_bug_info_tool, root_skill_registry],
    before_agent_callback=before_agent_callback
)

