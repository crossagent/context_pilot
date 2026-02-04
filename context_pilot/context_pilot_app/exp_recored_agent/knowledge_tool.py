import json
import os
import uuid
from datetime import datetime
from google.adk.tools import FunctionTool

data_dir = os.getenv("RAG_DATA_DIR", os.path.join(os.getcwd(), "data"))
KNOWLEDGE_BASE_PATH = os.path.join(data_dir, "knowledge_base.jsonl")

# Import DB Manager
try:
    from context_pilot.utils.db_manager import default_db_manager
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    from context_pilot.utils.db_manager import default_db_manager

def record_experience(
    intent: str, 
    problem_context: str,
    root_cause: str,
    solution_steps: str,
    evidence: str = "",
    tags: str = "",
    contributor: str = "User"
) -> str:
    """
    Records a structured engineering experience into the Knowledge Base (Cookbook).
    
    Args:
        intent: The core question or goal this experience answers (e.g., "Fix Redis Timeout").
        problem_context: Description of the symptoms, environment, and trigger.
        root_cause: The technical reason why the issue occurred.
        solution_steps: The specific steps taken to fix it (SOP).
        evidence: Git commits, logs, or links that verify the fix.
        tags: Comma-separated tags (e.g., "redis, timeout, production").
        contributor: Name of the author.
    """
    
    entry_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    # Ensure DB is ready
    default_db_manager.init_db()
    
    try:
        with default_db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO knowledge_entries 
                (id, intent, problem_context, root_cause, solution_steps, evidence, tags, contributor, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id, 
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
            
        return f"✅ Experience recorded successfully: '{intent}' (ID: {entry_id})"
    except Exception as e:
        return f"❌ Failed to record experience: {e}"

record_experience_tool = FunctionTool(record_experience)
