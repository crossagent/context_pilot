# start_windows_test_env.ps1
# 启动 Context Pilot Windows 本地全量测试环境
# 包括主 Agent (Port 8000) 和 Knowledge Expert Agent (Port 8003)

$ProjectRoot = $PSScriptRoot

$DataDir = Join-Path $ProjectRoot "adk_data"
$KnowledgeDataDir = Join-Path $ProjectRoot "adk_data\knowledge_agent"

# Ensure directories exist
if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir | Out-Null }
if (-not (Test-Path $KnowledgeDataDir)) { New-Item -ItemType Directory -Path $KnowledgeDataDir | Out-Null }

Write-Host "=============================================="
Write-Host "Starting Context Pilot Windows Test Environment"
Write-Host "Project Root: $ProjectRoot"
Write-Host "=============================================="

# Define environment variables globally for the child processes
$env:TZ = "Asia/Shanghai"

# 解决 Windows 上 URL 无法解析知识库容器主机名的问题
# 强制使用 localhost，以保证跨平台 agent_card 能够被正常请求
$env:KNOWLEDGE_EXPERT_URL = "http://127.0.0.1:8003"
$env:PLANNING_EXPERT_URL = "http://127.0.0.1:8001"

# === 启动主 Agent (Port 8000) ===
Write-Host ">>> Starting Context Pilot Main Agent (8000)..."
$MainArgs = "run python -m context_pilot.main serve --port 8000 --data-dir ""$DataDir"""
$MainJob = Start-Process -FilePath "uv" -ArgumentList $MainArgs -NoNewWindow -PassThru

# === 启动 Knowledge Agent (Port 8003) ===
Write-Host ">>> Starting Knowledge Expert Agent (8003)..."
$KnowledgeSessionDb = Join-Path $KnowledgeDataDir "sessions.db"
$KnowledgeArtifactsDir = Join-Path $KnowledgeDataDir "artifacts"
$KnowledgeSessionUri = "sqlite:///$KnowledgeSessionDb"
$KnowledgeArtifactUri = "file:///$KnowledgeArtifactsDir"

$KnowledgeArgs = "run adk api_server --verbose --a2a --port 8003 --host 127.0.0.1 --session_service_uri ""$KnowledgeSessionUri"" --artifact_service_uri ""$KnowledgeArtifactUri"" ""$ProjectRoot\context_pilot\context_pilot_app\remote_a2a"""

# NOTE: 为防止两个进程的输出混在一起不好调试，我们把 Knowledge Agent 放到后台运行并且不保留在新窗口
# 如果需要调试输出，可以拆分成两个单独的控制台窗口
$KnowledgeJob = Start-Process -FilePath "uv" -ArgumentList $KnowledgeArgs -NoNewWindow -PassThru

Write-Host "Both agents started locally."
Write-Host "Main App   : http://127.0.0.1:8000"
Write-Host "Knowledge  : http://127.0.0.1:8003/a2a/knowledge_agent/.well-known/agent-card.json"
Write-Host "Press Ctrl+C to stop both agents."

try {
    # Keep the script running to keep processes alive in PS depending on execution policy
    Wait-Process -Id $MainJob.Id, $KnowledgeJob.Id
}
catch {
    Write-Host "Shutting down..."
}
finally {
    if (-not $MainJob.HasExited) { Stop-Process -Id $MainJob.Id -Force }
    if (-not $KnowledgeJob.HasExited) { Stop-Process -Id $KnowledgeJob.Id -Force }
}
