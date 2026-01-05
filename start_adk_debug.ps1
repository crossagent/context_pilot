# start_adk_debug.ps1
# 启动 Bug Sleuth Server (Wrapper)

# Get the project root
$ProjectRoot = $PSScriptRoot

# Define Data Directory explicitly to keep it consistent
$DataDir = Join-Path $ProjectRoot "adk_data"

Write-Host "=============================================="
Write-Host "🚀 Starting Bug Sleuth Server (CLI Mode)"
Write-Host "📂 Project Root: $ProjectRoot"
Write-Host "💾 Data Dir:     $DataDir"
Write-Host "=============================================="

# Call the custom CLI
# - Uses 'uv run' to ensure installed package context
# - Explicitly passes data-dir
# - Relies on CLI's auto-discovery for .env, config.yaml, and skills/
uv run bug-sleuth serve --data-dir "$DataDir"
