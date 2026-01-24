from datetime import datetime
from context_pilot.shared_libraries.constants import USER_TIMEZONE

# --- Utility Tools ---

def time_convert_tool(beijing_time: str) -> int:
    """
    将指定时区的时间字符串转换为Unix时间戳

    Args:
        beijing_time: 时间字符串，格式为"YYYY-MM-DD HH:MM:SS"

    Returns:
        int: Unix时间戳
    """
    # 解析时间字符串
    dt = datetime.strptime(beijing_time, "%Y-%m-%d %H:%M:%S")

    # 设置时区
    dt_with_tz = dt.replace(tzinfo=USER_TIMEZONE)

    # 转换为时间戳并返回整数
    return int(dt_with_tz.timestamp())
