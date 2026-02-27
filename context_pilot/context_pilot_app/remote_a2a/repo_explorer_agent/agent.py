import os

# 3. Imports
from datetime import datetime
from context_pilot.shared_libraries.config_utils import load_and_inject_config

from context_pilot.shared_libraries.constants import MODEL, USER_TIMEZONE
from context_pilot.skill_library.extensions import analyze_skill_registry
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.run_config import RunConfig
from context_pilot.shared_libraries import constants
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


from .tools import (
    time_convert_tool, 
    run_bash_command,
    read_file_tool,
    search_file_tool, # Unified Search Tool
    get_git_log_tool,
    get_git_diff_tool,
    get_git_blame_tool,
    get_svn_log_tool,
    get_svn_diff_tool
)

from .tools.search_file import search_file_tool
from .tools.svn import get_svn_log_tool, get_svn_diff_tool

from google.adk.tools import load_artifacts
from google.adk.planners import BuiltInPlanner
from google.genai import types
from context_pilot.shared_libraries.state_keys import StateKeys, AgentKeys


logger = logging.getLogger(__name__)


async def initialize_and_validate(callback_context: CallbackContext) -> Optional[types.Content]:
    """在此代理初始化前运行的验证逻辑"""
    # [MODIFIED] Validation moved to Root Agent. Sub-agent assumes state is populated.
    inject_default_values(callback_context)
    
    # 1. Check if Repositories are available in State (Populated by Root Agent)
    # If missing (standalone sub-agent run), attempt to initialize using shared logic.
    if "repository_list" not in callback_context.state:
        logger.info("Info: Agent state not pre-initialized. Attempting to load configuration.")
        load_and_inject_config(callback_context.state)
        
        # Re-check after initialization attempt
        if "repository_list" not in callback_context.state:
            error_msg = (
                "CRITICAL ERROR: Repository Configuration Missing.\n"
                "Failed to initialize 'repository_list' from config.yaml.\n"
                "Please ensure Config File exists and contains 'repositories' list."
            )
            logger.error(error_msg)
            return types.Content(parts=[types.Part.from_text(text=error_msg)])


    # 2. Validate Search Tools (Unified Check)
    # The new tool checks for rg internally during execution or we can check shutil here
    # Since search_file_tool imports logic, we don't have a check_search_tools function there exposed yet.
    # But initialize_and_validate doesn't necessarily need to check rg if the tool handles it gracefully.
    # Or we can check it now.
    import shutil
    if not shutil.which("rg"):
        error_msg = "Critical Error: 'ripgrep' (rg) is missing. Please contact administrator to install it."
        logger.error(error_msg)
        return types.Content(parts=[types.Part.from_text(text=error_msg)])

    # 3. Validate clientLogUrl (Optional)

    # External processes should provide this if available.
    client_log_url = callback_context.state.get(StateKeys.CLIENT_LOG_URL)
    if not client_log_url:
         logger.warning("Warning: Missing 'clientLogUrl'. Agent will proceed without log analysis.")
         # Not returning error Content, allowing the agent to continue.

    # 5. Initialize Token & Cost Counters
    if StateKeys.TOTAL_SESSION_TOKENS not in callback_context.state:
        callback_context.state[StateKeys.TOTAL_SESSION_TOKENS] = 0
    if StateKeys.TOTAL_INPUT_TOKENS not in callback_context.state:
        callback_context.state[StateKeys.TOTAL_INPUT_TOKENS] = 0
    if StateKeys.TOTAL_CACHED_TOKENS not in callback_context.state:
        callback_context.state[StateKeys.TOTAL_CACHED_TOKENS] = 0
    if StateKeys.TOTAL_OUTPUT_TOKENS not in callback_context.state:
        callback_context.state[StateKeys.TOTAL_OUTPUT_TOKENS] = 0
    
    if StateKeys.TOTAL_ESTIMATED_COST not in callback_context.state:
        callback_context.state[StateKeys.TOTAL_ESTIMATED_COST] = 0.0
    if StateKeys.CURRENT_AUTONOMOUS_COST not in callback_context.state:
        callback_context.state[StateKeys.CURRENT_AUTONOMOUS_COST] = 0.0

    return None

