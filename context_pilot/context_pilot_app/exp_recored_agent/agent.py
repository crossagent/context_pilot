from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from context_pilot.shared_libraries import constants
from context_pilot.skill_library.extensions import report_skill_registry
from . import prompt

from context_pilot.shared_libraries.constants import MODEL

import logging

logger = logging.getLogger(__name__)

from typing import Optional, List
from google.adk.tools import BaseTool

from .knowledge_tool import extract_experience_tool, save_experience_tool

from context_pilot.shared_libraries.state_keys import StateKeys

def initialize_experience_state(context: CallbackContext):
    """Initializes experience recording state keys to None."""
    state = context.session.state
    keys_to_init = [
        StateKeys.EXP_INTENT,
        StateKeys.EXP_PROBLEM_CONTEXT,
        StateKeys.EXP_ROOT_CAUSE,
        StateKeys.EXP_SOLUTION_STEPS,
        StateKeys.EXP_EVIDENCE,
        StateKeys.EXP_TAGS,
        StateKeys.EXP_CONTRIBUTOR
    ]
    
    for key in keys_to_init:
        if key not in state:
            state[key] = None

exp_recored_agent = Agent(
    name="exp_recored_agent",
    model=MODEL,
    description=(
        "Agent to record the experience of the user's interaction with the system."
    ),
    instruction=prompt.EXPERIENCE_RECORDING_PROMPT,
    output_key="record_experience_info",
    before_agent_callback=initialize_experience_state,
    tools=[
        extract_experience_tool,
        save_experience_tool,
        report_skill_registry
        ]
)

root_agent = exp_recored_agent


