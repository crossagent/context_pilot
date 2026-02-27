
import os
import sys
import logging
import click
import uvicorn
from dotenv import load_dotenv

# Import for RunConfig configuration
from google.adk.agents.run_config import StreamingMode, RunConfig as ADKRunConfig

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("context_pilot.main")

@click.group()
def main():
    """Context Pilot CLI Tool"""
    pass

@main.command()
@click.option("--port", default=8000, help="Port to run the server on.")
@click.option("--host", default="127.0.0.1", help="Host to run the server on.")
@click.option("--skills-dir", envvar="SKILL_PATH", help="Path to the skills directory.")
@click.option("--config", envvar="CONFIG_FILE", help="Path to the configuration file.")
@click.option("--env-file", default=".env", help="Path to .env file.")
@click.option("--data-dir", default="adk_data", help="Directory for local data storage.")
@click.option("--knowledge-base-dir", help="Path to the knowledge base directory.")
def serve(port, host, skills_dir, config, env_file, data_dir, knowledge_base_dir):
    """
    Start the Context Pilot Agent Server.
    """
    # 1. Load Environment Variables
    if os.path.exists(env_file):
        logger.info(f"Loading environment from {env_file}")
        load_dotenv(env_file)
    
    # 2. Set Environment Variables
    
    # Set RAG_DATA_DIR if knowledge_base_dir is provided
    if knowledge_base_dir:
        abs_kb_dir = os.path.abspath(knowledge_base_dir)
        os.environ["RAG_DATA_DIR"] = abs_kb_dir
        logger.info(f"Set RAG_DATA_DIR to {abs_kb_dir}")
    # Auto-discovery for skills
    if not skills_dir and os.path.exists("skills") and os.path.isdir("skills"):
        skills_dir = "skills"
        logger.info("Auto-discovered 'skills' directory in current location.")
    
    if skills_dir:
        os.path.abspath_skills = os.path.abspath(skills_dir)
        os.environ["SKILL_PATH"] = os.path.abspath_skills
        logger.info(f"Set SKILL_PATH to {os.environ['SKILL_PATH']}")

    if config:
        os.environ["CONFIG_FILE"] = os.path.abspath(config)
        logger.info(f"Set CONFIG_FILE to {os.environ['CONFIG_FILE']}")
        
    if data_dir:
        os.environ["ADK_DATA_DIR"] = data_dir

    # 3. Load Skills
    # This must be done before App/Agent loading so skills are registered
    path = os.getenv("SKILL_PATH")
    if path and os.path.exists(path):
        from context_pilot.skill_library.skill_loader import SkillLoader
        logger.info(f"Loading skills from: {path}")
        SkillLoader(path).load_skills()
    else:
        logger.info("No skills loaded or SKILL_PATH not found.")

    # 4. Initialize Server
    try:
        app = None
        
        # Configure Data/Artifact Paths for ADK
        data_dir_env = os.getenv("ADK_DATA_DIR", "adk_data")
        data_dir = os.path.abspath(data_dir_env) if not os.path.isabs(data_dir_env) else data_dir_env
        artifacts_dir = os.path.join(data_dir, "artifacts")
        
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(artifacts_dir, exist_ok=True)
        
        from pathlib import Path
        artifact_service_uri = Path(artifacts_dir).resolve().as_uri()
        session_db_path = os.path.join(data_dir, "sessions.db")
        session_service_uri = f"sqlite+aiosqlite:///{session_db_path}"

        logger.info("Starting in ADK Web Server Mode")
        
        # Imports for ADK Web
        from google.adk.cli.fast_api import get_fast_api_app
        
        # Determine Agents Directory
        # Strictly use the package root (context_pilot directory)
        agents_dir = os.path.dirname(os.path.abspath(__file__))
        
        logger.info(f"ADK Agents Dir (Locked): {agents_dir}")

        # Use standard ADK Web Server wrapper
        app = get_fast_api_app(
            agents_dir=agents_dir,
            session_service_uri=session_service_uri,
            artifact_service_uri=artifact_service_uri,
            web=True,
            a2a=True
        )
        
        # 5. Start Server
        logger.info(f"Starting Server on {host}:{port}")
        # Note: When using click, sys.exit might be handled differently, but run() blocks.
        uvicorn.run(app, host=host, port=port)
        
    except Exception as e:
        logger.exception(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
