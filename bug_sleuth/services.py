import platform
import urllib.parse
import os
import logging
from typing import List, Optional
from google.adk.cli.service_registry import get_service_registry
from google.adk.artifacts import file_artifact_service
from google.adk.tools import FunctionTool
from bug_sleuth.skill_loader import SkillLoader

logger = logging.getLogger(__name__)

# Global Singleton for the loader
_SKILL_LOADER: Optional[SkillLoader] = None

def create_artifact_service_windows(uri: str, **kwargs):
    """
    Custom factory for file:// URIs on Windows to handle absolute paths correctly.
    Fixes the issue where 'file:///E:/...' becomes '/E:/...' (invalid) instead of 'E:/...'
    """
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme != "file":
        return None
    
    # On Windows, parsed.path for 'file:///E:/foo' is '/E:/foo'.
    # We need to strip the leading slash to make it a valid path 'E:/foo'.
    path_str = parsed.path
    if path_str.startswith("/") and ":" in path_str:
        path_str = path_str[1:]
        
    print(f"[Services] Windows Path Patch: Resolved '{uri}' to '{path_str}'")
    return file_artifact_service.FileArtifactService(root_dir=path_str)

# --- Extension Loading Facade ---

def load_extensions(skill_path: Optional[str] = None):
    """
    Central entry point for loading all extensions (Skills and Services).
    """
    global _SKILL_LOADER
    
    # 1. Register Infrastructure Services (Standard Patches)
    if platform.system() == "Windows":
        logger.info("[Services] Loading Windows compatibility patch for Artifact Service...")
        registry = get_service_registry()
        registry.register_artifact_service("file", create_artifact_service_windows)

    # 2. Load Skills if path is provided
    if skill_path:
        if os.path.exists(skill_path):
            logger.info(f"[Services] Loading skills from: {skill_path}")
            _SKILL_LOADER = SkillLoader(skill_path)
            _SKILL_LOADER.load_skills()
        else:
            logger.warning(f"[Services] SKILL_PATH defined but not found: {skill_path}")

def get_loaded_tools(agent_name: str) -> List[FunctionTool]:
    """Retrieve tools for a specific agent from the global loader."""
    if _SKILL_LOADER:
        return _SKILL_LOADER.get_tools_for_agent(agent_name)
    return []



# --- Auto-Initialization ---
# If SKILL_PATH is set in the environment, automatically attempt to load extensions.
# This ensures services are initialized just by importing this module.
_env_skill_path = os.getenv("SKILL_PATH")
if _env_skill_path:
    # Avoid double loading if imported multiple times (handled by python module caching anyway)
    # But logging it is useful
    if not _SKILL_LOADER:
        logger.info(f"[Services] Auto-initializing Extension System with SKILL_PATH={_env_skill_path}")
        load_extensions(_env_skill_path)
else:
    logger.info("[Services] SKILL_PATH not set. Extension System is DISABLED. Only core agents will be available.")
