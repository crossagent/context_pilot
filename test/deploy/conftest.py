"""
Deploy test scripts - manual streaming verification.

These scripts are NOT auto-discovered by pytest.
They require a running Docker environment (docker-compose up).

Usage:
    python test/deploy/manual_streaming_context_pilot.py
    python test/deploy/manual_streaming_knowledge_agent.py
    python test/deploy/manual_streaming_integration.py
"""
collect_ignore_glob = ["*"]
