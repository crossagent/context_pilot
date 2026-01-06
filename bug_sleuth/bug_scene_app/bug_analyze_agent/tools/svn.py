
import os
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict
from .bash import run_bash_command
from .decorators import validate_path
from google.adk.tools import ToolContext

@validate_path
async def get_svn_log_tool(
    path: Optional[str] = None, 
    tool_context: ToolContext = None,
    limit: int = 5,
    author: Optional[str] = None
) -> dict:
    """
    Get recent SVN commits using `svn log`.
    
    Args:
        path: Optional. Specific file or directory path to check history for.
        limit: Number of commits to retrieve (default 5).
        author: Optional. Filter by author (filtering done in Python as svn log --search is newer).
        
    Returns:
        dict: List of commits with revision, author, date, message.
    """
    # Use XML for easier parsing
    cmd = f'svn log --xml -l {limit}'
    
    if path:
        cmd += f' "{path}"'
        
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
    
    try:
        if output.strip():
            root = ET.fromstring(output)
            for entry in root.findall('logentry'):
                rev = entry.get('revision')
                author_tag = entry.find('author')
                date_tag = entry.find('date')
                msg_tag = entry.find('msg')
                
                commit_author = author_tag.text if author_tag is not None else "unknown"
                
                # Filter by author if requested
                if author and author != commit_author:
                    continue
                    
                commits.append({
                    "revision": rev,
                    "author": commit_author,
                    "date": date_tag.text if date_tag is not None else "",
                    "message": msg_tag.text if msg_tag is not None else ""
                })
    except ET.ParseError:
        return {"status": "error", "error": "Failed to parse SVN XML output", "raw_output": output}
                
    return {"status": "success", "commits": commits}

@validate_path
async def get_svn_diff_tool(
    target: str,
    tool_context: ToolContext = None,
    base: Optional[str] = None,
    path: Optional[str] = None
) -> dict:
    """
    Get SVN diff.
    
    Args:
        target: The revision number (e.g., '1001') or 'HEAD'.
                If 'base' is NOT provided, behaves like `svn diff -c target` (changes IN that revision).
        base: Optional. If provided, `svn diff -r base:target`.
        path: Optional. Limit diff to specific file path.

    Returns:
        dict: The diff output.
    """
    if base:
        # Range diff: svn diff -r base:target
        cmd = f"svn diff -r {base}:{target}"
    else:
        # Single commit change: svn diff -c target
        # Note: 'svn show' is not standard in older SVN, usually 'diff -c' or 'log -v --diff'
        cmd = f"svn diff -c {target}"
        
    if path:
        cmd += f' "{path}"'
    
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
    if len(output) > 10000:
        output = output[:10000] + "\n... (Diff truncated, too long) ..."
        
    return {"status": "success", "diff": output}

@validate_path
async def get_svn_blame_tool(
    path: str,
    start_line: int,
    end_line: int,
    tool_context: ToolContext = None
) -> dict:
    """
    Get SVN blame for a file.
    Note: SVN blame does not support line range natively in CLI, so we fetch all and slice.

    Args:
        path: File path.
        start_line: Start line number (1-based).
        end_line: End line number.

    Returns:
        dict: Blame info for selected lines.
    """
    cmd = f'svn blame "{path}"'
    
    # Determine CWD
    cwd = None
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
    lines = output.splitlines()
    
    # Slice lines (1-based index)
    # Ensure indices are within bounds
    total_lines = len(lines)
    start_idx = max(0, start_line - 1)
    end_idx = min(total_lines, end_line)
    
    selected_lines = lines[start_idx:end_idx]
    
    # SVN Blame format: "  123   user   line content"
    return {"status": "success", "blame": "\n".join(selected_lines)}
