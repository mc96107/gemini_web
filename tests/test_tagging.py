import pytest
import os
import json
import shutil
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.llm_service import GeminiAgent

@pytest.fixture
def agent(tmp_path):
    working_dir = tmp_path / "work"
    working_dir.mkdir()
    agent = GeminiAgent(working_dir=str(working_dir))
    return agent

@pytest.mark.asyncio
async def test_tag_management(agent):
    user_id = "test_user"
    session_uuid = "12345678-1234-1234-1234-123456789012"
    
    # Setup user data
    agent.user_data[user_id] = {
        "active_session": session_uuid,
        "sessions": [session_uuid],
        "session_tools": {},
        "pending_tools": [],
        "pinned_sessions": []
    }
    
    # Mock subprocess for get_user_sessions
    mock_stdout = f" 1. Test Session (2026-01-18 07:00:00) [{session_uuid}]".encode()
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_stdout, b"")
        mock_exec.return_value = mock_proc
        
        # Test adding tags
        await agent.update_session_tags(user_id, session_uuid, ["work", "urgent"])
        sessions_data = await agent.get_user_sessions(user_id)
        all_sessions = sessions_data["pinned"] + sessions_data["history"]
        assert len(all_sessions) > 0
        target_session = next(s for s in all_sessions if s['uuid'] == session_uuid)
        assert "work" in target_session.get("tags", [])
        assert "urgent" in target_session.get("tags", [])
        
        # Test unique tags
        unique_tags = agent.get_unique_tags(user_id)
        assert set(unique_tags) == {"work", "urgent"}
        
        # Test removing tags
        await agent.update_session_tags(user_id, session_uuid, ["work"])
        sessions_data = await agent.get_user_sessions(user_id)
        all_sessions = sessions_data["pinned"] + sessions_data["history"]
        target_session = next(s for s in all_sessions if s['uuid'] == session_uuid)
        assert "work" in target_session.get("tags", [])
        assert "urgent" not in target_session.get("tags", [])

@pytest.mark.asyncio
async def test_tag_filtering(agent):
    user_id = "test_user"
    s1 = "11111111-1111-1111-1111-111111111111"
    s2 = "22222222-2222-2222-2222-222222222222"
    
    agent.user_data[user_id] = {
        "active_session": None,
        "sessions": [s1, s2],
        "session_tags": {
            s1: ["work"],
            s2: ["personal"]
        }
    }
    
    mock_stdout = (
        f" 1. S1 (2026-01-18 07:00:00) [{s1}]\n"
        f" 2. S2 (2026-01-18 07:01:00) [{s2}]"
    ).encode()
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_stdout, b"")
        mock_exec.return_value = mock_proc
        
        # Filter by 'work'
        sessions_data = await agent.get_user_sessions(user_id, tags=["work"])
        filtered = sessions_data["pinned"] + sessions_data["history"]
        assert len(filtered) == 1
        assert filtered[0]['uuid'] == s1
        
        # Filter by 'personal'
        sessions_data = await agent.get_user_sessions(user_id, tags=["personal"])
        filtered = sessions_data["pinned"] + sessions_data["history"]
        assert len(filtered) == 1
        assert filtered[0]['uuid'] == s2
        
        # Filter by both (none match both)
        sessions_data = await agent.get_user_sessions(user_id, tags=["work", "personal"])
        filtered = sessions_data["pinned"] + sessions_data["history"]
        assert len(filtered) == 0

        # Filter by multiple existing tags on one session
        agent.user_data[user_id]["session_tags"][s1] = ["work", "urgent"]
        sessions_data = await agent.get_user_sessions(user_id, tags=["work", "urgent"])
        filtered = sessions_data["pinned"] + sessions_data["history"]
        assert len(filtered) == 1
        assert filtered[0]['uuid'] == s1
        