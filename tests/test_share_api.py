import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user
import json

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.anyio
async def test_share_api_success(client, mocker):
    # Mock authentication
    app.dependency_overrides[get_user] = lambda: "alice"
    
    # Mock agent and user_manager
    mock_agent = mocker.Mock()
    mock_user_manager = mocker.Mock()
    app.state.agent = mock_agent
    app.state.user_manager = mock_user_manager
    
    session_uuid = "test-session-uuid"
    target_user = "bob"
    
    # Configure mocks
    mock_agent.is_user_session.return_value = True
    mock_agent.share_session = mocker.AsyncMock(return_value=True)
    
    response = client.post(
        f"/sessions/{session_uuid}/share",
        json={"username": target_user}
    )
    
    assert response.status_code == 200
    assert response.json() == {"success": True}
    
    mock_agent.is_user_session.assert_called_with("alice", session_uuid)
    mock_agent.share_session.assert_called_with("alice", session_uuid, target_user, mock_user_manager)
    
    # Cleanup
    app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_share_api_unauthorized(client, mocker):
    app.dependency_overrides[get_user] = lambda: "alice"
    
    mock_agent = mocker.Mock()
    app.state.agent = mock_agent
    
    session_uuid = "test-session-uuid"
    mock_agent.is_user_session.return_value = False
    
    response = client.post(
        f"/sessions/{session_uuid}/share",
        json={"username": "bob"}
    )
    
    assert response.status_code == 403
    
    app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_share_api_no_username(client, mocker):
    app.dependency_overrides[get_user] = lambda: "alice"
    
    mock_agent = mocker.Mock()
    app.state.agent = mock_agent
    mock_agent.is_user_session.return_value = True
    
    response = client.post(
        f"/sessions/some-uuid/share",
        json={}
    )
    
    assert response.status_code == 400
    
    app.dependency_overrides.clear()
