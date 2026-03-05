#!/bin/sh

# Start main server in foreground
exec python context_pilot/main.py serve --host 0.0.0.0 --port 8000
