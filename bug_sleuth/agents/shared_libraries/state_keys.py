# 定义所有状态键的常量
class StateKeys:
    DEVICE_INFO = "deviceInfo"
    DEVICE_NAME = "deviceName"


    BUG_DESCRIPTION = "bug_description"
    BUG_USER_DESCRIPTION = "bug_user_description"
    PRODUCT_BRANCH = "productBranch"
    CLIENT_LOG_URL = "clientLogUrl"
    CLIENT_LOG_URLS = "clientLogUrls"  # LIST
    CLIENT_SCREENSHOT_URLS = "clientScreenshotUrls"  # LIST
    CLIENT_VERSION = "clientVersion"
    SERVER_ID = "serverId"
    ROLE_ID = "roleId"
    NICK_NAME = "nickName"
    BUG_OCCURRENCE_TIME = "bug_occurrence_time"
    FPS = "fps"
    PING = "ping"

    CUR_DATE_TIME = "cur_date_time"
    CUR_TIMESTAMP = "cur_timestamp"
    CURRENT_OS = "current_os"
    REPO_REGISTRY = "repo_registry"
    REPOSITORY_LIST_FORMATTED = "repository_list"
    PRODUCT_DESCRIPTION = "product_description"

    USER_INTENT = "user_intent"

    BUG_DESCRIPTION = "bug_description"


    CURRENT_INVESTIGATION_PLAN = "current_investigation_plan"
    STEP_COUNT = "step_count"
    
    # [NEW] Token Tracking Keys
    CURRENT_AUTONOMOUS_COST = "current_autonomous_cost"        # Float (USD)

    PAUSE_COUNT = "pause_count" # Integer
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