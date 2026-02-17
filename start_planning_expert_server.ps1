# Start Planning Expert A2A Server
# Port: 8001 (default)

Write-Host "Starting Planning Expert A2A Server on port 8001..." -ForegroundColor Green

python -m uvicorn context_pilot.context_pilot_app.remote_a2a.planning_expert_agent.agent:app --port 8001 --reload
