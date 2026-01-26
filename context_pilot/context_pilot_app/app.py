import os
import sys
import importlib
from google.adk.apps.app import App, EventsCompactionConfig, ResumabilityConfig
from google.adk.agents.context_cache_config import ContextCacheConfig

# from context_pilot.context_pilot_app.bug_analyze_agent.agent import bug_analyze_agent
from context_pilot.context_pilot_app.agent import context_pilot_agent

# --- Instantiate App (Global) ---

# --- Select Root Agent ---
selected_root_agent = context_pilot_agent
target_agent_name = os.getenv("ADK_ROOT_AGENT_NAME")

if target_agent_name:
    # Look for the agent in sub-agents
    found = False
    if context_pilot_agent.sub_agents:
        for sub in context_pilot_agent.sub_agents:
            if sub.name == target_agent_name:
                selected_root_agent = sub
                found = True
                break
    
    if not found:
        print(f"WARNING: Requested root agent '{target_agent_name}' not found in sub-agents. Defaulting to Supervisor.")

# --- Configure Plugins based on mode ---
_app_mode = os.getenv("ADK_APP_MODE", "adk-web").lower()
_plugins = []

if _app_mode == "ag-ui":
    # Add LoggingPlugin for detailed debugging in UI mode
    try:
        from google.adk.plugins.logging_plugin import LoggingPlugin
        _plugins.append(LoggingPlugin())
        print("[App] LoggingPlugin enabled for AG-UI mode")
    except ImportError:
        print("[App] Warning: LoggingPlugin not available")

app = App(
    name="context_pilot_app",
    root_agent=selected_root_agent,
    plugins=_plugins,
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=600,
        cache_intervals=1,
    ),
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,
        overlap_size=1
    ),
    resumability_config=ResumabilityConfig(
        is_resumable=True
    )
)

