import os
import sys
import importlib
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.agents.context_cache_config import ContextCacheConfig

from bug_sleuth.bug_scene_app.bug_analyze_agent.agent import bug_analyze_agent
from bug_sleuth.bug_scene_app.agent import context_pilot_agent

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
