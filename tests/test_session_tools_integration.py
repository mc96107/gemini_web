import pytest
import os
import shutil
import asyncio
from app.services.llm_service import GeminiAgent
from unittest.mock import patch, MagicMock

@pytest.mark.anyio
async def test_tool_enforcement_integration(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    session_uuid = "test-session"
    
    agent.user_data = {
        user_id: {
            "active_session": session_uuid,
            "sessions": [session_uuid],
            "session_tools": {
                session_uuid: ["read_file"] # ONLY read_file
            }
        }
    }
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"output", b"error")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc
        
        await agent.generate_response(user_id, "test prompt")
        
        # Check arguments
        # args is a tuple, we want the positional args passed to create_subprocess_exec
        call_args = mock_exec.call_args[0]
        assert "--allowed-tools" in call_args
        idx = call_args.index("--allowed-tools")
        assert call_args[idx+1] == "read_file"
        assert "--approval-mode" in call_args
        idx_appr = call_args.index("--approval-mode")
        assert call_args[idx_appr+1] == "default"

@pytest.mark.anyio
async def test_no_tools_whitelists_none(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    session_uuid = "test-session"
    
    agent.user_data = {
        user_id: {
            "active_session": session_uuid,
            "sessions": [session_uuid],
            "session_tools": {
                session_uuid: [] # EMPTY
            }
        }
    }
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"output", b"error")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc
        
        await agent.generate_response(user_id, "test prompt")
        
        call_args = mock_exec.call_args[0]
        assert "--allowed-tools" in call_args
        idx = call_args.index("--allowed-tools")
        assert call_args[idx+1] == "none"

@pytest.mark.anyio
async def test_new_tools_integration(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    user_id = "test_user"
    session_uuid = "test-session"
    
    new_tools = ["cli_help", "ask_user", "confirm_output", "activate_skill", "codebase_investigator"]
    
    agent.user_data = {
        user_id: {
            "active_session": session_uuid,
            "sessions": [session_uuid],
            "session_tools": {
                session_uuid: new_tools
            }
        }
    }
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"output", b"error")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc
        
        await agent.generate_response(user_id, "test prompt")
        
        call_args = mock_exec.call_args[0]
        assert "--allowed-tools" in call_args
        idx = call_args.index("--allowed-tools")
        # The tools are joined by comma
        allowed_tools = call_args[idx+1].split(",")
        for tool in new_tools:
            assert tool in allowed_tools
