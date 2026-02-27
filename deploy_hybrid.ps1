Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Context Pilot Hybrid Deployment (Win+Docker) " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Step 1: Starting Repo Explorer Agent (Local Windows Host)..." -ForegroundColor Yellow
# Start Repo Explorer in a new PowerShell window so it runs in parallel and stays open
Start-Process powershell -ArgumentList "-NoExit -File .\start_repo_explorer_server.ps1"

Write-Host "Step 2: Building and Starting Docker Containers (Main Agent & Planning Expert)..." -ForegroundColor Yellow
# Run docker-compose in detached mode
docker-compose up -d --build

Write-Host ""
Write-Host "Deployment Initiated Successfully!" -ForegroundColor Green
Write-Host " - Repo Explorer: Running in the newly opened PowerShell window (Port 8002)"
Write-Host " - Main Agent: Docker container (Port 8000 / Host Port 54089)"
Write-Host " - Planning Expert: Docker container (Port 8001)"
Write-Host ""
Write-Host "You can view Docker logs with the following command:" -ForegroundColor Cyan
Write-Host "docker logs -f context_pilot-app-1"
Write-Host ""
Write-Host "Press any key to exit..."
$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null
