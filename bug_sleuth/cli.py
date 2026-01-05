
import os
import sys
import logging
import click
import uvicorn
from pathlib import Path
from dotenv import load_dotenv
from google.adk.cli.fast_api import get_fast_api_app
from fastapi.responses import HTMLResponse

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bug_sleuth.cli")

@click.group()
def main():
    """Bug Sleuth CLI Tool"""
    pass

@main.command()
@click.option("--port", default=8000, help="Port to run the server on.")
@click.option("--host", default="127.0.0.1", help="Host to run the server on.")
@click.option("--skills-dir", envvar="SKILL_PATH", help="Path to the skills directory.")
@click.option("--config", envvar="CONFIG_FILE", help="Path to the configuration file.")
@click.option("--env-file", default=".env", help="Path to .env file.")
@click.option("--data-dir", default="adk_data", help="Directory for local data storage.")
def serve(port, host, skills_dir, config, env_file, data_dir):
    """
    Start the Bug Sleuth Agent Server.
    """
    # 1. Load Environment Variables
    # Default is ".env", so it checks CWD automatically.
    if os.path.exists(env_file):
        logger.info(f"Loading environment from {env_file}")
        load_dotenv(env_file)
    
    # 2. Set Environment Variables for Agent
    # Auto-discovery: If not provided, check CWD for 'skills' folder
    if not skills_dir and os.path.exists("skills") and os.path.isdir("skills"):
        skills_dir = "skills"
        logger.info("Auto-discovered 'skills' directory in current location.")

    if skills_dir:
        os.path.abspath_skills = os.path.abspath(skills_dir)
        os.environ["SKILL_PATH"] = os.path.abspath_skills
        logger.info(f"Set SKILL_PATH to {os.path.abspath_skills}")
    
    # Auto-discovery: If not provided, check CWD for 'config.yaml'
    if not config and os.path.exists("config.yaml"):
        config = "config.yaml"
        logger.info("Auto-discovered 'config.yaml' in current directory.")

    if config:
        os.environ["CONFIG_FILE"] = os.path.abspath(config)
        logger.info(f"Set CONFIG_FILE to {os.environ['CONFIG_FILE']}")
        
    # 3. Path Configuration
    # APP_ROOT is the directory containing this cli.py (package root 'bug_sleuth')
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    AGENTS_DIR = os.path.join(APP_ROOT, "agents")
    
    # Resolve Data Directory
    # If valid absolute path, use it. If relative, anchor to CWD (users expect data in their project dir)
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
        # 4. Create FastAPI App using ADK Wrapper
        app = get_fast_api_app(
            agents_dir=AGENTS_DIR,
            session_service_uri=session_service_uri,
            artifact_service_uri=artifact_service_uri,
            web=True,
            a2a=False, # Can be enabled via flag if needed
            host=host,
            port=port
        )
        
        # 5. Register UI Endpoint
        @app.get("/reporter", response_class=HTMLResponse)
        async def get_reporter_ui():
            """Serve the embedded bug reporter UI."""
            ui_path = os.path.join(APP_ROOT, "ui", "index.html")
            if os.path.exists(ui_path):
                with open(ui_path, "r", encoding="utf-8") as f:
                    return f.read()
            return "<h1>Bug Sleuth UI Not Found</h1>"

        # 6. Start Server
        logger.info(f"Starting Server on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
