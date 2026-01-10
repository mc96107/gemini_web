import pytest
import json
import os
from app.services.llm_service import GeminiAgent

def test_session_tools_persistence(tmp_path):
    # Setup
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    session_uuid = "test-session-uuid"
    
    # Mock existing user data
    agent.user_data = {
        user_id: {
            "active_session": session_uuid,
            "sessions": [session_uuid]
        }
    }
    agent._save_user_data()
    
    # Action: Set tools for the session
    tools = ["read_file", "list_directory"]
    # These methods don't exist yet, so this test will fail
    agent.set_session_tools(user_id, session_uuid, tools)
    
    # Verify in memory
    assert agent.get_session_tools(user_id, session_uuid) == tools
    
    # Verify persistence
    agent2 = GeminiAgent(working_dir=str(tmp_path))
    assert agent2.get_session_tools(user_id, session_uuid) == tools

def test_default_tools_empty(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    session_uuid = "test-session-uuid"
    
    agent.user_data = {
        user_id: {
            "active_session": session_uuid,
            "sessions": [session_uuid]
        }
    }
    
    # Default should be empty list
    # This method doesn't exist yet, so this test will fail
    assert agent.get_session_tools(user_id, session_uuid) == []
