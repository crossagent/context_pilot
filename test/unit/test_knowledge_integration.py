
import unittest
import os
import shutil
import tempfile
import sqlite3
import logging
from unittest.mock import patch
from datetime import datetime

# Adjust paths to import modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from context_pilot.utils.db_manager import DBManager, default_db_manager
from context_pilot.context_pilot_app.remote_a2a.planning_expert_agent.knowledge_tool import record_experience
from context_pilot.scripts.build_index import build_index
from context_pilot.scripts.rag_config import RagConfig
from llama_index.core import StorageContext, load_index_from_storage

# Configure logging to see build output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestKnowledgeIntegration(unittest.TestCase):
    def setUp(self):
        # 1. Setup Temporary Directories
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_knowledge.sqlite")
        self.storage_dir = os.path.join(self.test_dir, "rag_storage")
        
        # 2. Patch Configurations
        # Patch DB Manager global instance to use our test DB
        self.original_db_path = default_db_manager.db_path
        default_db_manager.db_path = self.db_path
        default_db_manager._ensure_dir()
        default_db_manager.init_db()

        # Patch RagConfig to use our test storage dir and DB path
        self.rag_config_patcher = patch.multiple(
            RagConfig,
            STORAGE_DIR=self.storage_dir,
            LOCAL_DATA_DIR=self.test_dir,
            DB_FILENAME="test_knowledge.sqlite"
        )
        self.rag_config_patcher.start()
        
        # Ensure RagConfig.DB_PATH property returns the correct test path
        # (Since it's a property, patch.multiple on class attributes might not affect the instance property logic if it uses self.LOCAL_DATA_DIR directly, 
        # but since LOCAL_DATA_DIR is patched on the class, it should work for static access or if we patch the property)
        # Actually simplest is just to rely on the class attributes being patched if code uses RagConfig.LOCAL_DATA_DIR
        
    def tearDown(self):
        # Stop patches
        self.rag_config_patcher.stop()
        
        # Restore DB Manager
        default_db_manager.db_path = self.original_db_path
        
        # Cleanup files
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except Exception as e:
                print(f"Error cleaning up: {e}")

    def get_index_doc_count(self):
        """Helper to load index and count docs."""
        if not os.path.exists(self.storage_dir):
            return 0
        storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
        index = load_index_from_storage(storage_context)
        return len(index.docstore.docs)

    def get_doc_text_by_intent(self, intent_snippet):
        """Helper to find doc content."""
        storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
        index = load_index_from_storage(storage_context)
        for doc in index.docstore.docs.values():
            if intent_snippet in doc.text:
                return doc.text
        return None

    def test_full_integration_lifecycle(self):
        """
        Tests the complete lifecycle:
        1. create initial record -> build index
        2. add new record -> incremental update
        3. modify existing record -> incremental update (refresh)
        """
        print("\n=== Step 1: Create Initial Record ===")
        record_experience(
            intent="Initial Bug",
            problem_context="System crashing on boot",
            root_cause="Null pointer",
            solution_steps="Add null check",
            tags="bug, fix"
        )
        
        # Build Index (Full Init)
        build_index(mode="full")
        
        # Verify
        count = self.get_index_doc_count()
        self.assertEqual(count, 1, "Index should have 1 document")
        self.assertIsNotNone(self.get_doc_text_by_intent("Initial Bug"))

        print("\n=== Step 2: Add Incremental Record ===")
        record_experience(
            intent="Feature Request",
            problem_context="Need dark mode",
            root_cause="User demand",
            solution_steps="Install theme plugin",
            tags="feature, ui"
        )
        
        # Build Index (Incremental)
        build_index(mode="incremental")
        
        # Verify
        count = self.get_index_doc_count()
        self.assertEqual(count, 2, "Index should have 2 documents")
        self.assertIsNotNone(self.get_doc_text_by_intent("Initial Bug"))
        self.assertIsNotNone(self.get_doc_text_by_intent("Feature Request"))

        print("\n=== Step 3: Modify Content (Update) ===")
        # Simulate an update knowing the Intent (finding ID first)
        with default_db_manager.get_connection() as conn:
            row = conn.execute("SELECT id FROM knowledge_entries WHERE intent = ?", ("Initial Bug",)).fetchone()
            entry_id = row['id']
            
            # Updating the solution steps
            new_solution = "Refactored entire bootloader (Updated)"
            conn.execute("UPDATE knowledge_entries SET solution_steps = ? WHERE id = ?", (new_solution, entry_id))
        
        # Build Index (Incremental - should trigger refresh)
        build_index(mode="incremental")
        
        # Verify
        count = self.get_index_doc_count()
        self.assertEqual(count, 2, "Index count should remain 2")
        
        updated_text = self.get_doc_text_by_intent("Initial Bug")
        self.assertIn("Refactored entire bootloader (Updated)", updated_text, "Index should contain updated text")
        
        print("\n=== ✅ All Integration Scenarios Passed ===")

if __name__ == "__main__":
    unittest.main()
