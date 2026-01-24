import json
import os
from google.adk.tools import FunctionTool

KNOWLEDGE_BASE_PATH = os.path.join(os.getcwd(), "data", "knowledge_base.jsonl")

def record_experience(title: str, method: str, tags: str = "") -> str:
    """
    Record a successful problem-solving experience into the knowledge base.
    
    Args:
        title: A concise title for the problem (e.g., "Inventory Sync Failure").
        method: The EFFECTIVE method used to solve or diagnose it (e.g., "Checked Server.log for 'InventorySyncError'").
        tags: Optional comma-separated tags (e.g., "Network, Inventory").
        
    Returns:
        Success message.
    """
    entry = {
        "title": title,
        "content": method,
        "metadata": {
            "category": "AutoRecorded",
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
