
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from bug_sleuth.bug_analyze_agent.tools.git import get_git_blame_tool
from pathlib import Path
import os

class TestGitBlameTool(unittest.IsolatedAsyncioTestCase):
    
    async def test_get_git_blame_success(self):
        # Patch _load_repos to bypass validation requirements
        with patch("bug_sleuth.bug_analyze_agent.tools.decorators._load_repos") as mock_repos:
            mock_repos.return_value = [{"name": "test", "path": "d:/"}]
            
            # Mocking run_bash_command to return a success response
            with patch("bug_sleuth.bug_analyze_agent.tools.git.run_bash_command", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = {"status": "success", "output": "author time line content"}
                
                test_file = "d:/path/to/file.py"
                
                # Mock path existence checks
                with patch("os.path.isfile", return_value=True):
                     with patch("os.path.exists", return_value=True):
                         # Patch Path.resolve to return the path itself to avoid filesystem interaction
                         with patch("pathlib.Path.resolve", side_effect=lambda: Path(test_file)):
                             result = await get_git_blame_tool(test_file, 1, 10)
                     
                self.assertEqual(result["status"], "success")
                mock_run.assert_called_once()
                args, kwargs = mock_run.call_args
                self.assertIn("git blame -L 1,10", args[0])
                self.assertIn("d:\\path\\to\\file.py", args[0].replace("/", "\\")) 

    async def test_get_git_blame_command_failure(self):
        with patch("bug_sleuth.bug_analyze_agent.tools.decorators._load_repos") as mock_repos:
            mock_repos.return_value = [{"name": "test", "path": "d:/"}]
            
            with patch("bug_sleuth.bug_analyze_agent.tools.git.run_bash_command", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = {"status": "error", "error": "fatal: no such path"}
                
                test_file = "d:/file.py"
                with patch("os.path.isfile", return_value=True):
                    with patch("os.path.exists", return_value=True):
                        with patch("pathlib.Path.resolve", side_effect=lambda: Path(test_file)):
                            result = await get_git_blame_tool(test_file, 1, 5)
                    
                self.assertEqual(result["status"], "error")

