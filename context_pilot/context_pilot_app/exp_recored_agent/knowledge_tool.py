import json
import os
import uuid
from datetime import datetime
from google.adk.tools import FunctionTool, ToolContext
from context_pilot.shared_libraries.state_keys import StateKeys

data_dir = os.getenv("RAG_DATA_DIR", os.path.join(os.getcwd(), "data"))

# Import DB Manager
try:
    from context_pilot.utils.db_manager import default_db_manager
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    from context_pilot.utils.db_manager import default_db_manager

def extract_experience(
    tool_context: ToolContext,
    intent: str, 
    problem_context: str,
    root_cause: str,
    solution_steps: str,
    evidence: str = "",
    tags: str = "",
    contributor: str = "User"
) -> str:
    """
    Extracts and stages experience data from conversation to be saved later.
    
    Args:
        intent: The core question or goal this experience answers.
        problem_context: Description of the symptoms, environment, and trigger.
        root_cause: The technical reason why the issue occurred.
        solution_steps: The specific steps taken to fix it (SOP).
        evidence: Git commits, logs, or links that verify the fix.
        tags: Comma-separated tags (e.g., "redis, timeout, production").
        contributor: Name of the author.
    """
    # Store in individual state keys
    tool_context.state[StateKeys.EXP_INTENT] = intent
    tool_context.state[StateKeys.EXP_PROBLEM_CONTEXT] = problem_context
    tool_context.state[StateKeys.EXP_ROOT_CAUSE] = root_cause
    tool_context.state[StateKeys.EXP_SOLUTION_STEPS] = solution_steps
    tool_context.state[StateKeys.EXP_EVIDENCE] = evidence
    tool_context.state[StateKeys.EXP_TAGS] = tags
    tool_context.state[StateKeys.EXP_CONTRIBUTOR] = contributor
    
    return (
        f"✅ Experience extracted and staged for review.\n"
        f"Intent: {intent}\n"
        f"Tags: {tags}\n\n"
        f"Please review the details. If correct, proceed to save."
    )

def save_experience(tool_context: ToolContext, entry_id: str = "") -> str:
    """
    Commits the staged experience data to the permanent Knowledge Base.
    Must be called AFTER extract_experience.
    
    Args:
        entry_id: Optional. If provided and exists in DB, update that entry.
                  If not provided or not found, create a new entry.
    """
    # Retrieve from individual state keys
    intent = tool_context.state.get(StateKeys.EXP_INTENT)
    problem_context = tool_context.state.get(StateKeys.EXP_PROBLEM_CONTEXT)
    root_cause = tool_context.state.get(StateKeys.EXP_ROOT_CAUSE)
    solution_steps = tool_context.state.get(StateKeys.EXP_SOLUTION_STEPS)
    evidence = tool_context.state.get(StateKeys.EXP_EVIDENCE)
    tags = tool_context.state.get(StateKeys.EXP_TAGS)
    contributor = tool_context.state.get(StateKeys.EXP_CONTRIBUTOR)
    
    if not intent or not root_cause:
        return "❌ No pending experience found (Intent or Root Cause missing). Please extract experience first."
    
    now = datetime.now().isoformat()
    
    # Ensure DB is ready
    default_db_manager.init_db()
    
    try:
        with default_db_manager.get_connection() as conn:
            # Check if entry_id exists (for update)
            is_update = False
            if entry_id:
                existing = conn.execute(
                    "SELECT id FROM knowledge_entries WHERE id = ?", 
                    (entry_id,)
                ).fetchone()
                is_update = existing is not None
            
            if is_update:
                # UPDATE existing entry
                conn.execute("""
                    UPDATE knowledge_entries 
                    SET intent=?, problem_context=?, root_cause=?, solution_steps=?, 
                        evidence=?, tags=?, contributor=?, updated_at=?
                    WHERE id=?
                """, (
                    intent, 
                    problem_context, 
                    root_cause, 
                    solution_steps, 
                    evidence, 
                    tags, 
                    contributor, 
                    now,
                    entry_id
                ))
                result_id = entry_id
                action = "updated"
            else:
                # INSERT new entry
                result_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO knowledge_entries 
                    (id, intent, problem_context, root_cause, solution_steps, evidence, tags, contributor, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result_id, 
                    intent, 
                    problem_context, 
                    root_cause, 
                    solution_steps, 
                    evidence, 
                    tags, 
                    contributor, 
                    now, 
                    now
                ))
                action = "created"
            
        # Clear state after successful save
        tool_context.state[StateKeys.EXP_INTENT] = None
        tool_context.state[StateKeys.EXP_PROBLEM_CONTEXT] = None
        tool_context.state[StateKeys.EXP_ROOT_CAUSE] = None
        tool_context.state[StateKeys.EXP_SOLUTION_STEPS] = None
        tool_context.state[StateKeys.EXP_EVIDENCE] = None
        tool_context.state[StateKeys.EXP_TAGS] = None
        tool_context.state[StateKeys.EXP_CONTRIBUTOR] = None
        
        return f"✅ Experience {action} in Knowledge Base. (ID: {result_id})"
    except Exception as e:
        return f"❌ Failed to save experience to DB: {e}"

extract_experience_tool = FunctionTool(extract_experience)
save_experience_tool = FunctionTool(save_experience)
