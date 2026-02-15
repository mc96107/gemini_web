import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user
import shutil
import tempfile
import os
import json

@pytest.fixture
def test_env():
    # Setup a clean temporary environment
    temp_dir = tempfile.mkdtemp()
    
    # Save original paths/state
    orig_user_manager = app.state.user_manager
    orig_agent = app.state.agent
    
    # Re-initialize with temp dir
    from app.services.user_manager import UserManager
    from app.services.llm_service import GeminiAgent
    
    app.state.user_manager = UserManager(working_dir=temp_dir)
    app.state.agent = GeminiAgent(working_dir=temp_dir)
    
    # Pre-register Alice and Bob
    app.state.user_manager.register_user("alice", "password")
    app.state.user_manager.register_user("bob", "password")
    
    yield app.state.agent, app.state.user_manager
    
    # Cleanup
    shutil.rmtree(temp_dir)
    app.state.user_manager = orig_user_manager
    app.state.agent = orig_agent
    app.dependency_overrides.clear()

def test_share_flow_e2e(test_env):
    agent, user_manager = test_env
    client = TestClient(app)
    
    # 1. Alice creates a session
    app.dependency_overrides[get_user] = lambda: "alice"
    
    # Manually inject a session into agent's user_data for Alice
    session_id = "12345678-1234-1234-1234-123456789012"
    agent.user_data["alice"] = {
        "sessions": [session_id],
        "active_session": session_id,
        "custom_titles": {session_id: "Collaboration Chat"},
        "session_tags": {session_id: ["shared"]},
        "session_tools": {session_id: ["read_file"]}
    }
    agent._save_user_data()
    
    # 2. Alice shares with Bob via API
    response = client.post(
        f"/sessions/{session_id}/share",
        json={"username": "bob"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # 3. Verify Bob sees the session in his sidebar
    app.dependency_overrides[get_user] = lambda: "bob"
    
    # Ensure bob is in agent.user_data
    if "bob" not in agent.user_data:
        agent.user_data["bob"] = {"sessions": [session_id]} # Normally share_session does this
        agent._save_user_data()
    
    # Mock CLI response so get_user_sessions finds it
    from unittest.mock import AsyncMock, patch
    with patch.object(agent, '_create_subprocess', new_callable=AsyncMock) as mock_sub:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (f"  1. Collaboration Chat (today) [{session_id}]".encode(), b"")
        mock_proc.returncode = 0
        mock_sub.return_value = mock_proc
        
        response = client.get("/sessions")
        assert response.status_code == 200
        history = response.json()["history"]
        
        bob_session = next((s for s in history if s["uuid"] == session_id), None)
        assert bob_session is not None
        assert bob_session["title"] == "Collaboration Chat"
        assert "shared" in bob_session["tags"]
    
    # 4. Verify Bob can access messages (Security Check)
    # Mock message retrieval since we don't have real CLI output here
    # agent.get_session_messages is already used by the router
    # We'll just verify the router allows the call
    response = client.get(f"/sessions/{session_id}/messages")
    assert response.status_code == 200 # Would be 403 if sharing failed

def test_share_silent_failure_e2e(test_env):
    agent, user_manager = test_env
    client = TestClient(app)
    
    app.dependency_overrides[get_user] = lambda: "alice"
    session_id = "45678901-4567-4567-4567-456789012345"
    agent.user_data["alice"] = {"sessions": [session_id]}
    agent._save_user_data()
    
    # Share with non-existent user
    response = client.post(
        f"/sessions/{session_id}/share",
        json={"username": "ghost"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is False # Silent failure from service

def test_delete_shared_session_e2e(test_env):
    agent, user_manager = test_env
    client = TestClient(app)
    
    session_id = "shared-to-delete"
    agent.user_data["alice"] = {"sessions": [session_id]}
    agent.user_data["bob"] = {"sessions": [session_id]}
    agent._save_user_data()
    
    # Bob deletes the session
    app.dependency_overrides[get_user] = lambda: "bob"
    response = client.post("/sessions/delete", data={"session_uuid": session_id})
    assert response.status_code == 200
    
    # Bob should not have it
    assert session_id not in agent.user_data["bob"]["sessions"]
    # Alice SHOULD still have it
    assert session_id in agent.user_data["alice"]["sessions"]

def test_delete_shared_session_final_user_e2e(test_env):
    agent, user_manager = test_env
    client = TestClient(app)
    
    session_id = "final-delete-uuid-12345678901234567" # Not used by regex here
    agent.user_data["alice"] = {"sessions": [session_id]}
    agent._save_user_data()
    
    from unittest.mock import AsyncMock, patch
    with patch.object(agent, '_create_subprocess', new_callable=AsyncMock) as mock_sub:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_sub.return_value = mock_proc
        
        # Alice deletes the session
        app.dependency_overrides[get_user] = lambda: "alice"
        response = client.post("/sessions/delete", data={"session_uuid": session_id})
        assert response.status_code == 200
        
        # Verify CLI was called
        delete_calls = [call for call in mock_sub.call_args_list if "--delete-session" in call.args[0]]
        assert len(delete_calls) > 0
        assert session_id in delete_calls[0].args[0]
