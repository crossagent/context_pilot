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
from .bug_report_agent.agent import bug_report_agent
from .tools import refine_bug_state, update_strategic_plan
from datetime import datetime
# from .skill_library.extensions import root_skill_registry, report_skill_registry, analyze_skill_registry
from bug_sleuth.skill_library.extensions import root_skill_registry, report_skill_registry, analyze_skill_registry
from bug_sleuth.shared_libraries import constants
from bug_sleuth.shared_libraries.state_keys import StateKeys

# RAG Imports
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag
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
    defaults = {
        StateKeys.STRATEGIC_PLAN: "暂无计划"
    }
    for key, value in defaults.items():
        if state.get(key) is None:
            state[key] = value

    return None

# --- RAG Tool Definition ---
retrieve_rag_documentation = VertexAiRagRetrieval(
    name='retrieve_rag_documentation',
    description=(
        'Use this tool to retrieve documentation and reference materials for the question from the RAG corpus.'
    ),
    rag_resources=[
        rag.RagResource(
            rag_corpus=os.environ.get("RAG_CORPUS", "projects/YOUR_PROJECT/locations/YOUR_LOCATION/ragCorpora/YOUR_CORPUS") # Fallback or env
        )
    ],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

from google.adk.tools import FunctionTool

# --- 4. Instantiate Root Agent (Global) ---
context_pilot_agent = LlmAgent(
    name="context_pilot_agent",
    model=constants.MODEL,
    instruction=ROOT_AGENT_PROMPT,
    sub_agents=[
        bug_analyze_agent,
        bug_report_agent,
    ],
    tools=[
        FunctionTool(refine_bug_state), 
        FunctionTool(update_strategic_plan), 
        retrieve_rag_documentation, 
        root_skill_registry
    ],
    before_agent_callback=before_agent_callback
)

