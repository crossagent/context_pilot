# ContextPilot: 智能工程领航员

ContextPilot 是一个专注于**工程上下文导航**与**记忆驱动规划**的智能 Agent 系统。它旨在帮助开发者在复杂的工程环境中快速定位信息、理解逻辑并制定解决方案。

## 1. 核心意义

在大型软件工程中，解决问题往往需要跨越代码、配置、文档与历史记录的鸿沟。ContextPilot 通过以下机制填补这一空白：
*   **全链路感知**：打通代码 (Code)、配置 (Config)、流程 (Process) 与历史 (History) 的信息壁垒。
*   **记忆驱动规划**：利用 RAG 技术优先检索历史经验，避免重复踩坑，实现从“盲目探索”到“经验复用”的转变。当一次成功的查询之后，执行的方法，会被当作经验保留。

## 2. 核心功能

*   **多维信息检索**：
    *   **代码分析**：基于语义的静态分析与调用链追踪。
    *   **配置解析**：支持 JSON/YAML/Excel/Proto 等多种配置格式的读取与数值关联。
    *   **文档导航**：自动索引并检索项目 README、Wiki 及 SOP 文档。
*   **战略规划 (Strategic Planning)**：
    *   战略规划其实就是从已知的经验中，按照一个标准的路径去查询最新的状态。
    *   维护全局任务状态与待办事项。
    *   根据检索结果动态调整排查路径。
*   **任务分发**：
    *   Root Agent (领航员) 负责意图识别。
    *   Sub Agents (RepositorySleuth, DocNavigator) 负责具体领域的深度执行。

## 3. 架构角色

ContextPilot 采用 **Artifact-Driven (制品驱动)** 架构：

*   **ContextPilot (Root Agent)**: 战略指挥官，负责 RAG 检索、计划制定与任务分发。
*   **RepositorySleuth (Sub Agent)**: 代码专家，负责根据代码仓库的静态分析去寻找线索。
*   **DocNavigator (Sub Agent)**: 知识库管理员，负责文档与流程检索。

## 4. 开发指南

### 4.1 安装

```bash
# 在项目根目录下执行 Editable Install
pip install -e .
```
*(注：为保持兼容性，命令行工具仍名为 `context-pilot`)*

### 4.2 启动服务

支持零配置启动，自动加载当前目录下的 `.env` 与 `config.yaml`。

```bash
# 默认启动 (AG-UI 模式，支持 CopilotKit 前端)
context-pilot serve

# 纯后端模式 (仅 REST API)
context-pilot serve --mode adk-web
```

### 4.3 扩展能力 (Skills)

通过 Python 插件机制扩展 Agent 能力：

1.  在 `skills/` 目录下创建包 (e.g., `skills/my_feature/`)。
2.  编写 `tool.py` 实现业务逻辑。
3.  在 `__init__.py` 中将工具注册到 `root_skill_registry`。

```python
# skills/my_feature/__init__.py
try:
    from context_pilot.context_pilot_app.skill_library.extensions import root_skill_registry
    from google.adk.tools import FunctionTool
    from .tool import my_cool_feature

    root_skill_registry.add_tool(FunctionTool(fn=my_cool_feature))
except ImportError:
    pass
```

### 4.4 测试

使用 `pytest` 运行集成测试。测试框架内置 `MockLlm`，无需消耗真实 Token 即可验证 Agent 流程。

```bash
# 运行所有测试
python -m pytest test/integration/ -v

# 运行特定测试
python -m pytest test/integration/test_context_pilot_plan.py -v
```