class TokenLimitHandler:
    @staticmethod
    def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
        """Checks if COST budget is exceeded (Cost Logic restored, but Silent Output)."""
        
        current_autonomous_cost = callback_context.state.get(StateKeys.CURRENT_AUTONOMOUS_COST, 0.0)
        
        # Budget Configuration
        # [MODIFIED] Access config directly from State (flattened injection)
        max_budget = callback_context.state.get("max_autonomous_budget_usd", 0.5)

        # Log internal status (Debug only)
        # logger.info(f"Budget Check: ${current_autonomous_cost:.4f} / ${max_budget:.4f}")

        if current_autonomous_cost >= max_budget:
            # Increment Pause Count
            pause_count = callback_context.state.get(StateKeys.PAUSE_COUNT, 0) + 1
            callback_context.state[StateKeys.PAUSE_COUNT] = pause_count
            
            logger.warning(f"Cost budget reached (${current_autonomous_cost:.4f}). Pausing (Count: {pause_count}).")
            
            # Reset for next turn
            callback_context.state[StateKeys.CURRENT_AUTONOMOUS_COST] = 0.0
            
            # Get token stats
            total_input = callback_context.state.get(StateKeys.TOTAL_INPUT_TOKENS, 0)
            total_cached = callback_context.state.get(StateKeys.TOTAL_CACHED_TOKENS, 0)
            total_output = callback_context.state.get(StateKeys.TOTAL_OUTPUT_TOKENS, 0)
            
            # Friendly Message with Pause Count
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(
                        text=f"🛑 **自主探索暂停 (Autonomous Paused)** - 第 {pause_count} 次 (Sequence #{pause_count})\n\n"
                        f"已达到本次自动运行的资源上限 (Resource Limit Reached)。\n"
                        f"**本次会话统计 (Session Stats):**\n"
                        f"- 输入 (Input): {total_input} Tokens\n"
                        f"- 缓存 (Cached): {total_cached} Tokens\n"
                        f"- 输出 (Output): {total_output} Tokens\n\n"

                        f"请确认下一步行动 (Please confirm next step)：\n"
                        f"- **继续 (Continue)**: 重置计数器并继续任务。\n"
                        f"- **调整 (Adjust)**: 修改计划或停止。"
                    )]
                )
            )
        return None

    @staticmethod
    async def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
        """Tracks token usage, calculates cost, and updates autonomous loop count."""
        # 3. Update Token Counts
        if llm_response.usage_metadata:
            u = llm_response.usage_metadata
            total_prompt_tokens = u.prompt_token_count or 0
            cached_tokens = u.cached_content_token_count or 0
            output_tokens = u.candidates_token_count or 0
            
            # Gemini API prompt_token_count includes cached_tokens. 
            # We must subtract it to get the currently billed non-cached tokens.
            billed_input_tokens = max(0, total_prompt_tokens - cached_tokens)
            
            # Update Totals
            callback_context.state[StateKeys.TOTAL_INPUT_TOKENS] = callback_context.state.get(StateKeys.TOTAL_INPUT_TOKENS, 0) + billed_input_tokens
            callback_context.state[StateKeys.TOTAL_CACHED_TOKENS] = callback_context.state.get(StateKeys.TOTAL_CACHED_TOKENS, 0) + cached_tokens
            callback_context.state[StateKeys.TOTAL_OUTPUT_TOKENS] = callback_context.state.get(StateKeys.TOTAL_OUTPUT_TOKENS, 0) + output_tokens

            # Update Cost (Internal Tracking Only)
            # Direct access to State Config
            price_in = callback_context.state.get("price_per_million_input_tokens", 0.50)
            price_cached = callback_context.state.get("price_per_million_cached_tokens", 0.10)
            price_out = callback_context.state.get("price_per_million_output_tokens", 1.50)

            step_cost = (
                (billed_input_tokens / 1_000_000 * price_in) +
                (cached_tokens / 1_000_000 * price_cached) +
                (output_tokens / 1_000_000 * price_out)
            )
            
            callback_context.state[StateKeys.TOTAL_ESTIMATED_COST] = callback_context.state.get(StateKeys.TOTAL_ESTIMATED_COST, 0.0) + step_cost
            callback_context.state[StateKeys.CURRENT_AUTONOMOUS_COST] = callback_context.state.get(StateKeys.CURRENT_AUTONOMOUS_COST, 0.0) + step_cost
            
            # Log usage (no cost in INFO log if prefered, but keeping it for debug is usually fine. User request was about Prompt Output)
            logger.info(f"Step Stats: {input_tokens} In, {cached_tokens} Cache, {output_tokens} Out.")
        
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
    
    # Inject Formatted Repository List (For Prompt)
    # [MODIFIED] Assuming Root Agent strictly handles this. Logic removed.
    # repo_list_str logic moved to agent.py
    pass

    # Inject Product
    product_description = callback_context.state.get("product_description") or os.getenv("PRODUCT_DESCRIPTION") or "Rust-like Survival Game"
    callback_context.state[StateKeys.PRODUCT_DESCRIPTION] = product_description

    defaults = {
        StateKeys.BUG_USER_DESCRIPTION: "暂无用户描述 (No user description provided)",
        StateKeys.DEVICE_NAME: "Unknown",
        StateKeys.ROLE_ID: "Unknown",
        StateKeys.NICK_NAME: "Unknown",
        StateKeys.SERVER_ID: "Unknown",
        StateKeys.FPS: "Unknown",
        StateKeys.PING: "Unknown",
        StateKeys.CLIENT_LOG_URLS: "[]",
        StateKeys.CLIENT_SCREENSHOT_URLS: "[]",
        StateKeys.STRATEGIC_PLAN: "暂无计划"
    }
    for key, value in defaults.items():
        if key not in callback_context.state:
            callback_context.state[key] = value


