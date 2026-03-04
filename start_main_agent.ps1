# start_main_agent.ps1
# 启动 Context Pilot 主 Agent 服务

# Get the project root
$ProjectRoot = $PSScriptRoot

# Define Data Directory explicitly to keep it consistent
$DataDir = Join-Path $ProjectRoot "adk_data"
$ArtifactsDir = Join-Path $DataDir "artifacts"
$SessionDb = Join-Path $DataDir "sessions.db"

# Ensure directories exist
if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir | Out-Null }
if (-not (Test-Path $ArtifactsDir)) { New-Item -ItemType Directory -Path $ArtifactsDir | Out-Null }

Write-Host "=============================================="
Write-Host "Starting Context Pilot Main Agent"
Write-Host "Project Root: $ProjectRoot"
Write-Host "Data Dir:     $DataDir"
Write-Host "Port:         54089"
Write-Host "=============================================="

# URI format: 3 slashes for absolute path
# The Python logic in main.py and services.py handles slash normalization.
$SessionUri = "sqlite:///$SessionDb" 
$ArtifactUri = "file:///$ArtifactsDir"

$env:ADK_DATA_DIR = $DataDir
$env:ADK_SESSION_SERVICE_URI = $SessionUri
$env:ADK_ARTIFACT_SERVICE_URI = $ArtifactUri
$env:PYTHONPATH = $ProjectRoot

# Build the command arguments
# Note: Using the main.py serve command
$cmdArgs = "run python -m context_pilot.main serve --port 54089 --data-dir ""$DataDir"""

# Call via uv
cmd /c "uv $cmdArgs"
