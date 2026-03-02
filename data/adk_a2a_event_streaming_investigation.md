# ADK A2A Event 流式输出调查报告

> 调查时间：2026-03-01  
> 调查环境：adk-python（本地 dev 版）、a2a-sdk 0.3.24  
> 测试架构：Consumer（port 8000）→ A2A → Provider（port 8001）

---

## 一、背景与目标

在使用 ADK 的 `/run_sse` 端点时，用户希望通过 A2A 通信能实时看到 Remote Agent 工具调用的过程（function_call / function_response），而不只是等到最终答案。

目标：验证工具调用事件是否真的通过 A2A 协议流式传输到 Consumer 端。

---

## 二、架构图

```
测试脚本 (streaming_test.py)
    │  POST /run_sse (HTTP SSE, streaming=True)
    ▼
Consumer Agent (adk api_server, port 8000)
  - App: a2a_root
  - Agent: RemoteA2aAgent(name="remote_dice_agent")
    │  A2A message/stream (JSON-RPC over SSE)
    ▼
Provider Agent (uvicorn, port 8001)
  - App: hello_world_agent (to_a2a 包装)
  - 工具: roll_die, check_prime
```

---

## 三、启动命令

### Provider（远端 Remote Agent）

```powershell
$env:GEMINI_API_KEY='...'
$env:GOOGLE_GENAI_USE_VERTEXAI='FALSE'
uv run uvicorn contributing.samples.a2a_root.remote_a2a.hello_world.agent:a2a_app --host localhost --port 8001
```

### Consumer（根 Agent，API Server）

```powershell
uv run adk api_server --auto_create_session --port 8000 d:\MyProject\adk-python\contributing\samples
```

---

## 四、关键代码修改

### 4.1 开启 Provider 端流式声明

`contributing/samples/a2a_root/remote_a2a/hello_world/agent.py`

```python
from a2a.types import AgentCapabilities

a2a_app = to_a2a(
    root_agent,
    port=8001,
    capabilities=AgentCapabilities(streaming=True),  # ← 新增
)
```

**作用**：在 Agent Card 中声明 `streaming=True`，使 Consumer 知道 Provider 支持流式。

### 4.2 开启 Consumer 端流式客户端

`contributing/samples/a2a_root/agent.py`

```python
from a2a.client.client import ClientConfig as A2AClientConfig
from a2a.client.client_factory import ClientFactory as A2AClientFactory
from a2a.types import TransportProtocol as A2ATransport

_streaming_client_factory = A2AClientFactory(
    config=A2AClientConfig(
        streaming=True,   # ← 关键：默认是 False
        polling=False,
        supported_transports=[A2ATransport.jsonrpc],
    )
)

root_agent = RemoteA2aAgent(
    name="remote_dice_agent",
    agent_card=f"http://localhost:8001/{AGENT_CARD_WELL_KNOWN_PATH}",
    a2a_client_factory=_streaming_client_factory,  # ← 注入
)
```

**作用**：`RemoteA2aAgent` 默认 hardcode `streaming=False`（`remote_a2a_agent.py` 第220行）。需通过 `a2a_client_factory` 参数注入流式配置来覆盖。

### 4.3 框架层修改（agent_to_a2a.py）

`src/google/adk/a2a/utils/agent_to_a2a.py`

为 `to_a2a()` 函数增加了可选的 `capabilities` 参数，并透传给 `AgentCardBuilder`。

---

## 五、实测 Event 流（7个事件完整链路）

请求：`"Roll a 6-sided die and check if the result is prime. Show your steps."`

