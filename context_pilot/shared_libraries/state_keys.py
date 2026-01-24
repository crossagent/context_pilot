# 定义所有状态键的常量
class StateKeys:
    # Device & Environment
    DEVICE_NAME = "device_name"
    CURRENT_OS = "current_os"

    # Bug Info
    BUG_USER_DESCRIPTION = "bug_user_description"
    
    # Product & Branch
    PRODUCT_DESCRIPTION = "product_description"
    CLIENT_VERSION = "client_version"

    # User Info
    SERVER_ID = "server_id"
    ROLE_ID = "role_id"
    NICK_NAME = "nick_name"
    
    # Performance
    FPS = "fps"
    PING = "ping"
    
    # Attachments
    CLIENT_LOG_URL = "client_log_url"
    CLIENT_LOG_URLS = "client_log_urls"  # LIST
    CLIENT_SCREENSHOT_URLS = "client_screenshot_urls"  # LIST

    # Time
    CUR_DATE_TIME = "cur_date_time"
    CUR_TIMESTAMP = "cur_timestamp"
    
    # Repository
    REPO_REGISTRY = "repo_registry"

    # Agent State
    USER_INTENT = "user_intent"
    CURRENT_INVESTIGATION_PLAN = "current_investigation_plan"
    STRATEGIC_PLAN = "strategic_plan"
    STEP_COUNT = "step_count"
    
    # Token Tracking Keys
    CURRENT_AUTONOMOUS_COST = "current_autonomous_cost"  # Float (USD)
    PAUSE_COUNT = "pause_count"  # Integer
    TOTAL_SESSION_TOKENS = "total_session_tokens"
    TOTAL_INPUT_TOKENS = "total_input_tokens"
    TOTAL_CACHED_TOKENS = "total_cached_tokens"
    TOTAL_OUTPUT_TOKENS = "total_output_tokens"
    TOTAL_ESTIMATED_COST = "total_estimated_cost"  # Float (USD)


class AgentKeys:
    BUG_REASON = "bug_reason_agent"
    USER_INTENT = "user_intent_agent"
    BUG_INFO = "bug_info_agent"
    BUG_REPORT = "bug_report_agent"