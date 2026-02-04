import json
import os
import uuid
from datetime import datetime
from google.adk.tools import FunctionTool

data_dir = os.getenv("RAG_DATA_DIR", os.path.join(os.getcwd(), "data"))
KNOWLEDGE_BASE_PATH = os.path.join(data_dir, "knowledge_base.jsonl")

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
    
    # 1. Compile Content into the Standard Markdown Schema
    markdown_content = f"""# Intent
{intent}

# 1. Problem Context
{problem_context}

# 2. Root Cause Analysis
{root_cause}

# 3. Solution / SOP
{solution_steps}

# 4. Evidence
{evidence}
"""

    # 2. Construct Entry
    entry = {
        "id": str(uuid.uuid4()),
        "title": intent, # Use intent as title for compatibility
        "content": markdown_content, # The Rich Content for RAG
        "metadata": {
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "contributor": contributor,
            "timestamp": datetime.now().isoformat(),
            "type": "cookbook_record"
        }
    }
    
    try:
        os.makedirs(os.path.dirname(KNOWLEDGE_BASE_PATH), exist_ok=True)
        with open(KNOWLEDGE_BASE_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return f"✅ Experience recorded successfully: '{intent}'"
    except Exception as e:
        return f"❌ Failed to record experience: {e}"

record_experience_tool = FunctionTool(record_experience)
