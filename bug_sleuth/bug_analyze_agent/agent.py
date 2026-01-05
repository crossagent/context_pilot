import os
import json
import yaml
from pathlib import Path

# 2. Startup Check & Configuration Loading
def load_config():
    config_path = os.getenv("CONFIG_FILE", "bug_sleuth/config.yaml")
    if not os.path.exists(config_path):
        # Fallback to local if running from agents dir
        if os.path.exists("config.yaml"):
             config_path = "config.yaml"
        else:
             print(f"WARNING: Config file not found at {config_path}. Using default empty config.")
             return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise ValueError(f"Critical Error: Failed to load config file: {e}")

CONFIG = load_config()

# Repositories
# Repositories (Lazy Load or Default Empty)
REPO_REGISTRY = CONFIG.get("repositories", [])

# Note: Strict validation moved to initialize_and_validate or factory to allow import without config.
if not REPO_REGISTRY:
    # Try legacy env var
    try:
        if env_repos := os.getenv("REPOSITORIES"):
            REPO_REGISTRY = json.loads(env_repos)
    except:
        pass


# 3. Imports
from datetime import datetime

from ..shared_libraries.constants import MODEL, USER_TIMEZONE
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.run_config import RunConfig
from ..shared_libraries import constants
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
    get_git_blame_tool,
    deploy_fix_tool
)
from .tools.search_code import check_search_tools

from google.adk.tools import load_artifacts
from google.adk.planners import BuiltInPlanner
from google.genai import types
from ..shared_libraries.state_keys import StateKeys, AgentKeys


logger = logging.getLogger(__name__)


async def initialize_and_validate(callback_context: CallbackContext) -> Optional[types.Content]:
    """在此代理初始化前运行的验证逻辑"""
    inject_default_values(callback_context)
    # 1. Validate Repositories
    # (Already validated at startup, but good to ensure state is clean)
    if not REPO_REGISTRY:
         return types.Content(parts=[types.Part(text="Error: No configured repositories available.")])


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
    
    # 5. Initialize Token Counters (if not present)
    if StateKeys.TOTAL_SESSION_TOKENS not in callback_context.state:
        callback_context.state[StateKeys.TOTAL_SESSION_TOKENS] = 0
    if StateKeys.CURRENT_AUTONOMOUS_TOKENS not in callback_context.state:
        callback_context.state[StateKeys.CURRENT_AUTONOMOUS_TOKENS] = 0

    return None

class TokenLimitHandler:
    @staticmethod
    def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
        """Checks if token budget is exceeded for the current autonomous loop."""
        
        current_tokens = callback_context.state.get(StateKeys.CURRENT_AUTONOMOUS_TOKENS, 0)
        
        # Soft Limit Configuration
        max_tokens = CONFIG.get("max_autonomous_tokens")
        if not max_tokens:
             max_tokens = int(os.environ.get("MAX_AUTONOMOUS_TOKENS", 8000))

        if current_tokens > max_tokens:
            logger.warning(f"Token budget ({max_tokens}) reached. Forcing yield to user.")
            
            # Reset Loop Counters for the NEXT run (Auto-Recharge)
            callback_context.state[StateKeys.CURRENT_AUTONOMOUS_TOKENS] = 0
            
            current_plan = callback_context.state.get(StateKeys.CURRENT_INVESTIGATION_PLAN, "暂无计划内容")
            total_tokens = callback_context.state.get(StateKeys.TOTAL_SESSION_TOKENS, 0)

            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(
                        text=f"🛑 **自主探索暂停 ({current_tokens} Tokens)**\n\n"
                        f"当前的自主探索已消耗约 **{current_tokens}** Tokens (本次会话总消耗: {total_tokens})。\n"
                        f"为了确保调查方向符合您的预期，我先暂停一下。\n\n"
                        f"--- **当前调查计划 (Current Plan)** ---\n\n"
                        f"{current_plan}\n\n"
                        f"---------------------------------------\n"
                        f"请检视上述计划。\n"
                        f"- 如果方向正确，请指示我 **继续** (预算已自动重置)。\n"
                        f"- 如果发现偏离，请 **指出问题**，我会立即调整。"
                    )]
                )
            )
        return None

    @staticmethod
    async def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
        """Tracks token usage from the model response."""
        if llm_response.usage_metadata:
             new_tokens = llm_response.usage_metadata.total_token_count
             
             # Accumulate
             callback_context.state[StateKeys.TOTAL_SESSION_TOKENS] = \
                 callback_context.state.get(StateKeys.TOTAL_SESSION_TOKENS, 0) + new_tokens
             
             callback_context.state[StateKeys.CURRENT_AUTONOMOUS_TOKENS] = \
                 callback_context.state.get(StateKeys.CURRENT_AUTONOMOUS_TOKENS, 0) + new_tokens
             
             logger.debug(f"Token Usage Updated: +{new_tokens} -> Limit: {callback_context.state[StateKeys.CURRENT_AUTONOMOUS_TOKENS]}")
        
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
    
    # Inject Repository Registry (Object)
    callback_context.state[StateKeys.REPO_REGISTRY] = REPO_REGISTRY
    
    # Inject Formatted Repository List (For Prompt)
    repo_list_str = []
    for r in REPO_REGISTRY:
        repo_list_str.append(f"- **{r.get('name')}**: `{r.get('path')}` - {r.get('description', '')}")
    callback_context.state["repository_list"] = "\n    ".join(repo_list_str)

    if not callback_context.state.get(StateKeys.BUG_OCCURRENCE_TIME):
        callback_context.state[StateKeys.BUG_OCCURRENCE_TIME] = cur_date_time

    # Inject Product
    product_description = CONFIG.get("product_description") or os.getenv("PRODUCT_DESCRIPTION") or "Rust-like Survival Game"
    callback_context.state[StateKeys.PRODUCT_DESCRIPTION] = product_description

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


from google.adk.agents.llm_agent import LlmAgent
from ..shared_libraries.visual_llm_agent import VisualLlmAgent

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
    before_model_callback=TokenLimitHandler.before_model_callback,
    after_model_callback=TokenLimitHandler.after_model_callback,

    tools=[
        AgentTool(agent=log_analysis_agent),
        time_convert_tool, 
        update_investigation_plan_tool, 
        run_bash_command,
        read_file_tool,
        read_code_tool,
        search_code_tool,
        get_git_log_tool,
        get_git_diff_tool,
        get_git_blame_tool,
        load_artifacts,
        FunctionTool(
            deploy_fix_tool,
            require_confirmation=True
        )
    ],
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
