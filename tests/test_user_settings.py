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

@pytest.mark.asyncio
async def test_system_prompt_injection(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    
    # 1. Enabled (Default)
    agent.update_user_settings(user_id, {"interactive_mode": True})
    
    # Mock generate_response_stream to see what prompt it receives
    # We need to reach the point where prompt is modified but BEFORE subprocess
    # Since we can't easily mock just the modified prompt, let's use a simpler approach:
    # We'll just check if we can verify the injection logic by inspecting the code if needed,
    # OR we can mock _create_subprocess and check the prompt passed to it.
    
    from unittest.mock import AsyncMock
    agent._create_subprocess = AsyncMock()
    
    # Just to get past the await write_to_stdin
    # We need to mock proc.stdin.write or use a dummy proc
    mock_proc = AsyncMock()
    mock_proc.stdin = AsyncMock()
    mock_proc.stdout = AsyncMock()
    mock_proc.stderr = AsyncMock()
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.stdout.readline = AsyncMock(return_value=b"")
    mock_proc.stderr.readline = AsyncMock(return_value=b"")
    agent._create_subprocess.return_value = mock_proc

    async for _ in agent.generate_response_stream(user_id, "Hello"):
        pass
    
    # Check the prompt written to stdin
    # prompt is prompt.encode('utf-8') in code
    call_args = mock_proc.stdin.write.call_args_list
    # The first write should be our injected prompt
    written_data = b"".join([arg[0][0] for arg in call_args]).decode()
    assert "[SYSTEM INSTRUCTION: INTERACTIVE QUESTIONING ENABLED]" in written_data
    assert "Hello" in written_data

    # 2. Disabled
    agent.update_user_settings(user_id, {"interactive_mode": False})
    mock_proc.stdin.write.reset_mock()
    
    async for _ in agent.generate_response_stream(user_id, "Hello"):
        pass
        
    written_data = b"".join([arg[0][0] for arg in mock_proc.stdin.write.call_args_list]).decode()
    assert "Provide standard text responses only" in written_data
    assert "Hello" in written_data
