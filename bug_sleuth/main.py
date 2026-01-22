
import os
import sys
import logging
import click
import uvicorn
from dotenv import load_dotenv

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bug_sleuth.main")

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
@click.option("--root-agent-name", default=None, help="Name of the sub-agent to start as root (e.g., bug_analyze_agent).")
@click.option("--mode", type=click.Choice(["ag-ui", "adk-web"], case_sensitive=False), default="adk-web", help="Server mode: ag-ui (frontend middleware) or adk-web (legacy/api).")
def serve(port, host, skills_dir, config, env_file, data_dir, root_agent_name, mode):
    """
    Start the Bug Sleuth Agent Server.
    
    Unified entry point supporting:
    - AG-UI Mode: For use with CopilotKit/AG-UI frontend.
    - ADK-Web Mode: For use with standard ADK web tools.
    """
    # 1. Load Environment Variables
    if os.path.exists(env_file):
        logger.info(f"Loading environment from {env_file}")
        load_dotenv(env_file)
    
    # 2. Set Environment Variables
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

    if root_agent_name:
        os.environ["ADK_ROOT_AGENT_NAME"] = root_agent_name

    os.environ["ADK_APP_MODE"] = mode

    # 3. Load Skills
    # This must be done before App/Agent loading so skills are registered
    path = os.getenv("SKILL_PATH")
    if path and os.path.exists(path):
        from bug_sleuth.skill_library.skill_loader import SkillLoader
        logger.info(f"Loading skills from: {path}")
        SkillLoader(path).load_skills()
    else:
        logger.info("No skills loaded or SKILL_PATH not found.")

    # 4. Initialize Server based on Mode
    try:
        app = None
        
        # Configure Data/Artifact Paths for ADK (Common for both modes)
        data_dir_env = os.getenv("ADK_DATA_DIR", "adk_data")
        data_dir = os.path.abspath(data_dir_env) if not os.path.isabs(data_dir_env) else data_dir_env
        artifacts_dir = os.path.join(data_dir, "artifacts")
        
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(artifacts_dir, exist_ok=True)
        
        from pathlib import Path
        artifact_service_uri = Path(artifacts_dir).resolve().as_uri()
        session_db_path = os.path.join(data_dir, "sessions.db")
        session_service_uri = f"sqlite+aiosqlite:///{session_db_path}"

        if mode == "ag-ui":
            logger.info("Starting in AG-UI Middleware Mode (Frontend enabled)")
            
            # Imports for AG-UI
            from fastapi import FastAPI
            from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
            # Import App (Late import to ensure env vars are set)
            from bug_sleuth.bug_scene_app.app import app as adk_app
            
            # Use Service Registry (same pattern as get_fast_api_app)
            from google.adk.cli.service_registry import get_service_registry
            
            # agents_dir for service registry context
            agents_dir = os.path.dirname(os.path.abspath(__file__))
            service_registry = get_service_registry()
            
            # Build Session Service (using registry, with DatabaseSessionService fallback)
            session_service = service_registry.create_session_service(
                session_service_uri, agents_dir=agents_dir
            )
            if not session_service:
                # Fallback to DatabaseSessionService if registry doesn't support the URI
                from google.adk.sessions.database_session_service import DatabaseSessionService
                session_service = DatabaseSessionService(db_url=session_service_uri)
            logger.info(f"Session Service Configured: {session_service_uri}")
            
            # Build Artifact Service (using registry)
            artifact_service = service_registry.create_artifact_service(
                artifact_service_uri, agents_dir=agents_dir
            )
            if not artifact_service:
                logger.warning(f"Could not create artifact service for {artifact_service_uri}, using InMemory fallback.")
                from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
                artifact_service = InMemoryArtifactService()
            else:
                logger.info(f"Artifact Service Configured: {artifact_service_uri}")

            # Create AG-UI Adapter Agent
            # Wraps the ADK agent with AG-UI protocol support
            ui_agent = ADKAgent.from_app(
                 app=adk_app,
                 user_id="demo_user",
                 session_timeout_seconds=3600,
                 use_in_memory_services=False,
                 # Inject persistent services
                 session_service=session_service,
                 artifact_service=artifact_service,
            )
            
            # Create FastAPI app
            app = FastAPI(title="Bug Sleuth ADK Agent (AG-UI)")
            
            # Add AG-UI Endpoint
            add_adk_fastapi_endpoint(app, ui_agent, path="/")
            
        else:
            logger.info("Starting in ADK Web Server Mode (API server)")
            
            # Imports for ADK Web
            from google.adk.cli.fast_api import get_fast_api_app
            
            # Determine Agents Directory
            # Strictly use the package root (bug_sleuth directory)
            agents_dir = os.path.dirname(os.path.abspath(__file__))
            
            logger.info(f"ADK Agents Dir (Locked): {agents_dir}")

            # Use standard ADK Web Server wrapper
            app = get_fast_api_app(
                agents_dir=agents_dir,
                session_service_uri=session_service_uri,
                artifact_service_uri=artifact_service_uri,
                web=True,
                a2a=False
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
