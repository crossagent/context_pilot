import logging
from typing import Optional
from google.adk.tools import ToolContext
from context_pilot.shared_libraries.state_keys import StateKeys

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


async def update_strategic_plan(tool_context: ToolContext, plan_content: str):
    """
    Update the Strategic Plan (Query Plan) with user review and approval (Human-in-the-Loop).
    Uses ADK Advanced Confirmation to pause execution until user approves or rejects.

    Args:
        plan_content: The full content of the plan, describing what information needs to be gathered and from where.
                      Format suggestions: Markdown list or steps.
    """
    # Check if this is the confirmation response (second call after user interaction)
    tool_confirmation = tool_context.tool_confirmation
    
    if not tool_confirmation:
        # First call - request user confirmation
        logger.info(f"Requesting user confirmation for strategic plan ({len(plan_content)} chars)")
        tool_context.request_confirmation(
            hint="Please review and approve the strategic investigation plan. You can edit it before approving.",
            payload={
                "plan_content": plan_content,
                "approved": False
            }
        )
        # Return intermediate status - MUST be dict format
        return {'status': 'User approval is required.'}
    
    # Second call - process confirmation response
    confirmation_data = tool_confirmation.payload
    
    if confirmation_data.get('approved'):
        # User approved - use the (possibly edited) plan content
        final_content = confirmation_data.get('plan_content', plan_content)
        
        # 1. Update State
        state = tool_context.state
        state[StateKeys.STRATEGIC_PLAN] = final_content
        
        # 2. Persist to Artifact
        try:
            from google.genai import types
            plan_artifact = types.Part.from_bytes(
                data=final_content.encode('utf-8'),
                mime_type="text/markdown"
            )
            
            metadata = {
                "type": "task", 
                "subtype": "investigation_plan"
            }
            
            await tool_context.save_artifact(
                filename="investigation_plan.md",
                artifact=plan_artifact,
                custom_metadata=metadata
            )
            
            logger.info(f"Strategic plan approved and saved ({len(final_content)} chars)")
            return {
                'status': 'ok',
                'message': 'Strategic plan approved and saved successfully.',
                'plan_length': len(final_content)
            }
        except Exception as e:
            logger.error(f"Failed to save plan artifact: {e}")
            return {
                'status': 'error',
                'message': f'Failed to save artifact: {e}'
            }
    else:
        # User rejected
        reason = confirmation_data.get('reason', 'User rejected the plan')
        logger.info(f"Strategic plan rejected: {reason}")
        return {
            'status': 'rejected',
            'reason': reason
        }
