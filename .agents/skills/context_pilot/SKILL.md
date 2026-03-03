---
name: context-pilot
description: |
  Context Pilot 是业务知识库与内部开发知识库的管理 Agent。
  知识库收集的内容：实际业务流程、配置方法与配置文件位置、跨部门协作所需的背景知识。
  目标：填补跨部门沟通中的信息断层，避免重复踩坑。

  【必须调用此 Skill 的场景】
  - 编写代码时涉及业务逻辑理解：先查询知识库，确认业务理解是否正确
  - 业务理解为空（不确定某个流程是什么）：查询，若无记录则记录当前理解
  - 业务理解有误（发现代码或注释与实际业务不符）：更新知识库中的错误记录
  - 发现配置文件位置、环境变量、部署参数等内部信息：立即记录
  - 遇到跨部门流程（接入方式、协议格式、接口约定等）：记录到知识库

  【不需要调用的场景】
  - 纯技术实现问题（算法、数据结构、框架用法）
  - 已有充分文档的公开 API

  调用方式：运行 scripts/call_a2a.py 脚本与 Context Pilot Agent 交互。
---

# Context Pilot Agent

## 什么是 Context Pilot

Context Pilot 是运行在本地的**业务知识库 & 内部开发知识库**管理 Agent。

**知识库收录范围：**
- 实际业务流程（下单流程、支付流程、审批链路等）
- 配置方法与配置文件位置（环境变量、部署参数、Feature Flag）
- 跨部门协作所需的背景知识（接入协议、接口约定、数据格式）

**核心能力：**
1. **查询知识** — 在编写代码前，查询知识库确认业务理解是否正确
2. **记录知识** — 将发现的业务流程、配置信息等自动结构化保存
3. **纠正错误** — 发现代码/注释与实际业务不符时，更新错误记录

## 何时使用本 Skill

**【必须调用】编写代码时：**
- 代码涉及业务流程理解 → **先查询**，确认理解正确后再写
- 不确定某个流程是什么 → 查询；若无记录，记录当前理解待核实
- 发现代码或注释与实际业务不符 → 查询并**更新**错误的记录

**【主动记录】发现以下信息时：**
- 配置文件位置、环境变量名、部署参数
- 跨部门接入方式、协议格式、接口约定
- 业务流程的关键节点、特殊规则、历史坑点

**【不需要调用】：**
- 纯技术实现（算法、框架 API、数据结构）
- 已有完整公开文档的标准 API

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
