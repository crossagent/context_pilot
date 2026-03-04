# start_knowledge_expert.ps1
# 启动 Knowledge Expert Agent 服务 (Remote A2A Mode)

# Get the project root
$ProjectRoot = $PSScriptRoot

# Define Data Directory explicitly to keep it consistent
# User requested specifically to save knowledge_agent data to adk_data/knowledge_agent
$DataDir = Join-Path $ProjectRoot "adk_data/knowledge_agent"
$ArtifactsDir = Join-Path $DataDir "artifacts"
$SessionDb = Join-Path $DataDir "sessions.db"

# Ensure directories exist
if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir | Out-Null }
if (-not (Test-Path $ArtifactsDir)) { New-Item -ItemType Directory -Path $ArtifactsDir | Out-Null }

Write-Host "=============================================="
Write-Host "Starting Knowledge Expert Agent (A2A MODE)"
Write-Host "Project Root: $ProjectRoot"
Write-Host "Data Dir:     $DataDir"
Write-Host "=============================================="

# URI format: 3 slashes for absolute path
# The Python logic in services.py handles slash normalization.
$SessionUri = "sqlite:///$SessionDb" 
$ArtifactUri = "file:///$ArtifactsDir"

$env:ADK_DATA_DIR = $DataDir
$env:ADK_SESSION_SERVICE_URI = $SessionUri
$env:ADK_ARTIFACT_SERVICE_URI = $ArtifactUri

# SET PYTHONPATH to project root so agents can be loaded correctly
$env:PYTHONPATH = "$ProjectRoot"

# Build the command arguments
$cmdArgs = "run adk api_server --verbose --a2a --port 54090 --host 0.0.0.0 --session_service_uri ""$SessionUri"" --artifact_service_uri ""$ArtifactUri"" ""$ProjectRoot\context_pilot\context_pilot_app\remote_a2a"""

# Call the custom CLI via uv
cmd /c "uv $cmdArgs"
