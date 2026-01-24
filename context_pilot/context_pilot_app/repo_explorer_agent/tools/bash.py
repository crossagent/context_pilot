import asyncio
import os
import subprocess
import logging
from typing import Optional
from context_pilot.shared_libraries.tool_response import ToolResponse

async def run_bash_command(command: str, cwd: Optional[str] = None) -> dict:
    """
    Run a bash command or shell command.
    
    Args:
        command: The command to run.
        cwd: Optional working directory.
        
    Returns:
        dict: Result with keys 'status', 'output', 'error', 'exit_code'.
    """
    if not command:
        return ToolResponse.error("Command is required.")

    # FIX: Default CWD to Primary Repository if not specified
    if not cwd:
        import json
        cwd = os.getcwd() # Fallback
        try:
             repos_json = os.environ.get("REPOSITORIES")
             if repos_json:
                 repos = json.loads(repos_json)
                 if repos and "path" in repos[0]:
                     cwd = repos[0]["path"]
        except:
             pass

    logging.info(f"Executing command: {command} (cwd={cwd})")

    try:
        # Determine shell based on OS
        # Windows ADK Environment often uses ProactorEventLoop which might not support asyncio.create_subprocess_shell elegantly.
        # Fallback to synchronous subprocess.run in a thread executor.
        
        def run_sync_cmd():
            if os.name == 'nt':
                # Force UTF-8 encoding for output decoding if possible, though cmd.exe is tricky.
                return subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    cwd=cwd,
                    text=False # Capture bytes to decode safely with 'replace'
                )
            else:
                 return subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    executable="/bin/bash",
                    cwd=cwd,
                    text=False
                )

        # Run blocking IO in a separate thread
        completed_process = await asyncio.to_thread(run_sync_cmd)
        
        # Helper to decode with fallback
        def decode_output(data: bytes) -> str:
            if not data:
                return ""
            try:
                # 1. Try system locale (e.g. cp936 on CN Windows)
                import locale
                return data.decode(locale.getpreferredencoding(), errors='strict')
            except UnicodeDecodeError:
                try:
                    # 2. Try UTF-8
                    return data.decode('utf-8', errors='strict')
                except UnicodeDecodeError:
                    # 3. Fallback to system locale with replace
                    return data.decode(locale.getpreferredencoding(), errors='replace')

        output_str = decode_output(completed_process.stdout).strip()
        error_str = decode_output(completed_process.stderr).strip()
        
        exit_code = completed_process.returncode
        
        if exit_code == 0:
            logging.info(f"Command success: {command}")
            summary_msg = f"Executed '{command}' successfully (rc=0)."
            return ToolResponse.success(
                summary=summary_msg,
                output=output_str,
                error=error_str,
                exit_code=0
            )
        else:
             # Create a concise summary including the first line of error/output for context
             # This avoids the need for valid_llm_agent to append large blocks
             short_err = error_str.split('\n')[0] if error_str else output_str.split('\n')[0]
             if len(short_err) > 100: short_err = short_err[:100] + "..."
             
             summary_msg = f"Command '{command}' failed (rc={exit_code}). Reason: {short_err}"
             return ToolResponse.error(
                error=error_str or summary_msg,
                summary=summary_msg,
                output=output_str,
                exit_code=exit_code
             )

    except Exception as e:
        error_msg = f"Execution failed: {str(e)}"
        logging.error(error_msg, exc_info=True) # Log full traceback
        return ToolResponse.error(
            error=error_msg,
            summary="Command execution failed internally."
        )
