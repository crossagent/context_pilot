import pytest
import os
from google.adk.tools import ToolContext
from context_pilot.context_pilot_app.exp_recored_agent.knowledge_tool import extract_experience, save_experience
from context_pilot.shared_libraries.state_keys import StateKeys
from context_pilot.utils.db_manager import default_db_manager, DBManager

TEST_DB_PATH = "test_knowledge_flow.sqlite"

@pytest.fixture
def mock_tool_context():
    from unittest.mock import MagicMock
    mock_invocation_context = MagicMock()
    mock_invocation_context.session.state = {}
    context = ToolContext(invocation_context=mock_invocation_context)
    # The context.state is initialized from invocation_context.session.state
    # But for our test we might want to interact with context.state directly
    return context

@pytest.fixture
def test_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # Initialize DB Manager with test path
    db = DBManager(db_path=TEST_DB_PATH)
    db.init_db()
    
    # Patch global
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

def test_experience_flow(mock_tool_context, test_db):
    """Test the full extract -> save flow via tools."""
    
    # 1. Test Extraction
    intent = "Test Intent"
    extract_result = extract_experience(
        tool_context=mock_tool_context,
        intent=intent,
        problem_context="Context",
        root_cause="Root Cause",
        solution_steps="Steps",
        tags="test, flow"
    )
    
    assert "✅ Experience extracted" in extract_result
    
    # Verify individual state keys
    assert mock_tool_context.state[StateKeys.EXP_INTENT] == intent
    assert mock_tool_context.state[StateKeys.EXP_ROOT_CAUSE] == "Root Cause"
    assert mock_tool_context.state[StateKeys.EXP_TAGS] == "test, flow"
    
    # 2. Test Saving
    save_result = save_experience(tool_context=mock_tool_context)
    
    assert "✅ Experience permanently saved" in save_result
    
    # State should be cleared
    assert mock_tool_context.state[StateKeys.EXP_INTENT] is None
    assert mock_tool_context.state[StateKeys.EXP_ROOT_CAUSE] is None
    
    # Verify DB
    with test_db.get_connection() as conn:
        row = conn.execute("SELECT * FROM knowledge_entries WHERE intent=?", (intent,)).fetchone()
        assert row is not None
        assert row["root_cause"] == "Root Cause"

def test_save_without_extract(mock_tool_context):
    """Test saving when no experience is staged."""
    result = save_experience(tool_context=mock_tool_context)
    assert "❌ No pending experience found" in result
