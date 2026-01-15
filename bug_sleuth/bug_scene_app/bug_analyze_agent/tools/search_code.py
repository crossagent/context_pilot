import os
import json
from datetime import datetime
from typing import Optional
from pathlib import Path
from .decorators import validate_path
from .bash import run_bash_command
import shutil
import logging

logger = logging.getLogger(__name__)

def check_search_tools() -> Optional[str]:
    """
    Verify if 'ripgrep' is available.
    Returns error message if not found, else None.
    """
    # Check for rg (ripgrep)
    if shutil.which("rg"):
        return None
        
    return "Critical Error: 'ripgrep' (rg) is missing. Please contact administrator to install it."


from google.adk.tools.tool_context import ToolContext
from bug_sleuth.shared_libraries.state_keys import StateKeys
from bug_sleuth.shared_libraries.tool_response import ToolResponse

@validate_path
async def search_code_file_tool(
    query: str,
    tool_context: ToolContext,
    file_pattern: Optional[str] = None
) -> dict:
    """
    全文搜索代码和配置内容。基于 ripgrep 实现。
    
    **适用场景 (When to Use)**:
    - 查找**引用** (References): 谁调用了某个函数？哪里使用了某个常量？
    - 查找**字符串常量**: 错误码 (e.g., "ERR_1001")、日志关键词
    - 搜索**配置和脚本**: Lua, Json, XML, 配置表等
    - 查找**类或方法定义**: 在代码中搜索 "class BattleManager" 等
    
    **限制 (Limitations)**:
    - 全文本扫描，大仓库可能较慢
    - 结果可能包含注释、字符串等非定义位置
    
    Args:
        query: 要搜索的内容字符串 (e.g., "InitPlayer", "ERR_1001")
        file_pattern: 可选，文件名过滤 (e.g., "*.cs", "*.json")
                      用于缩减搜索范围提高速度

    Returns:
        dict: 包含匹配行的搜索结果
    """
    if not query:
        return ToolResponse.error("Query is required.")

    # 1. Build Command (Strictly use rg)
    cmd_parts = ["rg", "-n", "-C", "2", "--no-heading", "--smart-case"]
    
    if file_pattern:
        # rg uses --glob for patterns
        # Handle OS-specific quoting
        if os.name == 'nt':
            # Windows (cmd.exe) requires double quotes
            cmd_parts.append(f'--glob "{file_pattern}"')
        else:
            # Linux/macOS (bash) prefers single quotes to prevent expansion
            cmd_parts.append(f"--glob '{file_pattern}'")
    
    cmd_parts += ["-e", f'"{query}"']

    # New Multi-Repo Logic: Retrieve from ToolContext
    repo_registry = tool_context.state.get(StateKeys.REPO_REGISTRY, [])
    
    # Process Repositories
    repo_list = []
    try:
        # If it's the list of dicts directly (from StateKeys.REPO_REGISTRY)
        for repo in repo_registry:
            if p := repo.get("path"):
                vcs_type = repo.get("vcs", "git").lower()
                # SKIP SVN repositories (assumed to be Assets/Binary) for code search
                if vcs_type == "svn":
                    logger.info(f"DEBUG: Skipping SVN repo for code search: {p}")
                    continue
                
                # Normalize to system path separator (Crucial for Windows CMD + rg)
                repo_list.append(str(Path(p).resolve()))
    except Exception as e:
        logger.error(f"DEBUG: Repo parsing failed: {e}")
        pass
        
    for path in repo_list:
        cmd_parts.append(f'"{path}"')
        
    cmd = " ".join(cmd_parts)
    logger.info(f"DEBUG: Search CMD: {cmd}") # Fallback to default behavior (search cwd)

    # cmd = " ".join(cmd_parts)

    # 3. Execution
    # Run from Primary Repo as CWD (fallback '.' if fail)

    cwd = "."
    try:
        if repo_registry:
            cwd = repo_registry[0].get("path", ".")
    except:
        pass
    
    logger.info(f"DEBUG: Running RG command: {cmd}")
    # Increase timeout for large searches
    result = await run_bash_command(cmd, cwd=cwd)
    
    # ... (Regex fallback logic skipped for brevity, assumed unchanged) ...

    if result.get("status") == "error":
        # 4. Handle 'rg' exit codes
        # rc=1 means "No matches found" (not an error)
        # rc=2 means Error
        if result.get("exit_code") == 1:
             return ToolResponse.success(
                 summary=f"No matches found for '{query}'.",
                 output="No matches found."
             )
        return result

    output = result.get("output", "")
    # logger.info(f"DEBUG: Raw RG Output:\n{output[:500]}") 

    # --- PATH FIX: Convert to Absolute Paths ---
    # rg -n output format: relative_path:line_num:content
    # OR absolute_path:line_num:content (if args were absolute)
    
    lines = output.splitlines()
    abs_lines = []
    root_path = Path(cwd).resolve()
    
    for line in lines:
        # Standard rg -n output: path:line:content
        # On Windows absolute path: C:\path\file:line:content (Colon issue)
        
        parts = line.split(':', 2) 
        path_str = ""
        line_num = ""
        content = ""
        
        if len(parts) >= 3:
            # Check for Windows Drive Letter (e.g. C:\...)
            if len(parts[0]) == 1 and parts[1].startswith('\\'):
                # Resplit with limit 3 to capture drive, path_part, line, content
                # Actually, simpler: reconstruct path
                # parts[0] = 'C', parts[1] = '\path\file', parts[2] = 'line:content'
                # But wait, split(':', 2) results in 3 parts max.
                # If C:\path:5:txt
                # 0: C
                # 1: \path
                # 2: 5:txt
                # So we need to parse parts[2] further.
                
                path_str = f"{parts[0]}:{parts[1]}"
                
                # parts[2] is 'line:content'
                subparts = parts[2].split(':', 1)
                if len(subparts) >= 2:
                    line_num = subparts[0]
                    content = subparts[1]
                else:
                    # Malformed or different format
                    abs_lines.append(line)
                    continue
            else:
                # Standard relative path or Linux absolute
                path_str = parts[0]
                line_num = parts[1]
                content = parts[2]
        
        if path_str:
            try:
                # Normalize slashes first
                path_str = str(Path(path_str))
                p = Path(path_str)
                
                is_abs = p.is_absolute()
                # logger.info(f"DEBUG: Path check: '{path_str}' is_abs={is_abs}")

                if not is_abs:
                    # Check if it has a drive letter manually (Windows Edge Case)
                    if os.name == 'nt' and len(path_str) > 1 and path_str[1] == ':':
                            # It IS absolute but pathlib missed it? (Rare/Impossible for Path, but safest to fallback)
                            abs_path = p.resolve()
                    else:
                            abs_path = (root_path / p).resolve()
                else:
                    abs_path = p.resolve()
                
                # Reconstruct line
                new_line = f"{abs_path}:{line_num}:{content}"
                abs_lines.append(new_line)
            except Exception:
                abs_lines.append(line)
        else:
            abs_lines.append(line)
            
    final_output = "\n".join(abs_lines)

    # 4. Formatting (Optional cleanup or truncation)
    match_count = len(abs_lines)
    if len(final_output) > 20000:
        final_output = final_output[:20000] + "\n... (Truncated) ..."
        
    fallback_note = " (Literal search fallback used)" if result.get("_fallback_used") else ""
        
    return ToolResponse.success(
        summary=f"Found ~{match_count} matches for '{query}' in All.{fallback_note}",
        output=f"Search Results ('{file_pattern or 'All'}'){fallback_note}:\n{final_output}"
    )
