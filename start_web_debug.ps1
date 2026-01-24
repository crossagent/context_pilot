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
Write-Host "=============================================="

# Optional: Set this to start with a specific sub-agent (e.g. "bug_analyze_agent")
# If empty, it defaults to the Supervisor (context_pilot_agent)
$RootAgentName = ""

# Build the command arguments
$cmdArgs = "run context-pilot serve --data-dir ""$DataDir"""

if ($RootAgentName) {
    $cmdArgs += " --root-agent-name ""$RootAgentName"""
}

# Call the custom CLI
# - Uses 'uv run' to ensure installed package context
# - Explicitly passes data-dir
# - Relies on CLI's auto-discovery for .env, config.yaml, and skills/
# Use cmd /c to wrap execution. This prevents PowerShell terminal from freezing 
# (losing input echo) after Ctrl+C.
cmd /c "uv $cmdArgs"
