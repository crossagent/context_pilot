# Start Repo Explorer A2A Server
# Port: 8002 (default)
# NOTE: This server must run on the LOCAL MACHINE (not in Docker)
#       because it needs access to local files, git, svn, and bash commands.

Write-Host "Starting Repo Explorer A2A Server on port 8002..." -ForegroundColor Green
Write-Host "This server provides file system access to the Docker-hosted context_pilot_app." -ForegroundColor Cyan

python -m uvicorn context_pilot.context_pilot_app.remote_a2a.repo_explorer_agent.agent:app --port 8002 --reload
