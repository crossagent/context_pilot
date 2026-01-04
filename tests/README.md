# ADK Testing Framework

This directory contains the automated testing infrastructure for the ADK components of this project.

## Testing Strategy: The 3-Level Pyramid

We employ a progressive testing strategy to isolate faults efficiently, moving from pure code logic to complex agentic reasoning.

### Level 0: Unit Tests (Pure Logic)
*   **Goal**: Verify individual functions, parsers, and utilities in isolation. No ADK dependencies (where possible).
*   **Location**: `tests/unit/`
*   **Key Concept**: **Input/Output**. Given a specific input (e.g., a regex string), does the function return the expected output?
*   **Approach**: Standard `pytest`. Direct function calls. Mock external libraries (like `requests` or `subprocess`) using `unittest.mock`.
*   **When to run**: On every file save.

### Level 1: Integration Tests (Engineering Validation)
*   **Goal**: specific Agent/Tool workflow. "If the LLM *wants* to do X, can the system execute X correctly?"
*   **Location**: `tests/integration/`
*   **Key Concept**: **MockLlm & Runner**.
    *   **Runner**: The real ADK runtime engine. Executes tools, converts types, and manages session state.
    *   **MockLlm**: A "Scripted Brain" that returns pre-defined responses based on keyword triggers.
*   **Approach**: Use `TestClient(agent=..., model="mock/...")`. Define `MockLlm.set_behaviors({"keyword": {"tool": "name"}})` to traverse code paths deterministically.
*   **When to run**: On feature completion / Pre-commit.

### Level 2: System Tests (Intelligence Validation)
*   **Goal**: Evaluate "Smartness" and Prompt Quality. Verify that the agent selects the correct tools and plans logically for realistic scenarios.
*   **Location**: `eval_cases/` (Source Data) -> `setup_eval_suites.py` (Generator) -> `*.evalset.json` (Artifact).
*   **Key Concept**: **ADK Eval System**.
    *   **Eval Set**: A collection of "Conversation Starters" and "Expected Goals".
    *   **Mechanism**: `adk eval run` executes the agent against these cases using a Real LLM (e.g., Gemini).
    *   **Scoring**: Manual review or semantic matching of the trajectory.
*   **When to run**: Nightly or when modifying core Prompts.

## Directory Structure
*   `tests/unit/`: Level 0 Tests.
*   `tests/integration/`: Level 1 Tests.
*   `tests/utils/`: Infrastructure (`MockLlm`, `TestClient`).
*   `eval_cases/`: Level 2 Test Scenarios (JSON).

## Running Tests
**Run Level 0 & 1 (Fast):**
```bash
python -m pytest tests/
```

**Run Level 2 (Eval):**
1.  **Generate Suites**: `python setup_eval_suites.py`
2.  **Run Evaluation**: `adk eval run <agent_path> <suite_id>`
    (Reference `setup_eval_suites.py` for available Suite IDs).

## How to Write Level 1 Tests
1.  **Identify the Path**: "I need to test the 'Missing Info' flow."
2.  **Script the Brain**: "When Agent sees 'It crashed', it should ask 'Which device?'. When it sees 'Pixel 6', it should call `update_bug_info_tool`."
3.  **Configure Mock**:
    ```python
    MockLlm.set_behaviors({
        "crashed": "Which device?",
        "Pixel 6": {"tool": "update_bug_info_tool", "args": {"device_name": "Pixel 6"}}
    })
    ```
4.  **Run & Assert**: `client.chat("It crashed")` -> Verify response or state change.

## How to Add Level 2 Cases
1.  **Edit Source**: Add new scenario to `eval_cases/<agent>/<suite>/cases.json`.
2.  **Regenerate**: Run `python setup_eval_suites.py`.
3.  **Run Eval**: Use ADK CLI to execute and review results.
