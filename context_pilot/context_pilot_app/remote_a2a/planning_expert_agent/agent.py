import os
import logging
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import FunctionTool
from typing import Optional
from google.genai import types

from context_pilot.shared_libraries import constants
from context_pilot.shared_libraries.state_keys import StateKeys
from context_pilot.skill_library.extensions import root_skill_registry, report_skill_registry

from . import prompt
from .knowledge_tool import extract_experience_tool, save_experience_tool

# Import tools from main agent
from context_pilot.context_pilot_app.llama_rag_tool import retrieve_rag_documentation_tool, initialize_rag_tool
from context_pilot.context_pilot_app.tools import update_strategic_plan

logger = logging.getLogger(__name__)


async def before_planning_expert_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Callback to initialize the planning expert agent.
    Combines RAG initialization and experience state initialization.
    """
    state = callback_context.state
    
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
    
    # Initialize strategic plan if not present
    if StateKeys.STRATEGIC_PLAN not in state:
        state[StateKeys.STRATEGIC_PLAN] = "暂无计划"
    
    # RAG Initialization
    rag_storage_path = os.getenv("RAG_STORAGE_DIR")
    if not rag_storage_path:
        # Default: ProjectRoot/adk_data/rag_storage
        # Current file: .../context_pilot/context_pilot_app/remote_a2a/planning_expert_agent/agent.py
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        rag_storage_path = os.path.join(base_dir, "adk_data", "rag_storage")
    
    try:
        initialize_rag_tool(rag_storage_path)
    except Exception as e:
        logger.warning(f"RAG Initialization Warning: {e}")
        return types.Content(parts=[types.Part.from_text(
            text=f"⚠️ **System Warning**: Knowledge Base (RAG) is unavailable. "
                 f"Reason: {str(e)}. "
                 f"Strategic planning will proceed without RAG support."
        )])
    
    return None


planning_expert_agent = Agent(
    name="planning_expert_agent",
    model=constants.MODEL,
    description=(
        "Planning Expert Agent responsible for strategic planning, "
        "knowledge retrieval (RAG), and experience recording."
    ),
    instruction=prompt.PLANNING_EXPERT_PROMPT,
    output_key="planning_expert_output",
    before_agent_callback=before_planning_expert_callback,
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
        report_skill_registry
    ]
)

# Required for ADK agent discovery
root_agent = planning_expert_agent

# A2A app for remote access
# Usage: uvicorn context_pilot.context_pilot_app.remote_a2a.planning_expert_agent.agent:app --port 8001 --reload
from google.adk.a2a.utils.agent_to_a2a import to_a2a

app = to_a2a(
    planning_expert_agent,
    port=8001,  # Default port, can be overridden via uvicorn CLI: --port <port>
)
