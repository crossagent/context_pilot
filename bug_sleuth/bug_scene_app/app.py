import os
import sys
import importlib
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.agents.context_cache_config import ContextCacheConfig

from bug_sleuth.bug_scene_app.bug_analyze_agent.agent import bug_analyze_agent
from bug_sleuth.bug_scene_app.agent import bug_scene_agent

# --- Instantiate App (Global) ---

def load_agent_from_dir(agent_dir: str):
    """Dynamically loads 'agent' from a given directory using standard import."""
    if not os.path.isdir(agent_dir):
        raise ValueError(f"Agent directory not found: {agent_dir}")
        
    # Standard ADK-like approach: Module name is the folder name.
    # We allow the import system to handle __init__.py resolution.
    parent_dir = os.path.dirname(agent_dir)
    module_name = os.path.basename(agent_dir)
    
    # Ensure parent is in path so we can import the module
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(f"Failed to import module '{module_name}' from '{parent_dir}': {e}")

    # Strictly look for 'root_agent' as requested
    try:
        return getattr(module, "root_agent")
    except AttributeError:
        raise ImportError(f"Module '{module_name}' loaded, but has no 'root_agent' attribute. Please add 'from .X import X as root_agent' to __init__.py")

# Check for dynamic target from CLI
target_agent_dir = os.getenv("ADK_TARGET_AGENT_DIR")

if target_agent_dir:
    try:
        selected_root_agent = load_agent_from_dir(target_agent_dir)
    except Exception as e:
        raise RuntimeError(f"Could not load agent from {target_agent_dir}: {e}")
else:
    # Default to Supervisor
    selected_root_agent = bug_scene_agent

app = App(
    name="bug_scene_app",
    root_agent=selected_root_agent,
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=600,
        cache_intervals=1,
    ),
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,
        overlap_size=1
    )
)
