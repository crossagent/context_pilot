from enum import Enum
from google.adk.tools import ToolContext
import google.genai.types as types
from typing import List, Dict, Union, Optional, TypedDict
import re
import requests
from datetime import datetime
from bug_sleuth.agents.shared_libraries.constants import USER_TIMEZONE

# --- Log Tools Definitions ---

# 定义一个 TypedDict 来清晰地描述日志条目的结构
class LogEntry(TypedDict):
    original_index: int # 用于追踪原始顺序
    time: str
    logtype: str
    content: str

def _parse_log_content(log_content: str) -> List[LogEntry]:
    """
    将原始日志文本解析为结构化的日志条目列表。
    """
    parsed_logs: List[LogEntry] = []
    # 正则表达式，用于匹配并捕获三个关键部分：
    # 1. (时间戳): '2025-06-19 11:47:10,045'
    # 2. (日志级别): 'Warning', 'Log', 'Assert' 等
    # 3. (日志内容): 级别标签之后的所有内容
    log_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s*,?\s*\[([A-Za-z]+)\]\s*(.*)$")

    current_index = 0
    for line in log_content.splitlines():
        match = log_pattern.match(line)
        if match:
            timestamp, log_type, content = match.groups()
            parsed_logs.append({
                "original_index": current_index,
                "time": timestamp,
                "logtype": log_type,
                "content": content.strip()
            })
            current_index += 1
        elif parsed_logs:
            # 如果行不匹配（例如，多行日志的续行），追加到上一条
            parsed_logs[-1]["content"] += "\n" + line
            
    return parsed_logs

async def search_logs_tool(
    keyword: str, 
    tool_context: ToolContext, 
    start_timestamp: Optional[int] = None, 
    end_timestamp: Optional[int] = None, 
    max_results: int = 50
) -> dict:
    """
    Search for logs containing a specific keyword (case-insensitive) and return matches 
    with surrounding context (5 logs before and after). Optionally filter by time range.

    Args:
        keyword: The keyword string to search for (Mandatory).
        start_timestamp: Optional start Unix timestamp (seconds).
        end_timestamp: Optional end Unix timestamp (seconds).
        max_results: Maximum number of MATCHING logs to find (default 50). 
                     Note: Total returned logs will be higher due to context lines.

    Returns:
        A dictionary containing the status and the list of logs (merged contexts).
    """
    
    file_version = tool_context.state.get("file_version", -1)
    clientLogUrl = tool_context.state.get("clientLogUrl")

    if not clientLogUrl:
        return {"error": "未在工具上下文中找到 clientLogUrl。"}
        
    # --- File Loading Logic (Same as before) ---
    is_remote_url = clientLogUrl.startswith("http://") or clientLogUrl.startswith("https://")
    filename = clientLogUrl.split('/')[-1]
    log_content = ""
    
    try:
        if is_remote_url:
            if file_version == -1:
                print(f"正在从 {clientLogUrl} 拉取日志...")
                response = requests.get(clientLogUrl, timeout=20)
                response.raise_for_status()
                response.encoding = 'utf-8'
                log_content = response.text
                log_artifact = types.Part(text=log_content)
                version = await tool_context.save_artifact(filename=filename, artifact=log_artifact)
                tool_context.state["file_version"] = version
            else:
                cached = await tool_context.load_artifact(filename=filename, version=file_version)
                if cached and cached.text: log_content = cached.text
                elif cached and cached.inline_data: log_content = cached.inline_data.data.decode('utf-8', errors='ignore')
        else:
            import os
            if os.path.exists(clientLogUrl) and os.path.isfile(clientLogUrl):
                 print(f"检测到本地文件路径: {clientLogUrl}")
                 with open(clientLogUrl, 'r', encoding='utf-8') as f:
                     log_content = f.read()
            else:
                log_artifact = await tool_context.load_artifact(filename=clientLogUrl)
                if log_artifact and log_artifact.text:
                    log_content = log_artifact.text
                elif log_artifact and log_artifact.inline_data:
                    log_content = log_artifact.inline_data.data.decode('utf-8')
                    
    except Exception as e:
        return {"error": f"Failed to load logs: {e}"}

    all_logs = _parse_log_content(log_content)
    if not all_logs:
        return {"error": "无法解析日志内容或日志为空。"}

    # --- Time Range Setup ---
    user_start_time = None
    user_end_time = None
    if start_timestamp is not None:
         user_start_time = datetime.fromtimestamp(start_timestamp, tz=USER_TIMEZONE)
    if end_timestamp is not None:
         user_end_time = datetime.fromtimestamp(end_timestamp, tz=USER_TIMEZONE)

    # --- Search Logic ---
    matched_indices = []
    keyword_lower = keyword.lower()
    
    for i, log in enumerate(all_logs):
        # 1. Keyword Check
        if keyword_lower not in log['content'].lower() and keyword_lower not in log['logtype'].lower():
            continue
            
        # 2. Time Logic Check (if range provided)
        if user_start_time or user_end_time:
            try:
                log_time_naive = datetime.strptime(log['time'], "%Y-%m-%d %H:%M:%S,%f")
                log_time = log_time_naive.replace(tzinfo=USER_TIMEZONE)
                
                if user_start_time and log_time < user_start_time:
                    continue
                if user_end_time and log_time > user_end_time:
                    continue
            except (ValueError, KeyError):
                # If time parsing fails, decide whether to include or exclude. 
                # Safe default: exclude if strict time filtering is requested.
                continue

        matched_indices.append(i)
        if len(matched_indices) >= max_results:
            break
    
    if not matched_indices:
        time_hint = ""
        if user_start_time or user_end_time:
            time_hint = f" within specified time range"
        return {"status": f"No logs found containing '{keyword}'{time_hint}.", "count": 0, "logs": []}

    # --- Context Merging Logic ---
    indices_to_include = set()
    for idx in matched_indices:
        start = max(0, idx - 5)
        end = min(len(all_logs) - 1, idx + 5)
        for i in range(start, end + 1):
            indices_to_include.add(i)
            
    sorted_unique_indices = sorted(list(indices_to_include))
    
    final_logs = []
    for idx in sorted_unique_indices:
        entry = all_logs[idx]
        # Add a marker if it is a direct match
        entry['is_match'] = (idx in matched_indices)
        final_logs.append(entry)

    return {
        "status": f"Found {len(matched_indices)} matches for '{keyword}'. Returned {len(final_logs)} logs with 5-line context buffer.",
        "count": len(final_logs),
        "logs": final_logs
    }
