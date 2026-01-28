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
        question = "Test Question"
        answer = "Test Answer"
        category = "TestCategory"
        contributor = "TestUser"
        tags = "tag1, tag2"

        # Mock KNOWLEDGE_BASE_PATH to use the temporary path
        with patch('context_pilot.context_pilot_app.exp_recored_agent.knowledge_tool.KNOWLEDGE_BASE_PATH', self.test_kb_path):
            result = record_experience(question, answer, category, contributor, tags)

        # Verify function return
        self.assertEqual(result, "Experience successfully recorded.")

        # Verify file content
        self.assertTrue(os.path.exists(self.test_kb_path))
        with open(self.test_kb_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])

            # Verify top-level fields
            self.assertIn("id", entry)
            self.assertTrue(entry["id"]) # Check id is not empty
            self.assertEqual(entry["title"], question)
            self.assertEqual(entry["content"], answer)
            
            # Verify metadata
            self.assertIn("metadata", entry)
            metadata = entry["metadata"]
            self.assertEqual(metadata["category"], category)
            self.assertEqual(metadata["contributor"], contributor)
            self.assertIn("timestamp", metadata)
            self.assertEqual(metadata["tags"], ["tag1", "tag2"])


if __name__ == '__main__':
    unittest.main()
