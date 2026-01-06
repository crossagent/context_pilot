from google.adk.tools import ToolContext
import google.genai.types as types
from typing import Optional



async def update_investigation_plan_tool(
    tool_context: ToolContext,
    content: str
) -> str:
    """
    Overwrites the 'investigation_plan.md' with the provided Markdown content.
    Use this to create the initial plan or update the status/tasks.
    
    Format:
    ## Tasks
    - [V] Step 1
    - [_] Step 2
    """
    filename = "investigation_plan.md"
    try:
        plan_artifact = types.Part.from_bytes(
            data=content.encode('utf-8'),
            mime_type="text/markdown"
        )
        
        # Add metadata to hint UI about the task nature
        metadata = {
            "type": "task", 
            "subtype": "investigation_plan"
        }
        
        await tool_context.save_artifact(
            filename=filename,
            artifact=plan_artifact,
            custom_metadata=metadata
        )
        
        # Sync to State for Context Injection
        from bug_sleuth.agents.shared_libraries.state_keys import StateKeys
        tool_context.state[StateKeys.CURRENT_INVESTIGATION_PLAN] = content
        
        # Cleanup: Visualization is now handled by prompt instructions (Prompt-Driven).
        return f"Investigation Plan Updated:\n\n{content}"
    except Exception as e:
        return f"Error updating plan: {e}"
