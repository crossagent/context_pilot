import asyncio
import os
from typing import Optional, List, Dict
from .bash import run_bash_command
from google.adk.tools import ToolContext
from .decorators import validate_path

@validate_path
async def get_git_log_tool(
    path: Optional[str] = None, 
    tool_context: ToolContext = None,
    limit: int = 5,
    author: Optional[str] = None
) -> dict:
    """
    Get recent git commits. 
    Useful to check "Who touched this file recently?" or "What changes happened globally?".

    Args:
        path: Optional. Specific file or directory path to check history for.
        limit: Number of commits to retrieve (default 5).
        author: Optional. Filter by author.

    Returns:
        dict: List of commits with hash, author, date, message.
    """
    cmd = f'git log -n {limit} --pretty=format:"%h|%an|%ad|%s"'
    
    if author:
        cmd += f' --author="{author}"'
        
    if path:
        cmd += f' -- "{path}"'
        
    # Determine CWD
    cwd = None
    if path:
        if os.path.isfile(path):
            cwd = os.path.dirname(path)
        elif os.path.isdir(path):
            cwd = path
    
    if not cwd:
        cwd = os.environ.get("PROJECT_ROOT")

    result = await run_bash_command(cmd, cwd=cwd)
    
    if result.get("status") == "error":
        return result
        
    output = result.get("output", "")
    commits = []
    if output:
        for line in output.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                })
                
    return {"status": "success", "commits": commits}

@validate_path
async def get_git_diff_tool(
    target: str,
    tool_context: ToolContext = None,
    base: Optional[str] = None,
    path: Optional[str] = None
) -> dict:
    """
    Get git diff to see what actually changed.
    
    Args:
        target: The commit hash (or 'HEAD') to check. 
                If 'base' is provided, shows diff between base and target (base..target).
                If 'base' is NOT provided, shows changes IN that commit (git show).
        base: Optional. Create a range diff (base..target). 
        path: Optional. Limit diff to specific file path.

    Returns:
        dict: The diff output.
    """
    if base:
        # Range diff: git diff base target -- path
        cmd = f"git diff {base} {target}"
    else:
        # Single commit show: git show target -- path
        cmd = f"git show {target}"
        
    if path:
        cmd += f' -- "{path}"'
    
    # Determine CWD
    cwd = None
    if path:
        if os.path.isfile(path):
            cwd = os.path.dirname(path)
        elif os.path.isdir(path):
            cwd = path
            
    if not cwd:
        cwd = os.environ.get("PROJECT_ROOT")
    
    result = await run_bash_command(cmd, cwd=cwd)
    
    if result.get("status") == "error":
        return result
        
    # Truncate if too long (simple protection)
    output = result.get("output", "")
    if len(output) > 10000:
        output = output[:10000] + "\n... (Diff truncated, too long) ..."
        
    return {"status": "success", "diff": output}

@validate_path
async def get_git_blame_tool(
    path: str,
    start_line: int,
    end_line: int,
    tool_context: ToolContext = None
) -> dict:
    """
    Get git blame for a specific code range to see who last modified it.

    Args:
        path: File path.
        start_line: Start line number (1-based).
        end_line: End line number.

    Returns:
        dict: Blame info for lines.
    """
    cmd = f'git blame -L {start_line},{end_line} -- "{path}"'
    
    # Determine CWD
    cwd = None
    if os.path.isfile(path):
        cwd = os.path.dirname(path)
    elif os.path.isdir(path):
        cwd = path
        
    if not cwd:
        cwd = os.environ.get("PROJECT_ROOT")

    result = await run_bash_command(cmd, cwd=cwd)
    return result
