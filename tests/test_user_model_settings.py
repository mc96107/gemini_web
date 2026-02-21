import os
import json
import pytest
from app.services.llm_service import GeminiAgent

def test_user_settings_default_model(tmp_path):
    # Use a temporary file for sessions
    session_file = tmp_path / "user_sessions.json"
    agent = GeminiAgent(working_dir=str(tmp_path))
    agent.session_file = str(session_file)
    
    user_id = "test_user"
    
    # Test default settings (should be gemini-3-pro-preview or similar)
    settings = agent.get_user_settings(user_id)
    assert settings.get("default_model") == "gemini-3-pro-preview"
    
    # Update settings
    agent.update_user_settings(user_id, {"default_model": "gemini-3-flash-preview"})
    
    # Verify update
    settings = agent.get_user_settings(user_id)
    assert settings["default_model"] == "gemini-3-flash-preview"
    assert settings["interactive_mode"] is True # Should remain default
    
    # Verify persistence
    with open(session_file, "r") as f:
        data = json.load(f)
        assert data[user_id]["settings"]["default_model"] == "gemini-3-flash-preview"

@pytest.mark.asyncio
async def test_new_chat_uses_default_model(tmp_path):
    # Use a temporary file for sessions
    session_file = tmp_path / "user_sessions.json"
    agent = GeminiAgent(working_dir=str(tmp_path))
    agent.session_file = str(session_file)
    
    user_id = "test_user"
    
    # 1. Set a custom default model
    custom_model = "gemini-3-flash-preview"
    agent.update_user_settings(user_id, {"default_model": custom_model})
    
    # Mock _create_subprocess to see what model is passed in args
    from unittest.mock import AsyncMock
    agent._create_subprocess = AsyncMock()
    
    mock_proc = AsyncMock()
    mock_proc.stdin = AsyncMock()
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.stdout.readline = AsyncMock(return_value=b"")
    mock_proc.stderr.readline = AsyncMock(return_value=b"")
    agent._create_subprocess.return_value = mock_proc

    # Trigger a new chat (resume_session=None)
    # The current generate_response_stream uses `model or self.model_name`
    # We need to see if it should use `model or user_settings.get("default_model") or self.model_name`
    async for _ in agent.generate_response_stream(user_id, "Hello", resume_session=None):
        pass
    
    # Check the args passed to _create_subprocess
    # args should contain ["--model", custom_model]
    call_args = agent._create_subprocess.call_args[0][0]
    
    # Find --model in args
    try:
        model_idx = call_args.index("--model")
        assert call_args[model_idx + 1] == custom_model
    except ValueError:
        pytest.fail("--model not found in args")
