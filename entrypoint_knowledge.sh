#!/bin/sh
# Start auto indexer in background
python context_pilot/scripts/run_auto_index.py &

# Start Knowledge Expert Agent server in foreground
exec adk api_server --a2a --host 0.0.0.0 --port 8003 \
    --session_service_uri sqlite:////app/adk_data/sessions.db \
    --artifact_service_uri file:///app/adk_data/artifacts \
    context_pilot/context_pilot_app/remote_a2a
