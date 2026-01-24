import os
import functools
from pathlib import Path

import json

def _load_repos():
    try:
        repos_json = os.getenv("REPOSITORIES")
        if repos_json:
            return json.loads(repos_json)
    except:
        pass
    return []

def validate_path(func):
    """
    Decorator to validate and resolve 'path' argument against configured REPOSITORIES.
    
    1. Intercepts 'path'.
    2. Resolves relative path (assumes relative to FIRST repository in registry).
    3. Checks if path is within ANY registered repository.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Determine Context Source
        # ADK injects 'tool_context' (exact name) into kwargs if requested by tool signature.
        
        repos = []
        context = kwargs.get('tool_context')
        
        if context and hasattr(context, 'state'):
             from context_pilot.shared_libraries.state_keys import StateKeys
             repos = context.state.get(StateKeys.REPO_REGISTRY, [])
             
        # Fallback to loading from env (for legacy or tools without context)
        if not repos:
             repos = _load_repos()

        if not repos:
             return {"status": "error", "error": "REPOSITORIES not configured in environment or context."}
             
        # Inspect arguments to find 'path'
        if 'path' in kwargs:
            original_path = kwargs['path']
            if original_path:
                resolved_path = _resolve_and_check(original_path, repos)
                if isinstance(resolved_path, dict): # Error dict
                     return resolved_path
                kwargs['path'] = str(resolved_path)
        
        return await func(*args, **kwargs)

    return wrapper

def _resolve_and_check(path_str: str, repos: list) -> Path | dict:
    try:
        # 1. Resolve Path
        p = Path(path_str)
        primary_root = Path(repos[0]['path']).resolve() # Access first repo as primary
        
        if not p.is_absolute():
            p = (primary_root / p).resolve()
        else:
            p = p.resolve()
            
        # 2. Security Check (Any Repo)
        valid_repo = False
        allowed_roots = []
        
        for repo in repos:
            root = Path(repo['path']).resolve()
            allowed_roots.append(str(root))
            
            try:
                # Check if p is inside root
                if root in p.parents or root == p:
                    valid_repo = True
                    break
            except ValueError:
                # Different drive, continue checking other repos
                continue

        if not valid_repo:
             return {
                 "status": "error", 
                 "error": f"Access Denied: Path '{path_str}' is not within any configured repository: {allowed_roots}"
             }
             
        return p
    except Exception as e:
        return {"status": "error", "error": f"Path validation error: {str(e)}"}
