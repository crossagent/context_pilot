
import os
import sqlite3
import logging
from typing import List, Dict, Optional
from google.adk.tools.tool_context import ToolContext
import yaml
from google.adk.tools.tool_context import ToolContext

# Configure logging
logger = logging.getLogger("SearchSymbolTool")

def load_repos_from_config():
    """Lengths configured repositories safely."""
    # Try multiple paths for config
    candidates = ["agents/config.yaml", "../agents/config.yaml", "config.yaml"]
    config_path = None
    for p in candidates:
        if os.path.exists(p):
            config_path = p
            break
            
    if not config_path:
        return []

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            repos = []
            if 'repositories' in config:
                repo_list = config['repositories']
                if isinstance(repo_list, list):
                    for repo_data in repo_list:
                        if isinstance(repo_data, dict) and 'path' in repo_data:
                            repos.append(repo_data['path'])
            return repos
    except Exception:
        return []

async def search_symbol_tool(
    symbol_name: str,
    tool_context: ToolContext,
    type_filter: Optional[str] = None
) -> dict:
    """
    Searches for code symbols (classes, methods, enums) using the pre-built SQLite index.
    
    Args:
        symbol_name: The name of the symbol to find (e.g., "BattleManager", "Explode"). Supports partial matches.
        type_filter: Optional. Filter by type: 'class', 'method', 'field', 'enum', etc.
        
    Returns:
        Summary of found symbols and their locations.
    """
    
    # 1. Identify Repositories
    repos = load_repos_from_config()

    if not repos:
        return {"status": "error", "summary": "No repositories configured."}

    results = []
    
    # 2. Query each repo's DB
    for repo_path in repos:
        db_path = os.path.join(repo_path, ".bug_sleuth_agent", "code_index.db")
        
        if not os.path.exists(db_path):
            logger.warning(f"Index not found for {repo_path}")
            continue
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            query = "SELECT name, type, file_path, start_line, end_line FROM symbols WHERE name LIKE ? "
            params = [f"%{symbol_name}%"]
            
            if type_filter:
                query += " AND type = ?"
                params.append(type_filter)
                
            query += " LIMIT 20" # Cap per repo
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            for row in rows:
                results.append({
                    "repo": os.path.basename(repo_path),
                    "name": row[0],
                    "type": row[1],
                    "file": row[2],
                    "lines": f"{row[3]}-{row[4]}"
                })
                
            conn.close()
            
        except Exception as e:
            logger.error(f"Error querying DB {db_path}: {e}")

    # 3. Format Output
    if not results:
        return {
            "status": "success",
            "summary": f"No symbols found matching '{symbol_name}'."
        }
        
    output_lines = [f"Found {len(results)} matches for '{symbol_name}':"]
    for i, res in enumerate(results[:20], 1):
        output_lines.append(f"{i}. [{res['type']}] {res['name']} in {res['repo']}/{res['file']} (Lines {res['lines']})")
        
    if len(results) > 20:
        output_lines.append(f"... and {len(results) - 20} more.")

    return {
        "status": "success",
        "output": "\n".join(output_lines),
        "summary": f"Found {len(results)} symbols matching '{symbol_name}'."
    }
