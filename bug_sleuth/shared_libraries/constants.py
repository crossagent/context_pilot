import os
import logging
import sys
from datetime import timezone, timedelta
from typing import Union, Any

# =============================================================================
# Model Configuration
# =============================================================================

def get_model() -> Union[str, Any]:
    """
    Get the model instance based on environment variable.
    
    Supported formats:
    - "gemini-2.0-flash" (default) -> Returns string, ADK handles natively
    - "mock/xxx" -> Returns MockLlm instance for testing
    - "openai/gpt-4o" -> Returns LiteLlm instance (requires litellm package)
    - "anthropic/claude-3-sonnet" -> Returns LiteLlm instance
    
    Set via environment variable: GOOGLE_GENAI_MODEL
    """
    model_str = os.getenv("GOOGLE_GENAI_MODEL", "gemini-3-flash-preview")
    
    # Mock mode for testing
    if model_str.startswith("mock/"):
        try:
            from bug_sleuth.testing import MockLlm
            return MockLlm(model=model_str)
        except ImportError:
            raise ImportError(
                f"MockLlm requested ({model_str}) but bug_sleuth.testing usage failed. "
                "Ensure bug_sleuth package is installed correctly."
            )
    
    # LiteLLM mode for OpenAI/Anthropic/other providers
    # Format: "provider/model-name" (e.g., "openai/gpt-4o", "anthropic/claude-3")
    if "/" in model_str and not model_str.startswith("gemini"):
        try:
            from google.adk.models.lite_llm import LiteLlm
            return LiteLlm(model=model_str)
        except ImportError:
            raise ImportError(
                f"LiteLLM model requested ({model_str}) but litellm package not installed. "
                "Run: pip install litellm"
            )
    
    # Default: Return string for native Gemini support
    return model_str


# Global MODEL instance - evaluated once at import time
MODEL = get_model()

# =============================================================================
# Timezone Configuration
# =============================================================================

USER_TIMEZONE = timezone(timedelta(hours=8))

# =============================================================================
# Logging Configuration
# =============================================================================

# 1. Get log level from environment
loglevel = os.getenv("GOOGLE_GENAI_FOMC_AGENT_LOG_LEVEL", "INFO")
numeric_level = getattr(logging, loglevel.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {loglevel}")

# 2. Configure package logger
package_logger = logging.getLogger("bug_sleuth")
package_logger.setLevel(numeric_level)

# Prevent propagation to root logger to avoid duplicate output
package_logger.propagate = False

# 3. Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s (line:%(lineno)d)'
)

# 4. Add handler (only once)
if not package_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    package_logger.addHandler(handler)

# 5. Export module logger
logger = logging.getLogger(__name__)

# Log initial model configuration
logger.info(f"Model configured: {MODEL}")