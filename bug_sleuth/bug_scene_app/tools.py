import logging
from typing import Optional
from google.adk.tools import ToolContext
from bug_sleuth.shared_libraries.state_keys import StateKeys

logger = logging.getLogger(__name__)

def refine_bug_state(
    tool_context: ToolContext,
    device_name: Optional[str] = None,
    fps: Optional[str] = None,
    ping: Optional[str] = None,
    nick_name: Optional[str] = None,
    client_version: Optional[str] = None
) -> str:
    """
    Refine and update the bug state with new or corrected information.
    
    Args:
        device_name: Specific device model (e.g., Pixel 6, iPhone 13).
        fps: Frame per second at the time of the bug.
        ping: Network latency (ms).
        nick_name: User's nickname.
        client_version: The version of the client software.
    """
    state = tool_context.state
    updated_fields = []

    if device_name:
        state[StateKeys.DEVICE_NAME] = device_name
        updated_fields.append(StateKeys.DEVICE_NAME)

    if fps:
        state[StateKeys.FPS] = fps
        updated_fields.append(StateKeys.FPS)

    if ping:
        state[StateKeys.PING] = ping
        updated_fields.append(StateKeys.PING)

    if nick_name:
        state[StateKeys.NICK_NAME] = nick_name
        updated_fields.append(StateKeys.NICK_NAME)

    if client_version:
        state[StateKeys.CLIENT_VERSION] = client_version
        updated_fields.append(StateKeys.CLIENT_VERSION)
        
    if not updated_fields:
        return "No information provided to update."

    return f"Successfully updated fields: {', '.join(updated_fields)}"


def update_strategic_plan(tool_context: ToolContext, plan_content: str) -> str:
    """
    Update the Strategic Plan (Query Plan) for the current session.

    Args:
        plan_content: The full content of the plan, describing what information needs to be gathered and from where.
                      Format suggestions: Markdown list or steps.
    """
    state = tool_context.state
    state[StateKeys.STRATEGIC_PLAN] = plan_content
    return f"Strategic Plan updated. Current Plan:\n{plan_content}"
