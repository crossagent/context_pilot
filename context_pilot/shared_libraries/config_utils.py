
import os
import json
import yaml
import logging
from typing import Dict, Any

from context_pilot.shared_libraries.state_keys import StateKeys

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """
    Loads configuration from the file specified by CONFIG_FILE env var, 
    or defaults to 'context_pilot/config.yaml' or 'config.yaml'.
    """
    config_path = os.getenv("CONFIG_FILE", "context_pilot/config.yaml")
    if not os.path.exists(config_path):
        # Fallback to local
        if os.path.exists("config.yaml"):
             config_path = "config.yaml"
        else:
             return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Critical Error: Failed to load config file: {e}")
        return {}

def load_and_inject_config(state: Dict[str, Any]) -> None:
    """
    Loads configuration and injects keys directly into the provided state dictionary.
    
    Keys injected:
    - All keys from config.yaml (e.g. 'repositories', 'max_autonomous_budget_usd', etc.)
    - 'REPO_REGISTRY' (derived from 'repositories')
    - 'repository_list' (formatted string)
    """
    # 1. Load Config if not present
    # We use a flag to check if config was already loaded into this state to avoid re-reading file
    # or overwriting if not needed.
    if not state.get("config_loaded"):
        config = load_config()
        state.update(config)
        state["config_loaded"] = True
    
    # 2. Inject Repositories
    if StateKeys.REPO_REGISTRY not in state:
        # Load Repos from Config (now in state)
        repositories = state.get("repositories", [])
        if not repositories:
            # Legacy Env Fallback
            try:
                if env_repos := os.getenv("REPOSITORIES"):
                    repositories = json.loads(env_repos)
            except:
                pass
        
        state[StateKeys.REPO_REGISTRY] = repositories
        
        # Format Repository List for Prompt
        if repositories:
            repo_list_str = []
            for r in repositories:
                capabilities = []
                if r.get("symbol_index_path") or r.get("symbol_index_paths"):
                    capabilities.append("**[Symbol Index Available]**")
                
                desc = r.get('description', '')
                cap_str = " ".join(capabilities)
                repo_list_str.append(f"- **{r.get('name')}**: `{r.get('path')}` - {desc} {cap_str}")
            state["repository_list"] = "\n    ".join(repo_list_str)
        else:
            state["repository_list"] = "No repositories configured."
            logger.warning("No repositories found in configuration.")
