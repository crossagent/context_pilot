---
name: context-pilot
description: |
  Context Pilot 是一个专业的代码分析与知识管理 Agent。
  在以下场景中使用此 Skill：
  - 需要将当前分析结论、根因、解决步骤记录到知识库
  - 需要从知识库检索历史经验或类似案例
  - 需要分析代码仓库结构、追踪 Bug 根因、理解业务逻辑
  - 需要制定复杂任务的排查计划
  调用方式：运行 scripts/call_a2a.py 脚本，以对话形式与 Context Pilot Agent 交互。
---

# Context Pilot Agent

## 什么是 Context Pilot

Context Pilot 是运行在本地的智能领航员 Agent，提供以下核心能力：

1. **知识记录 (Experience Recording)** — 将分析过程中发现的根因、操作步骤、模块功能等自动结构化并保存到 RAG 知识库，无需用户手动整理
2. **知识检索 (RAG Retrieval)** — 从历史知识库中检索类似问题，避免重复劳动
3. **代码库探索 (Repo Exploration)** — 通过内置的 repo_explorer 子 Agent 搜索文件、执行命令、追踪 Git 历史
4. **战略规划 (Strategic Planning)** — 将复杂问题分解为结构化排查计划

## 何时使用本 Skill

主动调用此 Skill 的场景：

- **记录经验**: "把刚才分析的这个 Bug 根因记录到知识库"
- **检索经验**: "知识库里有没有处理过类似的内存泄漏问题"
- **代码分析**: "帮我分析 `agent.py` 的实现逻辑" 或 "这个模块是做什么的"
- **Bug 排查**: 需要系统性地通过代码查找问题根因
- **沉淀知识**: 当发现重要业务逻辑、架构决策、或技术细节时

## 调用方式

使用 `scripts/call_a2a.py` 脚本与 Context Pilot Agent 交互：

```bash
# 基本用法（发送一条消息）
python .agents/skills/context_pilot/scripts/call_a2a.py --query "你的任务描述"

# 复用已有 session（继续对话）
python .agents/skills/context_pilot/scripts/call_a2a.py \
  --query "继续分析..." \
  --session-id <session_id_from_previous_run>

# 自定义服务器地址（默认 localhost:54089）
python .agents/skills/context_pilot/scripts/call_a2a.py \
  --query "任务" \
  --host localhost --port 54089
```

## 解读输出

脚本会实时打印 SSE 流式事件：

- `💭 [thought]` — Agent 的中间思考过程（内部推理，帮助理解进展）
- `🔧 [tool_call]` — Agent 调用工具（如 extract_experience_tool、repo_explorer）
- `📥 [tool_resp]` — 工具返回结果
- `💬 [final]` — 最终回复内容（最重要）
- `Session ID` — 每次输出中打印，用于下次 --session-id 复用对话

## 配置说明

服务器默认地址：`http://localhost:8000`（context_pilot_agent 主 Agent）

如需修改，参考 `assets/api_reference.md`。
