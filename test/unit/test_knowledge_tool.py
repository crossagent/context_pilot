import unittest
import json
import os
import shutil
import tempfile
from unittest.mock import patch
from context_pilot.context_pilot_app.exp_recored_agent.knowledge_tool import record_experience, KNOWLEDGE_BASE_PATH

class TestKnowledgeTool(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.test_kb_path = os.path.join(self.test_dir, "knowledge_base.jsonl")

    def tearDown(self):
        # Cleanup temporary directory
        shutil.rmtree(self.test_dir)

    def test_record_experience(self):
        # Setup test data
        intent = "Fix Redis Timeout"
        problem_context = "Redis connection timed out in production."
        root_cause = "Default timeout was too low (2s)."
        solution_steps = "Increased timeout to 5s."
        evidence = "Commit abc1234"
        tags = "redis, timeout"
        contributor = "TestUser"

        # Mock KNOWLEDGE_BASE_PATH to use the temporary path
        with patch('context_pilot.context_pilot_app.exp_recored_agent.knowledge_tool.KNOWLEDGE_BASE_PATH', self.test_kb_path):
            result = record_experience(
                intent=intent,
                problem_context=problem_context,
                root_cause=root_cause,
                solution_steps=solution_steps,
                evidence=evidence,
                tags=tags,
                contributor=contributor
            )

        # Verify function return
        self.assertEqual(result, f"✅ Experience recorded successfully: '{intent}'")

        # Verify file content
        self.assertTrue(os.path.exists(self.test_kb_path))
        with open(self.test_kb_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])

            # Verify top-level fields
            self.assertIn("id", entry)
            self.assertTrue(entry["id"]) # Check id is not empty
            self.assertEqual(entry["title"], intent)
            
            # Verify Markdown Content Structure
            content = entry["content"]
            self.assertIn("# Intent", content)
            self.assertIn(intent, content)
            self.assertIn("# 1. Problem Context", content)
            self.assertIn(problem_context, content)
            self.assertIn("# 2. Root Cause Analysis", content)
            self.assertIn(root_cause, content)
            self.assertIn("# 3. Solution / SOP", content)
            self.assertIn(solution_steps, content)
            self.assertIn("# 4. Evidence", content)
            self.assertIn(evidence, content)
            
            # Verify metadata
            self.assertIn("metadata", entry)
            metadata = entry["metadata"]
            self.assertEqual(metadata["contributor"], contributor)
            self.assertIn("timestamp", metadata)
            self.assertEqual(metadata["tags"], ["redis", "timeout"])
            self.assertEqual(metadata["type"], "cookbook_record")


if __name__ == '__main__':
    unittest.main()
