import os
import json
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from context_pilot.scripts.rag_config import RagConfig
try:
    from context_pilot.utils.db_manager import default_db_manager
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    from context_pilot.utils.db_manager import default_db_manager

router = APIRouter()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Context Pilot - Knowledge Base Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .btn {{ background-color: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; border-radius: 4px; }}
        .btn:hover {{ background-color: #45a049; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; }}
        .danger {{ background-color: #f44336; }}
        .danger:hover {{ background-color: #da190b; }}
    </style>
    <script>
        function triggerIndex(mode) {{
            if (confirm("Are you sure you want to trigger a " + mode + " index build?")) {{
                fetch("/admin/api/build_index?mode=" + mode, {{ method: "POST" }})
                    .then(response => response.json())
                    .then(data => alert(data.message))
                    .catch(err => alert("Error triggering build"));
            }}
        }}
    </script>
</head>
<body>
    <div class="header">
        <h1>Knowledge Base Dashboard</h1>
        <div>
            <button class="btn" onclick="triggerIndex('incremental')">Trigger Incremental Build</button>
            <button class="btn danger" onclick="triggerIndex('full')">Trigger Full Rebuild</button>
        </div>
    </div>
    
    <div style="display: flex; gap: 40px;">
        <div style="flex: 1; background: #f9f9f9; padding: 20px; border-radius: 8px;">
            <h2>SQLite Stats</h2>
            <p><strong>Total Entries:</strong> {total_count}</p>
        </div>
        <div style="flex: 1; background: #eef7ff; padding: 20px; border-radius: 8px;">
            <h2>RAG Index Stats</h2>
            <p><strong>Last Build:</strong> {rag_last_build}</p>
            <p><strong>Vector Count:</strong> {rag_doc_count}</p>
            <p><strong>Embedding Model:</strong> {rag_model}</p>
            <p><strong>Last Strategy:</strong> {rag_strategy}</p>
        </div>
        <div style="flex: 1; background: #fff4e5; padding: 20px; border-radius: 8px;">
            <h2>Background Task</h2>
            <p><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{task_status}</span></p>
            <p><strong>Message:</strong> {task_message}</p>
            <p><strong>Next Run:</strong> {next_run}</p>
            <p><strong>Last Check:</strong> {last_check}</p>
        </div>
    </div>
    
    <h2>Recent Experiences</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Intent</th>
            <th>Root Cause</th>
            <th>Tags</th>
            <th>Created At</th>
        </tr>
        {rows_html}
    </table>
</body>
</html>
"""

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    default_db_manager.init_db()
    
    # RAG Stats
    manifest_path = os.path.join(RagConfig.STORAGE_DIR, RagConfig.MANIFEST_FILE)
    rag_meta = {
        "build_time": "Never",
        "doc_count": 0,
        "embedding_model": RagConfig.EMBEDDING_MODEL,
        "strategy": "-"
    }
    
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                rag_meta.update(json.load(f))
        except:
            pass

    try:
        with default_db_manager.get_connection() as conn:
            # Get total count
            count_result = conn.execute("SELECT COUNT(*) FROM knowledge_entries").fetchone()
            total_count = count_result[0] if count_result else 0
            
            # Get latest 50 entries
            rows = conn.execute("SELECT id, intent, root_cause, tags, created_at FROM knowledge_entries ORDER BY created_at DESC LIMIT 50").fetchall()
            
            rows_html = ""
            for row in rows:
                tags = row['tags'] if row['tags'] else '-'
                # truncate long text
                intent = row['intent'][:50] + '...' if len(row['intent']) > 50 else row['intent']
                rc = row['root_cause'][:50] + '...' if len(row['root_cause']) > 50 else row['root_cause']
                
                rows_html += f"<tr><td>{row['id'][:8]}...</td><td>{intent}</td><td>{rc}</td><td>{tags}</td><td>{row['created_at']}</td></tr>"
                
            if not rows_html:
                rows_html = "<tr><td colspan='5'>No entries found in knowledge base.</td></tr>"
                
    except Exception as e:
        total_count = "Error"
        rows_html = f"<tr><td colspan='5'>Error connecting to DB: {e}</td></tr>"
        
    # Task Status
    status_path = os.path.join(RagConfig.STORAGE_DIR, "index_status.json")
    task_info = {
        "status": "Unknown",
        "message": "N/A",
        "result": "N/A",
        "last_check": "-",
        "next_run": "-"
    }
    if os.path.exists(status_path):
        try:
            with open(status_path, 'r') as f:
                task_info.update(json.load(f))
        except:
            pass
            
    status_color = "orange"
    if task_info['status'] == "Running": status_color = "blue"
    elif task_info['status'] == "Idle":
        status_color = "green" if task_info.get('result') == "Success" else "red"

    return HTML_TEMPLATE.format(
        total_count=total_count, 
        rows_html=rows_html,
        rag_last_build=rag_meta['build_time'],
        rag_doc_count=rag_meta['doc_count'],
        rag_model=rag_meta['embedding_model'],
        rag_strategy=rag_meta['strategy'],
        task_status=task_info['status'],
        task_message=task_info['message'],
        next_run=task_info['next_run'],
        last_check=task_info['last_check'],
        status_color=status_color
    )

@router.post("/admin/api/build_index")
async def trigger_build_index(mode: str = "incremental"):
    # Note: Because filelock is used in build_index.py, running this concurrently is safe.
    import subprocess
    import threading
    
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "build_index.py")
    
    def run_build():
        subprocess.run(["python", script_path, f"--mode={mode}"])
        
    threading.Thread(target=run_build, daemon=True).start()
    return {"status": "success", "message": f"Background {mode} index build triggered. Check logs for details."}
