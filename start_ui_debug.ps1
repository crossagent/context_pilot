# start_ui_debug.ps1
# 启动 Bug Sleuth Server (AG-UI Mode for Frontend Testing)

# Get the project root
$ProjectRoot = $PSScriptRoot

# Define Data Directory explicitly to keep it consistent
$DataDir = Join-Path $ProjectRoot "adk_data"

Write-Host "=============================================="
Write-Host "Starting Bug Sleuth Server (AG-UI Mode)"
Write-Host "Project Root: $ProjectRoot"
Write-Host "Data Dir:     $DataDir"
Write-Host "Mode:         ag-ui"
Write-Host "=============================================="

# Call the custom CLI with AG-UI mode
# - Uses 'uv run' to ensure installed package context
# - Explicitly passes data-dir and mode
# - Relies on CLI's auto-discovery for .env, config.yaml, and skills/
# Use cmd /c to wrap execution. This prevents PowerShell terminal from freezing 
# (losing input echo) after Ctrl+C.
cmd /c "uv run bug-sleuth serve --data-dir ""$DataDir"" --mode ag-ui"
