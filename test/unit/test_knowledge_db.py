
import pytest
import os
import sqlite3
import uuid
from datetime import datetime
from context_pilot.utils.db_manager import default_db_manager, DBManager
from context_pilot.context_pilot_app.exp_recored_agent.knowledge_tool import record_experience
from context_pilot.scripts.build_index import load_documents_from_db, reconstruct_markdown

# Use a temporary DB for testing
TEST_DB_PATH = "test_knowledge_base.sqlite"

@pytest.fixture
def test_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # Initialize DB Manager with test path
    db = DBManager(db_path=TEST_DB_PATH)
    db.init_db()
    
    # Patch the global default_db_manager in the modules we are testing
    # Note: This is a bit hacky for integration tests, ideally we'd use dependency injection
    # But since we are modifying global state in the modules, we need to ensure they use OUR db
    
    # We will just swap the instance variables of the global object for this test
    original_path = default_db_manager.db_path
    default_db_manager.db_path = TEST_DB_PATH
    default_db_manager._ensure_dir()
    
    yield db
    
    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except:
            pass
    default_db_manager.db_path = original_path

def test_db_initialization(test_db):
    """Test table creation."""
    with test_db.get_connection() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_entries';")
        assert cursor.fetchone() is not None

def test_record_experience(test_db):
    """Test writing to the DB via the tool function."""
    
    result = record_experience(
        intent="Test Intent",
        problem_context="Context",
        root_cause="Cause",
        solution_steps="Steps",
        evidence="Evidence",
        tags="tag1, tag2",
        contributor="Tester"
    )
    
    assert "✅ Experience recorded successfully" in result
    
    with test_db.get_connection() as conn:
        row = conn.execute("SELECT * FROM knowledge_entries WHERE intent='Test Intent'").fetchone()
        assert row is not None
        assert row['problem_context'] == "Context"
        assert row['tags'] == "tag1, tag2"
        assert row['contributor'] == "Tester"

def test_load_documents(test_db):
    """Test reading from DB via build_index loader."""
    
    # Insert a record first
    record_experience(
        intent="Read Test",
        problem_context="Ctx",
        root_cause="Root",
        solution_steps="Sol",
        evidence="Evid"
    )
    
    docs = load_documents_from_db()
    assert len(docs) == 1
    doc = docs[0]
    
    assert doc.metadata['intent'] == "Read Test"
    assert "Read Test" in doc.text
    assert "# 1. Problem Context\nCtx" in doc.text
