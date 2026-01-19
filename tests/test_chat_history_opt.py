import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.llm_service import GeminiAgent
import json
import os

@pytest.fixture
def agent(tmp_path):
    return GeminiAgent(working_dir=str(tmp_path))

@pytest.mark.asyncio
async def test_get_sessions_caching(agent):
    valid_uuid = "12345678-1234-1234-1234-123456789012"
    # Setup initial state with no metadata
    agent.user_data["user1"] = {
        "sessions": [valid_uuid],
        "session_metadata": {}
    }
    
    # Mock CLI output
    cli_output = f"1. My Chat (2 days ago) [{valid_uuid}]\n"
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock process
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (cli_output.encode(), b"")
        mock_exec.return_value = process_mock
        
        # First call: Should hit CLI because metadata is missing
        sessions = await agent.get_user_sessions("user1")
        
        assert len(sessions) == 1
        assert sessions[0]["uuid"] == valid_uuid
        assert sessions[0]["title"] == "My Chat"
        assert mock_exec.called
        
        # Check cache was updated
        assert "session_metadata" in agent.user_data["user1"]
        assert valid_uuid in agent.user_data["user1"]["session_metadata"]
        assert agent.user_data["user1"]["session_metadata"][valid_uuid]["original_title"] == "My Chat"
        
        # Reset mock to verify 2nd call doesn't hit it
        mock_exec.reset_mock()
        
        # Second call: Should use cache because metadata exists
        sessions_2 = await agent.get_user_sessions("user1")
        assert len(sessions_2) == 1
        assert sessions_2[0]["title"] == "My Chat"
        assert not mock_exec.called

@pytest.mark.asyncio
async def test_delete_removes_metadata(agent):
    valid_uuid = "12345678-1234-1234-1234-123456789012"
    # Setup state with metadata
    agent.user_data["user1"] = {
        "sessions": [valid_uuid],
        "active_session": None,
        "session_metadata": {
            valid_uuid: {"original_title": "My Chat", "time": "now"}
        }
    }
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (b"", b"")
        mock_exec.return_value = process_mock
        
        # Execute delete
        result = await agent.delete_specific_session("user1", valid_uuid)
        
        assert result is True
        assert valid_uuid not in agent.user_data["user1"]["sessions"]
        assert valid_uuid not in agent.user_data["user1"]["session_metadata"]

@pytest.mark.asyncio
async def test_get_sessions_with_deleted_remote(agent):
    valid_uuid = "12345678-1234-1234-1234-123456789012"
    # Case: Session exists in local JSON but CLI doesn't return it (deleted remotely)
    agent.user_data["user1"] = {
        "sessions": [valid_uuid],
        "session_metadata": {} # Missing metadata triggers CLI call
    }
    
    # Mock CLI output EMPTY
    cli_output = ""
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (cli_output.encode(), b"")
        mock_exec.return_value = process_mock
        
        sessions = await agent.get_user_sessions("user1")
        
        # Should be empty list
        assert len(sessions) == 0
        
        # Should have removed it from local sessions list
        assert valid_uuid not in agent.user_data["user1"]["sessions"]

@pytest.mark.asyncio
async def test_legacy_data_auto_cache(agent):
    # Setup legacy state: sessions exist but session_metadata is MISSING (not just empty dict, but key missing)
    valid_uuid = "12345678-1234-1234-1234-123456789012"
    agent.user_data["user1"] = {
        "sessions": [valid_uuid]
        # "session_metadata" is intentionally omitted to simulate legacy data
    }

    # Mock CLI output
    cli_output = f"1. Legacy Chat (2 days ago) [{valid_uuid}]\n"
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (cli_output.encode(), b"")
        mock_exec.return_value = process_mock
        
        # This call should initialize session_metadata, fetch from CLI, and populate it
        sessions = await agent.get_user_sessions("user1")
        
        assert len(sessions) == 1
        assert sessions[0]["title"] == "Legacy Chat"
        
        # Verify metadata is now present and populated
        assert "session_metadata" in agent.user_data["user1"]
        assert valid_uuid in agent.user_data["user1"]["session_metadata"]
        assert agent.user_data["user1"]["session_metadata"][valid_uuid]["original_title"] == "Legacy Chat"