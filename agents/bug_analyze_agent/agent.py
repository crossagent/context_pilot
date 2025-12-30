import os
# 2. Startup Check
PROJECT_ROOT = os.getenv("PROJECT_ROOT")
print(f"DEBUG: Startup PROJECT_ROOT is: '{PROJECT_ROOT}'")



if not PROJECT_ROOT:
    raise ValueError(f"严重错误：未在环境变量中配置 PROJECT_ROOT。")

# 3. Imports
from datetime import datetime

from agents.shared_libraries.constants import MODEL, USER_TIMEZONE
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from agents.shared_libraries import constants
from google.adk.apps.app import App
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.models.llm_response import LlmResponse
from google.adk.models.llm_request import LlmRequest
from . import prompt
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool
from typing import Optional
import logging
import platform

from .sub_agents.log_analyst import log_analysis_agent

from .tools import (
    time_convert_tool, 
    update_investigation_plan_tool,
    run_bash_command,
    read_file_tool,
    read_code_tool,
    search_code_tool,
    get_git_log_tool,
    get_git_diff_tool,
    get_blame_tool,
    deploy_fix_tool
)
from .tools.search_code import check_search_tools
# from agents.shared_libraries.plugin_loader import load_plugin_tools

from google.adk.tools import load_artifacts
from google.adk.planners import BuiltInPlanner
from google.genai import types
from agents.shared_libraries.state_keys import StateKeys, AgentKeys


logger = logging.getLogger(__name__)


async def initialize_and_validate(callback_context: CallbackContext) -> Optional[types.Content]:
    """Initialize agent context and validate required environment/inputs.
    
    Acts as a gatekeeper:
    1. Validates PROJECT_ROOT existence.
    2. Validates Search Tools (rg/git/grep).
    3. Validates clientLogUrl presence.
    4. Injects default values if validation passes.
    
    Returns:
        types.Content if validation fails (stopping execution).
        None if validation succeeds (continuing execution).
    """
    # 1. Validate PROJECT_ROOT
    if not PROJECT_ROOT or not os.path.exists(PROJECT_ROOT):
        error_msg = f"Critical Error: PROJECT_ROOT is invalid or not found at: {PROJECT_ROOT}"
        logger.error(error_msg)
        return types.Content(parts=[types.Part.from_text(text=error_msg)])

    # 2. Validate Search Tools
    search_error = check_search_tools()
    if search_error:
        logger.error(search_error)
        return types.Content(parts=[types.Part.from_text(text=search_error)])

    # 3. Validate clientLogUrl (Optional)

    # External processes should provide this if available.
    client_log_url = callback_context.state.get(StateKeys.CLIENT_LOG_URL)
    if not client_log_url:
         logger.warning("Warning: Missing 'clientLogUrl'. Agent will proceed without log analysis.")
         # Not returning error Content, allowing the agent to continue.

    # 3. Inject Defaults (Original Logic)
    inject_default_values(callback_context)

    # 4. [NEW] Inject Investigation Plan (Context Injection)
    # Strategy: Check State -> Check Artifact -> Default
    if StateKeys.CURRENT_INVESTIGATION_PLAN not in callback_context.state:
        plan_content = None
        try:
            # Try to load from Artifact Service (Persistence)
            plan_file_name = "investigation_plan.md"
            artifact_part = await callback_context.load_artifact(plan_file_name)
            
            if artifact_part:
                 # Handle Part content extraction
                 if artifact_part.text:
                     plan_content = artifact_part.text
                 elif artifact_part.inline_data:
                     plan_content = artifact_part.inline_data.data.decode('utf-8')
        except Exception as e:
            # Artifact might not exist or service error
            logger.warning(f"Failed to load investigation plan from artifact: {e}")

        if plan_content:
             callback_context.state[StateKeys.CURRENT_INVESTIGATION_PLAN] = plan_content
        else:
             callback_context.state[StateKeys.CURRENT_INVESTIGATION_PLAN] = "当前尚无调查计划 (No plan created yet). Use update_investigation_plan_tool to create one."
    
    # 5. Initialize Step Counter for Turn Restriction
    # Used by check_step_limit callback
    callback_context.state[StateKeys.STEP_COUNT] = 0

    return None