from google.adk.agents.llm_agent import LlmAgent


repo_explorer_agent = LlmAgent(
    name="repo_explorer_agent",
    model=MODEL,
    description=(
        "Agent to explore the repository context and gathering facts."
    ),
    planner=BuiltInPlanner(
          thinking_config=types.ThinkingConfig(
              include_thoughts=False,      # capture intermediate reasoning
              thinking_budget=1024        # tokens allocated for planning
          )
        ),
    instruction=prompt.get_prompt(),
    before_agent_callback=initialize_and_validate,
    before_model_callback=TokenLimitHandler.before_model_callback,
    after_model_callback=TokenLimitHandler.after_model_callback,

    tools=[
        time_convert_tool, 
        run_bash_command,
        read_file_tool,

        search_file_tool,
        get_git_log_tool,
        get_git_diff_tool,
        get_git_blame_tool,
        get_svn_log_tool,
        get_svn_diff_tool,
        load_artifacts,
        analyze_skill_registry
    ],
    output_key=AgentKeys.BUG_REASON,
)

root_agent = repo_explorer_agent

# A2A app for remote access
# Usage: uvicorn context_pilot.context_pilot_app.remote_a2a.repo_explorer_agent.agent:app --port 8002 --reload
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.runners import Runner
from google.adk.plugins.context_cache_plugin import ContextCachePlugin

runner = Runner(
    plugins=[
        ContextCachePlugin(
            ContextCacheConfig(
                min_tokens=2048,
                ttl_seconds=600,
                cache_intervals=1,
            )
        )
    ]
)

app = to_a2a(
    repo_explorer_agent,
    host=os.getenv("A2A_HOST", "host.docker.internal"),
    port=8002,  # Default port, can be overridden via uvicorn CLI: --port <port>
    runner=runner
)
