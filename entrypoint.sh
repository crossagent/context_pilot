#!/bin/sh
# Start auto indexer in background
python context_pilot/scripts/run_auto_index.py &

# Start main server in foreground
exec python context_pilot/main.py serve --host 0.0.0.0 --port 8000