def check_step_limit(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """Callback to enforce a strict limit on autonomous steps triggers human intervention."""


    # Increment counter
    current_count = callback_context.state.get(StateKeys.STEP_COUNT, 0) + 1
    callback_context.state[StateKeys.STEP_COUNT] = current_count
    
    # Get limit from env, default to 30
    try:
        step_limit = int(os.environ.get("MAX_AUTONOMOUS_STEPS", 5))
    except ValueError:
        step_limit = 30

    if current_count > step_limit:
        logger.warning(f"Autonomous step limit ({step_limit}) reached. Forcing yield to user.")
        
        # Retrieve current plan for display
        current_plan = callback_context.state.get(StateKeys.CURRENT_INVESTIGATION_PLAN, "暂无计划内容")
        
        # Cleanup: Visualization is now handled by prompt instructions (Prompt-Driven).
        # No need for manual string replacement here.
        
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(
                    text=f"🛑 **自主探索暂停 (Autonomous Limit Reached)**\n\n"
                    f"我已经连续自主思考并执行了 {step_limit} 个步骤。为了确保调查方向符合您的预期，我先暂停一下。\n\n"
                    f"--- **当前调查计划 (Current Plan)** ---\n\n"
                    f"{current_plan}\n\n"
                    f"---------------------------------------\n"
                    f"请检视上述计划。\n"
                    f"- 如果方向正确，请指示我 **继续**。\n"
                    f"- 如果发现偏离，请 **指出问题**，我会立即调整。"
                )]
            )
        )
    
    return None

def inject_default_values(callback_context: CallbackContext):
    """在此代理初始化前设置默认值"""
    
    # 获取当前时间（带时区）
    current_time = datetime.now(USER_TIMEZONE)
    
    # 添加当前时间信息
    cur_date_time = current_time.strftime("%Y年%m月%d日 %H:%M:%S")
    callback_context.state[StateKeys.CUR_DATE_TIME] = cur_date_time

    # 添加当前时间戳
    cur_timestamp = int(current_time.timestamp())
    callback_context.state[StateKeys.CUR_TIMESTAMP] = cur_timestamp
    
    # Inject Current OS
    current_os = f"{platform.system()} {platform.release()}"
    callback_context.state[StateKeys.CURRENT_OS] = current_os

    # Inject Product Type
    product = os.getenv("PRODUCT", "未配置 (Unknown Product)")
    callback_context.state[StateKeys.PRODUCT] = product
    
    # Inject PROJECT_ROOT for prompt
    callback_context.state["project_root"] = PROJECT_ROOT

    if not callback_context.state.get(StateKeys.BUG_OCCURRENCE_TIME):
        callback_context.state[StateKeys.BUG_OCCURRENCE_TIME] = cur_date_time

    defaults = {
        StateKeys.BUG_USER_DESCRIPTION: "暂无用户描述 (No user description provided)",
        "deviceInfo": "Unknown",
        "deviceName": "Unknown",
        "productBranch": "Unknown",
        "roleId": "Unknown",
        "nickName": "Unknown",
        "serverId": "Unknown",
        "fps": "Unknown",
        "ping": "Unknown",
        StateKeys.CLIENT_LOG_URLS: "[]",
        StateKeys.CLIENT_SCREENSHOT_URLS: "[]"
    }
    for key, value in defaults.items():
        if key not in callback_context.state:
            callback_context.state[key] = value


# Load Core Tools
core_tools = [
    AgentTool(agent=log_analysis_agent),
    time_convert_tool, 
    update_investigation_plan_tool, 
    read_file_tool,
    read_code_tool,
    search_code_tool,
    run_bash_command,
    get_git_log_tool,
    get_git_diff_tool,
    get_blame_tool,
    load_artifacts,
    FunctionTool(
        deploy_fix_tool,
        require_confirmation=True
    )
]

bug_analyze_agent = VisualLlmAgent(
    name="bug_analyze_agent",
    model=MODEL,
    description=(
        "Agent to analyze the bug cause systematically via hypothesis and verification."
    ),
    planner=BuiltInPlanner(
          thinking_config=types.ThinkingConfig(
              include_thoughts=False,      # capture intermediate reasoning
              thinking_budget=1024        # tokens allocated for planning
          )
        ),
    instruction=prompt.get_prompt(),
    before_agent_callback=initialize_and_validate,
    before_model_callback=check_step_limit,

    tools=core_tools,
    output_key=AgentKeys.BUG_REASON,
)

app = App(
    name="bug_analyze_app",
    root_agent=bug_analyze_agent,
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=600,
        cache_intervals=10
    )
)

root_agent = bug_analyze_agent
