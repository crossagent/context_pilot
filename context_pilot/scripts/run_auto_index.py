import os
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutoIndex")

INTERVAL = int(os.getenv("RAG_AUTO_INDEX_INTERVAL", "300"))

def main():
    logger.info(f"Starting Auto RAG Indexer... (Interval: {INTERVAL} seconds)")
    
    # Path to build script
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(project_root, "scripts", "build_index.py")
    
    # Status file path (in the same storage dir as the index)
    from context_pilot.scripts.rag_config import RagConfig
    status_file = os.path.join(RagConfig.STORAGE_DIR, "index_status.json")
    os.makedirs(RagConfig.STORAGE_DIR, exist_ok=True)

    def update_status(status, message="", result=""):
        try:
            with open(status_file, 'w') as f:
                json.dump({
                    "status": status,
                    "message": message,
                    "result": result,
                    "last_check": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "next_run": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + INTERVAL)) if status == "Idle" else "Now"
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update status file: {e}")

    import json
    
    while True:
        try:
            update_status("Running", "Triggering incremental RAG index build...")
            logger.info("Triggering background incremental RAG index build...")
            result = subprocess.run(
                ["python", script_path, "--mode=incremental"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Build index failed with code {result.returncode}:\n{result.stderr}")
                update_status("Idle", "Last build failed", "Error")
            else:
                logger.info("Background RAG index check completed.")
                update_status("Idle", "Success", "Success")
                
        except Exception as e:
            logger.error(f"Error during auto index trigger: {e}")
            update_status("Idle", f"Error: {str(e)}", "Error")
            
        logger.info(f"Sleeping for {INTERVAL} seconds...")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
