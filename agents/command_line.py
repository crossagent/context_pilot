import os
import sys
import uvicorn
from agents.shared_libraries import constants

def main():
    """
    Entry point for the 'bug-sleuth-server' command.
    """
    # 1. Environment Validation
    project_root = os.getenv("PROJECT_ROOT")
    if not project_root:
        print("❌ Error: PROJECT_ROOT environment variable is not set.")
        print("Please set it to the path of your game project root.")
        print("Example: export PROJECT_ROOT=/path/to/game")
        sys.exit(1)
        
    product = os.getenv("PRODUCT")
    if not product:
        print("⚠️  Warning: PRODUCT environment variable is not set.")
        print("Using default: 'Unknown Product'")
        
    print(f"🚀 Starting BugSleuth Server...")
    print(f"   Project Root: {project_root}")
    print(f"   Product:      {product or 'Unknown'}")
        
    # 3. Launch Uvicorn
    # We use string reference to allow reloading if needed, though usually False for prod
    try:
        uvicorn.run(
            "agents.bug_analyze_agent.agent:app",
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
