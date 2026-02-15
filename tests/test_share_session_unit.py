import os
import json
import pytest
import shutil
import tempfile
from app.services.llm_service import GeminiAgent
from app.services.user_manager import UserManager

@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)

@pytest.fixture
def agent(temp_dir):
    return GeminiAgent(working_dir=temp_dir)

@pytest.fixture
def user_manager(temp_dir):
    return UserManager(working_dir=temp_dir)

@pytest.mark.anyio
async def test_share_session_success(agent, user_manager, temp_dir):
    # Setup users
    user_manager.register_user("alice", "password")
    user_manager.register_user("bob", "password")
    
    session_id = "test-session-uuid"
    
    # Alice has a session
    agent.user_data["alice"] = {
        "sessions": [session_id],
        "active_session": session_id,
        "custom_titles": {session_id: "Alice's Chat"},
        "session_tags": {session_id: ["tag1"]},
        "session_tools": {session_id: ["tool1"]}
    }
    agent._save_user_data()
    
    # Share with Bob
    result = await agent.share_session("alice", session_id, "bob", user_manager)
    assert result is True
    
    # Verify Bob has it
    assert "bob" in agent.user_data
    assert session_id in agent.user_data["bob"]["sessions"]
    assert agent.user_data["bob"]["custom_titles"][session_id] == "Alice's Chat"
    assert agent.user_data["bob"]["session_tags"][session_id] == ["tag1"]
    assert agent.user_data["bob"]["session_tools"][session_id] == ["tool1"]

@pytest.mark.anyio
async def test_share_session_invalid_target_silent(agent, user_manager):
    # Setup user
    user_manager.register_user("alice", "password")
    
    session_id = "test-session-uuid"
    agent.user_data["alice"] = {"sessions": [session_id]}
    agent._save_user_data()
    
    # Share with non-existent user
    result = await agent.share_session("alice", session_id, "nonexistent", user_manager)
    assert result is False
    assert "nonexistent" not in agent.user_data

@pytest.mark.anyio
async def test_share_session_unauthorized(agent, user_manager):
    # Setup users
    user_manager.register_user("alice", "password")
    user_manager.register_user("bob", "password")
    
    session_id = "test-session-uuid"
    # Alice does NOT have the session
    agent.user_data["alice"] = {"sessions": []}
    agent._save_user_data()
    
    # Alice tries to share something she doesn't own
    result = await agent.share_session("alice", session_id, "bob", user_manager)
    assert result is False
    if "bob" in agent.user_data:
        assert session_id not in agent.user_data["bob"]["sessions"]

@pytest.mark.anyio
async def test_delete_shared_session_one_user_remains(agent, user_manager, mocker):
    # Setup users
    user_manager.register_user("alice", "password")
    user_manager.register_user("bob", "password")
    
    session_id = "shared-session-uuid"
    
    # Both users have the session
    agent.user_data["alice"] = {"sessions": [session_id]}
    agent.user_data["bob"] = {"sessions": [session_id]}
    agent._save_user_data()
    
    # Mock _create_subprocess to see if it's called
    mock_subprocess = mocker.patch.object(agent, '_create_subprocess', return_value=mocker.Mock())
    mock_subprocess.return_value.communicate = mocker.AsyncMock(return_value=(b"", b""))
    
    # Alice deletes the session
    result = await agent.delete_specific_session("alice", session_id)
    assert result is True
    
    # Alice should not have it, but Bob should
    assert session_id not in agent.user_data["alice"]["sessions"]
    assert session_id in agent.user_data["bob"]["sessions"]
    
    # gemini-cli --delete-session should NOT have been called because Bob still has it
    # We need to check the arguments.
    # Note: the current implementation deletes all related forks. 
    # For this test, let's assume no forks.
    delete_calls = [call for call in mock_subprocess.call_args_list if "--delete-session" in call.args[0]]
    assert len(delete_calls) == 0

@pytest.mark.anyio
async def test_delete_shared_session_last_user(agent, user_manager, mocker):
    # Setup users
    user_manager.register_user("alice", "password")
    
    session_id = "last-session-uuid"
    
    # Only Alice has the session
    agent.user_data["alice"] = {"sessions": [session_id]}
    agent._save_user_data()
    
    # Mock _create_subprocess
    mock_subprocess = mocker.patch.object(agent, '_create_subprocess', return_value=mocker.Mock())
    mock_subprocess.return_value.communicate = mocker.AsyncMock(return_value=(b"", b""))
    
    # Alice deletes the session
    result = await agent.delete_specific_session("alice", session_id)
    assert result is True
    
    # Alice should not have it
    assert session_id not in agent.user_data["alice"]["sessions"]
    
    # gemini-cli --delete-session SHOULD have been called
    delete_calls = [call for call in mock_subprocess.call_args_list if "--delete-session" in call.args[0]]
    assert len(delete_calls) > 0
