import os
import sys
import importlib
from google.adk.apps.app import App, EventsCompactionConfig, ResumabilityConfig
from google.adk.agents.context_cache_config import ContextCacheConfig

# from context_pilot.context_pilot_app.bug_analyze_agent.agent import bug_analyze_agent
from context_pilot.context_pilot_app.agent import context_pilot_agent

# --- Instantiate App (Global) ---

# --- Configure Plugins based on mode ---haod
_plugins = []

if os.getenv("ADK_ENABLE_LOGGING_PLUGIN", "false").lower() == "true":
    # Add LoggingPlugin for detailed debugging if explicitly enabled
    try:
        from google.adk.plugins.logging_plugin import LoggingPlugin
        _plugins.append(LoggingPlugin())
        print("[App] LoggingPlugin enabled (ADK_ENABLE_LOGGING_PLUGIN=true)")
    except ImportError:
        print("[App] Warning: LoggingPlugin not available")

app = App(
    name="context_pilot_app",
    root_agent=context_pilot_agent,
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

