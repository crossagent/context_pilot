import os
import logging
from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
# Note: Use LlmAgent for instantiation, but 'from google.adk import Agent' for sub-agents is fine if they prefer it.
from google.adk.apps.app import App
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .prompt import ROOT_AGENT_PROMPT
from .bug_analyze_agent.agent import create_bug_analyze_agent

from .bug_report_agent.agent import bug_report_agent
from .tools import update_bug_info_tool
from datetime import datetime
import bug_sleuth.services
from bug_sleuth.shared_libraries import constants
from bug_sleuth.shared_libraries.state_keys import StateKeys

logger = logging.getLogger(__name__)

# --- 1. Load Extensions (Services & Skills) ---
# Extensions must be loaded/configured by the entry point (e.g. bridge_agent.py) *before* this module is imported.
pass

# Retrieve injected assets for bug_analyze_agent
analyze_agent_tools = bug_sleuth.services.get_loaded_tools("bug_analyze_agent")

if analyze_agent_tools:
    logger.info(f"Injected {len(analyze_agent_tools)} tools into bug_analyze_agent.")

# --- 2. Create Sub-Agents ---
analyze_agent_instance = create_bug_analyze_agent(
    extra_tools=analyze_agent_tools
)

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
agent = LlmAgent(
    name="bug_scene_agent",
    model=constants.MODEL,
    instruction=ROOT_AGENT_PROMPT,
    sub_agents=[
        analyze_agent_instance,
        bug_report_agent,
    ],
    tools=[update_bug_info_tool],
    before_agent_callback=before_agent_callback
)

# --- 5. Instantiate App (Global) ---
app = App(
    name="bug_scene_app",
    root_agent=agent,
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=600,
        cache_intervals=10,
    )
)