import os
import logging
import sys
from datetime import timezone, timedelta

# ... (您的 MODEL 相关代码保持不变) ...
MODEL = os.getenv("GOOGLE_GENAI_MODEL")
if not MODEL:
    MODEL = "gemini-3-flash-preview"

USER_TIMEZONE = timezone(timedelta(hours=8))

# 1. 从环境变量获取日志级别
loglevel = os.getenv("GOOGLE_GENAI_FOMC_AGENT_LOG_LEVEL", "INFO")
numeric_level = getattr(logging, loglevel.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {loglevel}")

# 2. 获取根 logger，这里我们为您的主包 "soc_bug_scene" 配置 logger
#    这样所有子模块 (e.g., bug_sleuth.agent) 都会继承这个配置
package_logger = logging.getLogger("bug_sleuth")
package_logger.setLevel(numeric_level)

# 阻止向根logger传播，避免重复输出
package_logger.propagate = False

# 3. 创建一个 Formatter 来定义日志格式
#    %(name)s - logger 的名字 (即模块名)
#    %(lineno)d - 日志消息所在的代码行号
#    %(levelname)s - 日志级别 (INFO, DEBUG, etc.)
#    %(message)s - 日志消息
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s (line:%(lineno)d)'
)

# 4. 创建一个 Handler 来决定日志输出到哪里 (例如：控制台)
#    并防止重复添加 handler
if not package_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    package_logger.addHandler(handler)

# 5. (可选) 导出当前模块的 logger，方便在本文件内使用
logger = logging.getLogger(__name__)