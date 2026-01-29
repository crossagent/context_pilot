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

# Enable Logging Plugin for Debugging
$env:ADK_ENABLE_LOGGING_PLUGIN = "true"

# Start Backend in background job
Write-Host ""
Write-Host "[1/2] Starting Backend Agent (AG-UI Mode) on port $BackendPort..."
# Start Backend using Start-Process for better visibility and environment inheritance
Write-Host ""
Write-Host "[1/2] Starting Backend Agent (AG-UI Mode) on port $BackendPort..."

$uvPath = "uv"  # Assume 'uv' is in PATH. If not, you might need a full path or "cmd /c uv"

# We execute 'uv' directly. 
# ArgumentList must be parsed carefully by PowerShell.
# We pass the rest of the command as arguments to 'uv'.
# The constructed $backendArgs string (e.g. "run context-pilot serve ...") needs to be split or passed correctly.

# To simplify, we'll use 'cmd /c' to run the full command string, 
# ensuring correct parsing of quotes and spaces by the shell.
# This opens a new window for the backend server.
Start-Process -FilePath "cmd" -ArgumentList "/c uv $backendArgs" -WorkingDirectory $ProjectRoot

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

Push-Location (Join-Path $ProjectRoot "frontend")

try {
    # Run frontend (this will block)
    npm run dev:ui
}
finally {
    # Cleanup: Stop backend when frontend exits
    Write-Host ""
    Write-Host "Stopping Backend Agent..."
    # Cleanup: Backend is running in a separate window, so we don't need to kill a local job.
    # User can close the backend window manually.
    Write-Host ""
    Write-Host "Frontend stopped. Please close the Backend window manually if needed."
    
    Pop-Location
}
