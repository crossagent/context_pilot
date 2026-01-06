import os
import logging
from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
# Note: Use LlmAgent for instantiation, but 'from google.adk import Agent' for sub-agents is fine if they prefer it.
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .prompt import ROOT_AGENT_PROMPT
from .bug_analyze_agent.agent import bug_analyze_agent

from .bug_report_agent.agent import bug_report_agent
from .tools import update_bug_info_tool
from datetime import datetime
from .skill_library.skill_loader import SkillLoader
from .skill_library.extensions import RootAgentExtension, BugReportExtension
from .shared_libraries import constants
from .shared_libraries.state_keys import StateKeys

logger = logging.getLogger(__name__)

# --- 1. Load Extensions (Services & Skills) ---
# Explicitly initialize the Skill System here in the Agent Entry Point

skill_loader = None
skill_path = os.getenv("SKILL_PATH")
root_extensions = []
report_extensions = []

if skill_path and os.path.exists(skill_path):
    logger.info(f"Initializing Skill System from: {skill_path}")
    skill_loader = SkillLoader(skill_path)
    # Define which interfaces we care about
    targets = [RootAgentExtension, BugReportExtension]
    skill_loader.load_extensions(targets)
    
    # Retrieve instantiated extensions
    root_extensions = skill_loader.get_extensions_by_type(RootAgentExtension)
    report_extensions = skill_loader.get_extensions_by_type(BugReportExtension)
    
if root_extensions:
    logger.info(f"Injected {len(root_extensions)} extensions into Root Agent.")

if report_extensions:
    logger.info(f"Injected {len(report_extensions)} extensions into Bug Report Agent.")

# --- 2. Create Sub-Agents ---
# Inject Report Extensions into the Bug Report Agent
# Since bug_report_agent is a singleton instance, we extend its tools list in-place.
if report_extensions:
    for ext in report_extensions:
        # Check if ADK Agent exposes 'tools' list directly (it usually does)
        # We append to the existing tools list.
        if hasattr(bug_report_agent, "tools"):
            # LlmAgent tools can be mixed BaseTool/BaseToolset.
            bug_report_agent.tools.append(ext)
        else:
            logger.warning("Could not inject extensions: bug_report_agent has no 'tools' attribute.")

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
        bug_analyze_agent,
        bug_report_agent,
    ],
    tools=[update_bug_info_tool] + root_extensions,
    before_agent_callback=before_agent_callback
)

# --- 5. Instantiate App (Global) ---
app = App(
    name="bug_scene_app",
    root_agent=agent,
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=600,
        cache_intervals=1,
    ),
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,
        overlap_size=1
    )
)