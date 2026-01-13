"""Main entry point for ADK Middleware Bug Sleuth Agent."""

import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
from bug_sleuth.app_factory import create_app, AppConfig

load_dotenv()

# 1. Initialize the Bug Sleuth App
# This loads the configured agent (e.g., bug_analyze_agent) and skills
app_config = AppConfig.from_env()
bug_sleuth_app = create_app(app_config)

# 2. Create ADK middleware agent instance
# Wraps the ADK agent with AG-UI protocol support
adk_agent = ADKAgent(
    adk_agent=bug_sleuth_app.agent,
    user_id="demo_user",  # Default user for single-user dev/demo mode
    session_timeout_seconds=3600,
    use_in_memory_services=True, # Use in-memory for simpler deployment
)

# 3. Create FastAPI app
app = FastAPI(title="ADK Middleware Bug Sleuth Agent")

# 4. Add the ADK endpoint
add_adk_fastapi_endpoint(app, adk_agent, path="/")

if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  Warning: GOOGLE_API_KEY environment variable not set!")
        print("   Set it with: export GOOGLE_API_KEY='your-key-here'")
        print("   Get a key from: https://makersuite.google.com/app/apikey")
        print()

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