```
Event #1  author=remote_dice_agent
  text [thought=True]  →  "Roll a 6-sided die..."
  来源：A2A submitted 状态，Provider 把用户原始输入回显

Event #2  author=remote_dice_agent
  function_call [thought=True]  →  roll_die(sides=6)
  来源：Provider 内部 LLM 产生 function_call，经 A2A 转发

Event #3  author=remote_dice_agent
  function_response [thought=True]  →  roll_die → result=6
  来源：Provider 执行工具后返回结果，经 A2A 转发

Event #4  author=remote_dice_agent
  text [thought=True]  →  "I rolled a 6..."
  function_call [thought=True]  →  check_prime(nums=[6])
  来源：LLM 生成文本同时发出第二次工具调用（同一 Event 多 parts）

Event #5  author=remote_dice_agent
  function_response [thought=True]  →  check_prime → "No prime numbers found."

Event #6  author=remote_dice_agent
  text [thought=True]  →  "The number 6 is not a prime number."
  来源：Provider 最终 working 状态的文本，即将完成

Event #7  author=remote_dice_agent
  text  (无 thought)  →  "The number 6 is not a prime number."
  来源：TaskArtifactUpdateEvent，Provider 完成后的最终 artifact
```

---

## 六、核心机制分析

### 6.1 进度消息何时发送？

`a2a_agent_executor.py` 第242行主循环：

```python
async for adk_event in runner.run_async(...):        # ADK 每产生一个 Event
    for a2a_event in event_converter(adk_event, ...):  # 立即转成 A2A 事件
        await event_queue.enqueue_event(a2a_event)     # 立即通过 SSE 推送
```

**结论：ADK Runner 每产生一条内部事件（包括 function_call、function_response、文本 token）都会立即流式发出，不等全部完成。**

### 6.2 进度消息的内容是什么？

`event_converter.py` 把每个 ADK Event 的全部 Parts 转换：

| ADK 内部类型 | A2A 格式 |
|---|---|
| `Part(text=...)` | A2A `TextPart` |
| `Part(function_call=...)` | A2A `DataPart`（JSON）|
| `Part(function_response=...)` | A2A `DataPart`（JSON）|

### 6.3 为什么 function_call 不被执行？

Consumer 端 `remote_a2a_agent.py` 第 462~470 行：

```python
# 凡是 working 状态的事件，所有 part 都加 thought=True
for part in event.content.parts:
    part.thought = True
```

`thought=True` 是 ADK 的约定标志，表示这是"只读的内部思考记录"，**不会被 ADK 框架当成可执行的工具调用处理**。

这就是 A2A 服务边界在代码层的具体体现：

- Provider 内部的工具调用细节**完整地传输到了 Consumer**
- 但 Consumer 将其全部标记为 `thought=True`，作为"透明观察"暴露给外层，而不是重新执行

### 6.4 最终答案为何重复？

`a2a_agent_executor.py` 第 264~280 行：流程结束后，把最后一条 `working` 状态消息的 parts 复制，封装成 `TaskArtifactUpdateEvent` 再发一遍。这导致最后的文本内容出现两次：一次带 `thought=True`，一次不带。

---

## 七、Event thought 标志的含义

| thought | 含义 | ADK Web UI 渲染 |
|---|---|---|
| `True` | 来自 Remote Agent 内部的过程记录（包括 function_call） | 显示为"思考气泡"，不执行 |
| `False` / 无 | Consumer 最终暴露的回答 | 显示为普通聊天消息 |

---

## 八、A2A 架构的本质取舍

A2A 是跨团队、跨语言、跨进程的**服务边界协议**。

> **你只能看到对方的外部行为，看不到其内部实现细节。**

类比 HTTP API：你得到的是 Response，而不是对方的数据库查询和内存操作。

在 A2A 中：
- **可见**：每一轮 LLM 调用的输入输出、工具调用的入参和出参（以 `thought` 形式）、最终答案
- **不可见**：Provider 内部的 session 状态、内存、配置
- **不可执行**：Consumer 无法对 Provider 的 function_call 请求进行二次执行

---

## 九、相关源码位置

| 职责 | 文件 |
|---|---|
| Provider 端执行循环，发送进度更新 | `src/google/adk/a2a/executor/a2a_agent_executor.py` |
| ADK Event → A2A 事件转换 | `src/google/adk/a2a/converters/event_converter.py` |
| Consumer 端接收 A2A 响应，加 thought 标记 | `src/google/adk/agents/remote_a2a_agent.py` L460~470 |
| Provider 声明 streaming 能力 | `src/google/adk/a2a/utils/agent_to_a2a.py`（修改后支持 capabilities 参数）|
| Client 配置 streaming=True | `a2a.client.client.ClientConfig`（a2a-sdk 0.3.24）|

