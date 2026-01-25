"""
Bug Sleuth Testing Infrastructure.

This module exports utilities for integration testing Context Pilot agents and skills.
Extensions can use these tools to verify their injections works correctly.

Usage (in your test file):
    from context_pilot.testing import TestClient, MockLlm
    from context_pilot.app_factory import create_app, AppConfig

    @pytest.fixture
    def app():
        return create_app(AppConfig(skill_path="path/to/my/skills", agent_name="context_pilot_agent"))
        
    async def test_my_skill(app):
        # 1. Setup Mock Behavior
        MockLlm.set_behaviors({
            "trigger phrase": {"tool": "my_tool", "args": {"p": 1}}
        })
        
        # 2. Run Chat
        client = TestClient(agent=app.agent)
        await client.create_new_session("user", "sess")
        resp = await client.chat("trigger phrase")
        
        # 3. Verify
        assert "[MockLlm]" in resp[-1]
"""

from .api_client import AdkApiTestClient
from .mock_llm import MockLlm

__all__ = ["AdkApiTestClient", "MockLlm"]
