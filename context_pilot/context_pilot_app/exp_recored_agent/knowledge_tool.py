import json
import os
import uuid
from datetime import datetime
from google.adk.tools import FunctionTool

KNOWLEDGE_BASE_PATH = os.path.join(os.getcwd(), "data", "knowledge_base.jsonl")

def record_experience(question: str, answer: str, category: str, contributor: str, tags: str = "") -> str:
    """
    Record a Q&A experience into the knowledge base.
    
    Args:
        question: The problem or question (e.g., "Inventory Sync Failure").
        answer: The solution or effective method (e.g., "Checked Server.log for 'InventorySyncError'").
        category: The category of the knowledge (e.g., "BugAnalysis").
        contributor: The name of the person adding this entry.
        tags: Optional comma-separated tags (e.g., "Network, Inventory").
        
    Returns:
        Success message.
    """
    entry = {
        "id": str(uuid.uuid4()),
        "title": question,
        "content": answer,
        "metadata": {
            "category": category,
            "contributor": contributor,
            "timestamp": datetime.now().isoformat(),
            "tags": [t.strip() for t in tags.split(",") if t.strip()]
        }
    }
    
    try:
        os.makedirs(os.path.dirname(KNOWLEDGE_BASE_PATH), exist_ok=True)
        with open(KNOWLEDGE_BASE_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return "Experience successfully recorded."
    except Exception as e:
        return f"Failed to record experience: {e}"

record_experience_tool = FunctionTool(record_experience)