---

## 十、SSE 是什么？

**SSE（Server-Sent Events）** 是一种 HTTP 标准技术，允许服务器主动向客户端持续推送数据，客户端保持连接不关闭。

HTTP 响应格式：
```
HTTP/1.1 200 OK
Content-Type: text/event-stream

data: {"text": "第一个token"}

data: {"text": "第二个token"}

data: {"text": "完整回答"}
```

客户端（浏览器或测试脚本）保持这个 HTTP 长连接，服务器随时往里写，客户端就实时收到——这是"流式打字机输出"的底层实现。

---

## 十一、A2A 场景中的两条 SSE 链

在 A2A 架构里，一个请求经过**两个服务器**，每跨一次就有一条独立的 SSE 连接：

```
你的测试脚本
    ↑
    │ 第 2 条 SSE：ADK /run_sse 端点
    │ 传输格式：ADK Event JSON
    │ 内容：function_call/function_response（标记 thought=True）+ 最终文本
    │
Consumer 服务器（8000）
  RemoteA2aAgent：接收 A2A Event → 转回 ADK Event（加 thought=True）→ 追加到自己的 Session
    ↑
    │ 第 1 条 SSE：A2A message/stream 端点
    │ 传输格式：A2A TaskStatusUpdateEvent / TaskArtifactUpdateEvent
    │ 内容：TextPart + DataPart（function_call 的 JSON 序列化）
    │
Provider 服务器（8001）
  Runner.run_async() → event_converter → 推入 EventQueue → SSE 发出
```

| | 第 1 条 SSE | 第 2 条 SSE |
|---|---|---|
| **谁推给谁** | Provider（8001）→ Consumer（8000）| Consumer（8000）→ 测试脚本/浏览器 |
| **事件格式** | A2A Event（`TaskStatusUpdateEvent`）| ADK Event（`Event` JSON）|
| **谁订阅** | Consumer 内的 `RemoteA2aAgent` | 你的脚本 / ADK Web UI |

---

## 十二、ADK Event vs A2A Event 对比

### ADK Event（内部语言）

```python
Event(
    author="hello_world_agent",
    content=Content(parts=[
        Part(function_call=FunctionCall(name="roll_die", args={"sides": 6})),
    ])
)
```

- 存在于 ADK 执行引擎内部
- 强类型：`function_call`、`function_response`、`text`、`thought` 各有专属字段
- 会持久化到 `SessionService`（进入对话历史）
- `function_call` 会被 Runner 真正执行

### A2A Event（网络协议语言）

```python
TaskStatusUpdateEvent(
    task_id="...",
    status=TaskStatus(
        state=TaskState.working,
        message=Message(parts=[
            DataPart(data={"name": "roll_die", "args": {"sides": 6}})  # JSON 序列化
        ])
    )
)
```

- 跨网络传输用的协议对象，不知道 `function_call` 这个概念
- `TextPart` / `DataPart` 是唯一的 Part 类型
- 不直接参与 ADK 的 Session 持久化
- 经 `RemoteA2aAgent` 转换回 ADK Event 后才落库

### 三种执行路径对比

| 维度 | Local Sub-Agent | ADK /run_sse（不含A2A）| A2A message/stream |
|---|---|---|---|
| **事件类型** | ADK Event | ADK Event（JSON序列化）| A2A TaskStatusUpdateEvent |
| **function_call** | 真实执行 | 真实执行并持久化 | 只读快照（thought=True）|
| **跨进程** | ❌ | ❌ | ✅ |
| **持久化到Session** | ✅（本地）| ✅（本地）| ✅（双侧各自）|
| **SSE 条数** | 0（进程内）| 1条 | 2条串联 |
