# Context Pilot Agent — API 参考

## 服务器信息

| 项目 | 値 |
|------|-----|
| 主 Agent 地址 | `http://localhost:54089` |
| App 名称 | `context_pilot_app` |
| Repo Explorer 地址 | `http://localhost:8002` (子 Agent，通常不直接调用) |

## REST API

### 创建 Session

```
POST /apps/{app_name}/users/{user_id}/sessions
Body: {}
Response: {"id": "session_id", ...}
```

### 流式执行 (SSE)

```
POST /run_sse
Content-Type: application/json

{
  "app_name": "context_pilot_app",
  "user_id": "your_user_id",
  "session_id": "session_id",
  "new_message": {
    "role": "user",
    "parts": [{"text": "你的任务描述"}]
  },
  "streaming": true
}
```

### SSE 事件格式

每行格式：`data: {JSON}`

```json
{
  "id": "event_id",
  "author": "context_pilot_agent",
  "content": {
    "parts": [
      {"text": "...", "thought": true},   // 思考过程
      {"text": "..."},                     // 最终回复
      {"functionCall": {"name": "...", "args": {}}},    // 工具调用
      {"functionResponse": {"name": "...", "response": {}}}  // 工具结果
    ]
  }
}
```

## Agent 核心工具

| 工具 | 作用 |
|------|------|
| `extract_experience_tool` | 从对话中提取结构化经验 |
| `save_experience_tool` | 保存经验到 RAG 知识库 |
| `retrieve_rag_documentation_tool` | 检索知识库中的历史经验 |
| `update_strategic_plan` | 创建/更新排查计划 |
| `repo_explorer_agent` | 委派代码探索任务 (子 Agent) |

## 启动服务

```powershell
# 启动主 Agent
cd d:\MyProject\context_pilot
uv run python -m context_pilot.main serve --port 8000

# 如需同时使用代码探索功能，另开终端启动 repo_explorer
.\start_repo_explorer_server.ps1
```
