
import os
import sys
import logging
import click
import uvicorn
from dotenv import load_dotenv

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
@click.option("--agent-dir", default=None, help="Agent startup directory (containing agent definition).")
@click.option("--mode", type=click.Choice(["ag-ui", "adk"], case_sensitive=False), default="ag-ui", help="Server mode: ag-ui (frontend middleware) or adk (legacy/api).")
@click.option("--ui-path", envvar="BUG_SLEUTH_UI_PATH", help="Path to the reporter UI HTML file.")
def serve(port, host, skills_dir, config, env_file, data_dir, agent_dir, mode, ui_path):
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
        
    # 4. Configure Environment for Server
    if data_dir:
        os.environ["ADK_DATA_DIR"] = data_dir
        
    if agent_dir:
        # Pass the user's desired agent directory to app.py for dynamic loading
        os.environ["ADK_TARGET_AGENT_DIR"] = os.path.abspath(agent_dir)
        
    if ui_path:
        os.environ["BUG_SLEUTH_UI_PATH"] = os.path.abspath(ui_path)
        logger.info(f"Set BUG_SLEUTH_UI_PATH to {os.environ['BUG_SLEUTH_UI_PATH']}")
        
    # 5. Import Global App based on Mode
    try:
        if mode == "ag-ui":
            logger.info("Starting in AG-UI Middleware Mode (Frontend enabled)")
            from bug_sleuth.main import app
        else:
            logger.info("Starting in ADK Web Server Mode (API server)")
            from bug_sleuth.server import app
        
        # 6. Start Server
        logger.info(f"Starting Server on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
        
    except Exception as e:
        logger.exception(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
