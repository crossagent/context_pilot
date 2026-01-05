
import os
import sys
import logging
import click
import uvicorn
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
        
    # 4. Create App via Factory
    # This separates the 'CLI Runner' from the 'App Logic'.
    try:
        from bug_sleuth.application import create_app
        
        # Pass configuration to factory
        app = create_app(
            host=host, 
            port=port, 
            data_dir=data_dir
        )
        
        # 5. Start Server
        logger.info(f"Starting Server on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
