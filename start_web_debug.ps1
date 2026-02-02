# start_adk_debug.ps1
# 启动 Bug Sleuth Server (Wrapper)

# Get the project root
$ProjectRoot = $PSScriptRoot

# Define Data Directory explicitly to keep it consistent
$DataDir = Join-Path $ProjectRoot "adk_data"

Write-Host "=============================================="
Write-Host "Starting Context Pilot Server (CLI Mode)"
Write-Host "Project Root: $ProjectRoot"
Write-Host "Data Dir:     $DataDir"

# Inject CONFIG_FILE if available (Aligning with main.py logic)
$ConfigFile = Join-Path $ProjectRoot "config.yaml"
if (Test-Path $ConfigFile) {
    $env:CONFIG_FILE = $ConfigFile
    Write-Host "Config File:  $ConfigFile"
} else {
    Write-Host "Config File:  Not found (using defaults)"
}

Write-Host "=============================================="


# Set ADK_DATA_DIR environment variable (CLI logic relies on this or default)
$env:ADK_DATA_DIR = $DataDir

# Build the command arguments
# Debug Mode: Uses standard ADK Web CLI which supports targeting sub-agents directly
# Removed --data-dir as it is not a valid option for 'adk web'
$cmdArgs = "run python -m google.adk.cli web .\context_pilot\"
# Note: To debug a sub-agent, you can edit this script to point to the sub-agent directory:
# $cmdArgs = "run python -m google.adk.cli web .\context_pilot\context_pilot_app\"


# Call the custom CLI
# - Uses 'uv run' to ensure installed package context
# - Explicitly passes data-dir
# - Relies on CLI's auto-discovery for .env, config.yaml, and skills/
# Use cmd /c to wrap execution. This prevents PowerShell terminal from freezing 
# (losing input echo) after Ctrl+C.
cmd /c "uv $cmdArgs"
