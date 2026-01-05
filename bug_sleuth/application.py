
import os
import sys
import logging
from pathlib import Path
from typing import Optional

from google.adk.cli.fast_api import get_fast_api_app
from fastapi.responses import HTMLResponse
from fastapi import FastAPI

# Configure Logging
logger = logging.getLogger("bug_sleuth.application")

def create_app(
    host: str = "127.0.0.1",
    port: int = 8000,
    data_dir: Optional[str] = None
) -> FastAPI:
    """
    Factory function to create the Bug Sleuth FastAPI application.
    
    Args:
        host: Host to bind (used for display/logging).
        port: Port to bind (used for display/logging).
        data_dir: Path to the ADK data directory (sessions/artifacts). 
                  If None, defaults to 'adk_data' in CWD.
    
    Returns:
        Configured FastAPI app instance.
    """
    
    # 1. Path Configuration
    # APP_ROOT is the directory containing this file (package root 'bug_sleuth')
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    AGENTS_DIR = os.path.join(APP_ROOT, "agents")
    
    # Resolve Data Directory
    if not data_dir:
        data_dir = "adk_data"
        
    if not os.path.isabs(data_dir):
        DATA_DIR = os.path.abspath(data_dir)
    else:
        DATA_DIR = data_dir
        
    ARTIFACTS_DIR = os.path.join(DATA_DIR, "artifacts")
    
    # Ensure directories exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    # Services Configuration
    # Local Artifacts: file:// URI
    artifact_service_uri = Path(ARTIFACTS_DIR).resolve().as_uri()
    
    # Local Sessions: SQLite URI
    session_db_path = os.path.join(DATA_DIR, "sessions.db")
    session_service_uri = f"sqlite+aiosqlite:///{session_db_path}"
    
    logger.info(f"Server Configuration:")
    logger.info(f"  App Root:     {APP_ROOT}")
    logger.info(f"  Agents Dir:   {AGENTS_DIR}")
    logger.info(f"  Artifacts:    {artifact_service_uri}")
    logger.info(f"  Sessions:     {session_service_uri}")
    
    try:
        # 2. Create FastAPI App using ADK Wrapper
        # This wrapper handles the logic of loading agents from AGENTS_DIR 
        # and checking 'bug_analyze_agent' compatibility.
        app = get_fast_api_app(
            agents_dir=AGENTS_DIR,
            session_service_uri=session_service_uri,
            artifact_service_uri=artifact_service_uri,
            web=True,
            a2a=False, # Can be enabled via flag if needed
            host=host,
            port=port
        )
        
        # 3. Register UI Endpoint
        # Mounts the 'reporter' UI which is a simple HTML file.
        @app.get("/reporter", response_class=HTMLResponse)
        async def get_reporter_ui():
            """Serve the embedded bug reporter UI."""
            ui_path = os.path.join(APP_ROOT, "ui", "index.html")
            if os.path.exists(ui_path):
                with open(ui_path, "r", encoding="utf-8") as f:
                    return f.read()
            return "<h1>Bug Sleuth UI Not Found</h1>"
            
        return app

    except Exception as e:
        logger.error(f"Failed to create app: {e}")
        raise e
