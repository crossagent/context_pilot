import asyncio
import os
from typing import Optional, List, Dict
from .bash import run_bash_command
from google.adk.tools import ToolContext
from .decorators import validate_path
from context_pilot.shared_libraries.tool_response import ToolResponse

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
                
    return ToolResponse.success(
        summary=f"Found {len(commits)} commits.",
        data=commits
    )

@validate_path
async def get_git_diff_tool(
    target: str,
    tool_context: ToolContext = None,
    base: Optional[str] = None,
    path: Optional[str] = None
) -> dict:
    """
    Get git diff to see what actually changed in a commit or between commits.
    
    Args:
        target: **REQUIRED**. The commit hash (e.g., 'a1b2c3d') or 'HEAD' to check.
                **IMPORTANT**: Use ACTUAL commit hash from git log, NOT placeholder text like '<rev>' or '<commit>'.
                Examples of VALID values: 'HEAD', 'a1b2c3d', '9f8e7d6'
                Examples of INVALID values: '<rev>', '<commit>', '<target>'
        
        base: **OPTIONAL**. If provided, shows diff between two commits (base → target).
              **IMPORTANT**: Use ACTUAL commit hash, NOT placeholder text.
              Examples: 'HEAD~1', 'b2c3d4e', 'main'
              
        path: **OPTIONAL**. Limit diff to specific file path.
              Example: 'Assets/Scripts/Player.cs'
    
    Usage Examples:
        1. View changes in a specific commit:
           get_git_diff_tool(target='a1b2c3d')
        
        2. Compare two commits:
           get_git_diff_tool(base='HEAD~1', target='HEAD')
        
        3. View changes in a file for a commit:
           get_git_diff_tool(target='a1b2c3d', path='Assets/Scripts/Player.cs')

    Returns:
        dict: The diff output with status and diff content.
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
        
    return ToolResponse.success(
        summary="Git diff retrieved.",
        diff=output
    )

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
    # run_bash_command already returns ToolResponse dict, so we can return it directly
    return result
