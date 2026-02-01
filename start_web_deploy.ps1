# start_web_deploy.ps1
# 启动 Context Pilot Server (Production / Main App)
# 
# Usage: .\start_web_deploy.ps1
# This script strictly launches the main application server via `context-pilot serve`.
# It does NOT support direct sub-agent targeting (use start_web_debug.ps1 for that).

# Get the project root
$ProjectRoot = $PSScriptRoot

# Define Data Directory explicitly to keep it consistent
$DataDir = Join-Path $ProjectRoot "adk_data"

Write-Host "=============================================="
Write-Host "Starting Context Pilot Server (DEPLOY MODE)"
Write-Host "Project Root: $ProjectRoot"
Write-Host "Data Dir:     $DataDir"
Write-Host "=============================================="

# Build the command arguments
# Runs the main 'app.py' entry point exposed via 'main.py'
$cmdArgs = "run context-pilot serve --data-dir ""$DataDir"""

# Call the custom CLI
# - Uses 'uv run' to ensure installed package context
# - Explicitly passes data-dir
#Use cmd /c to wrap execution. This prevents PowerShell terminal from freezing 
# (losing input echo) after Ctrl+C.
cmd /c "uv $cmdArgs"
