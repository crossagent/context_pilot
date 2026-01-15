import os
import shutil
import logging
from pathlib import Path
from typing import Optional, List
from google.adk.tools.tool_context import ToolContext
from bug_sleuth.shared_libraries.state_keys import StateKeys
from bug_sleuth.shared_libraries.tool_response import ToolResponse
from .decorators import validate_path
from .bash import run_bash_command

logger = logging.getLogger(__name__)

@validate_path
async def search_file_tool(
    query: str,
    tool_context: ToolContext,
    search_type: str = "content",
    root_path: Optional[str] = None,
    file_pattern: Optional[str] = None
) -> dict:
    """
    Unified search tool for code content and file names using ripgrep (rg).
    
    Args:
        query: The string to search for. 
               - For 'content': The text/code to find.
               - For 'filename': The filename pattern (glob compatible).
        search_type: "content" (default) or "filename".
                     - "content": Full text search in files. Skips SVN/Binaries.
                     - "filename": Search for matching file paths. Includes SVN.
        root_path: Optional. If set, search ONLY this directory (must be absolute or relative to CWD).
                   If NOT set, searches all repositories in configured REPO_REGISTRY.
        file_pattern: Optional. Filter by filename glob (e.g. "*.json", "*.cs").
                      Only used when search_type="content".

    Returns:
        dict: ToolResponse with search results or error.
    """
    if not query:
        return ToolResponse.error("Query is required.")
        
    # Check rg availability
    if not shutil.which("rg"):
        return ToolResponse.error("Critical Error: 'ripgrep' (rg) is missing.")

    search_type = search_type.lower()
    if search_type not in ["content", "filename", "name"]:
        return ToolResponse.error(f"Invalid search_type: '{search_type}'. Use 'content' or 'filename'.")
    if search_type == "name": 
        search_type = "filename"

    # --- 1. Build Command ---
    cmd_parts = ["rg"]
    
    if search_type == "content":
        # Content Search Mode (from search_code.py)
        # -n: Line numbers
        # -C 2: 2 lines context
        # --no-heading: Easier parsing
        # --smart-case: Case insensitive if query is lowercase
        cmd_parts.extend(["-n", "-C", "2", "--no-heading", "--smart-case"])
        
        if file_pattern:
             # Standardize quotes for glob
             glob_opt = f"--glob '{file_pattern}'" if os.name != 'nt' else f'--glob "{file_pattern}"'
             cmd_parts.append(glob_opt)
             
        cmd_parts.extend(["-e", f'"{query}"'])
        
    else:
        # Filename Search Mode (from search_res.py)
        # --files: List files
        # --iglob: Case insensitive glob match on the FILE PATH/NAME
        cmd_parts.append("--files")
        
        # Determine glob pattern
        glob_pattern = query
        if "*" not in glob_pattern:
            glob_pattern = f"*{query}*"
        
        # On Windows, need double quotes usually
        cmd_parts.extend(["--iglob", f'"{glob_pattern}"'])

    # --- 2. Determine Search Paths ---
    search_paths = []
    
    if root_path:
        # Single path override
        abs_root = Path(root_path).resolve()
        if not abs_root.exists():
             return ToolResponse.error(f"Root path does not exist: {root_path}")
        search_paths.append(str(abs_root))
        cwd = str(abs_root) # Run relative to this path if possible
    else:
        # Use Registry
        repo_registry = tool_context.state.get(StateKeys.REPO_REGISTRY, [])
        cwd = "." # Fallback CWD
        
        # Try to set a logical CWD from first Repo
        try:
             if repo_registry:
                 if first_path := repo_registry[0].get("path"):
                     cwd = first_path
        except:
            pass

        for repo in repo_registry:
            path = repo.get("path")
            if not path:
                logger.warning(f"Repo entry missing path: {repo}")
                continue
            
            # Logic Separation: SVN Handling
            # Content search -> Skip SVN (binary/assets noise)
            # Filename search -> Include SVN (find assets)
            if search_type == "content":
                vcs_type = repo.get("vcs", "git").lower()
                if vcs_type == "svn":
                     logger.info(f"DEBUG: Skipping SVN repo for content search: {path}")
                     continue
            
            search_paths.append(str(Path(path).resolve()))

    if not search_paths:
        return ToolResponse.error("No valid search paths found (Check REPOSITORIES config or vcs types).")

    # Add paths to command
    for p in search_paths:
        cmd_parts.append(f'"{p}"')
    
    final_cmd = " ".join(cmd_parts)
    logger.info(f"DEBUG: Search CMD: {final_cmd}")
    
    # --- 3. Execute ---
    result = await run_bash_command(final_cmd, cwd=cwd)
    
    if result.get("status") == "error":
        # rg exit code 1 means "no matches", not error. 
        # run_bash_command might wrap this, let's check exit_code if available
        if result.get("exit_code") == 1:
             return ToolResponse.success(summary=f"No matches found for '{query}'.", output="No matches found.")
        return result

    output = result.get("output", "")
    
    # --- 4. Post-Process (Absolute Paths) ---
    # Convert 'relative_path' output from rg to 'absolute_path' for the LLM
    # This logic was crucial in search_code.py, bringing it here.
    
    lines = output.splitlines()
    processed_lines = []
    
    # We need a base for resolving relative paths if rg returned them
    # If we searched multiple absolute paths, rg usually returns the path as provided (absolute).
    # If we searched ".", it returns relative.
    # Since we explicitly appended absolute paths to cmd_parts, rg SHOULD returns absolute paths
    # or paths relative to CWD if the arg matched CWD.
    
    # To be safe, we don't do complex path math unless strictly needed.
    # But search_code.py had logic to fix Windows drive letter colons.
    
    root_path_obj = Path(cwd).resolve()
    
    for line in lines:
        if search_type == "content":
            # Format: path:line:content
            # Windows: C:\path...:line:content (Problem: ':' in drive)
            parts = line.split(':', 2)
            if len(parts) >= 3:
                # Basic Heuristic for Windows Drive C:\
                if os.name == 'nt' and len(parts[0]) == 1 and parts[1].startswith('\\'):
                     # It's a windows path C:\...
                     # Re-merge parts 0 and 1
                     path_str = f"{parts[0]}:{parts[1]}"
                     rest = parts[2] # line:content
                     
                     processed_lines.append(f"{path_str}:{rest}")
                else:
                     processed_lines.append(line)
            else:
                processed_lines.append(line)
        else:
            # Filename search: Just the path
            processed_lines.append(line)

    final_output = "\n".join(processed_lines)
    match_count = len(processed_lines)
    
    # Truncate
    if len(final_output) > 20000:
        final_output = final_output[:20000] + "\n... (Truncated) ..."

    return ToolResponse.success(
        summary=f"Found {match_count} matches for '{query}' ({search_type}).",
        output=final_output if final_output.strip() else "No matches found."
    )
