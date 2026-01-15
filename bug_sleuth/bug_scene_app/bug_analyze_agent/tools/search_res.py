
import os
import shutil
from pathlib import Path
from typing import Optional
from .decorators import validate_path
from .bash import run_bash_command
from google.adk.tools.tool_context import ToolContext
from bug_sleuth.shared_libraries.state_keys import StateKeys
from bug_sleuth.shared_libraries.tool_response import ToolResponse
import logging

logger = logging.getLogger(__name__)

@validate_path
async def search_res_tool(
    name_pattern: str,
    tool_context: ToolContext,
    directory_filter: Optional[str] = None
) -> dict:
    """
    Search for ASSET files by FILENAME (not content) across repositories.
    Use this to find resources like Prefabs, Textures, Anim sequences, etc.
    
    Args:
        name_pattern: The filename pattern to search for (glob). 
                      e.g., "*AK47*", "*.png", "B_Hero_*.uasset".
                      Case-insensitive.
        directory_filter: Optional. Limit search to a specific subdirectory name.
                          e.g., "SocClientRes" or "FX".

    Returns:
        dict: List of matching file paths.
    """
    if not name_pattern:
        return ToolResponse.error("name_pattern is required.")

    # Verify rg exists (reusing check from search_code is implicit, but let's be safe)
    if not shutil.which("rg"):
        return ToolResponse.error("'ripgrep' (rg) not found.")

    # 1. Build Command
    # rg --files: List files that would be searched
    # -g: Glob pattern
    # --iglob: Case insensitive glob (better for user queries)
    
    # We want to match the FILENAME. 
    # rg --files lists ALL files. We need to filter.
    # Actually, `rg --files -g "*pattern*"` works efficiently.
    
    # Ensure pattern is glob-friendly
    if "*" not in name_pattern:
        glob_pattern = f"*{name_pattern}*"
    else:
        glob_pattern = name_pattern

    cmd_parts = ["rg", "--files", "--iglob", f'"{glob_pattern}"']
    
    # 2. Target Directories (Repos)
    repo_registry = tool_context.state.get(StateKeys.REPO_REGISTRY, [])
    
    repo_paths = []
    # If directory_filter is provided (e.g. "SocClientRes"), we try to find that specific path
    # Otherwise we search all configured repos.
    
    for repo in repo_registry:
        path = repo.get("path")
        if not path:
            continue
            
        repo_abs = str(Path(path).resolve())
        
        if directory_filter:
            # Simple check: if filter is in the path or name
            if directory_filter.lower() in repo.get("name", "").lower() or directory_filter.lower() in repo_abs.lower():
                 repo_paths.append(repo_abs)
        else:
            repo_paths.append(repo_abs)

    # If filter provided but no repo matched, maybe it's a subdir?
    # We'll search all repos but pass the glob.
    if not repo_paths:
        # Fallback: Search all repos
        for repo in repo_registry:
            if p := repo.get("path"):
                repo_paths.append(str(Path(p).resolve()))

    if not repo_paths:
         return ToolResponse.error("No repositories configured to search.")

    # Append paths to command
    for p in repo_paths:
        cmd_parts.append(f'"{p}"')

    # Join 
    cmd = " ".join(cmd_parts)
    
    # 3. Execution
    # Run from CWD or first repo
    cwd = "."
    if repo_paths:
        cwd = repo_paths[0]

    result = await run_bash_command(cmd, cwd=cwd)
    
    if result.get("status") == "error":
         return result

    output = result.get("output", "")
    lines = output.splitlines()
    
    # 4. Filter by Directory Filter (Secondary Check if needed)
    # Since we passed query to rg, it filtered by name.
    # If we had a directory_filter that WASN'T a repo root, we might want to filter paths here.
    # But for now, simple is best.
    
    match_count = len(lines)
    
    # Truncate
    if match_count > 100:
        display_output = "\n".join(lines[:100]) + f"\n... (and {match_count - 100} more)"
    else:
        display_output = output

    if not output.strip():
        return ToolResponse.success(
            summary=f"No assets found for '{name_pattern}'.",
            output="No files found matching that name."
        )

    return ToolResponse.success(
        summary=f"Found {match_count} assets matching '{name_pattern}'.",
        output=f"Found {match_count} asset files:\n{display_output}"
    )
