from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from context_pilot.shared_libraries import constants
from skill_library.extensions import report_skill_registry
from . import prompt

from context_pilot.shared_libraries.constants import MODEL

import logging

logger = logging.getLogger(__name__)

from typing import Optional, List
from google.adk.tools import BaseTool

from .knowledge_tool import record_experience_tool

exp_recored_agent = Agent(
    name="exp_recored_agent",
    model=MODEL,
    description=(
        "Agent to record the experience of the user's interaction with the system."
    ),
    instruction=prompt.EXPERIENCE_RECORDING_PROMPT,
    output_key="record_experience_info",
    tools=[
        record_experience_tool,
        report_skill_registry
        ]
)

root_agent = exp_recored_agent


