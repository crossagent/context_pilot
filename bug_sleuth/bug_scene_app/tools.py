import logging
from typing import Optional
from google.adk.tools import ToolContext
from .shared_libraries.state_keys import StateKeys

logger = logging.getLogger(__name__)

def update_bug_info_tool(
    tool_context: ToolContext,
    bug_description: Optional[str] = None,
    occurrence_time: Optional[str] = None,
    product_branch: Optional[str] = None,
    device_info: Optional[str] = None,
    device_name: Optional[str] = None
) -> str:
    """
    更新Bug的基础信息到共享状态中。
    
    Args:
        bug_description: Bug的详细描述。
        occurrence_time: Bug发生的时间。
        product_branch: 代码分支。
        device_info: 设备平台信息 (e.g. Android, iOS)。
        device_name: 具体设备名称 (e.g. Pixel 6)。
    """
    state = tool_context.state
    updated_fields = []

    if bug_description:
        state[StateKeys.BUG_DESCRIPTION] = bug_description
        updated_fields.append("bug_description")
    
    if occurrence_time:
        state[StateKeys.BUG_OCCURRENCE_TIME] = occurrence_time
        updated_fields.append("occurrence_time")
        
    if product_branch:
        state[StateKeys.PRODUCT_BRANCH] = product_branch
        updated_fields.append("product_branch")
        
    if device_info:
        state[StateKeys.DEVICE_INFO] = device_info
        updated_fields.append("device_info")
        
    if device_name:
        state[StateKeys.DEVICE_NAME] = device_name
        updated_fields.append("device_name")

    if not updated_fields:
        return "未提供任何信息进行更新。"

    return f"成功更新了以下信息: {', '.join(updated_fields)}"
