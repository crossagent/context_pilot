# start_ui_debug.ps1
# 启动 Context Pilot 完整前端应用 (Frontend + Backend in AG-UI Mode)

# Get the project root
$ProjectRoot = $PSScriptRoot

# Define Data Directory explicitly to keep it consistent
$DataDir = Join-Path $ProjectRoot "adk_data"

Write-Host "=============================================="
Write-Host "Starting Context Pilot Full Stack (UI Mode)"
Write-Host "Project Root: $ProjectRoot"
Write-Host "Data Dir:     $DataDir"
Write-Host "Mode:         ag-ui + frontend"
Write-Host "=============================================="

# Optional: Set this to start with a specific sub-agent (e.g. "bug_analyze_agent")
# If empty, it defaults to the Supervisor (context_pilot_agent)
$RootAgentName = ""

# Backend port
$BackendPort = 8002

# Build the backend command arguments
$backendArgs = "run context-pilot serve --data-dir `"$DataDir`" --mode ag-ui --port $BackendPort"

if ($RootAgentName) {
    $backendArgs += " --root-agent-name `"$RootAgentName`""
}

# Start Backend in background job
Write-Host ""
Write-Host "[1/2] Starting Backend Agent (AG-UI Mode) on port $BackendPort..."
$backendJob = Start-Job -ScriptBlock {
    param($root, $args)
    Set-Location $root
    cmd /c "uv $args"
} -ArgumentList $ProjectRoot, $backendArgs

# Wait a bit for backend to initialize
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "[2/2] Starting Frontend (Next.js) on port 3000..."
Write-Host ""
Write-Host "=============================================="
Write-Host "Services:"
Write-Host "  - Frontend:  http://localhost:3000"
Write-Host "  - Backend:   http://localhost:$BackendPort"
Write-Host "  - API Docs:  http://localhost:$BackendPort/docs"
Write-Host "=============================================="
Write-Host ""

Set-Location (Join-Path $ProjectRoot "frontend")

try {
    # Run frontend (this will block)
    npm run dev:ui
}
finally {
    # Cleanup: Stop backend when frontend exits
    Write-Host ""
    Write-Host "Stopping Backend Agent..."
    Stop-Job -Job $backendJob
    Remove-Job -Job $backendJob
}
