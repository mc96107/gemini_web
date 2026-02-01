import os
import json
import pytest
from app.services.llm_service import GeminiAgent

def test_user_settings_interactive_mode(tmp_path):
    # Use a temporary file for sessions
    session_file = tmp_path / "user_sessions.json"
    agent = GeminiAgent(working_dir=str(tmp_path))
    agent.session_file = str(session_file)
    
    user_id = "test_user"
    
    # Test default settings
    settings = agent.get_user_settings(user_id)
    assert settings["interactive_mode"] is True
    assert settings["show_mic"] is True
    
    # Update settings
    agent.update_user_settings(user_id, {"interactive_mode": False})
    
    # Verify update
    settings = agent.get_user_settings(user_id)
    assert settings["interactive_mode"] is False
    assert settings["show_mic"] is True # Should remain same
    
    # Verify persistence
    with open(session_file, "r") as f:
        data = json.load(f)
        assert data[user_id]["settings"]["interactive_mode"] is False
